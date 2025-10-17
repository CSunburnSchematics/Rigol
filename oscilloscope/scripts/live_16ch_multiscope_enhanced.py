#!/usr/bin/env python3
"""
Multi-Scope 16-Channel Real-Time Capture - ENHANCED
Captures from 4 oscilloscopes simultaneously (4 channels each = 16 total)
Features:
- 16 live streaming graphs (main timeline)
- 16 detail waveform plots (last 10 overlaid)
- 4 histograms (one per scope, all channels)
- 4 stats panels (rate, coverage, time per scope)
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
            scope.timeout = 3000  # 3 second timeout for initialization
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

def capture_thread_for_scope(scope_info, config, data_queue, stop_event, stats, channel_names, csv_path):
    """Capture thread for one oscilloscope (4 channels)"""
    scope = scope_info['scope']
    scope_idx = scope_info['index']
    serial = scope_info['serial']

    print(f"[Scope {scope_idx+1} Thread] Started for {serial}")

    # Setup CSV file for this scope
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = os.path.join(csv_path, f'multiscope_{serial}_{timestamp_str}.csv')
    csv_file = open(csv_filename, 'w', newline='')
    csv_writer = csv.writer(csv_file)

    # Use channel names in CSV header
    ch1_name = channel_names.get(1, 'CH1')
    ch2_name = channel_names.get(2, 'CH2')
    ch3_name = channel_names.get(3, 'CH3')
    ch4_name = channel_names.get(4, 'CH4')
    csv_writer.writerow(['UTC_Timestamp', 'Time_Offset_s', f'{ch1_name}_V', f'{ch2_name}_V',
                        f'{ch3_name}_V', f'{ch4_name}_V', 'Capture_Num', 'Elapsed_s'])

    # Setup all 4 channels
    points = config['points_per_channel']
    preamble_caches = []

    print(f"[Scope {scope_idx+1}] Setting up channels...")
    for ch in range(1, 5):
        try:
            cache = setup_channel(scope, ch, points)
            preamble_caches.append(cache)
            print(f"[Scope {scope_idx+1}]   CH{ch}: x_incr={cache['x_increment']*1e6:.1f}us, y_incr={cache['y_increment']*1e3:.1f}mV")
        except Exception as e:
            print(f"[Scope {scope_idx+1}] ERROR: Failed to setup CH{ch}: {e}")
            csv_file.close()
            return

    if len(preamble_caches) != 4:
        print(f"[Scope {scope_idx+1}] ERROR: Only {len(preamble_caches)} channels configured!")
        csv_file.close()
        return

    print(f"[Scope {scope_idx+1}] All channels configured. Starting capture...")

    start_time = time.time()
    capture_count = 0
    first_timestamp = None
    consecutive_errors = 0
    max_consecutive_errors = 10

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
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print(f"[Scope {scope_idx+1}] ERROR: {consecutive_errors} consecutive capture failures. Stopping thread.")
                    break
                continue

            # Reset error counter on successful capture
            consecutive_errors = 0

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
            stats[scope_idx]['elapsed'] = elapsed

            # Small delay to avoid overwhelming the scope
            # Longer delay for larger memory depths
            delay_ms = max(1, points // 1000)  # 1ms per 1000 points
            time.sleep(delay_ms / 1000.0)

        except Exception as e:
            stats[scope_idx]['errors'] = stats[scope_idx].get('errors', 0) + 1
            time.sleep(0.01)

    csv_file.close()
    print(f"\n[Scope {scope_idx+1} Thread] Stopped. Total captures: {capture_count}")
    print(f"[Scope {scope_idx+1} Thread] CSV saved: {csv_filename}")

def on_key(event):
    """Handle key press events"""
    if event.key == 'q':
        print("\n'q' pressed - stopping capture...")
        plt.close('all')

def load_config(config_file):
    """Load configuration from JSON file"""
    # Support both relative and absolute paths
    if os.path.isabs(config_file):
        config_path = config_file
    else:
        config_path = os.path.join(os.path.dirname(__file__), "..", "configs", config_file)

    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        print("Using default settings...")
        return None

    with open(config_path, 'r') as f:
        config = json.load(f)

    print(f"Loaded config: {os.path.basename(config_path)}")
    return config

def main():
    print("="*70)
    print("16-CHANNEL MULTI-SCOPE REAL-TIME CAPTURE - ENHANCED")
    print("="*70)
    print("Press 'q' to quit | Close window to stop")
    print("="*70)

    # Load configuration - config file is required
    if len(sys.argv) < 2:
        print("ERROR: Config file required!")
        print("Usage: python live_16ch_multiscope_enhanced.py <config_file>")
        print("Example: python live_16ch_multiscope_enhanced.py multiscope_config.json")
        return 1

    config_file = sys.argv[1]
    config = load_config(config_file)

    if config is None:
        # Default configuration
        config = {
            'capture_settings': {
                'points_per_channel': 30,
                'timebase_seconds': 0.01,
                'max_display_time_seconds': 5,
                'max_points_per_channel': 5000,
                'update_interval_ms': 100,
                'detail_waveform_count': 10,
                'histogram_bins': 50
            },
            'scopes': {},
            'output': {
                'csv_enabled': True,
                'csv_path': '../../data',
                'screenshot_enabled': True,
                'screenshot_path': '../../plots'
            }
        }

    # Extract capture settings
    capture_config = config['capture_settings']

    # Get output paths from config and resolve relative to config directory
    output_config = config.get('output', {})
    csv_path_config = output_config.get('csv_path', '../../data')
    screenshot_path_config = output_config.get('screenshot_path', '../../plots')

    # Get config directory for resolving relative paths
    config_dir = os.path.dirname(os.path.abspath(config_file)) if os.path.isabs(config_file) else os.path.join(os.path.dirname(__file__), "..", "configs")

    # Resolve paths relative to config directory
    if not os.path.isabs(csv_path_config):
        csv_path = os.path.abspath(os.path.join(config_dir, csv_path_config))
    else:
        csv_path = csv_path_config

    if not os.path.isabs(screenshot_path_config):
        screenshot_path = os.path.abspath(os.path.join(config_dir, screenshot_path_config))
    else:
        screenshot_path = screenshot_path_config

    # Create timestamped session folder using UTC
    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    session_folder_name = f"scope_recording_{timestamp_str}"
    session_folder = os.path.join(csv_path, session_folder_name)

    # Create the session folder (both CSV and screenshots go here)
    os.makedirs(session_folder, exist_ok=True)
    csv_path = session_folder
    screenshot_path = session_folder

    print(f"Recording session folder: {session_folder}")

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
        serial = scope_info['serial']

        print(f"\nConfiguring {serial}...")

        # Apply acquisition settings if configured
        if 'acquisition' in config:
            acq_config = config['acquisition']

            # Set memory depth first
            if 'memory_depth' in acq_config:
                memory_depth = acq_config['memory_depth']
                scope.write(f':ACQuire:MDEPth {memory_depth}')
                time.sleep(0.1)
                print(f"  Memory Depth: {memory_depth} points")

            # Set sample rate explicitly
            if 'sample_rate_msa' in acq_config:
                sample_rate_msa = acq_config['sample_rate_msa']
                sample_rate_sa = sample_rate_msa * 1e6  # Convert MSa/s to Sa/s
                scope.write(f':ACQuire:SRATe {sample_rate_sa}')
                time.sleep(0.1)
                print(f"  Sample Rate: {sample_rate_msa} MSa/s")

                # Verify what was actually set
                try:
                    actual_rate = float(scope.query(':ACQuire:SRATe?'))
                    actual_rate_msa = actual_rate / 1e6
                    print(f"  Verified Sample Rate: {actual_rate_msa:.1f} MSa/s")
                except:
                    pass

        # Set timebase
        scope.write(f':TIMebase:MAIN:SCALe {capture_config["timebase_seconds"]}')
        time.sleep(0.1)

        # Reset time offset to 0 for synchronized capture
        scope.write(':TIMebase:MAIN:OFFSet 0')
        time.sleep(0.05)
        print(f"  Time Offset: Reset to 0")

        # Get scope-specific config if available
        scope_config = config.get('scopes', {}).get(serial, None)

        # Configure all 4 channels
        for ch in range(1, 5):
            if scope_config and 'channels' in scope_config:
                ch_config = scope_config['channels'].get(str(ch), {})

                # Apply channel settings from config
                if ch_config.get('enabled', True):
                    probe = ch_config.get('probe_attenuation', 10)
                    scale = ch_config.get('scale_volts_per_div', 1.0)
                    offset = ch_config.get('offset_volts', 0.0)
                    coupling = ch_config.get('coupling', 'DC')

                    scope.write(f':CHANnel{ch}:PROBe {probe}')
                    time.sleep(0.05)
                    scope.write(f':CHANnel{ch}:SCALe {scale}')
                    time.sleep(0.05)
                    scope.write(f':CHANnel{ch}:OFFSet {offset}')
                    time.sleep(0.05)
                    scope.write(f':CHANnel{ch}:COUPling {coupling}')
                    time.sleep(0.05)
                    scope.write(f':CHANnel{ch}:DISPlay ON')
                    time.sleep(0.02)

                    print(f"  CH{ch}: {scale}V/div, Probe={probe}x, {coupling}")
                else:
                    scope.write(f':CHANnel{ch}:DISPlay OFF')
                    time.sleep(0.02)
                    print(f"  CH{ch}: Disabled")
            else:
                # Default: just turn on the channel
                scope.write(f':CHANnel{ch}:DISPlay ON')
                time.sleep(0.02)

        # Apply trigger settings if configured
        if scope_config and 'trigger' in scope_config:
            trigger_config = scope_config['trigger']
            source = trigger_config.get('source', 'CH1')
            level = trigger_config.get('level_volts', 1.0)
            mode = trigger_config.get('mode', 'EDGE')
            sweep = trigger_config.get('sweep', 'AUTO')

            scope.write(f':TRIGger:EDGe:SOURce {source}')
            time.sleep(0.05)
            scope.write(f':TRIGger:EDGe:LEVel {level}')
            time.sleep(0.05)
            scope.write(f':TRIGger:SWEep {sweep}')
            time.sleep(0.05)

            print(f"  Trigger: {source} at {level}V, {mode} mode, {sweep} sweep")

        scope.write(':RUN')
        time.sleep(0.1)

    print("\nAll scopes configured.")

    # Threading setup
    data_queue = queue.Queue(maxsize=1000)
    stop_event = threading.Event()
    stats = [{} for _ in range(num_scopes)]

    # Extract channel names for each scope
    scope_channel_names = []
    for scope_info in scope_infos:
        serial = scope_info['serial']
        scope_config = config.get('scopes', {}).get(serial, {})
        ch_names = {}
        for ch in range(1, 5):
            ch_config = scope_config.get('channels', {}).get(str(ch), {})
            ch_names[ch] = ch_config.get('name', f'CH{ch}')
        scope_channel_names.append(ch_names)

    # Data storage (per scope, per channel)
    all_times = [[deque(maxlen=capture_config['max_points_per_channel']) for _ in range(4)]
                 for _ in range(num_scopes)]
    all_data = [[deque(maxlen=capture_config['max_points_per_channel']) for _ in range(4)]
                for _ in range(num_scopes)]
    first_timestamps = [None] * num_scopes

    # Store last N waveforms per scope
    last_waveforms = [deque(maxlen=capture_config['detail_waveform_count']) for _ in range(num_scopes)]

    # Start capture threads (one per scope) with staggered startup
    capture_threads = []
    for scope_info in scope_infos:
        scope_idx = scope_info['index']
        thread = threading.Thread(
            target=capture_thread_for_scope,
            args=(scope_info, capture_config, data_queue, stop_event, stats, scope_channel_names[scope_idx], csv_path),
            daemon=True
        )
        thread.start()
        capture_threads.append(thread)
        # Stagger thread startup to avoid USB contention during initialization
        time.sleep(0.5)  # Wait for this thread to initialize before starting next

    print("\nAll threads started, waiting for initialization...")
    time.sleep(1.0)  # Let all threads complete initialization
    run_start_time = time.time()

    # Setup plot with optimized layout
    print("\nInitializing plot...")
    plt.ion()

    # Set background color
    plt.rcParams['figure.facecolor'] = '#f5f3ef'
    plt.rcParams['axes.facecolor'] = '#f5f3ef'
    plt.rcParams['text.color'] = 'black'
    plt.rcParams['axes.labelcolor'] = 'black'
    plt.rcParams['xtick.color'] = 'black'
    plt.rcParams['ytick.color'] = 'black'

    fig = plt.figure(figsize=(28, 20))
    fig.canvas.manager.set_window_title('16-Channel Multi-Scope Capture - Enhanced (Press Q to Quit)')

    # Layout:
    # Column 0: 16 main timeline plots (all channels stacked)
    # Column 1: 16 detail waveform plots (all channels stacked, one column)
    # Column 2: 4 histograms (stacked)
    # Column 3: 4 stats panels (stacked)

    gs = GridSpec(16, 4, figure=fig, hspace=0.8, wspace=0.25,
                  width_ratios=[3.5, 3.0, 1.0, 0.4])

    # Create axes
    main_axes = []  # [16] - all channels as single list
    detail_axes = []  # [scope][channel] - detail waveforms
    hist_axes = []  # [scope] - histogram
    stats_axes = []  # [scope] - stats panel

    # Main timeline plots - Column 0, all 16 channels stacked
    for ch_idx in range(16):
        ax = fig.add_subplot(gs[ch_idx, 0])
        main_axes.append(ax)

    # Detail waveform plots - Column 1, all 16 channels stacked
    for scope_idx in range(num_scopes):
        scope_detail_axes = []
        for ch_idx in range(4):
            row = scope_idx * 4 + ch_idx
            ax = fig.add_subplot(gs[row, 1])
            scope_detail_axes.append(ax)
        detail_axes.append(scope_detail_axes)

    # Histograms - Column 2, 4 scopes stacked (4 rows each)
    for scope_idx in range(num_scopes):
        start_row = scope_idx * 4
        end_row = start_row + 4
        hist_ax = fig.add_subplot(gs[start_row:end_row, 2])
        hist_axes.append(hist_ax)

    # Stats panels - Column 3, 4 scopes stacked (4 rows each)
    for scope_idx in range(num_scopes):
        start_row = scope_idx * 4
        end_row = start_row + 4
        stats_ax = fig.add_subplot(gs[start_row:end_row, 3])
        stats_ax.axis('off')
        stats_axes.append(stats_ax)

    colors = ['red', 'yellow', 'green', 'blue']  # CH1=red (top), CH2=yellow, CH3=green, CH4=blue (bottom)

    # Initialize main timeline plots (16 channels stacked vertically)
    main_scatters = []
    for ch_global in range(16):
        scope_idx = ch_global // 4
        ch_idx = ch_global % 4
        ax = main_axes[ch_global]
        scatter = ax.scatter([], [], c=colors[ch_idx], s=1)
        main_scatters.append(scatter)

        # Labels - use custom channel names from config (max 8 chars per line)
        ch_name = scope_channel_names[scope_idx].get(ch_idx+1, f'CH{ch_idx+1}')
        ch_name = ch_name[:8] if len(ch_name) > 8 else ch_name
        ax.set_ylabel(f'S{scope_idx+1}\n{ch_name}\n(V)', fontsize=5, labelpad=8)
        if ch_global == 15:
            ax.set_xlabel('Time (s)', fontsize=6)
        else:
            ax.set_xticklabels([])

        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=6)

    # Initialize detail plots (all in one column)
    for scope_idx in range(num_scopes):
        for ch_idx in range(4):
            ax = detail_axes[scope_idx][ch_idx]

            # Y-label shows scope and channel with custom name (max 8 chars)
            ch_name = scope_channel_names[scope_idx].get(ch_idx+1, f'CH{ch_idx+1}')
            ch_name = ch_name[:8] if len(ch_name) > 8 else ch_name
            ax.set_ylabel(f'S{scope_idx+1} {ch_name}\n(V)', fontsize=5, labelpad=8)

            # Only show x-label for bottom plot
            if scope_idx == num_scopes - 1 and ch_idx == 3:
                ax.set_xlabel('Sample', fontsize=6)
            else:
                ax.set_xticklabels([])

            # Add title for the very top plot
            if scope_idx == 0 and ch_idx == 0:
                ax.set_title('Last 10 Waveforms', fontsize=8, fontweight='bold', color='#fcb911')

            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=6)

    # Initialize histograms
    for scope_idx in range(num_scopes):
        ax = hist_axes[scope_idx]
        ax.set_title(f'Scope {scope_idx+1}\nVoltage Dist', fontsize=8, fontweight='bold', color='#fcb911')

        # Only show x-label for bottom histogram
        if scope_idx == num_scopes - 1:
            ax.set_xlabel('Voltage (V)', fontsize=6)
        else:
            ax.set_xticklabels([])

        ax.set_ylabel('Count', fontsize=6)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=6)

    # Initialize stats text
    stats_texts = []
    for scope_idx in range(num_scopes):
        ax = stats_axes[scope_idx]
        text = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                      fontsize=5, verticalalignment='top')
        stats_texts.append(text)

    # Connect key handler
    fig.canvas.mpl_connect('key_press_event', on_key)

    plt.subplots_adjust(top=0.995, bottom=0.03, left=0.04, right=0.99)
    plt.show(block=False)
    plt.pause(0.1)

    print("\nCapturing from all scopes...\n")

    last_update = time.time()
    update_interval = capture_config['update_interval_ms'] / 1000.0
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

                    # Store complete waveform for detail view
                    last_waveforms[scope_idx].append(result)

                    data_processed = True

                except queue.Empty:
                    break

            # Update plot periodically
            current_time = time.time()
            if data_processed and (current_time - last_update) > update_interval:
                # Update main timeline plots (16 channels in single column)
                for ch_global in range(16):
                    scope_idx = ch_global // 4
                    ch_idx = ch_global % 4

                    if len(all_times[scope_idx][ch_idx]) > 0:
                        times_array = np.array(all_times[scope_idx][ch_idx])
                        data_array = np.array(all_data[scope_idx][ch_idx])

                        # Filter to show only last N seconds
                        max_time = times_array[-1]
                        min_time = max_time - capture_config['max_display_time_seconds']
                        time_mask = times_array >= min_time

                        filtered_times = times_array[time_mask]
                        filtered_data = data_array[time_mask]

                        # Update scatter plot
                        main_scatters[ch_global].set_offsets(
                            np.c_[filtered_times, filtered_data]
                        )

                        # Auto-scale axes
                        ax = main_axes[ch_global]
                        ax.set_xlim(min_time, max_time)

                        if len(filtered_data) > 0:
                            y_min = np.min(filtered_data)
                            y_max = np.max(filtered_data)
                            y_margin = max((y_max - y_min) * 0.1, 0.01)
                            ax.set_ylim(y_min - y_margin, y_max + y_margin)

                # Update detail waveform plots and histograms per scope
                for scope_idx in range(num_scopes):

                    # Update detail waveform plots (last 10 overlaid)
                    for ch_idx in range(4):
                        ax = detail_axes[scope_idx][ch_idx]
                        ax.clear()

                        # Restore labels with custom channel names (max 8 chars)
                        ch_name = scope_channel_names[scope_idx].get(ch_idx+1, f'CH{ch_idx+1}')
                        ch_name = ch_name[:8] if len(ch_name) > 8 else ch_name
                        ax.set_ylabel(f'S{scope_idx+1} {ch_name}\n(V)', fontsize=5, labelpad=8)

                        if scope_idx == num_scopes - 1 and ch_idx == 3:
                            ax.set_xlabel('Sample', fontsize=6)
                        else:
                            ax.set_xticklabels([])

                        if scope_idx == 0 and ch_idx == 0:
                            ax.set_title('Last 10 Waveforms', fontsize=8, fontweight='bold', color='#fcb911')

                        ax.grid(True, alpha=0.3)
                        ax.tick_params(labelsize=6)

                        # Plot last 10 waveforms
                        for wf_idx, waveform in enumerate(last_waveforms[scope_idx]):
                            alpha = 0.3 + (wf_idx / len(last_waveforms[scope_idx])) * 0.7
                            samples = np.arange(len(waveform['channels'][ch_idx+1]))
                            ax.plot(samples, waveform['channels'][ch_idx+1],
                                   color=colors[ch_idx], alpha=alpha, linewidth=0.8)

                    # Update histogram (all channels combined)
                    hist_ax = hist_axes[scope_idx]
                    hist_ax.clear()

                    # Restore labels
                    hist_ax.set_title(f'Scope {scope_idx+1}\nVoltage Dist', fontsize=8, fontweight='bold', color='#fcb911')

                    if scope_idx == num_scopes - 1:
                        hist_ax.set_xlabel('Voltage (V)', fontsize=6)
                    else:
                        hist_ax.set_xticklabels([])

                    hist_ax.set_ylabel('Count', fontsize=6)
                    hist_ax.grid(True, alpha=0.3)
                    hist_ax.tick_params(labelsize=6)

                    # Collect all voltage data from all channels for this scope
                    all_voltages = []
                    for ch_idx in range(4):
                        all_voltages.extend(list(all_data[scope_idx][ch_idx]))

                    if len(all_voltages) > 0:
                        hist_ax.hist(all_voltages, bins=capture_config['histogram_bins'],
                                    color='purple', alpha=0.7, edgecolor='black')

                    # Update stats panel
                    if stats[scope_idx]:
                        total_elapsed = time.time() - run_start_time
                        caps = stats[scope_idx].get('captures', 0)
                        rate = stats[scope_idx].get('rate', 0)
                        elapsed = stats[scope_idx].get('elapsed', 0)

                        # Calculate coverage - use actual time per waveform from x_increment
                        # Get the actual time increment from the last waveform if available
                        if len(last_waveforms[scope_idx]) > 0:
                            actual_time_increment = last_waveforms[scope_idx][-1]['time_increment']
                            time_per_waveform = capture_config['points_per_channel'] * actual_time_increment
                        else:
                            # Fallback to config estimate
                            time_per_waveform = capture_config['points_per_channel'] * capture_config['timebase_seconds'] / 10

                        total_sample_time = caps * time_per_waveform
                        coverage = (total_sample_time / elapsed * 100) if elapsed > 0 else 0

                        stats_str = (f"S{scope_idx+1}\n"
                                   f"{scope_infos[scope_idx]['serial'][:10]}\n"
                                   f"Rate:\n{rate:.1f}c/s\n"
                                   f"Cov:\n{coverage:.1f}%\n"
                                   f"Caps:\n{caps}\n"
                                   f"Time:\n{elapsed:.0f}s\n"
                                   f"Drop:\n{stats[scope_idx].get('dropped', 0)}\n"
                                   f"Err:\n{stats[scope_idx].get('errors', 0)}")
                        stats_texts[scope_idx].set_text(stats_str)

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

                        status = (f"S{scope_idx+1}: {caps:3d} | {rate:4.1f}c/s | "
                                f"D:{dropped:2d} E:{errors:2d}")
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

    # Save screenshot
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    screenshot_filename = os.path.join(screenshot_path, f'multiscope_16ch_{timestamp_str}.png')
    try:
        print("\nSaving screenshot...")
        fig.savefig(screenshot_filename, dpi=150, bbox_inches='tight')
        print(f"Screenshot saved: {screenshot_filename}")
    except Exception as e:
        print(f"Failed to save screenshot: {e}")

    # Final stats with coverage
    stats_output = []
    stats_output.append("="*70)
    stats_output.append("CAPTURE COMPLETE")
    stats_output.append("="*70)
    stats_output.append(f"Config: {config_file}")
    stats_output.append(f"Memory Depth: {capture_config['points_per_channel']} points")
    stats_output.append(f"Timebase: {capture_config['timebase_seconds']*1e6:.2f} us/div")
    stats_output.append("="*70)

    for scope_idx in range(num_scopes):
        if stats[scope_idx]:
            caps = stats[scope_idx].get('captures', 0)
            rate = stats[scope_idx].get('rate', 0)
            elapsed = stats[scope_idx].get('elapsed', 0)

            # Calculate time per capture and coverage using actual x_increment
            if len(last_waveforms[scope_idx]) > 0:
                actual_time_increment = last_waveforms[scope_idx][-1]['time_increment']
                time_per_capture = capture_config['points_per_channel'] * actual_time_increment
            else:
                # Fallback to config estimate
                time_per_capture = capture_config['points_per_channel'] * capture_config['timebase_seconds'] / 10

            total_sample_time = caps * time_per_capture
            coverage = (total_sample_time / elapsed * 100) if elapsed > 0 else 0

            stats_output.append(f"\nScope {scope_idx+1} ({scope_infos[scope_idx]['serial']}):")

            # Add channel names
            ch_names = scope_channel_names[scope_idx]
            stats_output.append(f"  Channels:")
            stats_output.append(f"    CH1: {ch_names.get(1, 'CH1')}")
            stats_output.append(f"    CH2: {ch_names.get(2, 'CH2')}")
            stats_output.append(f"    CH3: {ch_names.get(3, 'CH3')}")
            stats_output.append(f"    CH4: {ch_names.get(4, 'CH4')}")

            stats_output.append(f"  Captures:         {caps}")
            stats_output.append(f"  Capture Rate:     {rate:.2f} cap/s")
            stats_output.append(f"  Time per Capture: {time_per_capture*1e6:.1f} us")
            stats_output.append(f"  Coverage:         {coverage:.2f}%")
            stats_output.append(f"  Dropped:          {stats[scope_idx].get('dropped', 0)}")
            stats_output.append(f"  Errors:           {stats[scope_idx].get('errors', 0)}")

    # Print to console
    print("\n" + "\n".join(stats_output))

    # Save stats to file
    stats_filename = os.path.join(csv_path, f'performance_{os.path.splitext(os.path.basename(config_file))[0]}_{timestamp_str}.txt')
    try:
        with open(stats_filename, 'w') as f:
            f.write("\n".join(stats_output))
        print(f"\nPerformance stats saved: {stats_filename}")
    except Exception as e:
        print(f"Failed to save stats: {e}")

    # Keep plot open
    print("\nPlot window still open. Close it to exit.")
    plt.show()

    return 0

if __name__ == "__main__":
    sys.exit(main())
