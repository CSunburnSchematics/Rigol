#!/usr/bin/env python3
"""Debug oscilloscope state and trigger settings"""

import os
import sys
import time

dll_path = os.path.join(os.path.dirname(__file__), "..", "lib", "libusb-1.0.dll")
os.environ['PATH'] = os.path.dirname(dll_path) + os.pathsep + os.environ.get('PATH', '')

import pyvisa

rm = pyvisa.ResourceManager('@py')
resources = rm.list_resources()
usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

if not usb_resources:
    print("No scope found!")
    sys.exit(1)

scope = rm.open_resource(usb_resources[0])
scope.timeout = 3000

print("Oscilloscope State Diagnostics")
print("="*50)

# Check trigger mode
print('Trigger mode:', scope.query(':TRIGger:MODE?').strip())
print('Trigger status:', scope.query(':TRIGger:STATus?').strip())
print('Trigger sweep:', scope.query(':TRIGger:SWEep?').strip())
print('Timebase:', scope.query(':TIMebase:MAIN:SCALe?').strip(), 's/div')

# Set to AUTO trigger for continuous acquisition
print("\nSetting to AUTO trigger mode...")
scope.write(':TRIGger:SWEep AUTO')
time.sleep(0.5)
print('Trigger sweep now:', scope.query(':TRIGger:SWEep?').strip())

# Make sure running
scope.write(':RUN')
time.sleep(0.5)

# Try a quick capture
print("\nTesting fast capture...")
start = time.time()
scope.write(':WAVeform:SOURce CHANnel1')
scope.write(':WAVeform:MODE NORMal')
scope.write(':WAVeform:FORMat BYTE')
scope.write(':WAVeform:DATA?')
try:
    data = scope.read_raw()
    elapsed = time.time() - start
    print(f'✓ Success! Got {len(data)} bytes in {elapsed:.3f}s')
except Exception as e:
    elapsed = time.time() - start
    print(f'✗ Failed after {elapsed:.3f}s: {e}')

scope.close()
