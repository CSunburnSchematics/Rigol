#!/usr/bin/env python3
"""
Test libusb backend detection
"""

import os
import sys

print("libusb Backend Detection Test")
print("=" * 60)

# Check current directory
print(f"\nCurrent directory: {os.getcwd()}")
print(f"libusb-1.0.dll exists: {os.path.exists('libusb-1.0.dll')}")

# Try to import and get backend
try:
    import usb.core
    import usb.backend.libusb1

    print("\nPyUSB modules imported successfully")

    # Try to get backend with explicit path
    backend = usb.backend.libusb1.get_backend(find_library=lambda x: "libusb-1.0.dll")

    if backend:
        print(f"[OK] Backend found: {backend}")
        print(f"Backend library: {backend.lib}")
    else:
        print("[FAILED] Backend is None")

        # Try to find the library manually
        print("\nTrying manual backend load...")
        dll_path = os.path.join(os.getcwd(), "libusb-1.0.dll")
        print(f"DLL path: {dll_path}")

        backend = usb.backend.libusb1.get_backend(find_library=lambda x: dll_path)

        if backend:
            print(f"[OK] Manual backend found: {backend}")
        else:
            print("[FAILED] Manual backend also failed")

    # Try to list USB devices
    if backend:
        print("\nScanning for USB devices...")
        devices = list(usb.core.find(find_all=True, backend=backend))

        if devices:
            print(f"\nFound {len(devices)} USB device(s):")
            for dev in devices:
                print(f"\n  Device:")
                print(f"    Vendor ID:  0x{dev.idVendor:04x}")
                print(f"    Product ID: 0x{dev.idProduct:04x}")

                # Check if it's a Rigol device
                if dev.idVendor == 0x1AB1:
                    print(f"    >>> RIGOL OSCILLOSCOPE FOUND! <<<")
        else:
            print("\nNo USB devices found")

except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
