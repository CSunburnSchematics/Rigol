#!/usr/bin/env python3
"""
Connect to DS1054Z oscilloscope and use SCPI commands
"""

import sys
import os

def connect_oscilloscope():
    """Connect to the oscilloscope using ds1054z library"""
    print("DS1054Z Oscilloscope Connection")
    print("=" * 60)

    try:
        # Set up libusb backend path
        dll_path = os.path.join(os.getcwd(), "libusb-1.0.dll")
        os.environ['PATH'] = os.getcwd() + os.pathsep + os.environ.get('PATH', '')

        from ds1054z import DS1054Z
        import usb.backend.libusb1

        # Get backend with explicit DLL path
        backend = usb.backend.libusb1.get_backend(find_library=lambda x: dll_path)

        if not backend:
            print("[ERROR] Could not load libusb backend")
            return None

        print(f"[OK] libusb backend loaded")

        # The ds1054z library will try USB resources
        # Find the Rigol device using PyUSB first
        import usb.core

        print("\nSearching for Rigol oscilloscope...")
        dev = usb.core.find(idVendor=0x1AB1, idProduct=0x04CE, backend=backend)

        if dev is None:
            print("[ERROR] Rigol DS1054Z not found")
            print("Make sure:")
            print("  1. Oscilloscope is powered on")
            print("  2. USB cable is connected")
            print("  3. WinUSB driver is installed (via Zadig)")
            return None

        print(f"[OK] Found Rigol device: VID=0x{dev.idVendor:04x}, PID=0x{dev.idProduct:04x}")

        # Now try to connect with ds1054z library
        # Try different resource string formats
        resource_strings = [
            f'USB0::0x{dev.idVendor:04X}::0x{dev.idProduct:04X}::INSTR',
            f'USB0::{dev.idVendor}::{dev.idProduct}::INSTR',
            'USB0::0x1AB1::0x04CE::INSTR',
        ]

        scope = None
        for resource in resource_strings:
            try:
                print(f"\nTrying to connect with: {resource}")
                scope = DS1054Z(resource)
                print(f"[SUCCESS] Connected via {resource}")
                break
            except Exception as e:
                print(f"  Failed: {e}")
                continue

        if not scope:
            print("\n[ERROR] Could not connect using ds1054z library")
            print("Falling back to direct PyVISA connection...")

            # Try direct PyVISA with explicit backend
            import pyvisa

            # Patch PyVISA-py to use our backend
            os.environ['PYVISA_LIBRARY'] = '@py'

            rm = pyvisa.ResourceManager('@py')

            # Try to find USB resources
            print("\nAvailable resources:")
            resources = rm.list_resources()
            for res in resources:
                print(f"  - {res}")

            # Find the USB resource with Rigol device
            usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

            if not usb_resources:
                print("[ERROR] No USB resources found")
                return None

            resource_str = usb_resources[0]
            print(f"\nAttempting direct SCPI connection to: {resource_str}")

            try:
                inst = rm.open_resource(resource_str)
                inst.timeout = 5000

                idn = inst.query('*IDN?').strip()
                print(f"\n[SUCCESS] Connected via PyVISA!")
                print(f"Identification: {idn}")

                return inst

            except Exception as e:
                print(f"[ERROR] PyVISA connection failed: {e}")
                return None

        # If we got here, ds1054z connection worked
        print(f"\n{'=' * 60}")
        print("Scope Information:")
        print(f"  IDN: {scope.idn}")

        try:
            print(f"  Model: {scope.model_name}")
        except:
            pass

        # Test some queries
        print(f"\nChannel Status:")
        for i in range(1, 5):
            try:
                displayed = scope.get_channel_display(i)
                print(f"  Channel {i}: {'ON' if displayed else 'OFF'}")
            except Exception as e:
                print(f"  Channel {i}: Unable to query")

        return scope

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    scope = connect_oscilloscope()

    if scope:
        print(f"\n{'=' * 60}")
        print("[OK] Oscilloscope is ready!")
        print("\nYou can now use the 'scope' object to control it.")
        print("\nExample commands:")
        print("  scope.get_waveform_samples(1)  # Get channel 1 waveform")
        print("  scope.get_screenshot()         # Capture screenshot")
        print("\nClosing connection...")
        try:
            scope.close()
        except:
            pass
        return 0
    else:
        print("\n[FAILED] Could not connect to oscilloscope")
        return 1

if __name__ == "__main__":
    sys.exit(main())
