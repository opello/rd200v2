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

RD200_MAC = "EC:00:8F:5B:0C:89"
INFLUXDB_HOST = "127.0.0.1"
INFLUXDB_PORT = 8086
INFLUXDB_USER = "radon"
INFLUXDB_PASS = "radon"
INFLUXDB_DB = "radon"

def _get_radon_data(mac_address):
    # Discover by MAC
    ble_device = asyncio.run(bleak.BleakScanner.find_device_by_address(mac_address))

    # Read Data
    rd200 = rd200_ble.RD200BluetoothDeviceData(logging, is_metric=False)
    data = asyncio.run(rd200.update_device(ble_device=ble_device))

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
    starttime = time.monotonic()
    while True:
        data = _get_radon_data(RD200_MAC)
        _write_data_to_influx(INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_USER, INFLUXDB_PASS, INFLUXDB_DB, data)

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
    run()
