#!/usr/bin/env python3
"""
Optimized long-term data capture with timestamps and gap detection
"""

import sys
import os
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta

def connect_scope():
    """Connect to oscilloscope"""
    dll_path = os.path.join(os.getcwd(), "libusb-1.0.dll")
    os.environ['PATH'] = os.getcwd() + os.pathsep + os.environ.get('PATH', '')

    import pyvisa
    rm = pyvisa.ResourceManager('@py')
    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        return None

    scope = rm.open_resource(usb_resources[0])
    scope.timeout = 5000
    return scope

def capture_waveform(scope, channel=1):
    """Capture single waveform with timing"""
    capture_start = datetime.now(timezone.utc)

    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE NORMal')
    scope.write(':WAVeform:FORMat BYTE')

    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]

    x_increment = preamble_values[4]
    y_increment = preamble_values[7]
    y_origin = preamble_values[8]
    y_reference = preamble_values[9]

    transfer_start = time.time()
    scope.write(':WAVeform:DATA?')
    raw_data = scope.read_raw()
    transfer_time = time.time() - transfer_start

    header_len = 2 + int(chr(raw_data[1]))
    data = raw_data[header_len:-1]
    waveform_data = np.frombuffer(data, dtype=np.uint8)
    voltages = ((waveform_data - y_reference) * y_increment) + y_origin

    return {
        'timestamp': capture_start,
        'voltages': voltages,
        'time_increment': x_increment,
        'transfer_time': transfer_time,
        'v_max': np.max(voltages),
        'v_min': np.min(voltages),
        'v_avg': np.mean(voltages)
    }

def continuous_logging(scope, duration_sec=30, channel=1, delay_between=0.2):
    """
    Continuous data logging with:
    - UTC timestamps for each sample
    - Gap detection
    - Real-time progress display
    """

    print("="*70)
    print(f"CONTINUOUS DATA LOGGER - {duration_sec} seconds")
    print("="*70)
    print(f"Channel: {channel}")
    print(f"Delay between captures: {delay_between}s")
    print()

    start_time = time.time()
    end_time = start_time + duration_sec

    all_captures = []
    capture_num = 0

    # Keep scope running
    scope.write(':RUN')

    print(f"{'Time':<8} {'#':<4} {'Points':<8} {'Transfer':<10} {'V Range':<20} {'Status':<10}")
    print("-"*70)

    while time.time() < end_time:
        try:
            result = capture_waveform(scope, channel)

            elapsed = time.time() - start_time
            remaining = end_time - time.time()

            result['capture_num'] = capture_num
            result['elapsed'] = elapsed
            all_captures.append(result)

            # Real-time display
            print(f"{elapsed:6.1f}s  {capture_num:<4} {len(result['voltages']):<8} "
                  f"{result['transfer_time']:<10.3f} "
                  f"{result['v_min']:.2f} to {result['v_max']:.2f}V  "
                  f"OK", flush=True)

            capture_num += 1

            # Delay before next capture to prevent buffer overload
            time.sleep(delay_between)

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"{elapsed:6.1f}s  ERROR: {str(e)[:40]}", flush=True)
            time.sleep(delay_between * 2)  # Longer delay after error

    return all_captures

def save_timestamped_data(captures, filename='long_term_data.csv'):
    """Save all data with precise UTC timestamps"""

    print(f"\nSaving timestamped data to {filename}...")

    rows = []
    for cap in captures:
        timestamp = cap['timestamp']
        dt = cap['time_increment']

        for i, v in enumerate(cap['voltages']):
            sample_time = timestamp + timedelta(seconds=i * dt)
            rows.append({
                'UTC_Timestamp': sample_time.isoformat(),
                'Unix_Time': sample_time.timestamp(),
                'Capture_Num': cap['capture_num'],
                'Sample_Index': i,
                'Voltage_V': v
            })

    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False)

    file_size_mb = os.path.getsize(filename) / 1024 / 1024
    print(f"Saved {len(rows):,} samples ({file_size_mb:.2f} MB)")

    return filename

