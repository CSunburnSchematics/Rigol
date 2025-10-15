#!/usr/bin/env python3
"""
Real-time 4-channel capture with live plotting
Uses threading to capture at full speed while plotting updates smoothly
Features:
- Press 'q' to quit
- Saves data to CSV as captured
- Shows last 10 waveforms in separate subplot
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
matplotlib.use('TkAgg')  # Interactive backend
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
from collections import deque

def connect_scope(serial_number=None):
    """Connect to oscilloscope

    Args:
        serial_number: Optional serial number to connect to specific scope
                      (e.g., "DS1ZA273M00260")
    """
    dll_path = os.path.join(os.path.dirname(__file__), "..", "lib", "libusb-1.0.dll")
    os.environ['PATH'] = os.path.dirname(dll_path) + os.pathsep + os.environ.get('PATH', '')

    import pyvisa
    rm = pyvisa.ResourceManager('@py')
    resources = rm.list_resources()
    usb_resources = [r for r in resources if 'USB' in r and ('1AB1' in r.upper() or '6833' in r)]

    if not usb_resources:
        return None

    # If serial number specified, find matching resource
    if serial_number:
        matching = [r for r in usb_resources if serial_number in r]
        if matching:
            usb_resources = matching
            print(f"Connecting to scope with serial: {serial_number}")
        else:
            print(f"WARNING: Scope with serial {serial_number} not found!")
            print(f"Available scopes: {len(usb_resources)}")
            for r in usb_resources:
                print(f"  - {r}")
            return None

    scope = rm.open_resource(usb_resources[0])
    scope.timeout = 1000  # Will be set from config in main
    scope.chunk_size = 102400  # Will be set from config in main
    return scope

def setup_channel(scope, channel, points=120):
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

def capture_all_channels(scope, preamble_caches):
    """Capture all 4 channels as fast as possible"""
    capture_start = time.time()
    timestamp = datetime.now(timezone.utc)
    channels_data = {}

    for ch in range(1, 5):
        voltages = capture_channel(scope, ch, preamble_caches[ch-1])
        if voltages is None:
            return None
        channels_data[ch] = voltages

    transfer_time = time.time() - capture_start
    time_span = len(channels_data[1]) * preamble_caches[0]['x_increment']

    return {
        'timestamp': timestamp,
        'channels': channels_data,
        'points_per_channel': len(channels_data[1]),
        'time_span': time_span,
        'time_increment': preamble_caches[0]['x_increment'],
        'transfer_time': transfer_time
    }

def capture_thread(scope, preamble_caches, data_queue, stop_event, stats, csv_writer, csv_lock):
    """Background thread - captures as fast as possible and saves to CSV"""
    print("[Capture Thread] Started")
    start_time = time.time()
    capture_count = 0
    first_timestamp = None

    while not stop_event.is_set():
        result = capture_all_channels(scope, preamble_caches)

        if result:
            elapsed = time.time() - start_time
            result['elapsed'] = elapsed
            capture_count += 1

            if first_timestamp is None:
                first_timestamp = result['timestamp']

            # Write to CSV (if enabled)
            if csv_writer:
                with csv_lock:
                    time_offset = (result['timestamp'] - first_timestamp).total_seconds()
                    for i in range(result['points_per_channel']):
                        t = time_offset + i * result['time_increment']
                        row = [
                            result['timestamp'].isoformat(),
                            f'{t:.9f}',
                            f'{result["channels"][1][i]:.6f}',
                            f'{result["channels"][2][i]:.6f}',
                            f'{result["channels"][3][i]:.6f}',
                            f'{result["channels"][4][i]:.6f}',
                            capture_count,
                            f'{elapsed:.3f}'
                        ]
                        csv_writer.writerow(row)

            try:
                data_queue.put_nowait(result)

                # Update stats
                stats['capture_count'] = capture_count
                stats['elapsed'] = elapsed
                stats['capture_rate'] = capture_count / elapsed if elapsed > 0 else 0

            except queue.Full:
                # Queue full, skip this capture
                stats['dropped_count'] = stats.get('dropped_count', 0) + 1

    print(f"[Capture Thread] Stopped. Total captures: {capture_count}")

def on_key(event):
    """Handle key press events"""
    if event.key == 'q':
        print("\n'q' pressed - stopping capture...")
        plt.close('all')

def load_config(config_file):
    """Load configuration from JSON file"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", config_file)

    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        print("Using default config instead...")
        config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "default_capture_config.json")

    with open(config_path, 'r') as f:
        config = json.load(f)

    print(f"Loaded config: {os.path.basename(config_path)}")
    return config

