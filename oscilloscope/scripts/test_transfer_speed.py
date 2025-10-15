#!/usr/bin/env python3
"""
Test oscilloscope data transfer speeds with different memory depths
"""

import sys
import os
import time
import numpy as np

def connect_scope():
    """Connect to the oscilloscope"""
    dll_path = os.path.join(os.getcwd(), "libusb-1.0.dll")
    os.environ['PATH'] = os.getcwd() + os.pathsep + os.environ.get('PATH', '')

    import pyvisa

    print("Connecting to oscilloscope...", flush=True)
    rm = pyvisa.ResourceManager('@py')

    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        print("[ERROR] Oscilloscope not found", flush=True)
        return None

    resource_str = usb_resources[0]
    scope = rm.open_resource(resource_str)
    scope.timeout = 60000  # 60 second timeout

    idn = scope.query('*IDN?').strip()
    print(f"[OK] Connected: {idn}\n", flush=True)

    return scope

def test_memory_depth_transfer(scope, channel=1):
    """Test transfer speeds at different memory depths"""

    print("="*70, flush=True)
    print("OSCILLOSCOPE DATA TRANSFER BENCHMARK", flush=True)
    print("="*70, flush=True)

    # Memory depth options for DS1000Z series
    # AUTO, 12K, 120K, 1.2M, 12M, 24M
    memory_depths = ['AUTO', '12000', '120000', '1200000']

    results = []

    for mdepth in memory_depths:
        print(f"\n--- Testing Memory Depth: {mdepth} ---", flush=True)

        try:
            # Stop acquisition
            scope.write(':STOP')
            time.sleep(0.2)

            # Set memory depth
            scope.write(f':ACQuire:MDEPth {mdepth}')
            time.sleep(0.2)

            # Verify setting
            actual_mdepth = scope.query(':ACQuire:MDEPth?').strip()
            print(f"Set to: {actual_mdepth}", flush=True)

            # Start single acquisition
            scope.write(':SINGle')
            time.sleep(0.5)

            # Configure waveform readout
            scope.write(f':WAVeform:SOURce CHANnel{channel}')
            scope.write(':WAVeform:MODE NORMal')
            scope.write(':WAVeform:FORMat BYTE')

            # Get preamble
            preamble = scope.query(':WAVeform:PREamble?')
            preamble_values = [float(x) for x in preamble.split(',')]
            actual_points = int(preamble_values[2])

            print(f"Actual points: {actual_points:,}", flush=True)

            # Time the data transfer
            print("Transferring data...", flush=True)
            start_time = time.time()

            scope.write(':WAVeform:DATA?')
            raw_data = scope.read_raw()

            end_time = time.time()
            transfer_time = end_time - start_time

            # Calculate stats
            data_size = len(raw_data)
            throughput_kbps = (data_size / 1024) / transfer_time
            points_per_sec = actual_points / transfer_time

            print(f"Transfer time: {transfer_time:.3f} seconds", flush=True)
            print(f"Data size: {data_size:,} bytes ({data_size/1024:.1f} KB)", flush=True)
            print(f"Throughput: {throughput_kbps:.1f} KB/s", flush=True)
            print(f"Rate: {points_per_sec:,.0f} points/sec", flush=True)

            results.append({
                'memory_depth': mdepth,
                'actual_points': actual_points,
                'data_size': data_size,
                'transfer_time': transfer_time,
                'throughput_kbps': throughput_kbps,
                'points_per_sec': points_per_sec
            })

        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()

    # Print summary table
    print("\n" + "="*70, flush=True)
    print("SUMMARY", flush=True)
    print("="*70, flush=True)
    print(f"{'Memory Depth':<15} {'Points':<12} {'Time(s)':<10} {'KB/s':<12} {'Points/s':<12}", flush=True)
    print("-"*70, flush=True)

    for r in results:
        print(f"{r['memory_depth']:<15} {r['actual_points']:<12,} "
              f"{r['transfer_time']:<10.3f} {r['throughput_kbps']:<12.1f} "
              f"{r['points_per_sec']:<12,.0f}", flush=True)

    print("="*70, flush=True)

    # Calculate how many captures per minute
    if results:
        print("\nESTIMATES FOR 60-SECOND CAPTURE:", flush=True)
        for r in results:
            captures_per_min = 60 / r['transfer_time']
            total_points_per_min = captures_per_min * r['actual_points']
            print(f"  {r['memory_depth']}: ~{captures_per_min:.1f} captures/min "
                  f"= {total_points_per_min:,.0f} total points", flush=True)

    return results

def main():
    scope = connect_scope()
    if not scope:
        return 1

    try:
        results = test_memory_depth_transfer(scope, channel=1)

        print("\n[SUCCESS] Benchmark complete!", flush=True)

    except KeyboardInterrupt:
        print("\nInterrupted by user", flush=True)
    except Exception as e:
        print(f"\n[ERROR] {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        scope.close()
        print("Connection closed.", flush=True)

    return 0

if __name__ == "__main__":
    sys.exit(main())
