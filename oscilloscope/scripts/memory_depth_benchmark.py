#!/usr/bin/env python3
"""
Memory Depth Benchmark Test
Tests different memory depths and measures capture rate and coverage
"""

import sys
import os
import time
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
        idn = scope.query('*IDN?').strip()
        print(f"Connected to: {idn}")
        return scope
    except Exception as e:
        print(f"ERROR: Failed to connect - {e}")
        return None

def test_memory_depth(scope, memory_depth, timebase, test_duration=10):
    """Test capture rate and coverage for a given memory depth"""
    print(f"\n{'='*70}")
    print(f"Testing: {memory_depth} points at {timebase*1e6:.1f}us/div")
    print(f"{'='*70}")

    # Configure scope
    scope.write(f':ACQuire:MDEPth {memory_depth}')
    time.sleep(0.1)
    scope.write(f':TIMebase:MAIN:SCALe {timebase}')
    time.sleep(0.1)
    scope.write(':TIMebase:MAIN:OFFSet 0')
    time.sleep(0.1)

    # Query actual sample rate
    try:
        actual_rate = float(scope.query(':ACQuire:SRATe?'))
        actual_rate_msa = actual_rate / 1e6
    except:
        actual_rate_msa = 0

    # Setup waveform acquisition
    scope.write(':WAVeform:SOURce CHANnel1')
    scope.write(':WAVeform:MODE RAW')
    scope.write(':WAVeform:FORMat BYTE')
    scope.write(f':WAVeform:POINts {memory_depth}')
    time.sleep(0.1)

    # Get preamble to calculate time per capture
    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]
    x_increment = preamble_values[4]
    time_per_capture = memory_depth * x_increment

    print(f"  Sample Rate: {actual_rate_msa:.1f} MSa/s")
    print(f"  Time per capture: {time_per_capture*1e6:.1f} us ({time_per_capture*1e3:.3f} ms)")

    # Run capture test
    scope.write(':RUN')
    time.sleep(0.5)

    start_time = time.time()
    capture_count = 0
    errors = 0

    print(f"  Testing for {test_duration} seconds...")

    while (time.time() - start_time) < test_duration:
        try:
            scope.write(':WAVeform:DATA?')
            raw_data = scope.read_raw()
            capture_count += 1
        except:
            errors += 1
            time.sleep(0.01)

    elapsed = time.time() - start_time
    capture_rate = capture_count / elapsed

    # Calculate coverage
    total_sample_time = capture_count * time_per_capture
    coverage = (total_sample_time / elapsed) * 100

    print(f"\n  Results:")
    print(f"    Captures: {capture_count}")
    print(f"    Capture Rate: {capture_rate:.2f} cap/s")
    print(f"    Errors: {errors}")
    print(f"    Total Sample Time: {total_sample_time*1e3:.1f} ms")
    print(f"    Coverage: {coverage:.1f}%")

    return {
        'memory_depth': memory_depth,
        'timebase': timebase,
        'sample_rate_msa': actual_rate_msa,
        'time_per_capture_us': time_per_capture * 1e6,
        'capture_rate': capture_rate,
        'coverage': coverage,
        'errors': errors
    }

def main():
    print("="*70)
    print("MEMORY DEPTH BENCHMARK TEST")
    print("="*70)

    scope = connect_to_scope()
    if scope is None:
        return 1

    # Configure scope - basic setup
    scope.write(':CHANnel1:DISPlay ON')
    scope.write(':CHANnel1:PROBe 100')
    scope.write(':CHANnel1:SCALe 2.0')
    scope.write(':CHANnel1:COUPling DC')
    time.sleep(0.2)

    # Test different memory depths at 10us timebase
    timebase = 0.00001  # 10us/div
    memory_depths = [300, 600, 1200, 3000, 6000, 12000, 24000]

    print(f"\nTimebase: {timebase*1e6:.1f} us/div")
    print(f"Test Duration: 10 seconds per depth\n")

    results = []
    for depth in memory_depths:
        try:
            result = test_memory_depth(scope, depth, timebase, test_duration=10)
            results.append(result)
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"  ERROR during test: {e}")

    # Print summary table
    print("\n" + "="*70)
    print("SUMMARY TABLE")
    print("="*70)
    print(f"{'Depth':<8} {'Time/Cap':<12} {'Rate':<12} {'Coverage':<12} {'Sample Rate':<12}")
    print(f"{'(pts)':<8} {'(us)':<12} {'(cap/s)':<12} {'(%)':<12} {'(MSa/s)':<12}")
    print("-"*70)

    for r in results:
        print(f"{r['memory_depth']:<8} {r['time_per_capture_us']:<12.1f} "
              f"{r['capture_rate']:<12.2f} {r['coverage']:<12.1f} "
              f"{r['sample_rate_msa']:<12.1f}")

    scope.close()

    print("\n" + "="*70)
    print("Test complete!")
    print("="*70)

    return 0

if __name__ == "__main__":
    sys.exit(main())
