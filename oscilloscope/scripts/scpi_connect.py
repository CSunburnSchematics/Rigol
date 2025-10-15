#!/usr/bin/env python3
"""
Connect to DS1054Z oscilloscope using SCPI commands
"""

import sys
import pyvisa

def find_and_connect_scope():
    """Find and connect to oscilloscope using SCPI"""
    print("DS1054Z SCPI Connection")
    print("=" * 60)

    try:
        # Try PyVISA-py backend first
        print("Initializing VISA resource manager...")
        rm = pyvisa.ResourceManager('@py')

        print(f"Backend: {rm}")

        # List all resources
        resources = rm.list_resources()
        print(f"\nFound {len(resources)} resource(s):")
        for res in resources:
            print(f"  - {res}")

        # Try to find oscilloscope by querying each resource
        print("\nQuerying devices for identification...")

        scope_resource = None

        # Common USB resource patterns for Rigol scopes
        usb_patterns = [
            'USB0::0x1AB1::0x04CE::*::INSTR',
            'USB0::6833::1230::*::INSTR',
            'USB::0x1AB1::0x04CE::*::INSTR',
            'USB::6833::1230::*::INSTR',
        ]

        # Try to open each resource and send *IDN? query
        for resource_name in resources:
            try:
                print(f"\n  Trying: {resource_name}")
                inst = rm.open_resource(resource_name)
                inst.timeout = 5000  # 5 second timeout

                # Send SCPI identification query
                idn = inst.query('*IDN?').strip()
                print(f"    Response: {idn}")

                # Check if it's a Rigol scope
                if 'RIGOL' in idn.upper() or 'DS1' in idn.upper():
                    print(f"    >>> Found Rigol oscilloscope! <<<")
                    scope_resource = resource_name
                    inst.close()
                    break

                inst.close()

            except Exception as e:
                print(f"    No response or error: {e}")
                continue

        # If we didn't find it in existing resources, try common patterns
        if not scope_resource:
            print("\nTrying common USB resource patterns...")
            for pattern in usb_patterns:
                try:
                    print(f"  Trying: {pattern}")
                    inst = rm.open_resource(pattern)
                    inst.timeout = 5000
                    idn = inst.query('*IDN?').strip()
                    print(f"    Response: {idn}")

                    if 'RIGOL' in idn.upper():
                        scope_resource = pattern
                        inst.close()
                        break
                    inst.close()
                except:
                    continue

        if not scope_resource:
            print("\n[FAILED] Could not find oscilloscope")
            print("\nPossible issues:")
            print("  1. Oscilloscope is not powered on")
            print("  2. USB cable not connected")
            print("  3. USB drivers not installed (try Zadig with WinUSB)")
            print("  4. Oscilloscope USB mode not configured correctly")
            print("\nOn the oscilloscope, try:")
            print("  - Utility -> I/O Setting -> USB Device -> Enable")
            return None

        # Connect to the scope
        print(f"\n{'=' * 60}")
        print(f"Connecting to: {scope_resource}")
        scope = rm.open_resource(scope_resource)
        scope.timeout = 5000

        # Get identification
        idn = scope.query('*IDN?').strip()
        print(f"\n[SUCCESS] Connected!")
        print(f"Identification: {idn}")

        # Parse IDN response (format: Manufacturer,Model,SerialNumber,FirmwareVersion)
        idn_parts = idn.split(',')
        if len(idn_parts) >= 4:
            print(f"\nDevice Information:")
            print(f"  Manufacturer: {idn_parts[0]}")
            print(f"  Model:        {idn_parts[1]}")
            print(f"  Serial:       {idn_parts[2]}")
            print(f"  Firmware:     {idn_parts[3]}")

        # Try some additional SCPI queries
        try:
            print(f"\nAdditional Queries:")

            # Check acquisition status
            run_status = scope.query(':TRIGger:STATus?').strip()
            print(f"  Trigger Status: {run_status}")

            # Check timebase
            timescale = scope.query(':TIMebase:SCALe?').strip()
            print(f"  Timebase Scale: {timescale} s/div")

            # Check channels
            print(f"\n  Channel Status:")
            for ch in range(1, 5):
                try:
                    ch_display = scope.query(f':CHANnel{ch}:DISPlay?').strip()
                    ch_scale = scope.query(f':CHANnel{ch}:SCALe?').strip()
                    status = "ON" if ch_display == "1" else "OFF"
                    print(f"    Channel {ch}: {status:3s} (Scale: {ch_scale} V/div)")
                except:
                    pass

        except Exception as e:
            print(f"  (Could not query additional info: {e})")

        return scope

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    scope = find_and_connect_scope()

    if scope:
        print("\n" + "=" * 60)
        print("[OK] Oscilloscope is ready for SCPI commands!")
        print("\nExample commands you can try:")
        print("  scope.query('*IDN?')              # Get identification")
        print("  scope.query(':MEASure:VMAX?')     # Measure max voltage")
        print("  scope.write(':RUN')               # Start acquisition")
        print("  scope.write(':STOP')              # Stop acquisition")
        print("  scope.query(':WAVeform:DATA?')    # Get waveform data")
        scope.close()
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
