#!/usr/bin/env python3
"""
Quick Memory Depth Test
Tests one config for 10 seconds and outputs key stats
"""

import sys
import os
import time
import json
import pyvisa

def connect_to_scope():
    """Connect to first available oscilloscope"""
    dll_path = os.path.join(os.path.dirname(__file__), "..", "lib", "libusb-1.0.dll")
    os.environ['PATH'] = os.path.dirname(dll_path) + os.pathsep + os.environ.get('PATH', '')

    rm = pyvisa.ResourceManager('@py')
    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        print("ERROR: No oscilloscopes found!")
        return None

    try:
        scope = rm.open_resource(usb_resources[0])
        scope.timeout = 3000
        scope.chunk_size = 102400
        return scope
    except Exception as e:
        print(f"ERROR: Failed to connect - {e}")
        return None

def test_config(config_file, test_duration=10):
    """Test a config file and report stats"""

    # Load config
    with open(config_file, 'r') as f:
        config = json.load(f)

    points = config['capture_settings']['points_per_channel']
    timebase = config['capture_settings']['timebase_seconds']
    memory_depth = config['acquisition']['memory_depth']

    print(f"\n{'='*70}")
    print(f"TESTING: {os.path.basename(config_file)}")
    print(f"{'='*70}")
    print(f"Memory Depth: {memory_depth} points")
    print(f"Timebase: {timebase*1e6:.3f} us/div")
    print(f"Test Duration: {test_duration}s")

    # Connect
    scope = connect_to_scope()
    if not scope:
        return None

    # Configure scope
    scope.write(f':ACQuire:MDEPth {memory_depth}')
    time.sleep(0.1)
    scope.write(f':TIMebase:MAIN:SCALe {timebase}')
    time.sleep(0.1)
    scope.write(':TIMebase:MAIN:OFFSet 0')
    time.sleep(0.1)
    scope.write(':CHANnel1:DISPlay ON')
    time.sleep(0.05)
    scope.write(':RUN')
    time.sleep(0.2)

    # Setup waveform acquisition
    scope.write(':WAVeform:SOURce CHANnel1')
    scope.write(':WAVeform:MODE RAW')
    scope.write(':WAVeform:FORMat BYTE')
    scope.write(f':WAVeform:POINts {points}')
    time.sleep(0.1)

    # Get time increment
    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]
    x_increment = preamble_values[4]
    time_per_capture = points * x_increment

    print(f"Time per capture: {time_per_capture*1e6:.1f} us")
    print(f"\nCapturing for {test_duration} seconds...")

    # Capture loop
    start_time = time.time()
    capture_count = 0
    errors = 0
    transfer_times = []

    while (time.time() - start_time) < test_duration:
        try:
            t_start = time.time()
            scope.write(':WAVeform:DATA?')
            raw_data = scope.read_raw()
            t_end = time.time()

            capture_count += 1
            transfer_times.append(t_end - t_start)
            time.sleep(0.001)  # Small delay to avoid overwhelming scope

        except Exception as e:
            errors += 1
            time.sleep(0.01)

    elapsed = time.time() - start_time
    capture_rate = capture_count / elapsed if elapsed > 0 else 0

    # Calculate coverage
    total_sample_time = capture_count * time_per_capture
    coverage = (total_sample_time / elapsed) * 100

    # Stats
    avg_transfer = sum(transfer_times) / len(transfer_times) if transfer_times else 0

    print(f"\n{'='*70}")
    print(f"RESULTS:")
    print(f"{'='*70}")
    print(f"Captures:         {capture_count}")
    print(f"Errors:           {errors}")
    print(f"Capture Rate:     {capture_rate:.2f} cap/s")
    print(f"Avg Transfer:     {avg_transfer*1000:.1f} ms")
    print(f"Total Sample Time: {total_sample_time*1000:.1f} ms")
    print(f"Coverage:         {coverage:.2f}%")
    print(f"{'='*70}\n")

    scope.close()

    return {
        'points': points,
        'timebase_us': timebase * 1e6,
        'time_per_cap_us': time_per_capture * 1e6,
        'captures': capture_count,
        'errors': errors,
        'rate': capture_rate,
        'coverage': coverage,
        'avg_transfer_ms': avg_transfer * 1000
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_depth_test.py <config_file>")
        return 1

    config_file = sys.argv[1]
    result = test_config(config_file, test_duration=10)

    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())
