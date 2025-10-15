#!/usr/bin/env python3
"""
RAW mode with acquisition status checking
Waits for scope to complete acquisition before reading
"""

import sys
import os
import time
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')  # No GUI during capture
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta

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
    scope.timeout = 500  # Shorter timeout - fail fast
    scope.chunk_size = 20480  # Larger chunks for faster transfer
    return scope

def wait_for_acquisition(scope, max_wait=0.1):
    """Wait for scope to complete acquisition - with timeout"""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            status = scope.query(':TRIGger:STATus?').strip()
            # Status can be: TD (triggered), WAIT (waiting for trigger), RUN (running), AUTO, STOP
            if status in ['TD', 'STOP']:  # Triggered or stopped - data ready
                return True, status
            time.sleep(0.005)  # 5ms check interval
        except:
            return False, None
    return False, None

def capture_raw_data_checked(scope, channel=1):
    """RAW buffer read with acquisition status check"""
    capture_start = datetime.now(timezone.utc)

    # Check if acquisition is complete
    wait_start = time.time()
    ready, status = wait_for_acquisition(scope, max_wait=0.2)
    wait_time = time.time() - wait_start

    if not ready:
        return None  # Not ready, skip this attempt

    # Configure for RAW mode
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE RAW')
    scope.write(':WAVeform:FORMat BYTE')

    # Get preamble with scaling info
    preamble = scope.query(':WAVeform:PREamble?')
    preamble_values = [float(x) for x in preamble.split(',')]

    points = int(preamble_values[2])
    x_increment = preamble_values[4]
    y_increment = preamble_values[7]
    y_origin = preamble_values[8]
    y_reference = preamble_values[9]

    # Transfer waveform data
    transfer_start = time.time()
    scope.write(':WAVeform:DATA?')
    raw_data = scope.read_raw()
    transfer_time = time.time() - transfer_start

    # Parse IEEE 488.2 binary block format
    header_len = 2 + int(chr(raw_data[1]))
    data = raw_data[header_len:-1]
    waveform_data = np.frombuffer(data, dtype=np.uint8)

    # Convert to voltages
    voltages = ((waveform_data - y_reference) * y_increment) + y_origin

    return {
        'timestamp': capture_start,
        'voltages': voltages,
        'time_increment': x_increment,
        'transfer_time': transfer_time,
        'wait_time': wait_time,
        'status': status,
        'points': points,
        'v_max': np.max(voltages),
        'v_min': np.min(voltages),
        'v_avg': np.mean(voltages)
    }

