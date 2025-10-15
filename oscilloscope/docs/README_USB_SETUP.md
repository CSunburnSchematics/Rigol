# DS1054Z USB Connection Setup Guide (Windows)

## Current Status
- Python 3.12.10: Installed
- ds1054z library: Installed (v0.4.0)
- PyVISA: Installed
- PyVISA-py: Installed
- PyUSB: Installed

## The Problem
PyUSB requires a libusb backend on Windows to access USB devices. Currently, no backend is available.

## Solutions (Pick ONE)

### Option 1: Install Zadig and WinUSB Driver (Recommended - Free & Easy)

This is the easiest free solution:

1. **Download Zadig**
   - Go to: https://zadig.akeo.ie/
   - Download the latest version

2. **Install WinUSB Driver**
   - Connect your DS1054Z oscilloscope via USB
   - Run Zadig as Administrator
   - In Zadig:
     - Go to Options > List All Devices
     - Select your Rigol oscilloscope from the dropdown
     - Choose "WinUSB" as the target driver
     - Click "Replace Driver" or "Install Driver"

3. **Verify Installation**
   - Run: `python check_usb_devices.py`
   - You should now see the Rigol device (Vendor ID: 0x1AB1)

4. **Test Connection**
   - Run: `python test_scope_connection.py`

**Note**: Installing WinUSB will replace the default driver. If you need the original driver back, you can reinstall it through Device Manager.

### Option 2: Install NI-VISA (Commercial but Robust)

National Instruments provides a free runtime version:

1. Download from: https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html
2. Install NI-VISA Runtime
3. Modify the Python script to use NI-VISA backend instead of '@py'
4. Change: `rm = pyvisa.ResourceManager('@py')` to `rm = pyvisa.ResourceManager()`

### Option 3: Use Network Connection Instead

If you don't want to install drivers, you can connect via Ethernet:

1. Connect oscilloscope to network
2. Find its IP address (on scope: Utility > I/O > LAN Config)
3. Use IP address instead of USB:
   ```python
   scope = DS1054Z('TCPIP::192.168.1.100::INSTR')
   ```

## Verification Steps

After installing drivers:

1. Check USB devices are visible:
   ```bash
   python check_usb_devices.py
   ```

2. Test oscilloscope connection:
   ```bash
   python test_scope_connection.py
   ```

## Troubleshooting

- **No devices found**: Make sure oscilloscope is powered on and USB cable is connected
- **Driver installation fails**: Run Zadig as Administrator
- **Wrong device selected**: In Zadig, make sure you select the Rigol device (might show as "DSO-X XXXX" or similar)
- **PyUSB still shows no backend**: Restart your terminal/command prompt after installing Zadig

## Next Steps

Once connected, you can use the ds1054z library to:
- Capture waveforms
- Take screenshots
- Configure channels
- Read measurements
- And much more!

See: https://github.com/pklaus/ds1054z for full documentation.
