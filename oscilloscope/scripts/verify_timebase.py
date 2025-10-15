#!/usr/bin/env python3
"""
Verify that timebase changes are actually applied to the scope
"""

import sys
import os
import time

def connect_scope():
    """Connect to oscilloscope"""
    dll_path = os.path.join(os.path.dirname(__file__), "..", "lib", "libusb-1.0.dll")
    os.environ['PATH'] = os.path.dirname(dll_path) + os.pathsep + os.environ.get('PATH', '')

    import pyvisa
    rm = pyvisa.ResourceManager('@py')
    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        return None

    scope = rm.open_resource(usb_resources[0])
    scope.timeout = 2000
    return scope

def main():
    print("Timebase Verification Test")
    print("="*70)
    print("Watch your oscilloscope screen - the timebase should change!")
    print("="*70)

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect to oscilloscope")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}\n")

    # Read current timebase
    current = scope.query(':TIMebase:MAIN:SCALe?').strip()
    print(f"Current timebase: {float(current)*1e6:.1f} us/div\n")

    # Test different timebases with delays to see changes
    timebases = [
        (100e-9, "100ns"),
        (1e-6, "1us"),
        (10e-6, "10us"),
        (100e-6, "100us"),
        (1e-3, "1ms"),
        (10e-3, "10ms"),
        (100e-3, "100ms"),
    ]

    for timebase_sec, name in timebases:
        print(f"\nSetting timebase to {name}/div...")

        # Set the timebase
        scope.write(f':TIMebase:MAIN:SCALe {timebase_sec}')

        # Wait for scope to process
        time.sleep(0.5)

        # Read back to verify
        readback = scope.query(':TIMebase:MAIN:SCALe?').strip()
        readback_val = float(readback)

        print(f"  Sent: {timebase_sec:.9f} seconds/div")
        print(f"  Read back: {readback_val:.9f} seconds/div ({readback_val*1e6:.3f} us/div)")

        if abs(readback_val - timebase_sec) < 1e-12:
            print(f"  [OK] VERIFIED - Check your scope screen now!")
        else:
            print(f"  [ERROR] MISMATCH - Scope returned different value!")

        # Pause so user can see the change
        print(f"  Waiting 3 seconds for you to verify on screen...")
        time.sleep(3)

    # Restore original
    print(f"\nRestoring original timebase...")
    scope.write(f':TIMebase:MAIN:SCALe {current}')
    time.sleep(0.5)
    final = scope.query(':TIMebase:MAIN:SCALe?').strip()
    print(f"Restored to: {float(final)*1e6:.1f} us/div")

    scope.close()
    print("\nTest complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
