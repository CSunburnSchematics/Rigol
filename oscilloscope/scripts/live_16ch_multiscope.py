#!/usr/bin/env python3
"""
Multi-Scope 16-Channel Real-Time Capture
Captures from 4 oscilloscopes simultaneously (4 channels each = 16 total)
Features:
- 16 live streaming graphs (4×4 grid)
- Separate capture thread per oscilloscope
- Individual CSV output per scope
- Press 'q' to quit
"""

import sys
import os
import time
import threading
import queue
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime, timezone
from collections import deque

def connect_to_scopes():
    """Connect to all available oscilloscopes"""
    dll_path = os.path.join(os.path.dirname(__file__), "..", "lib", "libusb-1.0.dll")
    os.environ['PATH'] = os.path.dirname(dll_path) + os.pathsep + os.environ.get('PATH', '')

    import pyvisa
    rm = pyvisa.ResourceManager('@py')
    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        print("ERROR: No oscilloscopes found!")
        return []

    print(f"\nFound {len(usb_resources)} oscilloscope(s)")

    scopes = []
    for i, resource in enumerate(usb_resources):
        try:
            scope = rm.open_resource(resource)
            scope.timeout = 1000
            scope.chunk_size = 102400

            idn = scope.query('*IDN?').strip()
            serial = idn.split(',')[2] if len(idn.split(',')) >= 3 else f"Scope{i+1}"

            scopes.append({
                'scope': scope,
                'resource': resource,
                'idn': idn,
                'serial': serial,
                'index': i
            })
            print(f"  Scope {i+1}: {serial}")
        except Exception as e:
            print(f"  Scope {i+1}: Failed to connect - {e}")

    return scopes

def setup_channel(scope, channel, points=30):
    """Setup and cache preamble for one channel"""
    scope.write(f':WAVeform:SOURce CHANnel{channel}')
    scope.write(':WAVeform:MODE RAW')
    scope.write(':WAVeform:FORMat BYTE')
    scope.write(f':WAVeform:POINts {points}')
    time.sleep(0.02)

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

        header_len = 2 + int(chr(raw_data[1]))
        data = raw_data[header_len:-1]
        waveform_data = np.frombuffer(data, dtype=np.uint8)

        voltages = ((waveform_data - preamble_cache['y_reference']) *
                   preamble_cache['y_increment']) + preamble_cache['y_origin']

        return voltages
    except:
        return None

def capture_thread_for_scope(scope_info, config, data_queue, stop_event, stats):
    """Capture thread for one oscilloscope (4 channels)"""
    scope = scope_info['scope']
    scope_idx = scope_info['index']
    serial = scope_info['serial']

    print(f"[Scope {scope_idx+1} Thread] Started for {serial}")

    # Setup CSV file for this scope
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'../../data/multiscope_{serial}_{timestamp_str}.csv'
    csv_file = open(csv_filename, 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['UTC_Timestamp', 'Time_Offset_s', 'CH1_V', 'CH2_V', 'CH3_V', 'CH4_V',
                        'Capture_Num', 'Elapsed_s'])

    # Setup all 4 channels
    points = config['points_per_channel']
    preamble_caches = []
    for ch in range(1, 5):
        cache = setup_channel(scope, ch, points)
        preamble_caches.append(cache)

    start_time = time.time()
    capture_count = 0
    first_timestamp = None

    while not stop_event.is_set():
        try:
            # Capture all 4 channels
            capture_start = time.time()
            timestamp = datetime.now(timezone.utc)
            channels_data = {}

            for ch in range(1, 5):
                voltages = capture_channel(scope, ch, preamble_caches[ch-1])
                if voltages is None:
                    break
                channels_data[ch] = voltages

            if len(channels_data) != 4:
                continue

            transfer_time = time.time() - capture_start
            elapsed = time.time() - start_time
            capture_count += 1

            if first_timestamp is None:
                first_timestamp = timestamp

            # Write to CSV
            time_offset = (timestamp - first_timestamp).total_seconds()
            for i in range(len(channels_data[1])):
                t = time_offset + i * preamble_caches[0]['x_increment']
                row = [
                    timestamp.isoformat(),
                    f'{t:.9f}',
                    f'{channels_data[1][i]:.6f}',
                    f'{channels_data[2][i]:.6f}',
                    f'{channels_data[3][i]:.6f}',
                    f'{channels_data[4][i]:.6f}',
                    capture_count,
                    f'{elapsed:.3f}'
                ]
                csv_writer.writerow(row)

            # Queue result for plotting
            result = {
                'scope_idx': scope_idx,
                'serial': serial,
                'timestamp': timestamp,
                'channels': channels_data,
                'points_per_channel': len(channels_data[1]),
                'time_increment': preamble_caches[0]['x_increment'],
                'transfer_time': transfer_time,
                'capture_num': capture_count,
                'elapsed': elapsed
            }

            try:
                data_queue.put_nowait(result)
            except queue.Full:
                stats[scope_idx]['dropped'] = stats[scope_idx].get('dropped', 0) + 1

            # Update stats
            stats[scope_idx]['captures'] = capture_count
            stats[scope_idx]['rate'] = capture_count / elapsed if elapsed > 0 else 0

        except Exception as e:
            stats[scope_idx]['errors'] = stats[scope_idx].get('errors', 0) + 1

    csv_file.close()
    print(f"[Scope {scope_idx+1} Thread] Stopped. Total captures: {capture_count}")
    print(f"[Scope {scope_idx+1} Thread] CSV saved: {csv_filename}")

