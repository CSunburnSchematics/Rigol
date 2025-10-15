#!/usr/bin/env python3
"""
Maximum speed test - eliminate all waits and cache settings
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
    scope.timeout = 1000  # 1 second timeout
    scope.chunk_size = 102400
    return scope

def setup_capture(scope, channel=1, points=100):
    """One-time setup - cache preamble"""
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE RAW')
    scope.write(':WAVeform:FORMat BYTE')
    scope.write(f':WAVeform:POINts {points}')
    time.sleep(0.05)

    # Get preamble once and cache it
    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]

    return {
        'x_increment': preamble_values[4],
        'y_increment': preamble_values[7],
        'y_origin': preamble_values[8],
        'y_reference': preamble_values[9]
    }

def capture_fast(scope, preamble_cache):
    """Fastest possible capture - no waits, use cached preamble"""
    capture_start = time.time()

    try:
        # Just read data - no status check, no preamble query
        scope.write(':WAVeform:DATA?')
        raw_data = scope.read_raw()
        transfer_time = time.time() - capture_start

        # Parse binary data
        header_len = 2 + int(chr(raw_data[1]))
        data = raw_data[header_len:-1]
        waveform_data = np.frombuffer(data, dtype=np.uint8)

        # Convert to voltages using cached preamble
        voltages = ((waveform_data - preamble_cache['y_reference']) *
                   preamble_cache['y_increment']) + preamble_cache['y_origin']

        time_span = len(voltages) * preamble_cache['x_increment']

        return {
            'points': len(voltages),
            'time_span': time_span,
            'transfer_time': transfer_time,
            'voltages': voltages
        }
    except:
        return None

def test_max_speed(scope, points, timebase_sec, timebase_name, test_duration=20):
    """Test maximum capture speed"""
    print(f"\n{'='*70}")
    print(f"MAX SPEED TEST: {points} points at {timebase_name}/div")
    print(f"{'='*70}")

    # Set timebase
    scope.write(f':TIMebase:MAIN:SCALe {timebase_sec}')
    time.sleep(0.3)

    # Verify
    actual = scope.query(':TIMebase:MAIN:SCALe?').strip()
    print(f"Timebase: {float(actual)*1e6:.1f} us/div")

    # Make sure running
    scope.write(':RUN')
    time.sleep(0.2)

    # One-time setup
    print("Setting up capture (caching preamble)...")
    preamble_cache = setup_capture(scope, channel=1, points=points)
    print(f"Time per sample: {preamble_cache['x_increment']*1e6:.3f} us")

    captures = []
    start_time = time.time()
    success_count = 0
    fail_count = 0

    print(f"\nCapturing for {test_duration}s with NO waits...")
    print("This will read data as fast as possible!\n")

    while time.time() - start_time < test_duration:
        result = capture_fast(scope, preamble_cache)

        if result:
            elapsed = time.time() - start_time
            result['elapsed'] = elapsed
            captures.append(result)
            success_count += 1

            if success_count <= 5 or success_count % 20 == 0:
                print(f"[{elapsed:5.1f}s] #{success_count:4d}: {result['points']:,} pts "
                      f"in {result['transfer_time']:.3f}s | "
                      f"Span: {result['time_span']*1e6:.2f}us", flush=True)
        else:
            fail_count += 1

        # NO SLEEP - capture as fast as possible!

    total_time = time.time() - start_time

    if not captures:
        print("No successful captures!")
        return None

    # Statistics
    total_data_time = sum(c['time_span'] for c in captures)
    coverage_pct = (total_data_time / total_time) * 100

    if len(captures) > 1:
        intervals = [captures[i]['elapsed'] - captures[i-1]['elapsed']
                    for i in range(1, len(captures))]
        avg_interval = np.mean(intervals)
        min_interval = np.min(intervals)
    else:
        avg_interval = min_interval = 0

    transfer_times = [c['transfer_time'] for c in captures]
    avg_time_span = np.mean([c['time_span'] for c in captures])

    print(f"\n{'='*70}")
    print("RESULTS - MAXIMUM SPEED")
    print(f"{'='*70}")
    print(f"Test duration:      {total_time:.1f}s")
    print(f"Successful:         {success_count}")
    print(f"Failed:             {fail_count}")
    print(f"Success rate:       {success_count/(success_count+fail_count)*100:.1f}%")
    print(f"Capture rate:       {success_count/total_time:.2f} captures/sec")
    print(f"Avg interval:       {avg_interval*1000:.1f}ms")
    print(f"Min interval:       {min_interval*1000:.1f}ms")
    print(f"Avg transfer time:  {np.mean(transfer_times)*1000:.1f}ms")
    print(f"Sample timespan:    {avg_time_span*1e6:.2f}us per capture")
    print(f"Total data time:    {total_data_time*1e3:.1f}ms")
    print(f"COVERAGE:           {coverage_pct:.2f}%")

    return {
        'points': points,
        'timebase': timebase_name,
        'capture_rate': success_count/total_time,
        'coverage_pct': coverage_pct,
        'success_rate': success_count/(success_count+fail_count)*100,
        'avg_interval_ms': avg_interval*1000,
        'min_interval_ms': min_interval*1000
    }

def main():
    print("DS1054Z MAXIMUM SPEED TEST")
    print("="*70)
    print("Testing fastest possible capture (no waits, cached settings)")
    print("="*70)

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect")
        return 1

    print(f"Connected: {scope.query('*IDN?').strip()}")

    # Test configurations
    tests = [
        (100, 1e-3, "1ms", 20),   # 100 points, 1ms/div, 20 seconds
        (100, 100e-6, "100us", 20), # 100 points, 100us/div, 20 seconds
        (50, 1e-3, "1ms", 20),    # Try even fewer points
    ]

    results = []

    for points, timebase_sec, timebase_name, duration in tests:
        try:
            result = test_max_speed(scope, points, timebase_sec, timebase_name, duration)
            if result:
                results.append(result)
        except KeyboardInterrupt:
            print("\n\nStopped by user")
            break
        except Exception as e:
            print(f"Error: {e}")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY - Maximum Speed Comparison")
    print(f"{'='*70}")
    print(f"{'Config':<20} {'Rate':<12} {'Interval':<12} {'Coverage':<12}")
    print(f"{'':20} {'(cap/s)':<12} {'(ms)':<12} {'%':<12}")
    print("-"*70)

    for r in results:
        config = f"{r['points']}pts @ {r['timebase']}"
        print(f"{config:<20} {r['capture_rate']:<12.2f} "
              f"{r['avg_interval_ms']:<12.1f} {r['coverage_pct']:<12.2f}")

    print(f"{'='*70}")
    print("\nComparison with original (100pts@1ms with waits):")
    print("  Original: 4.75 cap/s, ~210ms interval, 0.48% coverage")
    print("  This test shows if we can go faster without waits!")

    scope.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
