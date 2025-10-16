#!/usr/bin/env python3
"""
List all Nice Power supplies detected on COM ports
Useful for diagnosing COM port changes
"""

import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from nice_power_usb_locator import NicePowerLocator

def main():
    print("="*70)
    print("NICE POWER SUPPLY DETECTOR")
    print("="*70)
    print("\nScanning all COM ports for Nice Power supplies...\n")

    locator = NicePowerLocator(verbose=True)
    locator.refresh()

    supplies = locator.get_power_supplies()

    print("\n" + "="*70)
    print(f"FOUND {len(supplies)} NICE POWER SUPPLY(S)")
    print("="*70)

    if len(supplies) > 0:
        for i, (com_port, device_type, addr, psu) in enumerate(supplies, 1):
            print(f"\n[{i}] Nice Power Supply:")
            print(f"    COM Port: {com_port}")
            print(f"    Type: {device_type}")
            print(f"    Address: {addr}")

            # Try to read voltage
            try:
                v = psu.measure_voltage()
                i_meas = psu.measure_current()
                print(f"    Current Reading: {v:.2f}V / {i_meas:.3f}A")
            except Exception as e:
                print(f"    Current Reading: Failed ({e})")
    else:
        print("\nNo Nice Power supplies detected!")
        print("Check:")
        print("  - USB connections")
        print("  - Drivers installed")
        print("  - Power supplies are on")

    print("\n" + "="*70)

    return 0

if __name__ == "__main__":
    sys.exit(main())
