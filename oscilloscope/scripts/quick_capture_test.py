#!/usr/bin/env python3
"""
Quick oscilloscope capture test with incremental point counts
Total runtime: ~30 seconds
"""

import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

def connect_scope():
    """Connect to the oscilloscope"""
    dll_path = os.path.join(os.getcwd(), "libusb-1.0.dll")
    os.environ['PATH'] = os.getcwd() + os.pathsep + os.environ.get('PATH', '')

    import pyvisa

    print("Connecting...", flush=True)
    rm = pyvisa.ResourceManager('@py')
    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        print("ERROR: Scope not found", flush=True)
        return None

    scope = rm.open_resource(usb_resources[0])
    scope.timeout = 10000

    print(f"Connected: {scope.query('*IDN?').strip()}\n", flush=True)
    return scope

def capture_with_settings(scope, channel=1):
    """Capture data and return timing info"""

    # Configure waveform
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE NORMal')
    scope.write(':WAVeform:FORMat BYTE')

    # Get preamble
    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]

    points = int(preamble_values[2])
    x_increment = preamble_values[4]
    y_increment = preamble_values[7]
    y_origin = preamble_values[8]
    y_reference = preamble_values[9]

    # Time the transfer
    start_time = time.time()

    scope.write(':WAVeform:DATA?')
    raw_data = scope.read_raw()

    transfer_time = time.time() - start_time

    # Parse data
    header_len = 2 + int(chr(raw_data[1]))
    data = raw_data[header_len:-1]
    waveform_data = np.frombuffer(data, dtype=np.uint8)

    # Convert to voltages
    voltages = ((waveform_data - y_reference) * y_increment) + y_origin

    return {
        'points': len(voltages),
        'transfer_time': transfer_time,
        'data_size': len(raw_data),
        'voltages': voltages,
        'time_increment': x_increment
    }

def run_30sec_capture(scope, channel=1):
    """Capture data continuously for 30 seconds"""

    print("="*70, flush=True)
    print("30-SECOND CONTINUOUS CAPTURE TEST", flush=True)
    print("="*70, flush=True)

    start_time = time.time()
    end_time = start_time + 30

    captures = []
    capture_num = 0

    print(f"\nStarting capture at {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print(f"Channel: {channel}\n", flush=True)

    while time.time() < end_time:
        try:
            # Trigger single capture
            scope.write(':STOP')
            time.sleep(0.01)
            scope.write(':SINGle')
            time.sleep(0.05)  # Wait for trigger

            # Capture data
            result = capture_with_settings(scope, channel)

            elapsed = time.time() - start_time
            remaining = end_time - time.time()

            captures.append({
                'num': capture_num,
                'timestamp': datetime.now(timezone.utc),
                'elapsed': elapsed,
                **result
            })

            # Progress update
            print(f"[{elapsed:5.1f}s] Cap #{capture_num:3d}: {result['points']:,} pts "
                  f"in {result['transfer_time']:.3f}s | Remaining: {remaining:.1f}s", flush=True)

            capture_num += 1

            if time.time() >= end_time:
                break

        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            break

    return captures

def analyze_and_save(captures):
    """Analyze captures and save results"""

    if not captures:
        print("\nNo captures recorded!", flush=True)
        return

    print("\n" + "="*70, flush=True)
    print("ANALYSIS", flush=True)
    print("="*70, flush=True)

    total_captures = len(captures)
    total_points = sum(c['points'] for c in captures)
    total_time = captures[-1]['elapsed']
    avg_transfer_time = np.mean([c['transfer_time'] for c in captures])
    total_data_mb = sum(c['data_size'] for c in captures) / 1024 / 1024

    print(f"\nTotal captures:       {total_captures}", flush=True)
    print(f"Total points:         {total_points:,}", flush=True)
    print(f"Total duration:       {total_time:.2f} seconds", flush=True)
    print(f"Avg transfer time:    {avg_transfer_time:.3f} seconds", flush=True)
    print(f"Captures per second:  {total_captures/total_time:.2f}", flush=True)
    print(f"Points per second:    {total_points/total_time:,.0f}", flush=True)
    print(f"Total data:           {total_data_mb:.2f} MB", flush=True)

    # Check for timing gaps
    print("\nTiming gaps:", flush=True)
    for i in range(1, min(10, len(captures))):
        gap = captures[i]['elapsed'] - captures[i-1]['elapsed']
        print(f"  Capture {i}: {gap:.3f}s from previous", flush=True)

    # Create quick plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # Plot capture timing
    times = [c['elapsed'] for c in captures]
    transfer_times = [c['transfer_time'] for c in captures]

    ax1.scatter(times, transfer_times, s=20, alpha=0.6)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Transfer Time (s)')
    ax1.set_title('Transfer Time per Capture')
    ax1.grid(True, alpha=0.3)

    # Plot voltage from last capture
    last_capture = captures[-1]
    times_us = np.arange(len(last_capture['voltages'])) * last_capture['time_increment'] * 1e6

    ax2.plot(times_us, last_capture['voltages'], linewidth=0.5)
    ax2.set_xlabel('Time (μs)')
    ax2.set_ylabel('Voltage (V)')
    ax2.set_title(f'Last Waveform (Capture #{total_captures-1})')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('quick_capture_results.png', dpi=150)
    print(f"\nPlot saved: quick_capture_results.png", flush=True)
    plt.close()

    # Save summary to file
    with open('quick_capture_summary.txt', 'w') as f:
        f.write(f"30-Second Capture Test Results\n")
        f.write(f"="*50 + "\n\n")
        f.write(f"Total captures:       {total_captures}\n")
        f.write(f"Total points:         {total_points:,}\n")
        f.write(f"Total duration:       {total_time:.2f} seconds\n")
        f.write(f"Avg transfer time:    {avg_transfer_time:.3f} seconds\n")
        f.write(f"Captures per second:  {total_captures/total_time:.2f}\n")
        f.write(f"Points per second:    {total_points/total_time:,.0f}\n")
        f.write(f"Total data:           {total_data_mb:.2f} MB\n")

    print("Summary saved: quick_capture_summary.txt", flush=True)

def main():
    scope = connect_scope()
    if not scope:
        return 1

    try:
        captures = run_30sec_capture(scope, channel=1)
        analyze_and_save(captures)

        print("\n" + "="*70, flush=True)
        print("SUCCESS!", flush=True)
        print("="*70, flush=True)

    except KeyboardInterrupt:
        print("\nInterrupted", flush=True)
    except Exception as e:
        print(f"\nERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        scope.close()
        print("\nConnection closed.", flush=True)

    return 0

if __name__ == "__main__":
    sys.exit(main())
