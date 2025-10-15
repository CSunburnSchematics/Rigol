#!/usr/bin/env python3
"""
Download and setup libusb DLL for PyUSB
"""

import urllib.request
import zipfile
import os
import sys
import shutil
import platform

def download_libusb():
    """Download and extract libusb DLL"""

    # Determine architecture
    is_64bit = platform.machine().endswith('64')
    arch = "x64" if is_64bit else "x86"

    print(f"Detected {arch} architecture")
    print("Downloading libusb binaries...")

    # GitHub releases URL for libusb
    url = "https://github.com/libusb/libusb/releases/download/v1.0.27/libusb-1.0.27.7z"

    # Alternative: Try to get it from SourceForge
    alt_url = "https://sourceforge.net/projects/libusb/files/libusb-1.0/libusb-1.0.27/libusb-1.0.27-binaries.7z/download"

    print("Note: This downloads a .7z file which requires 7-zip to extract.")
    print("\nAlternative approach:")
    print("1. Visit: https://github.com/libusb/libusb/releases/latest")
    print("2. Download: libusb-X.X.XX.7z")
    print("3. Extract the archive")
    print(f"4. Copy the DLL from VS2019/MS64/dll/libusb-1.0.dll (for {arch})")
    print("5. Place it in one of these locations:")
    print(f"   - C:\\Windows\\System32 (requires admin)")
    print(f"   - Current directory: {os.getcwd()}")
    print(f"   - Python installation directory")

    return False

def check_libusb():
    """Check if libusb can be found"""
    try:
        import usb.core
        import usb.backend.libusb1

        backend = usb.backend.libusb1.get_backend()
        if backend is None:
            print("[FAILED] libusb backend not found")
            return False
        else:
            print(f"[OK] libusb backend found: {backend}")
            return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    print("libusb Setup Tool")
    print("=" * 60)

    if check_libusb():
        print("\nlibusb is already working!")
        return 0

    print("\nlibusb backend not found. Manual installation required:")
    download_libusb()

    print("\n" + "=" * 60)
    print("After placing libusb-1.0.dll, run this script again to verify.")

    return 1

if __name__ == "__main__":
    sys.exit(main())
