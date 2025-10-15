#!/usr/bin/env python3
"""
Test script to connect to DS1054Z oscilloscope over USB
"""

import sys
import pyvisa

def list_resources():
    """List all available VISA resources"""
    print("Scanning for available VISA devices...")
    try:
        rm = pyvisa.ResourceManager('@py')
        resources = rm.list_resources()

        if resources:
            print(f"\nFound {len(resources)} device(s):")
            for i, resource in enumerate(resources, 1):
                print(f"  {i}. {resource}")
            return resources
        else:
            print("\nNo VISA devices found.")
            return []
    except Exception as e:
        print(f"Error scanning for devices: {e}")
        return []

def connect_to_scope(resource_name=None):
    """Connect to the oscilloscope"""
    from ds1054z import DS1054Z

    try:
        # If no resource name provided, try to find Rigol device
        if not resource_name:
            rm = pyvisa.ResourceManager('@py')
            resources = rm.list_resources()

            # Look for Rigol devices (vendor ID 0x1AB1)
            rigol_devices = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or 'RIGOL' in r.upper())]

            if rigol_devices:
                resource_name = rigol_devices[0]
                print(f"\nAuto-detected Rigol device: {resource_name}")
            else:
                print("\nNo Rigol device auto-detected. Trying common resource strings...")
                # Try common variations
                for attempt in ['USB0::0x1AB1::0x04CE::INSTR', 'USB0::6833::1230::INSTR']:
                    try:
                        print(f"  Trying: {attempt}")
                        scope = DS1054Z(attempt)
                        print(f"  Success with: {attempt}")
                        resource_name = attempt
                        break
                    except:
                        continue

                if not resource_name:
                    print("\nCould not find oscilloscope. Please specify the resource name.")
                    return None

        print(f"\nConnecting to: {resource_name}")
        scope = DS1054Z(resource_name)

        # Query the scope to verify connection
        print("\n[SUCCESS] Connection established!")
        print(f"Scope ID: {scope.idn}")

        # Get some basic info
        print(f"\nScope Information:")
        print(f"  Model: {scope.model_name}")

        # Check available channels
        print(f"\nChannel Status:")
        for i in range(1, 5):
            try:
                displayed = scope.get_channel_display(i)
                print(f"  Channel {i}: {'ON' if displayed else 'OFF'}")
            except Exception as e:
                print(f"  Channel {i}: Unable to query - {e}")

        return scope

    except Exception as e:
        print(f"\n[FAILED] Connection error: {e}")
        print("\nTroubleshooting tips:")
        print("  1. Ensure the oscilloscope is powered on")
        print("  2. Check that the USB cable is properly connected")
        print("  3. On Windows, you may need USB drivers:")
        print("     - Install NI-VISA from National Instruments, OR")
        print("     - Use Zadig to install WinUSB driver for the oscilloscope")
        print("  4. Try running: python -m pyvisa info")
        return None

def main():
    print("DS1054Z Oscilloscope USB Connection Test")
    print("=" * 50)

    # First, list all available resources
    resources = list_resources()

    print("\n" + "=" * 50)

    # Try to connect
    scope = connect_to_scope()

    if scope:
        print("\n[OK] Oscilloscope connection test successful!")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
