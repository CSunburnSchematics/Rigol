#!/usr/bin/env python3
"""
4-channel speed test with different point counts
Testing 30 and 120 points per channel at various timebases
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
    scope.timeout = 1000
    scope.chunk_size = 102400
    return scope

def setup_channel(scope, channel, points=100):
    """Setup and cache preamble for one channel"""
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE RAW')
    scope.write(':WAVeform:FORMat BYTE')
    scope.write(f':WAVeform:POINts {points}')
    time.sleep(0.02)

    # Get and cache preamble
    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]

    return {
        'channel': channel,
        'x_increment': preamble_values[4],
        'y_increment': preamble_values[7],
        'y_origin': preamble_values[8],
        'y_reference': preamble_values[9]
    }

def capture_channel(scope, channel, preamble_cache):
    """Capture single channel - fast"""
    try:
        scope.write(f':WAVeform:SOURce CHANnel{channel}')
        scope.write(':WAVeform:DATA?')
        raw_data = scope.read_raw()

        # Parse binary data
        header_len = 2 + int(chr(raw_data[1]))
        data = raw_data[header_len:-1]
        waveform_data = np.frombuffer(data, dtype=np.uint8)

        # Convert using cached preamble
        voltages = ((waveform_data - preamble_cache['y_reference']) *
                   preamble_cache['y_increment']) + preamble_cache['y_origin']

        return voltages
    except:
        return None

def capture_all_channels(scope, preamble_caches):
    """Capture all 4 channels as fast as possible"""
    capture_start = time.time()
    channels_data = {}

    for ch in range(1, 5):
        voltages = capture_channel(scope, ch, preamble_caches[ch-1])
        if voltages is None:
            return None
        channels_data[ch] = voltages

    transfer_time = time.time() - capture_start

    # Calculate time span (same for all channels)
    time_span = len(channels_data[1]) * preamble_caches[0]['x_increment']

    return {
        'channels': channels_data,
        'points_per_channel': len(channels_data[1]),
        'time_span': time_span,
        'transfer_time': transfer_time
    }

def test_config(scope, points, timebase_sec, timebase_name, test_duration=20):
    """Test specific configuration"""
    print(f"\n{'='*70}")
    print(f"Testing: {points} pts/ch @ {timebase_name}/div")
    print(f"{'='*70}")

    # Set timebase
    scope.write(f':TIMebase:MAIN:SCALe {timebase_sec}')
    time.sleep(0.3)

    # Verify
    actual = scope.query(':TIMebase:MAIN:SCALe?').strip()
    print(f"Timebase: {float(actual)*1e6:.3f} us/div")

    # Make sure running
    scope.write(':RUN')
    time.sleep(0.2)

    # Setup all 4 channels
    print("Setting up 4 channels...")
    preamble_caches = []
    for ch in range(1, 5):
        cache = setup_channel(scope, ch, points)
        preamble_caches.append(cache)

    captures = []
    start_time = time.time()
    success_count = 0
    fail_count = 0

    print(f"Capturing for {test_duration}s...")

    while time.time() - start_time < test_duration:
        result = capture_all_channels(scope, preamble_caches)

        if result:
            elapsed = time.time() - start_time
            result['elapsed'] = elapsed
            captures.append(result)
            success_count += 1

            if success_count <= 3 or success_count % 10 == 0:
                total_pts = result['points_per_channel'] * 4
                print(f"[{elapsed:5.1f}s] #{success_count:3d}: {total_pts:,} pts total "
                      f"in {result['transfer_time']:.3f}s", flush=True)
        else:
            fail_count += 1

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
    total_points = sum(c['points_per_channel'] * 4 for c in captures)

    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print(f"Config:             {points} pts/ch @ {timebase_name}/div")
    print(f"Test duration:      {total_time:.1f}s")
    print(f"Successful:         {success_count}")
    print(f"Failed:             {fail_count}")
    print(f"Success rate:       {success_count/(success_count+fail_count)*100:.1f}%")
    print(f"Capture rate:       {success_count/total_time:.2f} captures/sec")
    print(f"Avg interval:       {avg_interval*1000:.1f}ms")
    print(f"Min interval:       {min_interval*1000:.1f}ms")
    print(f"Avg transfer time:  {np.mean(transfer_times)*1000:.1f}ms")
    print(f"Sample timespan:    {avg_time_span*1e6:.2f}us per capture")
    print(f"Total points:       {total_points:,} ({total_points/4:,.0f} per channel)")
    print(f"COVERAGE:           {coverage_pct:.2f}%")
    print(f"Data rate:          {total_points/total_time:,.0f} points/sec")

    return {
        'points': points,
        'timebase': timebase_name,
        'timebase_sec': timebase_sec,
        'capture_rate': success_count/total_time,
        'coverage_pct': coverage_pct,
        'success_rate': success_count/(success_count+fail_count)*100,
        'avg_interval_ms': avg_interval*1000,
        'min_interval_ms': min_interval*1000,
        'avg_transfer_ms': np.mean(transfer_times)*1000,
        'total_points': total_points,
        'data_rate': total_points/total_time,
        'timespan_us': avg_time_span*1e6
    }

def main():
    print("DS1054Z 4-Channel Point/Timebase Comparison Test")
    print("="*70)
    print("Testing 30 and 120 points/channel at 1us, 100us, 1ms")
    print("="*70)

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect")
        return 1

    print(f"Connected: {scope.query('*IDN?').strip()}\n")

    # Test configurations: (points, timebase_sec, timebase_name, duration)
    tests = [
        # 30 points per channel
        (30, 1e-6, "1us", 20),
        (30, 100e-6, "100us", 20),
        (30, 1e-3, "1ms", 20),

        # 120 points per channel
        (120, 1e-6, "1us", 20),
        (120, 100e-6, "100us", 20),
        (120, 1e-3, "1ms", 20),
    ]

    results = []

    for points, timebase_sec, timebase_name, duration in tests:
        try:
            result = test_config(scope, points, timebase_sec, timebase_name, duration)
            if result:
                results.append(result)
        except KeyboardInterrupt:
            print("\n\nStopped by user")
            break
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    # Summary table
    print(f"\n{'='*90}")
    print("SUMMARY - 4-Channel Performance by Points and Timebase")
    print(f"{'='*90}")
    print(f"{'Points':<8} {'Timebase':<10} {'Cap/s':<10} {'Interval':<12} {'Transfer':<12} {'Coverage':<10} {'Span/Cap':<12}")
    print(f"{'(/ch)':<8} {'':10} {'':10} {'(ms)':<12} {'(ms)':<12} {'%':<10} {'(us)':<12}")
    print("-"*90)

    for r in results:
        print(f"{r['points']:<8} {r['timebase']:<10} {r['capture_rate']:<10.2f} "
              f"{r['avg_interval_ms']:<12.1f} {r['avg_transfer_ms']:<12.1f} "
              f"{r['coverage_pct']:<10.2f} {r['timespan_us']:<12.2f}")

    print(f"{'='*90}")

    # Compare 30 vs 120 at same timebase
    print("\nDirect Comparisons (30 vs 120 points):")
    print("-"*90)

    timebases = ["1us", "100us", "1ms"]
    for tb in timebases:
        r30 = next((r for r in results if r['points'] == 30 and r['timebase'] == tb), None)
        r120 = next((r for r in results if r['points'] == 120 and r['timebase'] == tb), None)

        if r30 and r120:
            interval_diff = r120['avg_interval_ms'] - r30['avg_interval_ms']
            coverage_ratio = r120['coverage_pct'] / r30['coverage_pct'] if r30['coverage_pct'] > 0 else 0

            print(f"\n{tb}/div:")
            print(f"  30 pts:  {r30['capture_rate']:.2f} cap/s, {r30['avg_interval_ms']:.1f}ms interval, {r30['coverage_pct']:.2f}% coverage")
            print(f"  120 pts: {r120['capture_rate']:.2f} cap/s, {r120['avg_interval_ms']:.1f}ms interval, {r120['coverage_pct']:.2f}% coverage")
            print(f"  Impact:  +{interval_diff:.1f}ms interval, {coverage_ratio:.2f}x coverage change")

    print(f"\n{'='*90}")

    # Save results
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'../../data/4ch_points_comparison_{timestamp_str}.txt'

    with open(results_file, 'w') as f:
        f.write("4-Channel Point/Timebase Comparison Test\n")
        f.write("="*90 + "\n\n")
        f.write(f"{'Points':<8} {'Timebase':<10} {'Cap/s':<10} {'Interval':<12} {'Transfer':<12} {'Coverage':<10} {'Span/Cap':<12}\n")
        f.write(f"{'(/ch)':<8} {'':10} {'':10} {'(ms)':<12} {'(ms)':<12} {'%':<10} {'(us)':<12}\n")
        f.write("-"*90 + "\n")
        for r in results:
            f.write(f"{r['points']:<8} {r['timebase']:<10} {r['capture_rate']:<10.2f} "
                   f"{r['avg_interval_ms']:<12.1f} {r['avg_transfer_ms']:<12.1f} "
                   f"{r['coverage_pct']:<10.2f} {r['timespan_us']:<12.2f}\n")

    print(f"\nResults saved: {results_file}")

    scope.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
