#!/usr/bin/env python3
"""
Coverage test - 1000 points at different timebases
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
    scope.timeout = 2000
    scope.chunk_size = 102400
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

def capture_1000_points(scope, channel=1):
    """Capture 1000 points"""
    capture_start = time.time()

    # Wait for acquisition
    ready, status = wait_for_acquisition(scope, max_wait=0.3)
    if not ready:
        return None

    # Configure waveform read
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE RAW')
    scope.write(':WAVeform:FORMat BYTE')
    scope.write(':WAVeform:POINts 1000')
    time.sleep(0.01)

    # Get preamble
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
    time_span = len(voltages) * x_increment

    return {
        'received_points': len(voltages),
        'time_span': time_span,
        'x_increment': x_increment,
        'transfer_time': transfer_time,
        'total_time': total_time,
        'voltages': voltages
    }

def set_timebase(scope, timebase_seconds):
    """Set the timebase (seconds per division)"""
    scope.write(f':TIMebase:MAIN:SCALe {timebase_seconds}')
    time.sleep(0.3)

def test_timebase(scope, timebase_seconds, timebase_name, test_duration=20):
    """Test a specific timebase setting"""
    print(f"\n{'='*70}")
    print(f"Testing 1000 points at {timebase_name} per division")
    print(f"{'='*70}")

    # Set the timebase
    set_timebase(scope, timebase_seconds)

    # Verify it was set
    actual = scope.query(':TIMebase:MAIN:SCALe?').strip()
    print(f"Timebase set to: {float(actual)*1e6:.1f} us/div")

    # Make sure running
    scope.write(':RUN')
    time.sleep(0.2)

    captures = []
    start_time = time.time()
    success_count = 0
    fail_count = 0

    while time.time() - start_time < test_duration:
        result = capture_1000_points(scope, channel=1)

        if result:
            elapsed = time.time() - start_time
            result['elapsed'] = elapsed
            captures.append(result)
            success_count += 1

            if success_count <= 3 or success_count % 5 == 0:
                print(f"[{elapsed:5.1f}s] #{success_count:3d}: {result['received_points']:,} pts "
                      f"in {result['total_time']:.3f}s "
                      f"| Span: {result['time_span']*1e6:.3f}us", flush=True)
        else:
            fail_count += 1
            if fail_count <= 3:
                print(f"  [Failed attempt #{fail_count}]", flush=True)

        time.sleep(0.01)

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
    received_points = [c['received_points'] for c in captures]
    avg_points = np.mean(received_points)
    avg_time_span = np.mean([c['time_span'] for c in captures])

    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print(f"Timebase:           {timebase_name}/div")
    print(f"Points received:    {avg_points:.0f} avg")
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
    print(f"Sample timespan:    {avg_time_span*1e6:.3f}us per capture")
    print(f"Total data time:    {total_data_time*1e3:.3f}ms")
    print(f"COVERAGE:           {coverage_pct:.2f}%")

    return {
        'timebase_name': timebase_name,
        'timebase_seconds': timebase_seconds,
        'avg_points': int(avg_points),
        'test_duration': total_time,
        'success_count': success_count,
        'fail_count': fail_count,
        'success_rate': success_count/(success_count+fail_count)*100,
        'capture_rate': success_count/total_time,
        'avg_interval': avg_interval,
        'min_interval': min_interval,
        'max_interval': max_interval,
        'avg_transfer_time': np.mean(transfer_times),
        'avg_total_time': np.mean(total_times),
        'avg_time_span': avg_time_span,
        'total_data_time': total_data_time,
        'coverage_pct': coverage_pct
    }

def main():
    print("DS1054Z Coverage Test - 1000 Points")
    print("="*70)
    print("Testing 1000-point captures at different timebase settings")
    print("="*70)

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect to oscilloscope")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}")

    # Get initial settings
    mdepth = scope.query(':ACQuire:MDEPth?').strip()
    print(f"Memory depth: {mdepth}")

    # Test different timebases with 1000 points
    timebases = [
        (1e-6, "1us"),
        (10e-6, "10us"),
        (100e-6, "100us"),
        (1e-3, "1ms"),
    ]

    test_duration = 20  # 20 seconds per test

    results = []

    for timebase_sec, timebase_name in timebases:
        try:
            result = test_timebase(scope, timebase_sec, timebase_name, test_duration)
            if result:
                results.append(result)
        except KeyboardInterrupt:
            print("\n\nStopped by user")
            break
        except Exception as e:
            print(f"Error testing {timebase_name}: {e}")

    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY - 1000 Point Coverage Analysis")
    print(f"{'='*80}")
    print(f"{'Timebase':<12} {'Cap Rate':<12} {'Span/Cap':<15} {'Success':<10} {'Coverage':<12}")
    print(f"{'(/div)':<12} {'(cap/s)':<12} {'(us)':<15} {'Rate %':<10} {'%':<12}")
    print("-"*80)

    for r in results:
        print(f"{r['timebase_name']:<12} {r['capture_rate']:<12.2f} "
              f"{r['avg_time_span']*1e6:<15.3f} {r['success_rate']:<10.1f} "
              f"{r['coverage_pct']:<12.2f}")

    print(f"{'='*80}")
    print("\nKey insight: 1000 points = 10x more data per capture than 100 points")
    print("Coverage should be ~10x better at the same timebase")
    print(f"{'='*80}")

    # Save results
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'../../data/coverage_1000pts_{timestamp_str}.txt'

    with open(results_file, 'w') as f:
        f.write("1000 Point Coverage Test Results\n")
        f.write("="*80 + "\n\n")
        f.write(f"{'Timebase':<12} {'Cap Rate':<12} {'Span/Cap':<15} {'Success':<10} {'Coverage':<12}\n")
        f.write(f"{'(/div)':<12} {'(cap/s)':<12} {'(us)':<15} {'Rate %':<10} {'%':<12}\n")
        f.write("-"*80 + "\n")
        for r in results:
            f.write(f"{r['timebase_name']:<12} {r['capture_rate']:<12.2f} "
                   f"{r['avg_time_span']*1e6:<15.3f} {r['success_rate']:<10.1f} "
                   f"{r['coverage_pct']:<12.2f}\n")

    print(f"\nResults saved: {results_file}")

    scope.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
