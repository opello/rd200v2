#!/home/pi/venv-ble/bin/python

import sys
import os
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../custom_components/rd200_ble'))

import daemon

import asyncio
import bleak
import logging

import rd200_ble
import influxdb
import datetime
import time

import traceback
import threading

RD200_MAC = "EC:00:8F:5B:0C:89"
INFLUXDB_HOST = "127.0.0.1"
INFLUXDB_PORT = 8086
INFLUXDB_USER = "radon"
INFLUXDB_PASS = "radon"
INFLUXDB_DB = "radon"

_bleak_scanner = None
_bleak_loop = None
_bleak_thread = None
_bleak_thread_ready = threading.Event()

def _setup_bleak():
    global _bleak_thread
    global _bleak_thread_ready

    _bleak_thread = threading.Thread(target=_run_bleak_loop, daemon=True)
    _bleak_thread.start()
    _bleak_thread_ready.wait()

def _run_bleak_loop():
    global _bleak_loop
    global _bleak_thread_ready

    _bleak_loop = asyncio.new_event_loop()
    _bleak_thread_ready.set()
    _bleak_loop.run_forever()

def _get_radon_data(mac_address):
    global _bleak_scanner
    global _bleak_loop

    if not _bleak_scanner:
        _bleak_scanner = bleak.BleakScanner(loop=_bleak_loop)

    # Discover by MAC
    #ble_device = asyncio.run(bleak.BleakScanner.find_device_by_address(mac_address))
    future = asyncio.run_coroutine_threadsafe(_bleak_scanner.find_device_by_address(mac_address), _bleak_loop)
    ble_device = future.result()

    # Read Data
    rd200 = rd200_ble.RD200BluetoothDeviceData(logging, is_metric=False)
    #data = asyncio.run(rd200.update_device(ble_device=ble_device))
    future = asyncio.run_coroutine_threadsafe(rd200.update_device(ble_device=ble_device), _bleak_loop)
    data = future.result()

    return data

def _write_data_to_influx(host, port, username, password, db, data):
    now = datetime.datetime.now(datetime.timezone.utc)
    point = {
        "time": now.isoformat(timespec="seconds"),
        "measurement": "radon",
        "tags": {
            "name": data.name,
            "address": data.address,
            },
        "fields": {
            "radon_pCipL": data.sensors["radon"],
            "radon_1day_level_pCipL": data.sensors["radon_1day_level"],
            "radon_1month_level_pCipL": data.sensors["radon_1month_level"],
            "radon_peak_pCipL": data.sensors["radon_peak"],
            "radon_uptime_s": data.sensors["radon_uptime"],
            },
        }
    client = influxdb.InfluxDBClient(host=host, port=port, username=username, password=password, database=db)
    client.write_points(points=[point], time_precision="s")

def main():
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    _setup_bleak()

    starttime = time.monotonic()
    while True:
        logging.info("main: top of loop")
        try:
            data = _get_radon_data(RD200_MAC)
            logging.info("main: got data")
            _write_data_to_influx(INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_USER, INFLUXDB_PASS, INFLUXDB_DB, data)
            logging.info("main: wrote data")
        except:
            logging.error("Exception:", exc_info=1)
            pass

        # This may be a silly optimization, but it makes the delay between loop
        # iterations be even counts of 60 seconds.  Mainly avoiding the drift
        # that can occur when the iteration takes longer than expected.
        #
        # Ref: https://stackoverflow.com/a/25251804/
        time.sleep(60.0 - ((time.monotonic() - starttime) % 60.0))
        #time.sleep(1.0 - ((time.monotonic() - starttime) % 1.0))

def run():
    with daemon.DaemonContext():
        main()

if __name__ == "__main__":
    main()