def main():
    # Load configuration
    config_file = sys.argv[1] if len(sys.argv) > 1 else "default_capture_config.json"
    config = load_config(config_file)

    print("DS1054Z 4-Channel Real-Time Capture (Config-Driven)")
    print("="*70)
    print("Press 'q' to quit | Close window to stop")
    print("="*70)

    # Get serial number from config if specified
    serial_number = config.get('serial_number', None)

    scope = connect_scope(serial_number)
    if not scope:
        print("ERROR: Could not connect to oscilloscope")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}")

    # Apply oscilloscope config from JSON
    scope.timeout = config['oscilloscope']['timeout_ms']
    scope.chunk_size = config['oscilloscope']['chunk_size']

    # Set timebase
    timebase_val = config['oscilloscope']['timebase_seconds']
    scope.write(f':TIMebase:MAIN:SCALe {timebase_val}')
    time.sleep(0.2)
    print(f"Timebase set to: {timebase_val*1e6:.1f} us/div")

    # Configure all 4 channels from config
    print("\nConfiguring channels...")
    for ch in range(1, 5):
        ch_config = config['oscilloscope']['channels'][str(ch)]

        if ch_config['enabled']:
            # Set probe attenuation
            scope.write(f':CHANnel{ch}:PROBe {ch_config["probe_attenuation"]}')
            time.sleep(0.05)
            # Set voltage scale
            scope.write(f':CHANnel{ch}:SCALe {ch_config["scale_volts_per_div"]}')
            time.sleep(0.05)
            # Set offset
            scope.write(f':CHANnel{ch}:OFFSet {ch_config["offset_volts"]}')
            time.sleep(0.05)
            # Set coupling
            scope.write(f':CHANnel{ch}:COUPling {ch_config["coupling"]}')
            time.sleep(0.05)
            # Turn channel on
            scope.write(f':CHANnel{ch}:DISPlay ON')
            time.sleep(0.05)
        else:
            # Turn channel off
            scope.write(f':CHANnel{ch}:DISPlay OFF')
            time.sleep(0.05)

    # Small delay for scope to process
    time.sleep(0.3)

    # Read back settings to verify
    print("\nReading back channel settings:")
    for ch in range(1, 5):
        try:
            scale = scope.query(f':CHANnel{ch}:SCALe?').strip()
            offset = scope.query(f':CHANnel{ch}:OFFSet?').strip()
            coupling = scope.query(f':CHANnel{ch}:COUPling?').strip()
            probe = scope.query(f':CHANnel{ch}:PROBe?').strip()
            print(f"  CH{ch}: Scale={float(scale):.2f}V/div, Offset={float(offset):.2f}V, "
                  f"Coupling={coupling}, Probe={float(probe):.0f}x")
        except Exception as e:
            print(f"  CH{ch}: Query failed - {e}")

    # Make sure running
    scope.write(f':{config["oscilloscope"]["run_mode"]}')
    time.sleep(0.2)

    # Setup all 4 channels for data capture
    points = config['capture_settings']['points_per_channel']
    print(f"\nSetting up capture ({points} points per channel)...")
    preamble_caches = []
    for ch in range(1, 5):
        if config['oscilloscope']['channels'][str(ch)]['enabled']:
            cache = setup_channel(scope, ch, points)
            preamble_caches.append(cache)
            print(f"  CH{ch}: Ready (x_incr: {cache['x_increment']*1e6:.3f}us, y_incr: {cache['y_increment']*1e3:.3f}mV)")

    print("="*70)

    # Setup CSV file
    if config['output']['csv_enabled']:
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'{config["output"]["csv_path"]}/{config["output"]["csv_prefix"]}_{timestamp_str}.csv'
        csv_file = open(csv_filename, 'w', newline='')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['UTC_Timestamp', 'Time_Offset_s', 'CH1_V', 'CH2_V', 'CH3_V', 'CH4_V', 'Capture_Num', 'Elapsed_s'])
        csv_lock = threading.Lock()
        print(f"Saving to: {csv_filename}")
    else:
        csv_file = None
        csv_writer = None
        csv_lock = None
        print("CSV output disabled")

    # Threading setup
    data_queue = queue.Queue(maxsize=100)
    stop_event = threading.Event()
    stats = {'capture_count': 0, 'elapsed': 0, 'capture_rate': 0, 'dropped_count': 0}

    # Data storage (rolling window) - from config
    max_display_time = config['capture_settings']['max_display_time_seconds']
    max_points_per_channel = config['capture_settings']['max_points_per_channel']

    all_times = deque(maxlen=max_points_per_channel)
    all_data = {ch: deque(maxlen=max_points_per_channel) for ch in range(1, 5)}

    # Store last N complete waveforms for detail view
    detail_count = config['display']['detail_waveform_count']
    last_waveforms = deque(maxlen=detail_count)

    # Track 10-second window stats
    captures_last_10s = deque(maxlen=1000)  # Store (timestamp, capture_num)

    first_timestamp = None
    run_start_time = time.time()

    # Start capture thread
    capture_thread_obj = threading.Thread(
        target=capture_thread,
        args=(scope, preamble_caches, data_queue, stop_event, stats, csv_writer, csv_lock),
        daemon=True
    )
    capture_thread_obj.start()

    # Setup plot with GridSpec for custom layout
    print("\nInitializing plot...")
    plt.ion()  # Interactive mode

    from matplotlib.gridspec import GridSpec
    fig = plt.figure(figsize=(config['display']['figure_width'], config['display']['figure_height']))
    gs = GridSpec(6, 5, figure=fig, height_ratios=[1, 1, 1, 1, 0.8, 0.8],
                  hspace=0.6, wspace=0.3)

    # Main 4 channel plots (top 4 rows, spanning all columns)
    main_axes = []
    for i in range(4):
        ax = fig.add_subplot(gs[i, :])
        main_axes.append(ax)

    # Last 10 waveforms plots (row 4, first 4 columns)
    detail_axes = []
    for i in range(4):
        ax = fig.add_subplot(gs[4, i])
        detail_axes.append(ax)

    # Stats display (row 4, column 4)
    stats_ax = fig.add_subplot(gs[4, 4])
    stats_ax.axis('off')
    stats_text = stats_ax.text(0.05, 0.95, '', transform=stats_ax.transAxes,
                              fontsize=9, verticalalignment='top',
                              fontfamily='monospace')

    # Voltage histogram (row 5, spanning all columns)
    hist_ax = fig.add_subplot(gs[5, :])
    hist_ax.set_xlabel('Voltage (V)', fontsize=9)
    hist_ax.set_ylabel('Count', fontsize=9)
    hist_ax.set_title('Voltage Distribution (All Channels, Entire Run)', fontsize=10)
    hist_ax.grid(True, alpha=0.3)
    hist_ax.tick_params(labelsize=8)

    colors = ['blue', 'orange', 'green', 'red']
    channel_names = ['CH1', 'CH2', 'CH3', 'CH4']

    # Main plot scatter plots
    main_scatters = []
    for i, ax in enumerate(main_axes):
        scatter = ax.scatter([], [], c=colors[i], s=1, label=channel_names[i])
        main_scatters.append(scatter)
        ax.set_ylabel(f'{channel_names[i]}\n(V)', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=8)

    main_axes[-1].set_xlabel('Time (seconds)', fontsize=10)

    # Detail plot setup
    for i, ax in enumerate(detail_axes):
        ax.set_title(f'{channel_names[i]} - Last 10', fontsize=8)
        ax.set_xlabel('Sample', fontsize=7)
        ax.set_ylabel('V', fontsize=7)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=7)

    fig.suptitle('4-Channel Real-Time Capture (Press Q to Quit)', fontsize=13, fontweight='bold', y=0.995)

    # Connect key handler
    fig.canvas.mpl_connect('key_press_event', on_key)

    plt.subplots_adjust(top=0.97, bottom=0.05, left=0.05, right=0.98)
    plt.show(block=False)
    plt.pause(0.1)

    print("\nCapturing... (close plot window to stop)\n")

    last_update = time.time()
    update_interval = config['capture_settings']['update_interval_ms'] / 1000.0  # Convert to seconds
    last_stats_print = time.time()

    try:
        while plt.fignum_exists(fig.number):
            # Process all available data from queue
            data_processed = False
            while not data_queue.empty():
                try:
                    result = data_queue.get_nowait()

                    # Set first timestamp
                    if first_timestamp is None:
                        first_timestamp = result['timestamp']

                    # Calculate time offset
                    time_offset = (result['timestamp'] - first_timestamp).total_seconds()

                    # Add data points to rolling window
                    for i in range(result['points_per_channel']):
                        t = time_offset + i * result['time_increment']
                        all_times.append(t)

                        for ch in range(1, 5):
                            all_data[ch].append(result['channels'][ch][i])

                    # Store complete waveform for detail view
                    last_waveforms.append(result)

                    # Track captures for 10-second window stats
                    captures_last_10s.append((result['timestamp'], stats['capture_count']))

                    data_processed = True

                except queue.Empty:
                    break

            # Update plot periodically
            current_time = time.time()
            if data_processed and (current_time - last_update) > update_interval:
                if len(all_times) > 0:
                    # Convert deques to arrays for plotting
                    times_array = np.array(all_times)

                    # Filter to show only last 10 seconds
                    max_time = times_array[-1]
                    min_time = max_time - max_display_time
                    time_mask = times_array >= min_time

                    # Update main scatter plots with filtered data
                    for ch in range(1, 5):
                        data_array = np.array(all_data[ch])
                        filtered_times = times_array[time_mask]
                        filtered_data = data_array[time_mask]
                        main_scatters[ch-1].set_offsets(np.c_[filtered_times, filtered_data])

                    # Auto-scale main axes with fixed x-range
                    for i, ax in enumerate(main_axes):
                        if len(all_data[i+1]) > 0:
                            ax.set_xlim(min_time, max_time)
                            # Only auto-scale y-axis
                            data_array = np.array(all_data[i+1])
                            filtered_data = data_array[time_mask]
                            if len(filtered_data) > 0:
                                y_min = np.min(filtered_data)
                                y_max = np.max(filtered_data)
                                y_margin = (y_max - y_min) * 0.1
                                ax.set_ylim(y_min - y_margin, y_max + y_margin)

                    # Update detail plots (last 10 waveforms overlaid)
                    for ch_idx in range(4):
                        ch = ch_idx + 1
                        ax = detail_axes[ch_idx]
                        ax.clear()
                        ax.set_title(f'{channel_names[ch_idx]} - Last 10', fontsize=8)
                        ax.set_xlabel('Sample', fontsize=7)
                        ax.set_ylabel('V', fontsize=7)
                        ax.grid(True, alpha=0.3)
                        ax.tick_params(labelsize=7)

                        # Plot last 10 waveforms
                        for wf_idx, waveform in enumerate(last_waveforms):
                            alpha = 0.3 + (wf_idx / len(last_waveforms)) * 0.7  # Fade older ones
                            samples = np.arange(len(waveform['channels'][ch]))
                            ax.plot(samples, waveform['channels'][ch],
                                   color=colors[ch_idx], alpha=alpha, linewidth=0.5)

                    # Update voltage histogram
                    hist_ax.clear()
                    hist_ax.set_xlabel('Voltage (V)', fontsize=9)
                    hist_ax.set_ylabel('Count', fontsize=9)
                    hist_ax.set_title('Voltage Distribution (All Channels, Entire Run)', fontsize=10)
                    hist_ax.grid(True, alpha=0.3)
                    hist_ax.tick_params(labelsize=8)

                    # Collect all voltage data from all channels
                    all_voltages = []
                    for ch in range(1, 5):
                        all_voltages.extend(list(all_data[ch]))

                    if len(all_voltages) > 0:
                        hist_ax.hist(all_voltages, bins=config['display']['histogram_bins'], color='purple', alpha=0.7, edgecolor='black')

                    # Calculate 10-second window stats
                    if len(captures_last_10s) > 1:
                        # Filter to last 10 seconds
                        now = datetime.now(timezone.utc)
                        cutoff = now - timedelta(seconds=10)
                        recent_captures = [(ts, cnt) for ts, cnt in captures_last_10s if ts >= cutoff]

                        if len(recent_captures) > 1:
                            time_span_10s = (recent_captures[-1][0] - recent_captures[0][0]).total_seconds()
                            captures_10s = recent_captures[-1][1] - recent_captures[0][1]
                            rate_10s = captures_10s / time_span_10s if time_span_10s > 0 else 0

                            # Calculate coverage for last 10 seconds
                            total_sample_time_10s = captures_10s * preamble_caches[0]['x_increment'] * 120
                            coverage_10s = (total_sample_time_10s / time_span_10s) * 100 if time_span_10s > 0 else 0
                        else:
                            rate_10s = 0
                            coverage_10s = 0
                    else:
                        rate_10s = 0
                        coverage_10s = 0

                    # Calculate overall stats
                    total_elapsed = time.time() - run_start_time
                    total_rate = stats['capture_count'] / total_elapsed if total_elapsed > 0 else 0
                    total_sample_time = stats['capture_count'] * preamble_caches[0]['x_increment'] * 120
                    total_coverage = (total_sample_time / total_elapsed) * 100 if total_elapsed > 0 else 0

                    # Update stats text
                    stats_str = (f"LAST 10s:\n"
                                f"  Rate: {rate_10s:.2f} cap/s\n"
                                f"  Cov:  {coverage_10s:.2f}%\n\n"
                                f"OVERALL:\n"
                                f"  Rate: {total_rate:.2f} cap/s\n"
                                f"  Cov:  {total_coverage:.2f}%\n"
                                f"  Time: {total_elapsed:.1f}s\n"
                                f"  Caps: {stats['capture_count']}")
                    stats_text.set_text(stats_str)

                    # Update display
                    fig.canvas.draw_idle()
                    fig.canvas.flush_events()

                    last_update = current_time

            # Print stats periodically
            if current_time - last_stats_print > 2.0:
                # Calculate voltage ranges
                v_ranges = []
                for ch in range(1, 5):
                    if len(all_data[ch]) > 0:
                        data_array = np.array(all_data[ch])
                        v_min = np.min(data_array)
                        v_max = np.max(data_array)
                        v_ranges.append(f"CH{ch}:{v_min:.2f}-{v_max:.2f}V")
                    else:
                        v_ranges.append(f"CH{ch}:N/A")

                print(f"Captures: {stats['capture_count']:4d} | "
                      f"Rate: {stats['capture_rate']:5.2f} cap/s | "
                      f"Queue: {data_queue.qsize():3d} | "
                      f"Dropped: {stats.get('dropped_count', 0):3d} | "
                      f"Points: {len(all_times):6d} | "
                      f"{' | '.join(v_ranges)}",
                      flush=True)
                last_stats_print = current_time

            # Small sleep to prevent CPU spinning
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    # Stop capture thread
    print("\nStopping capture...")
    stop_event.set()
    capture_thread_obj.join(timeout=2.0)

    # Close CSV file
    if csv_file:
        csv_file.close()

    # Save screenshot of the plot
    if config['output']['screenshot_enabled']:
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_filename = f'{config["output"]["screenshot_path"]}/{config["output"]["screenshot_prefix"]}_{timestamp_str}.png'
        try:
            fig.savefig(screenshot_filename, dpi=150, bbox_inches='tight')
            print(f"\nScreenshot saved: {screenshot_filename}")
        except Exception as e:
            print(f"\nFailed to save screenshot: {e}")

    # Final stats
    print(f"\n{'='*70}")
    print("CAPTURE COMPLETE")
    print('='*70)
    print(f"Total captures:  {stats['capture_count']}")
    print(f"Duration:        {stats['elapsed']:.1f}s")
    print(f"Capture rate:    {stats['capture_rate']:.2f} captures/sec")
    print(f"Dropped:         {stats.get('dropped_count', 0)}")
    print(f"Total points:    {len(all_times)} displayed")
    if csv_file:
        print(f"CSV saved:       {csv_filename}")

    scope.close()
    print("\nConnection closed.")

    # Keep plot open
    print("\nPlot window still open. Close it to exit.")
    plt.show()

    return 0

if __name__ == "__main__":
    sys.exit(main())
