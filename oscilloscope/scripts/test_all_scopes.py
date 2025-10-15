"""
Test all connected oscilloscopes individually
Verifies each scope can be connected to and queried
"""

import os
import time
import pyvisa

def test_scope(rm, resource_name):
    """Test a single oscilloscope"""
    try:
        print(f"\nTesting: {resource_name}")
        print("="*60)

        # Connect
        scope = rm.open_resource(resource_name)
        scope.timeout = 2000
        scope.chunk_size = 102400

        # Query identity
        idn = scope.query('*IDN?').strip()
        print(f"  Identity: {idn}")

        # Parse serial number
        parts = idn.split(',')
        if len(parts) >= 3:
            serial = parts[2]
            print(f"  Serial: {serial}")

        # Query system settings
        timebase = scope.query(':TIMebase:MAIN:SCALe?').strip()
        print(f"  Timebase: {float(timebase)*1e6:.1f} us/div")

        # Query channel 1
        ch1_scale = scope.query(':CHANnel1:SCALe?').strip()
        ch1_probe = scope.query(':CHANnel1:PROBe?').strip()
        print(f"  CH1: {float(ch1_scale):.2f}V/div, Probe: {float(ch1_probe):.0f}x")

        # Try a quick waveform capture from CH1
        scope.write(':WAVeform:SOURce CHANnel1')
        scope.write(':WAVeform:MODE NORMAL')
        scope.write(':WAVeform:FORMat BYTE')
        scope.write(':WAVeform:POINts 30')
        time.sleep(0.1)

        scope.write(':WAVeform:DATA?')
        raw_data = scope.read_raw()
        header_len = 2 + int(chr(raw_data[1]))
        data = raw_data[header_len:-1]
        points = len(data)
        print(f"  Waveform capture: {points} points")

        scope.close()
        print(f"  Status: PASSED")
        return True

    except Exception as e:
        print(f"  Status: FAILED - {type(e).__name__}: {e}")
        try:
            scope.close()
        except:
            pass
        return False

def main():
    # Setup libusb path
    dll_path = os.path.join(os.path.dirname(__file__), "..", "lib", "libusb-1.0.dll")
    os.environ['PATH'] = os.path.dirname(dll_path) + os.pathsep + os.environ.get('PATH', '')

    print("\n" + "="*60)
    print("OSCILLOSCOPE TEST - ALL CONNECTED SCOPES")
    print("="*60)

    # Create resource manager
    rm = pyvisa.ResourceManager('@py')

    # List all resources
    resources = rm.list_resources()
    print(f"\nTotal VISA resources: {len(resources)}")

    # Filter for USB scopes
    usb_scopes = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    print(f"USB Oscilloscopes found: {len(usb_scopes)}\n")

    if not usb_scopes:
        print("ERROR: No oscilloscopes found!")
        return 1

    # Test each scope
    results = []
    for i, resource in enumerate(usb_scopes, 1):
        passed = test_scope(rm, resource)
        results.append((resource, passed))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed_count = sum(1 for r, p in results if p)
    failed_count = len(results) - passed_count

    for resource, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"{status}: {resource}")

    print(f"\nTotal: {len(results)} scopes")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")

    if failed_count == 0:
        print("\nAll oscilloscopes are working correctly!")
        return 0
    else:
        print(f"\n{failed_count} oscilloscope(s) failed testing.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