def analyze_gaps(captures):
    """Detect and report timing gaps"""

    print("\n" + "="*70)
    print("GAP ANALYSIS")
    print("="*70)

    if len(captures) < 2:
        print("Not enough captures for gap analysis")
        return

    gaps = []
    for i in range(1, len(captures)):
        time_diff = (captures[i]['timestamp'] - captures[i-1]['timestamp']).total_seconds()
        expected_time = captures[i-1]['transfer_time']
        gap = time_diff - expected_time

        gaps.append({
            'capture': i,
            'time_diff': time_diff,
            'expected': expected_time,
            'gap': gap
        })

    # Report largest gaps
    sorted_gaps = sorted(gaps, key=lambda x: x['gap'], reverse=True)

    print(f"\nTotal captures: {len(captures)}")
    print(f"Total time: {captures[-1]['elapsed']:.1f}s")
    print(f"\nTop 5 largest gaps:")
    for g in sorted_gaps[:5]:
        print(f"  Capture {g['capture']}: {g['gap']:.3f}s gap "
              f"(expected {g['expected']:.3f}s, actual {g['time_diff']:.3f}s)")

    avg_gap = np.mean([g['gap'] for g in gaps])
    print(f"\nAverage gap: {avg_gap:.3f}s")

def create_summary_plot(captures, filename='long_term_summary.png'):
    """Create visualization of long-term capture"""

    fig = plt.figure(figsize=(14, 12))

    # Plot 1: Voltage trends over time
    ax1 = plt.subplot(4, 1, 1)
    times = [c['elapsed'] for c in captures]
    v_max = [c['v_max'] for c in captures]
    v_min = [c['v_min'] for c in captures]
    v_avg = [c['v_avg'] for c in captures]

    ax1.plot(times, v_max, 'r-', label='Max', linewidth=1.5, alpha=0.7)
    ax1.plot(times, v_min, 'b-', label='Min', linewidth=1.5, alpha=0.7)
    ax1.plot(times, v_avg, 'g-', label='Avg', linewidth=1.5, alpha=0.7)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Voltage (V)')
    ax1.set_title('Voltage Range Over Time')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Transfer times
    ax2 = plt.subplot(4, 1, 2)
    transfer_times = [c['transfer_time'] for c in captures]
    ax2.scatter(times, transfer_times, s=10, alpha=0.6)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Transfer Time (s)')
    ax2.set_title('Data Transfer Times')
    ax2.grid(True, alpha=0.3)

    # Plot 3: Sample waveforms from different times
    ax3 = plt.subplot(4, 1, 3)
    indices = [0, len(captures)//2, -1]
    colors = ['blue', 'green', 'red']
    labels = ['Start', 'Middle', 'End']

    for idx, color, label in zip(indices, colors, labels):
        if idx < len(captures):
            cap = captures[idx]
            wf_times = np.arange(len(cap['voltages'])) * cap['time_increment'] * 1e6
            ax3.plot(wf_times, cap['voltages'], color=color, label=label,
                     linewidth=0.7, alpha=0.7)

    ax3.set_xlabel('Time (μs)')
    ax3.set_ylabel('Voltage (V)')
    ax3.set_title('Sample Waveforms')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Plot 4: Histogram of all voltages
    ax4 = plt.subplot(4, 1, 4)
    all_voltages = np.concatenate([c['voltages'] for c in captures])
    ax4.hist(all_voltages, bins=100, color='purple', alpha=0.7, edgecolor='black')
    ax4.set_xlabel('Voltage (V)')
    ax4.set_ylabel('Count')
    ax4.set_title('Overall Voltage Distribution')
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"Plot saved: {filename}")
    plt.close()

def main():
    print("DS1104Z Long-Term Data Logger\n")

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect to oscilloscope")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}\n")

    try:
        # Run 30-second continuous capture
        captures = continuous_logging(scope, duration_sec=30, channel=1, delay_between=0.3)

        if captures:
            # Statistics
            total_points = sum(len(c['voltages']) for c in captures)
            total_time = captures[-1]['elapsed']
            avg_rate = total_points / total_time

            print("\n" + "="*70)
            print("SUMMARY")
            print("="*70)
            print(f"Captures:        {len(captures)}")
            print(f"Total points:    {total_points:,}")
            print(f"Duration:        {total_time:.1f}s")
            print(f"Effective rate:  {avg_rate:,.0f} points/sec")
            print(f"Data coverage:   {len(captures) * np.mean([c['transfer_time'] for c in captures]) / total_time * 100:.1f}%")

            # Save data
            csv_file = save_timestamped_data(captures)

            # Analyze gaps
            analyze_gaps(captures)

            # Create plots
            create_summary_plot(captures)

            print("\n" + "="*70)
            print("COMPLETE!")
            print("="*70)
            print(f"\nFiles created:")
            print(f"  - {csv_file}")
            print(f"  - long_term_summary.png")

        else:
            print("\nNo data captured!")

    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        scope.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())
