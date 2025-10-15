#!/usr/bin/env python3
"""
Simple 4-channel continuous capture
Captures all 4 channels for 10 seconds, then creates a simple waveform plot
"""

import sys
import os
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')  # No GUI during capture
import matplotlib.pyplot as plt
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
    scope.timeout = 1000
    scope.chunk_size = 102400
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

def create_waveform_plot(captures, timebase_name):
    """Create simple 4-channel waveform plot"""
    print("\nCreating waveform visualization...")

    fig, axes = plt.subplots(4, 1, figsize=(16, 10), sharex=True)

    colors = ['blue', 'orange', 'green', 'red']
    channel_names = ['CH1', 'CH2', 'CH3', 'CH4']

    # Plot each channel
    for ch_idx in range(4):
        ax = axes[ch_idx]
        ch = ch_idx + 1

        print(f"  Plotting Channel {ch}...")

        # Collect all waveform data for this channel across all captures
        for cap_idx, cap in enumerate(captures):
            # Calculate absolute time for each sample
            base_time = cap['timestamp']
            dt = cap['time_increment']

            # Time array in seconds relative to first capture
            if cap_idx == 0:
                time_offset = 0
            else:
                time_offset = (cap['timestamp'] - captures[0]['timestamp']).total_seconds()

            times = np.arange(len(cap['channels'][ch])) * dt + time_offset
            voltages = cap['channels'][ch]

            # Plot as connected line for continuous look
            ax.plot(times, voltages, color=colors[ch_idx], linewidth=0.5, alpha=0.7)

        # Format subplot
        ax.set_ylabel(f'{channel_names[ch_idx]}\nVoltage (V)', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, captures[-1]['elapsed'] if captures else 10)

    # Only show x-label on bottom plot
    axes[-1].set_xlabel('Time (seconds)', fontsize=11)

    # Main title
    fig.suptitle(f'4-Channel Waveform Capture @ {timebase_name}/div ({len(captures)} captures)',
                 fontsize=14, fontweight='bold')

    plt.tight_layout()

    return fig

def main():
    print("DS1054Z 4-Channel Simple Capture")
    print("="*70)

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect to oscilloscope")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}")

    # Get current settings
    timebase = scope.query(':TIMebase:MAIN:SCALe?').strip()
    timebase_val = float(timebase)
    print(f"Timebase: {timebase_val*1e6:.1f} us/div")

    if timebase_val < 100e-6:
        timebase_name = f"{timebase_val*1e9:.0f}ns"
    elif timebase_val < 1e-3:
        timebase_name = f"{timebase_val*1e6:.0f}us"
    else:
        timebase_name = f"{timebase_val*1e3:.0f}ms"

    # Make sure running
    scope.write(':RUN')
    time.sleep(0.2)
    print("Scope running")

    # Setup all 4 channels (120 points each for best coverage)
    points = 120
    print(f"\nSetting up 4 channels ({points} points each)...")
    preamble_caches = []
    for ch in range(1, 5):
        cache = setup_channel(scope, ch, points)
        preamble_caches.append(cache)
        print(f"  CH{ch}: Ready")

    print("="*70)

    # Capture parameters
    duration = 10  # 10 seconds
    captures = []
    start_time = time.time()
    success_count = 0

    print(f"\nCapturing 4 channels for {duration} seconds...")
    print("Press Ctrl+C to stop early\n")

    try:
        while time.time() - start_time < duration:
            result = capture_all_channels(scope, preamble_caches)

            if result:
                elapsed = time.time() - start_time
                result['elapsed'] = elapsed
                captures.append(result)
                success_count += 1

                if success_count <= 5 or success_count % 10 == 0:
                    total_pts = result['points_per_channel'] * 4
                    print(f"[{elapsed:5.1f}s] #{success_count:3d}: {total_pts:,} pts total "
                          f"({result['points_per_channel']:,} pts/ch) "
                          f"in {result['transfer_time']:.3f}s", flush=True)

    except KeyboardInterrupt:
        print("\n\nStopped by user")

    # Statistics
    total_time = time.time() - start_time
    total_points = sum(c['points_per_channel'] * 4 for c in captures)
    total_data_time = sum(c['time_span'] for c in captures)
    coverage_pct = (total_data_time / total_time) * 100 if total_time > 0 else 0

    print(f"\n{'='*70}")
    print("CAPTURE COMPLETE")
    print('='*70)
    print(f"Duration:        {total_time:.1f}s")
    print(f"Captures:        {success_count}")
    print(f"Total points:    {total_points:,} ({total_points/4:,.0f} per channel)")
    print(f"Capture rate:    {success_count/total_time:.2f} captures/sec")
    print(f"Coverage:        {coverage_pct:.2f}%")
    print(f"Data rate:       {total_points/total_time:,.0f} points/sec")

    if captures:
        # Create visualization
        fig = create_waveform_plot(captures, timebase_name)

        # Save
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        plot_filename = f'../../plots/4ch_waveforms_{timestamp_str}.png'
        fig.savefig(plot_filename, dpi=150, bbox_inches='tight')

        print(f"\nPlot saved: {plot_filename}")
        print(f"Total waveform time span: {total_data_time*1e3:.1f}ms")

    scope.close()
    print("\nConnection closed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
