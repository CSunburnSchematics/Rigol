#!/usr/bin/env python3
"""
Coverage test - measure capture frequency and coverage % for different point counts
Coverage % = (total time covered by samples) / (total test duration) * 100
"""

import sys
import os
import time
import numpy as np
from datetime import datetime

def connect_scope():
    """Connect to oscilloscope"""
    dll_path = os.path.join(os.path.dirname(__file__), "..", "lib", "libusb-1.0.dll")
    os.environ['PATH'] = os.path.dirname(dll_path) + os.pathsep + os.environ.get('PATH', '')

    import pyvisa
    rm = pyvisa.ResourceManager('@py')
    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        return None

    scope = rm.open_resource(usb_resources[0])
    scope.timeout = 2000  # 2 second timeout
    scope.chunk_size = 102400  # Large chunks for big transfers
    return scope

def wait_for_acquisition(scope, max_wait=0.2):
    """Wait for scope to complete acquisition"""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            status = scope.query(':TRIGger:STATus?').strip()
            if status in ['TD', 'STOP']:
                return True, status
            time.sleep(0.005)
        except:
            return False, None
    return False, None

def capture_with_point_count(scope, channel, target_points):
    """Capture data with specific point count"""
    capture_start = time.time()

    # Wait for acquisition
    ready, status = wait_for_acquisition(scope, max_wait=0.3)
    if not ready:
        return None

    # Configure waveform read
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE RAW')
    scope.write(':WAVeform:FORMat BYTE')

    # Try to set the point count - may be limited by memory depth
    try:
        scope.write(f':WAVeform:POINts {target_points}')
        time.sleep(0.01)  # Small delay for scope to process
    except:
        pass

    # Get actual point count from preamble
    try:
        preamble = scope.query(':WAVeform:PREamble?')
        preamble_values = [float(x) for x in preamble.split(',')]
        actual_points = int(preamble_values[2])
        x_increment = preamble_values[4]
        y_increment = preamble_values[7]
        y_origin = preamble_values[8]
        y_reference = preamble_values[9]
    except Exception as e:
        return None

    # Transfer data
    transfer_start = time.time()
    try:
        scope.write(':WAVeform:DATA?')
        raw_data = scope.read_raw()
        transfer_time = time.time() - transfer_start
    except Exception as e:
        return None

    # Parse binary data
    try:
        header_len = 2 + int(chr(raw_data[1]))
        data = raw_data[header_len:-1]
        waveform_data = np.frombuffer(data, dtype=np.uint8)
        voltages = ((waveform_data - y_reference) * y_increment) + y_origin
    except:
        return None

    total_time = time.time() - capture_start
    time_span = len(voltages) * x_increment  # Time duration covered by this capture

    return {
        'actual_points': actual_points,
        'received_points': len(voltages),
        'time_span': time_span,
        'x_increment': x_increment,
        'transfer_time': transfer_time,
        'total_time': total_time,
        'voltages': voltages
    }

