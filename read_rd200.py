import sys
import os
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_components/rd200_ble'))

import asyncio
import bleak
import logging

import rd200_ble

rd200mac = "EC:00:8F:5B:0C:89"

### Scanning works...
#ble_device = None
#devices = asyncio.run(bleak.BleakScanner.discover())
#for d in devices:
#    if d.address == rd200mac:
#        ble_device = d
#print(ble_device)

### Discover by MAC
ble_device = asyncio.run(bleak.BleakScanner.find_device_by_address(rd200mac))

### Read Data
rd200 = rd200_ble.RD200BluetoothDeviceData(logging, is_metric=False)
data = asyncio.run(rd200.update_device(ble_device=ble_device))
print(data)
