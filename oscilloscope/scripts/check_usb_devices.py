#!/usr/bin/env python3
"""
Script to check for USB devices and diagnose connection issues
"""

import sys

def check_pyusb():
    """Check PyUSB and list USB devices"""
    print("Checking PyUSB...")
    try:
        import usb.core
        import usb.util

        print("[OK] PyUSB is installed")

        # Find all USB devices
        devices = usb.core.find(find_all=True)
        device_list = list(devices)

        if device_list:
            print(f"\nFound {len(device_list)} USB device(s):")
            for dev in device_list:
                print(f"\n  Device:")
                print(f"    Vendor ID:  0x{dev.idVendor:04x}")
                print(f"    Product ID: 0x{dev.idProduct:04x}")
                try:
                    manufacturer = usb.util.get_string(dev, dev.iManufacturer)
                    product = usb.util.get_string(dev, dev.iProduct)
                    print(f"    Manufacturer: {manufacturer}")
                    print(f"    Product: {product}")
                except:
                    print(f"    (Could not read string descriptors)")

                # Check if it's a Rigol device (vendor ID 0x1AB1)
                if dev.idVendor == 0x1AB1:
                    print(f"    >>> This is a RIGOL device! <<<")

        else:
            print("\nNo USB devices found.")
            print("This might mean:")
            print("  - No USB devices are connected")
            print("  - libusb backend is not installed/working")
            print("  - Insufficient permissions to access USB devices")

    except ImportError:
        print("[FAILED] PyUSB is not installed")
        print("Install with: pip install pyusb")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        print("\nOn Windows, PyUSB requires a libusb backend:")
        print("  1. Download libusb from: https://libusb.info/")
        print("  2. Or use Zadig to install WinUSB driver for your device")
        print("     Download Zadig from: https://zadig.akeo.ie/")
        return False

    return True

def check_pyvisa():
    """Check PyVISA resources"""
    print("\n" + "="*60)
    print("Checking PyVISA...")
    try:
        import pyvisa
        rm = pyvisa.ResourceManager('@py')

        print(f"[OK] PyVISA is installed")
        print(f"Backend: {rm}")

        resources = rm.list_resources()
        if resources:
            print(f"\nFound {len(resources)} VISA resource(s):")
            for res in resources:
                print(f"  - {res}")
        else:
            print("\nNo VISA resources found")

    except ImportError:
        print("[FAILED] PyVISA is not installed")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

    return True

def main():
    print("USB Device Diagnostic Tool")
    print("="*60)

    pyusb_ok = check_pyusb()
    pyvisa_ok = check_pyvisa()

    print("\n" + "="*60)
    print("Summary:")
    if pyusb_ok and pyvisa_ok:
        print("  All checks passed!")
        print("\nIf you still can't connect to the oscilloscope:")
        print("  1. Make sure it's powered on and USB cable is connected")
        print("  2. On Windows, you may need to install WinUSB driver using Zadig")
        print("     - Download Zadig: https://zadig.akeo.ie/")
        print("     - Run Zadig, select your Rigol device, choose WinUSB driver")
        print("  3. Try unplugging and replugging the USB cable")
    else:
        print("  Some checks failed - see errors above")

if __name__ == "__main__":
    main()
