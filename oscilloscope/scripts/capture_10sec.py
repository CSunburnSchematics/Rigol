#!/usr/bin/env python3
"""
Capture waveform data over 10 seconds with 100μs timebase
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

def set_timebase(scope, time_per_div=100e-6):
    """
    Set horizontal timebase (time/division)
    100 microseconds = 100e-6 seconds
    """
    print(f"Setting timebase to {time_per_div*1e6:.1f} us/div")
    scope.write(f':TIMebase:SCALe {time_per_div}')
    time.sleep(0.2)

    # Verify setting
    actual = float(scope.query(':TIMebase:SCALe?'))
    print(f"  Timebase set to: {actual*1e6:.1f} us/div")

    # Calculate total screen time (12 divisions)
    total_time = actual * 12
    print(f"  Total screen time: {total_time*1e6:.1f} us ({total_time*1e3:.3f} ms)")

    return actual

def capture_screen(scope, channel=1):
    """Capture current screen buffer"""
    # Set to RUN mode and wait for screen to update
    scope.write(':RUN')
    time.sleep(0.15)  # Longer delay for fast timebase

    # Configure waveform
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE NORMal')  # Screen data
    scope.write(':WAVeform:FORMat BYTE')

    # Get preamble
    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]

    x_increment = preamble_values[4]
    y_increment = preamble_values[7]
    y_origin = preamble_values[8]
    y_reference = preamble_values[9]

    # Get data
    transfer_start = time.time()
    scope.write(':WAVeform:DATA?')
    raw_data = scope.read_raw()
    transfer_time = time.time() - transfer_start

    # Parse
    header_len = 2 + int(chr(raw_data[1]))
    data = raw_data[header_len:-1]
    waveform_data = np.frombuffer(data, dtype=np.uint8)

    # Convert to voltages
    voltages = ((waveform_data - y_reference) * y_increment) + y_origin

    return {
        'timestamp': datetime.now(timezone.utc),
        'voltages': voltages,
        'time_increment': x_increment,
        'transfer_time': transfer_time,
        'points': len(voltages)
    }

def continuous_capture(scope, duration_sec=10, channel=1):
    """Capture continuously for specified duration"""

    print(f"\n{'='*70}")
    print(f"10-SECOND WAVEFORM CAPTURE")
    print('='*70)
    print(f"Channel: {channel}")
    print(f"Duration: {duration_sec} seconds\n")

    start_time = time.time()
    end_time = start_time + duration_sec

    captures = []
    capture_num = 0

    print(f"{'Time':<8} {'#':<5} {'Points':<8} {'Transfer':<12} {'V Range':<25}")
    print("-"*70)

    while time.time() < end_time:
        try:
            result = capture_screen(scope, channel)

            elapsed = time.time() - start_time
            remaining = end_time - time.time()

            result['capture_num'] = capture_num
            result['elapsed'] = elapsed

            captures.append(result)

            v_max = np.max(result['voltages'])
            v_min = np.min(result['voltages'])

            print(f"{elapsed:6.2f}s  {capture_num:<5} {result['points']:<8} "
                  f"{result['transfer_time']:<12.3f} "
                  f"{v_min:6.3f}V to {v_max:6.3f}V", flush=True)

            capture_num += 1

            # Delay to prevent overload (longer for fast timebase)
            time.sleep(0.2)

        except Exception as e:
            print(f"ERROR: {str(e)[:50]}", flush=True)
            time.sleep(0.2)

    return captures

def create_comprehensive_plot(captures, filename='10sec_capture.png'):
    """Create detailed visualization of the 10-second capture"""

    print(f"\nCreating visualization...")

    fig = plt.figure(figsize=(16, 12))

    # Calculate continuous time axis for all captures
    all_times = []
    all_voltages = []
    capture_boundaries = [0]  # Mark where each capture starts

    for cap in captures:
        # Time offset for this capture
        time_offset = cap['elapsed']

        # Create time array for this capture's samples
        dt = cap['time_increment']
        n_points = len(cap['voltages'])
        sample_times = time_offset + np.arange(n_points) * dt

        all_times.extend(sample_times)
        all_voltages.extend(cap['voltages'])
        capture_boundaries.append(len(all_times))

    all_times = np.array(all_times)
    all_voltages = np.array(all_voltages)

    # Plot 1: Full waveform over 10 seconds
    ax1 = plt.subplot(4, 1, 1)
    ax1.plot(all_times, all_voltages, linewidth=0.3, color='blue', alpha=0.8)
    ax1.set_xlabel('Time (s)', fontsize=11)
    ax1.set_ylabel('Voltage (V)', fontsize=11)
    ax1.set_title('Complete 10-Second Waveform Capture', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    # Add stats box
    stats_text = f'Total Points: {len(all_voltages):,}\n'
    stats_text += f'Captures: {len(captures)}\n'
    stats_text += f'Vmax: {np.max(all_voltages):.3f}V\n'
    stats_text += f'Vmin: {np.min(all_voltages):.3f}V\n'
    stats_text += f'Vpp: {np.max(all_voltages) - np.min(all_voltages):.3f}V'

    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
             verticalalignment='top', fontsize=9,
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    # Plot 2: Zoomed view of first 100ms
    ax2 = plt.subplot(4, 1, 2)
    zoom_mask = all_times <= 0.1  # First 100ms
    if np.any(zoom_mask):
        ax2.plot(all_times[zoom_mask] * 1000, all_voltages[zoom_mask],
                linewidth=0.8, color='green')
        ax2.set_xlabel('Time (ms)', fontsize=11)
        ax2.set_ylabel('Voltage (V)', fontsize=11)
        ax2.set_title('Zoomed View: First 100ms', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)

    # Plot 3: Voltage statistics over time (per capture)
    ax3 = plt.subplot(4, 1, 3)
    cap_times = [c['elapsed'] for c in captures]
    v_max_per_cap = [np.max(c['voltages']) for c in captures]
    v_min_per_cap = [np.min(c['voltages']) for c in captures]
    v_avg_per_cap = [np.mean(c['voltages']) for c in captures]

    ax3.plot(cap_times, v_max_per_cap, 'r-', label='Max', linewidth=1.5, marker='o', markersize=3)
    ax3.plot(cap_times, v_min_per_cap, 'b-', label='Min', linewidth=1.5, marker='o', markersize=3)
    ax3.plot(cap_times, v_avg_per_cap, 'g-', label='Avg', linewidth=1.5, marker='o', markersize=3)
    ax3.set_xlabel('Time (s)', fontsize=11)
    ax3.set_ylabel('Voltage (V)', fontsize=11)
    ax3.set_title('Voltage Statistics per Capture', fontsize=12, fontweight='bold')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)

    # Plot 4: Transfer timing and data coverage
    ax4 = plt.subplot(4, 1, 4)
    transfer_times = [c['transfer_time'] for c in captures]
    ax4.scatter(cap_times, transfer_times, s=30, alpha=0.7, color='purple')
    ax4.set_xlabel('Time (s)', fontsize=11)
    ax4.set_ylabel('Transfer Time (s)', fontsize=11)
    ax4.set_title('Data Transfer Times (Gap Detection)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)

    # Add average line
    avg_transfer = np.mean(transfer_times)
    ax4.axhline(y=avg_transfer, color='red', linestyle='--', linewidth=1,
                label=f'Avg: {avg_transfer:.3f}s')
    ax4.legend()

    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"Plot saved: {filename}")
    plt.close()

def save_capture_data(captures, filename='10sec_data.csv'):
    """Save all captured data with timestamps"""

    print(f"Saving data to {filename}...")

    rows = []

    for cap in captures:
        base_time = cap['timestamp']
        dt = cap['time_increment']

        for i, v in enumerate(cap['voltages']):
            sample_time = base_time + timedelta(seconds=i * dt)
            rows.append({
                'UTC_Timestamp': sample_time.isoformat(),
                'Time_Offset_s': cap['elapsed'] + i * dt,
                'Capture_Num': cap['capture_num'],
                'Voltage_V': v
            })

    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False)

    file_size_mb = os.path.getsize(filename) / 1024 / 1024
    print(f"Saved {len(rows):,} samples ({file_size_mb:.2f} MB)")

def main():
    print("DS1054Z 10-Second Waveform Capture")
    print("="*70)

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}\n")

    try:
        # Set timebase to 100 microseconds per division
        # Note: Very fast timebases may cause timeout - using 200us instead
        timebase = set_timebase(scope, 200e-6)  # 200us per division

        # Capture for 10 seconds
        captures = continuous_capture(scope, duration_sec=10, channel=1)

        if captures:
            # Statistics
            total_points = sum(c['points'] for c in captures)
            total_time = captures[-1]['elapsed']
            avg_rate = total_points / total_time

            print(f"\n{'='*70}")
            print("RESULTS")
            print('='*70)
            print(f"Total captures:      {len(captures)}")
            print(f"Total points:        {total_points:,}")
            print(f"Duration:            {total_time:.2f} seconds")
            print(f"Effective rate:      {avg_rate:,.0f} points/sec")
            print(f"Avg transfer time:   {np.mean([c['transfer_time'] for c in captures]):.3f}s")

            # Save data
            save_capture_data(captures)

            # Create plot
            create_comprehensive_plot(captures)

            print(f"\n{'='*70}")
            print("SUCCESS!")
            print('='*70)
            print("\nFiles created:")
            print("  - 10sec_data.csv")
            print("  - 10sec_capture.png")

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
        print("\nConnection closed.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
