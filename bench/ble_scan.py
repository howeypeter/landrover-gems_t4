"""Dump the BLE services/characteristics of the gems-pico adapter.

Run:  python C:\\Users\\howey\\ble_scan.py
Tells us whether the Nordic UART Service (6e400001/2/3) is actually exposed,
which distinguishes a Windows GATT-cache problem from a firmware problem.
"""
import asyncio

from bleak import BleakClient, BleakScanner

NAME = "gems-pico"
NUS = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"


async def main() -> None:
    print(f"scanning for {NAME!r} (tolerating a truncated advertised name) ...")
    t = NAME.lower()
    dev = None
    seen = await BleakScanner.discover(timeout=10.0)
    for d in seen:
        n = (d.name or "").lower()
        if n and (n == t or n.startswith(t) or t.startswith(n)):
            dev = d
            break
    if dev is None:
        print("  NOT FOUND. Devices with names seen this scan:")
        for d in seen:
            if d.name:
                print(f"    {d.name}  [{d.address}]")
        return
    print(f"  found: {dev.name}  [{dev.address}]")
    print("connecting ...")
    async with BleakClient(dev) as c:
        print(f"  connected = {c.is_connected}")
        found_nus = False
        for s in c.services:
            print(f"SERVICE {s.uuid}")
            if s.uuid.lower() == NUS:
                found_nus = True
            for ch in s.characteristics:
                print(f"    char {ch.uuid}  {ch.properties}")
        print()
        print("Nordic UART Service present:", found_nus)
        if not found_nus:
            print("  -> Windows is serving a STALE/cached service list, or this")
            print("     'gems-pico' isn't the BLE firmware. Remove the device in")
            print("     Windows Bluetooth (pnputil /remove-device), toggle BT, retry.")


asyncio.run(main())
