# libusb DLL Installation Guide

## Current Status
- WinUSB driver: Installed on oscilloscope ✓
- PyUSB: Installed ✓
- libusb DLL: **NOT INSTALLED** (needed by PyUSB)

## The Issue
PyUSB needs libusb-1.0.dll to communicate with USB devices on Windows. Without it, PyVISA-py cannot see USB devices.

## Quick Solution: Manual libusb Installation

### Step 1: Download libusb

Visit: https://github.com/libusb/libusb/releases/latest

Download: `libusb-1.0.XX.7z` (the smaller file, not the binaries)

### Step 2: Extract the Archive

You'll need 7-Zip to extract .7z files:
- If you don't have it: Download from https://www.7-zip.org/
- Extract the libusb-1.0.XX.7z file

### Step 3: Copy the DLL

After extraction, navigate to:
- For 64-bit Python: `VS2019\MS64\dll\libusb-1.0.dll`
- For 32-bit Python: `VS2019\MS32\dll\libusb-1.0.dll`

You have Python 64-bit, so use **MS64**.

Copy `libusb-1.0.dll` to one of these locations:

**Option A (Easiest):**
```
C:\Users\andre\Claude\
```
(Same directory as your Python scripts)

**Option B (System-wide, requires admin):**
```
C:\Windows\System32\
```

### Step 4: Verify Installation

Run:
```bash
python check_usb_devices.py
```

You should now see:
- PyUSB backend found
- Your Rigol device listed (Vendor ID: 0x1AB1)

### Step 5: Test Connection

Run:
```bash
python test_scope_connection.py
```

Should now successfully connect to your oscilloscope!

## Alternative: Use NI-VISA Instead (Easier but larger download)

If you don't want to deal with libusb:

1. Download NI-VISA Runtime (free) from:
   https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html

2. Install NI-VISA Runtime

3. Modify `test_scope_connection.py` to use NI-VISA backend:
   - Change: `rm = pyvisa.ResourceManager('@py')`
   - To: `rm = pyvisa.ResourceManager()`  (uses NI-VISA by default)

4. Run `python test_scope_connection.py`

NI-VISA includes all necessary drivers and works well with oscilloscopes.

## Troubleshooting

- **"No backend available"** = libusb-1.0.dll not found in PATH
- **"No USB devices found"** = WinUSB driver not installed correctly (re-run Zadig)
- **Python crashes** = Wrong DLL architecture (32-bit vs 64-bit mismatch)
