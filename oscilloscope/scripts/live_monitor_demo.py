#!/usr/bin/env python3
"""
Live oscilloscope monitor - demo version that auto-saves and exits
Shows 4 graphs vertically with UTC timeline
"""

import sys
import os
import time
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta
from collections import deque

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
    scope.timeout = 5000
    return scope

def capture_waveform(scope, channel=1):
    """Capture single waveform"""
    capture_start = datetime.now(timezone.utc)

    scope.write(':RUN')
    time.sleep(0.1)

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

def create_live_plot(captures):
    """Create 4-panel vertical plot"""

    fig = plt.figure(figsize=(16, 14))

    ax1 = plt.subplot(4, 1, 1)  # Real-time UTC waveform data
    ax2 = plt.subplot(4, 1, 2)  # Transfer times
    ax3 = plt.subplot(4, 1, 3)  # Sample waveforms (scatter)
    ax4 = plt.subplot(4, 1, 4)  # Voltage distribution

    # Plot 1: Real-time UTC waveform data
    print("  Creating UTC timeline plot...")
    for cap in captures:
        base_time = cap['timestamp']
        dt = cap['time_increment']
        utc_times = [base_time + timedelta(seconds=i * dt) for i in range(len(cap['voltages']))]
        ax1.scatter(utc_times, cap['voltages'], s=1, alpha=0.6, c='blue')

    ax1.set_xlabel('UTC Time', fontsize=11)
    ax1.set_ylabel('Voltage (V)', fontsize=11)
    ax1.set_title('Waveform Data on Real-Time Axis (UTC) - Shows Capture Gaps', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Plot 2: Transfer times
    print("  Creating transfer times plot...")
    times = [c['elapsed'] for c in captures]
    transfer_times = [c['transfer_time'] for c in captures]

    ax2.scatter(times, transfer_times, s=30, alpha=0.6, c='purple')

    if len(transfer_times) > 1:
        avg_transfer = np.mean(transfer_times)
        ax2.axhline(y=avg_transfer, color='red', linestyle='--',
                   linewidth=1.5, label=f'Avg: {avg_transfer:.3f}s')
        ax2.legend()

    ax2.set_xlabel('Elapsed Time (s)', fontsize=11)
    ax2.set_ylabel('Transfer Time (s)', fontsize=11)
    ax2.set_title('Data Transfer Times (Gap Detection)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # Plot 3: Sample waveforms (scatter, last 3)
    print("  Creating sample waveforms plot...")
    num_samples = min(3, len(captures))
    indices = [-3, -2, -1][-num_samples:]
    colors = ['blue', 'green', 'red'][-num_samples:]
    labels = ['3rd Last', '2nd Last', 'Latest'][-num_samples:]

    for idx, color, label in zip(indices, colors, labels):
        if idx >= -len(captures):
            cap = captures[idx]
            wf_times = np.arange(len(cap['voltages'])) * cap['time_increment'] * 1e6
            ax3.scatter(wf_times, cap['voltages'], s=2, alpha=0.6, c=color, label=label)

    ax3.set_xlabel('Time (us)', fontsize=11)
    ax3.set_ylabel('Voltage (V)', fontsize=11)
    ax3.set_title('Sample Waveforms (Last 3 Captures - Scatter)', fontsize=12, fontweight='bold')
    ax3.legend(markerscale=5)
    ax3.grid(True, alpha=0.3)

    # Plot 4: Voltage distribution
    print("  Creating voltage distribution plot...")
    all_voltages = np.concatenate([c['voltages'] for c in captures])

    ax4.hist(all_voltages, bins=50, color='purple', alpha=0.7, edgecolor='black')
    ax4.set_xlabel('Voltage (V)', fontsize=11)
    ax4.set_ylabel('Count', fontsize=11)
    ax4.set_title(f'Overall Voltage Distribution ({len(all_voltages):,} samples)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    return fig

def main():
    print("DS1054Z Live Monitor Demo\n")

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect to oscilloscope")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}\n")

    # Setup CSV file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'../../data/live_monitor_demo_{timestamp}.csv'
    csv_file = open(csv_filename, 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['UTC_Timestamp', 'Time_Offset_s', 'Voltage_V',
                         'Capture_Num', 'Elapsed_Time_s'])
    print(f"CSV logging to: {csv_filename}\n")

    captures = []
    start_time = time.time()
    duration = 20  # 20 seconds
    interval = 0.35  # 0.35 second between captures

    print("="*70)
    print(f"CAPTURING DATA - {duration} seconds")
    print("="*70)
    print(f"Capture interval: {interval}s\n")

    capture_num = 0

    try:
        while time.time() - start_time < duration:
            try:
                result = capture_waveform(scope, channel=1)

                elapsed = time.time() - start_time
                result['capture_num'] = capture_num
                result['elapsed'] = elapsed

                # Write to CSV immediately
                base_time = result['timestamp']
                dt = result['time_increment']
                for i, voltage in enumerate(result['voltages']):
                    sample_time = base_time + timedelta(seconds=i * dt)
                    time_offset = i * dt
                    csv_writer.writerow([
                        sample_time.isoformat(),
                        f'{time_offset:.9f}',
                        f'{voltage:.6f}',
                        capture_num,
                        f'{elapsed:.3f}'
                    ])
                csv_file.flush()

                captures.append(result)

                print(f"[{elapsed:5.1f}s] #{capture_num:2d}: {len(result['voltages']):,} pts "
                      f"in {result['transfer_time']:.3f}s | V: {result['v_min']:.3f} to {result['v_max']:.3f}",
                      flush=True)

                capture_num += 1
                time.sleep(interval)

            except Exception as e:
                print(f"ERROR: {str(e)[:50]}", flush=True)
                time.sleep(interval * 2)

        if captures:
            print(f"\n{'='*70}")
            print("CREATING VISUALIZATION")
            print('='*70)

            # Create plot
            fig = create_live_plot(captures)

            # Save
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'../../plots/live_monitor_demo_{timestamp}.png'
            fig.savefig(filename, dpi=150, bbox_inches='tight')

            print(f"\nPlot saved: {filename}")

            # Statistics
            total_points = sum(len(c['voltages']) for c in captures)
            total_time = captures[-1]['elapsed']

            print(f"\n{'='*70}")
            print("SUMMARY")
            print('='*70)
            print(f"Total captures:  {len(captures)}")
            print(f"Total points:    {total_points:,}")
            print(f"Duration:        {total_time:.1f}s")
            print(f"Effective rate:  {total_points/total_time:,.0f} points/sec")

            # Close CSV
            csv_file.close()
            print(f"\nCSV data saved: {csv_filename}")

        else:
            print("\nNo data captured!")
            csv_file.close()

    except KeyboardInterrupt:
        print("\n\nStopped by user")
        csv_file.close()
    except Exception as e:
        print(f"\nERROR: {e}")
        csv_file.close()
        import traceback
        traceback.print_exc()
        return 1
    finally:
        scope.close()
        print("\nConnection closed.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