def create_final_plot(captures):
    """Create 4-panel visualization from all captures"""
    print("\nCreating visualization...")

    fig = plt.figure(figsize=(16, 14))

    ax1 = plt.subplot(4, 1, 1)  # UTC timeline
    ax2 = plt.subplot(4, 1, 2)  # Transfer times
    ax3 = plt.subplot(4, 1, 3)  # Sample waveforms
    ax4 = plt.subplot(4, 1, 4)  # Voltage distribution

    # Plot 1: UTC timeline
    print("  Plotting UTC timeline...")
    for cap in captures:
        base_time = cap['timestamp']
        dt = cap['time_increment']
        utc_times = [base_time + timedelta(seconds=i * dt) for i in range(len(cap['voltages']))]
        ax1.scatter(utc_times, cap['voltages'], s=1, alpha=0.6, c='blue')

    ax1.set_xlabel('UTC Time', fontsize=11)
    ax1.set_ylabel('Voltage (V)', fontsize=11)
    ax1.set_title(f'Waveform Data on UTC Timeline ({len(captures)} captures)', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Plot 2: Transfer times and wait times
    print("  Plotting transfer and wait times...")
    times = [c['elapsed'] for c in captures]
    transfer_times = [c['transfer_time'] for c in captures]
    wait_times = [c['wait_time'] for c in captures]

    ax2.scatter(times, transfer_times, s=30, alpha=0.6, c='purple', label='Transfer time')
    ax2.scatter(times, wait_times, s=30, alpha=0.6, c='orange', label='Wait time')

    if len(transfer_times) > 1:
        avg_transfer = np.mean(transfer_times)
        avg_wait = np.mean(wait_times)
        ax2.axhline(y=avg_transfer, color='purple', linestyle='--',
                   linewidth=1, alpha=0.5, label=f'Avg transfer: {avg_transfer:.3f}s')
        ax2.axhline(y=avg_wait, color='orange', linestyle='--',
                   linewidth=1, alpha=0.5, label=f'Avg wait: {avg_wait:.3f}s')
        ax2.legend()

    ax2.set_xlabel('Elapsed Time (s)', fontsize=11)
    ax2.set_ylabel('Time (s)', fontsize=11)
    ax2.set_title('Data Transfer and Wait Times', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # Plot 3: Sample waveforms (last 3)
    print("  Plotting sample waveforms...")
    num_samples = min(3, len(captures))
    indices = [-3, -2, -1][-num_samples:]
    colors = ['blue', 'green', 'red'][-num_samples:]
    labels = ['3rd Last', '2nd Last', 'Latest'][-num_samples:]

    for idx, color, label in zip(indices, colors, labels):
        if idx >= -len(captures):
            cap = captures[idx]
            # Downsample if too many points for plotting
            voltages = cap['voltages']
            if len(voltages) > 10000:
                step = len(voltages) // 10000
                voltages = voltages[::step]
            wf_times = np.arange(len(voltages)) * cap['time_increment'] * 1e6
            ax3.plot(wf_times, voltages, alpha=0.6, color=color, label=label, linewidth=0.5)

    ax3.set_xlabel('Time (us)', fontsize=11)
    ax3.set_ylabel('Voltage (V)', fontsize=11)
    ax3.set_title('Sample Waveforms (Last 3 Captures)', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Plot 4: Voltage distribution
    print("  Plotting voltage distribution...")
    all_voltages = np.concatenate([c['voltages'] for c in captures])

    ax4.hist(all_voltages, bins=50, color='purple', alpha=0.7, edgecolor='black')
    ax4.set_xlabel('Voltage (V)', fontsize=11)
    ax4.set_ylabel('Count', fontsize=11)
    ax4.set_title(f'Voltage Distribution ({len(all_voltages):,} total samples)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    return fig

def main():
    print("DS1054Z RAW Mode with Acquisition Status Check")
    print("="*70)

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect to oscilloscope")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}")

    # Setup
    timebase = scope.query(':TIMebase:MAIN:SCALe?').strip()
    print(f"Timebase: {float(timebase)*1e6:.1f} us/div")

    # Make sure scope is running
    scope.write(':RUN')
    time.sleep(0.2)

    # Get initial trigger status
    try:
        trig_status = scope.query(':TRIGger:STATus?').strip()
        print(f"Initial trigger status: {trig_status}")
    except:
        print("Could not read trigger status")

    # Get memory depth info
    mdepth = scope.query(':ACQuire:MDEPth?').strip()
    print(f"Memory depth: {mdepth}")

    print("Scope running - waiting for acquisitions to complete")

    # Setup CSV
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'../../data/raw_checked_{timestamp_str}.csv'
    csv_file = open(csv_filename, 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['UTC_Timestamp', 'Time_Offset_s', 'Voltage_V', 'Capture_Num', 'Elapsed_Time_s', 'Trigger_Status'])

    print(f"CSV: {csv_filename}")
    print("="*70)

    # Capture parameters
    duration = 30  # 30 seconds
    min_interval = 0.01  # Minimum time between capture attempts

    captures = []
    start_time = time.time()
    attempt_count = 0
    not_ready_count = 0
    timeout_count = 0
    success_count = 0

    print(f"\nCapturing for {duration} seconds...")
    print("Press Ctrl+C to stop early\n")

    try:
        while time.time() - start_time < duration:
            try:
                result = capture_raw_data_checked(scope, channel=1)

                if result is None:
                    # Acquisition not ready yet
                    not_ready_count += 1
                    if not_ready_count % 20 == 1:
                        elapsed = time.time() - start_time
                        print(f"[{elapsed:6.1f}s] Not ready #{not_ready_count}", flush=True)
                    time.sleep(min_interval)
                    attempt_count += 1
                    continue

                elapsed = time.time() - start_time
                result['capture_num'] = success_count
                result['elapsed'] = elapsed

                # Write to CSV
                base_time = result['timestamp']
                dt = result['time_increment']
                voltages = result['voltages']
                status = result['status']

                # Subsample if needed
                if len(voltages) > 10000:
                    step = len(voltages) // 10000
                    sample_indices = range(0, len(voltages), step)
                else:
                    sample_indices = range(len(voltages))

                for i in sample_indices:
                    sample_time = base_time + timedelta(seconds=i * dt)
                    csv_writer.writerow([
                        sample_time.isoformat(),
                        f'{i * dt:.9f}',
                        f'{voltages[i]:.6f}',
                        success_count,
                        f'{elapsed:.3f}',
                        status
                    ])
                csv_file.flush()

                captures.append(result)
                success_count += 1

                # Calculate time since last capture
                time_since_last = elapsed - captures[-2]['elapsed'] if len(captures) > 1 else elapsed

                print(f"[{elapsed:6.1f}s] #{success_count:3d}: {len(result['voltages']):,} pts "
                      f"| Wait: {result['wait_time']:.3f}s Transfer: {result['transfer_time']:.3f}s "
                      f"| Interval: {time_since_last:.3f}s | Status: {status} "
                      f"| V: {result['v_min']:.3f} to {result['v_max']:.3f}",
                      flush=True)

                time.sleep(min_interval)

            except KeyboardInterrupt:
                raise
            except Exception as e:
                timeout_count += 1
                # Print first few errors for debugging
                if timeout_count <= 3:
                    print(f"  [Error: {str(e)[:60]}]", flush=True)
                elif timeout_count % 10 == 0:
                    print(f"  [error #{timeout_count}]", flush=True)
                time.sleep(min_interval * 2)

            attempt_count += 1

    except KeyboardInterrupt:
        print("\n\nStopped by user")

    csv_file.close()

    # Statistics
    total_time = time.time() - start_time
    total_points = sum(len(c['voltages']) for c in captures)

    print(f"\n{'='*70}")
    print("CAPTURE COMPLETE")
    print('='*70)
    print(f"Duration:        {total_time:.1f}s")
    print(f"Attempts:        {attempt_count}")
    print(f"Successes:       {success_count}")
    print(f"Not ready:       {not_ready_count}")
    print(f"Timeouts:        {timeout_count}")
    print(f"Success rate:    {success_count/attempt_count*100:.1f}%")
    print(f"Total points:    {total_points:,}")
    print(f"Capture rate:    {success_count/total_time:.2f} captures/sec")
    print(f"Data rate:       {total_points/total_time:,.0f} points/sec")

    if len(captures) > 1:
        intervals = [captures[i]['elapsed'] - captures[i-1]['elapsed']
                    for i in range(1, len(captures))]
        print(f"Avg interval:    {np.mean(intervals):.3f}s")
        print(f"Min interval:    {np.min(intervals):.3f}s")
        print(f"Max interval:    {np.max(intervals):.3f}s")

        wait_times = [c['wait_time'] for c in captures]
        print(f"Avg wait time:   {np.mean(wait_times):.3f}s")

    if captures:
        # Create visualization
        fig = create_final_plot(captures)

        # Save
        plot_filename = f'../../plots/raw_checked_{timestamp_str}.png'
        fig.savefig(plot_filename, dpi=150, bbox_inches='tight')

        print(f"\nPlot saved: {plot_filename}")
        print(f"CSV saved:  {csv_filename}")

    scope.close()
    print("\nConnection closed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