def on_key(event):
    """Handle key press events"""
    if event.key == 'q':
        print("\n'q' pressed - stopping capture...")
        plt.close('all')

def main():
    print("="*70)
    print("16-CHANNEL MULTI-SCOPE REAL-TIME CAPTURE")
    print("="*70)
    print("Press 'q' to quit | Close window to stop")
    print("="*70)

    # Configuration
    config = {
        'points_per_channel': 30,
        'timebase_seconds': 0.01,  # 10ms/div
        'max_display_time_seconds': 5,
        'max_points_per_channel': 5000,
        'update_interval_ms': 100
    }

    # Connect to all scopes
    scope_infos = connect_to_scopes()

    if len(scope_infos) == 0:
        print("ERROR: No oscilloscopes connected!")
        return 1

    num_scopes = len(scope_infos)
    print(f"\nInitializing {num_scopes} oscilloscopes...")

    # Configure all scopes
    for scope_info in scope_infos:
        scope = scope_info['scope']
        scope.write(f':TIMebase:MAIN:SCALe {config["timebase_seconds"]}')
        time.sleep(0.1)

        # Turn on all channels
        for ch in range(1, 5):
            scope.write(f':CHANnel{ch}:DISPlay ON')
            time.sleep(0.02)

        scope.write(':RUN')
        time.sleep(0.1)

    print("All scopes configured.")

    # Threading setup
    data_queue = queue.Queue(maxsize=1000)
    stop_event = threading.Event()
    stats = [{} for _ in range(num_scopes)]

    # Data storage (per scope, per channel)
    all_times = [[deque(maxlen=config['max_points_per_channel']) for _ in range(4)]
                 for _ in range(num_scopes)]
    all_data = [[deque(maxlen=config['max_points_per_channel']) for _ in range(4)]
                for _ in range(num_scopes)]
    first_timestamps = [None] * num_scopes

    # Start capture threads (one per scope)
    capture_threads = []
    for scope_info in scope_infos:
        thread = threading.Thread(
            target=capture_thread_for_scope,
            args=(scope_info, config, data_queue, stop_event, stats),
            daemon=True
        )
        thread.start()
        capture_threads.append(thread)

    time.sleep(0.5)  # Let threads start

    # Setup plot - 4×4 grid (4 scopes × 4 channels)
    print("\nInitializing plot...")
    plt.ion()

    fig = plt.figure(figsize=(20, 16))
    gs = GridSpec(4, 4, figure=fig, hspace=0.4, wspace=0.3)

    axes = []
    for scope_idx in range(num_scopes):
        scope_axes = []
        for ch_idx in range(4):
            ax = fig.add_subplot(gs[scope_idx, ch_idx])
            scope_axes.append(ax)
        axes.append(scope_axes)

    colors = ['blue', 'orange', 'green', 'red']

    # Initialize plots
    scatters = []
    for scope_idx in range(num_scopes):
        scope_scatters = []
        for ch_idx in range(4):
            ax = axes[scope_idx][ch_idx]
            scatter = ax.scatter([], [], c=colors[ch_idx], s=1)
            scope_scatters.append(scatter)

            # Labels
            if scope_idx == 0:
                ax.set_title(f'CH{ch_idx+1}', fontsize=10, fontweight='bold')
            if ch_idx == 0:
                ax.set_ylabel(f'Scope {scope_idx+1}\n(V)', fontsize=9)
            if scope_idx == num_scopes - 1:
                ax.set_xlabel('Time (s)', fontsize=8)

            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=7)

        scatters.append(scope_scatters)

    fig.suptitle('16-Channel Multi-Scope Capture (Press Q to Quit)',
                 fontsize=14, fontweight='bold')

    # Connect key handler
    fig.canvas.mpl_connect('key_press_event', on_key)

    plt.show(block=False)
    plt.pause(0.1)

    print("\nCapturing from all scopes...\n")

    last_update = time.time()
    update_interval = config['update_interval_ms'] / 1000.0
    last_stats_print = time.time()

    try:
        while plt.fignum_exists(fig.number):
            # Process all available data from queue
            data_processed = False
            while not data_queue.empty():
                try:
                    result = data_queue.get_nowait()

                    scope_idx = result['scope_idx']

                    # Set first timestamp for this scope
                    if first_timestamps[scope_idx] is None:
                        first_timestamps[scope_idx] = result['timestamp']

                    # Calculate time offset
                    time_offset = (result['timestamp'] - first_timestamps[scope_idx]).total_seconds()

                    # Add data points to rolling window
                    for ch in range(1, 5):
                        ch_idx = ch - 1
                        for i in range(result['points_per_channel']):
                            t = time_offset + i * result['time_increment']
                            all_times[scope_idx][ch_idx].append(t)
                            all_data[scope_idx][ch_idx].append(result['channels'][ch][i])

                    data_processed = True

                except queue.Empty:
                    break

            # Update plot periodically
            current_time = time.time()
            if data_processed and (current_time - last_update) > update_interval:
                # Update each scope's plots
                for scope_idx in range(num_scopes):
                    for ch_idx in range(4):
                        if len(all_times[scope_idx][ch_idx]) > 0:
                            times_array = np.array(all_times[scope_idx][ch_idx])
                            data_array = np.array(all_data[scope_idx][ch_idx])

                            # Filter to show only last N seconds
                            max_time = times_array[-1]
                            min_time = max_time - config['max_display_time_seconds']
                            time_mask = times_array >= min_time

                            filtered_times = times_array[time_mask]
                            filtered_data = data_array[time_mask]

                            # Update scatter plot
                            scatters[scope_idx][ch_idx].set_offsets(
                                np.c_[filtered_times, filtered_data]
                            )

                            # Auto-scale axes
                            ax = axes[scope_idx][ch_idx]
                            ax.set_xlim(min_time, max_time)

                            if len(filtered_data) > 0:
                                y_min = np.min(filtered_data)
                                y_max = np.max(filtered_data)
                                y_margin = max((y_max - y_min) * 0.1, 0.01)
                                ax.set_ylim(y_min - y_margin, y_max + y_margin)

                fig.canvas.draw_idle()
                fig.canvas.flush_events()
                last_update = current_time

            # Print stats periodically
            if current_time - last_stats_print > 2.0:
                status_lines = []
                for scope_idx in range(num_scopes):
                    if stats[scope_idx]:
                        caps = stats[scope_idx].get('captures', 0)
                        rate = stats[scope_idx].get('rate', 0)
                        dropped = stats[scope_idx].get('dropped', 0)
                        errors = stats[scope_idx].get('errors', 0)

                        # Calculate voltage ranges
                        v_ranges = []
                        for ch_idx in range(4):
                            if len(all_data[scope_idx][ch_idx]) > 0:
                                v_min = np.min(all_data[scope_idx][ch_idx])
                                v_max = np.max(all_data[scope_idx][ch_idx])
                                v_ranges.append(f"{v_min:.2f}-{v_max:.2f}V")
                            else:
                                v_ranges.append("N/A")

                        status = (f"Scope {scope_idx+1}: {caps:3d} cap | {rate:4.1f} cap/s | "
                                f"D:{dropped:2d} E:{errors:2d} | {' '.join(v_ranges)}")
                        status_lines.append(status)

                print("\r" + " | ".join(status_lines), end="", flush=True)
                last_stats_print = current_time

            # Small sleep
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    # Stop all capture threads
    print("\n\nStopping all capture threads...")
    stop_event.set()

    for thread in capture_threads:
        thread.join(timeout=2.0)

    # Close all scopes
    for scope_info in scope_infos:
        try:
            scope_info['scope'].close()
        except:
            pass

    # Final stats
    print("\n" + "="*70)
    print("CAPTURE COMPLETE")
    print("="*70)
    for scope_idx in range(num_scopes):
        if stats[scope_idx]:
            print(f"Scope {scope_idx+1} ({scope_infos[scope_idx]['serial']}):")
            print(f"  Captures: {stats[scope_idx].get('captures', 0)}")
            print(f"  Rate: {stats[scope_idx].get('rate', 0):.2f} cap/s")
            print(f"  Dropped: {stats[scope_idx].get('dropped', 0)}")
            print(f"  Errors: {stats[scope_idx].get('errors', 0)}")

    # Keep plot open
    print("\nPlot window still open. Close it to exit.")
    plt.show()

    return 0

if __name__ == "__main__":
    sys.exit(main())