def test_point_count(scope, target_points, test_duration=20):
    """Test a specific point count for a duration and calculate coverage"""
    print(f"\n{'='*70}")
    print(f"Testing {target_points:,} points target")
    print(f"{'='*70}")

    captures = []
    start_time = time.time()
    success_count = 0
    fail_count = 0

    while time.time() - start_time < test_duration:
        result = capture_with_point_count(scope, channel=1, target_points=target_points)

        if result:
            elapsed = time.time() - start_time
            result['elapsed'] = elapsed
            captures.append(result)
            success_count += 1

            if success_count <= 3 or success_count % 5 == 0:
                print(f"[{elapsed:5.1f}s] #{success_count:3d}: Got {result['received_points']:,} pts "
                      f"in {result['total_time']:.3f}s (transfer: {result['transfer_time']:.3f}s) "
                      f"| Span: {result['time_span']*1e3:.2f}ms", flush=True)
        else:
            fail_count += 1
            if fail_count <= 3:
                print(f"  [Failed attempt #{fail_count}]", flush=True)

        time.sleep(0.01)  # Minimum interval

    total_time = time.time() - start_time

    # Calculate statistics
    if not captures:
        print("No successful captures!")
        return None

    # Coverage calculation
    total_data_time = sum(c['time_span'] for c in captures)
    coverage_pct = (total_data_time / total_time) * 100

    # Capture intervals
    if len(captures) > 1:
        intervals = [captures[i]['elapsed'] - captures[i-1]['elapsed']
                    for i in range(1, len(captures))]
        avg_interval = np.mean(intervals)
        min_interval = np.min(intervals)
        max_interval = np.max(intervals)
    else:
        avg_interval = min_interval = max_interval = 0

    # Transfer statistics
    transfer_times = [c['transfer_time'] for c in captures]
    total_times = [c['total_time'] for c in captures]
    actual_points = captures[0]['actual_points']
    received_points = [c['received_points'] for c in captures]

    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print(f"Target points:      {target_points:,}")
    print(f"Actual points set:  {actual_points:,}")
    print(f"Points received:    {np.mean(received_points):,.0f} avg")
    print(f"Test duration:      {total_time:.1f}s")
    print(f"Successful:         {success_count}")
    print(f"Failed:             {fail_count}")
    print(f"Success rate:       {success_count/(success_count+fail_count)*100:.1f}%")
    print(f"Capture rate:       {success_count/total_time:.2f} captures/sec")
    print(f"Avg interval:       {avg_interval:.3f}s")
    print(f"Min interval:       {min_interval:.3f}s")
    print(f"Max interval:       {max_interval:.3f}s")
    print(f"Avg transfer time:  {np.mean(transfer_times):.3f}s")
    print(f"Avg total time:     {np.mean(total_times):.3f}s")
    print(f"Sample timespan:    {captures[0]['time_span']*1e3:.3f}ms per capture")
    print(f"Total data time:    {total_data_time:.3f}s")
    print(f"COVERAGE:           {coverage_pct:.2f}%")

    return {
        'target_points': target_points,
        'actual_points': actual_points,
        'received_points': int(np.mean(received_points)),
        'test_duration': total_time,
        'success_count': success_count,
        'fail_count': fail_count,
        'capture_rate': success_count/total_time,
        'avg_interval': avg_interval,
        'min_interval': min_interval,
        'avg_transfer_time': np.mean(transfer_times),
        'avg_total_time': np.mean(total_times),
        'sample_timespan': captures[0]['time_span'],
        'coverage_pct': coverage_pct
    }

def main():
    print("DS1054Z Coverage Test")
    print("="*70)
    print("Testing different point counts to measure capture rate and coverage")
    print("="*70)

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect to oscilloscope")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}")

    # Get scope settings
    timebase = scope.query(':TIMebase:MAIN:SCALe?').strip()
    mdepth = scope.query(':ACQuire:MDEPth?').strip()
    print(f"Timebase: {float(timebase)*1e6:.1f} us/div")
    print(f"Memory depth: {mdepth}")

    # Make sure scope is running
    scope.write(':RUN')
    time.sleep(0.3)

    # Test different point counts
    test_points = [100, 1000, 10000, 100000, 1000000]
    test_duration = 20  # 20 seconds per test

    results = []

    for points in test_points:
        try:
            result = test_point_count(scope, points, test_duration)
            if result:
                results.append(result)
        except KeyboardInterrupt:
            print("\n\nStopped by user")
            break
        except Exception as e:
            print(f"Error testing {points}: {e}")

    # Summary table
    print(f"\n{'='*70}")
    print("SUMMARY - Coverage Analysis")
    print(f"{'='*70}")
    print(f"{'Target':<12} {'Actual':<12} {'Rate':<12} {'Span/Cap':<15} {'Coverage':<12}")
    print(f"{'Points':<12} {'Points':<12} {'(cap/s)':<12} {'(ms)':<15} {'(%)':<12}")
    print("-"*70)

    for r in results:
        print(f"{r['target_points']:<12,} {r['received_points']:<12,} "
              f"{r['capture_rate']:<12.2f} {r['sample_timespan']*1e3:<15.2f} "
              f"{r['coverage_pct']:<12.2f}")

    print(f"{'='*70}")
    print("\nKey insight: Coverage % = (time covered by samples) / (total time)")
    print("Higher coverage = more continuous data recording")
    print(f"{'='*70}")

    scope.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
