#!/usr/bin/env python3
"""
Simple continuous capture - uses RUN mode, no triggering required
Captures screen buffer repeatedly for 30 seconds
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
    scope.timeout = 5000  # 5 second timeout

    print(f"Connected: {scope.query('*IDN?').strip()}\n", flush=True)
    return scope

def simple_capture(scope, channel=1):
    """Simple capture from screen buffer"""

    # Set to RUN mode (continuous acquisition)
    scope.write(':RUN')
    time.sleep(0.1)  # Let it acquire some data

    # Configure waveform source
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE NORMal')
    scope.write(':WAVeform:FORMat BYTE')

    # Get preamble
    start_time = time.time()

    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]

    points = int(preamble_values[2])
    x_increment = preamble_values[4]
    y_increment = preamble_values[7]
    y_origin = preamble_values[8]
    y_reference = preamble_values[9]

    # Get waveform data
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
        'time_increment': x_increment,
        'v_max': np.max(voltages),
        'v_min': np.min(voltages),
        'v_avg': np.mean(voltages)
    }

def run_continuous_capture(scope, duration=30, channel=1):
    """Capture continuously for specified duration"""

    print("="*70, flush=True)
    print(f"{duration}-SECOND CONTINUOUS CAPTURE", flush=True)
    print("="*70, flush=True)

    start_time = time.time()
    end_time = start_time + duration

    captures = []
    capture_num = 0

    print(f"\nStarting at {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print(f"Channel: {channel}\n", flush=True)

    # Keep scope in RUN mode throughout
    scope.write(':RUN')

    while time.time() < end_time:
        try:
            # Capture current screen buffer
            result = simple_capture(scope, channel)

            elapsed = time.time() - start_time
            remaining = end_time - time.time()

            captures.append({
                'num': capture_num,
                'timestamp': datetime.now(timezone.utc),
                'elapsed': elapsed,
                **result
            })

            # Print progress
            print(f"[{elapsed:5.1f}s] #{capture_num:3d}: {result['points']:,} pts "
                  f"in {result['transfer_time']:.3f}s | "
                  f"V:{result['v_min']:.2f} to {result['v_max']:.2f} | "
                  f"Remain: {remaining:.1f}s", flush=True)

            capture_num += 1

        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            time.sleep(0.1)
            continue

    return captures

def analyze_results(captures):
    """Analyze and visualize capture results"""

    if not captures:
        print("\nNo data captured!", flush=True)
        return

    print("\n" + "="*70, flush=True)
    print("RESULTS", flush=True)
    print("="*70, flush=True)

    total_captures = len(captures)
    total_points = sum(c['points'] for c in captures)
    total_time = captures[-1]['elapsed']
    avg_transfer = np.mean([c['transfer_time'] for c in captures])
    total_data_mb = sum(c['data_size'] for c in captures) / 1024 / 1024

    print(f"\nTotal captures:      {total_captures}", flush=True)
    print(f"Total points:        {total_points:,}", flush=True)
    print(f"Duration:            {total_time:.2f} seconds", flush=True)
    print(f"Avg transfer time:   {avg_transfer:.3f} seconds", flush=True)
    print(f"Captures/second:     {total_captures/total_time:.2f}", flush=True)
    print(f"Points/second:       {total_points/total_time:,.0f}", flush=True)
    print(f"Total data:          {total_data_mb:.2f} MB", flush=True)
    print(f"Throughput:          {total_data_mb/total_time:.2f} MB/s", flush=True)

    # Calculate inter-capture gaps
    gaps = []
    for i in range(1, len(captures)):
        gap = captures[i]['elapsed'] - captures[i-1]['elapsed']
        gaps.append(gap)

    if gaps:
        print(f"\nInter-capture timing:", flush=True)
        print(f"  Min gap:  {min(gaps):.3f}s", flush=True)
        print(f"  Max gap:  {max(gaps):.3f}s", flush=True)
        print(f"  Avg gap:  {np.mean(gaps):.3f}s", flush=True)
        print(f"  Coverage: {total_captures * avg_transfer / total_time * 100:.1f}% of time spent transferring", flush=True)

    # Create plots
    fig = plt.figure(figsize=(14, 10))

    # Plot 1: Transfer times
    ax1 = plt.subplot(3, 1, 1)
    times = [c['elapsed'] for c in captures]
    transfer_times = [c['transfer_time'] for c in captures]
    ax1.scatter(times, transfer_times, s=15, alpha=0.6)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Transfer Time (s)')
    ax1.set_title('Transfer Time per Capture')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Voltage range over time
    ax2 = plt.subplot(3, 1, 2)
    v_max = [c['v_max'] for c in captures]
    v_min = [c['v_min'] for c in captures]
    v_avg = [c['v_avg'] for c in captures]
    ax2.plot(times, v_max, 'r-', label='Max', linewidth=1)
    ax2.plot(times, v_min, 'b-', label='Min', linewidth=1)
    ax2.plot(times, v_avg, 'g-', label='Avg', linewidth=1)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Voltage (V)')
    ax2.set_title('Voltage Range Over Time')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Last captured waveform
    ax3 = plt.subplot(3, 1, 3)
    last = captures[-1]
    wf_times = np.arange(len(last['voltages'])) * last['time_increment'] * 1e6
    ax3.plot(wf_times, last['voltages'], linewidth=0.5)
    ax3.set_xlabel('Time (μs)')
    ax3.set_ylabel('Voltage (V)')
    ax3.set_title(f'Last Waveform (Capture #{total_captures-1})')
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('continuous_capture_results.png', dpi=150)
    print(f"\nPlot saved: continuous_capture_results.png", flush=True)
    plt.close()

def main():
    scope = connect_scope()
    if not scope:
        return 1

    try:
        # Run 30-second capture
        captures = run_continuous_capture(scope, duration=30, channel=1)

        # Analyze
        analyze_results(captures)

        print("\n" + "="*70, flush=True)
        print("COMPLETE!", flush=True)
        print("="*70, flush=True)

    except KeyboardInterrupt:
        print("\nStopped by user", flush=True)
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
