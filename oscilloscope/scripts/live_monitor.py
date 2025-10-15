#!/usr/bin/env python3
"""
Live oscilloscope monitor with real-time updating plots
Captures data continuously and updates visualization every few seconds
"""

import sys
import os
import time
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime, timezone, timedelta
from collections import deque

# Enable interactive mode
plt.ion()

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
    scope.timeout = 10000  # Increased timeout to 10 seconds
    return scope

def capture_waveform(scope, channel=1):
    """Capture single waveform"""
    capture_start = datetime.now(timezone.utc)

    # Stop acquisition first to clear any busy state
    scope.write(':STOP')
    time.sleep(0.2)

    # Start acquisition and wait for data to be ready
    scope.write(':RUN')
    time.sleep(0.5)  # Longer wait for acquisition to complete

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

class LiveMonitor:
    """Real-time oscilloscope monitor"""

    def __init__(self, scope, channel=1, max_captures=100, csv_filename=None):
        self.scope = scope
        self.channel = channel
        self.max_captures = max_captures

        # Data storage
        self.captures = []
        self.start_time = time.time()

        # Running statistics
        self.capture_count = 0
        self.total_points = 0
        self.all_voltages = deque(maxlen=10000)  # Keep last 10k voltage samples

        # Plot update control (only update every N captures to reduce lag)
        self.update_every = 3  # Update plot every 3 captures
        self.last_plot_update = 0

        # CSV file for raw data
        if csv_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f'../../data/live_monitor_{timestamp}.csv'

        self.csv_filename = csv_filename
        self.csv_file = open(self.csv_filename, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)

        # Write CSV header
        self.csv_writer.writerow(['UTC_Timestamp', 'Time_Offset_s', 'Voltage_V',
                                   'Capture_Num', 'Elapsed_Time_s'])
        self.csv_file.flush()

        print(f"CSV logging to: {csv_filename}\n")

        # Create figure and subplots - 4 rows, 1 column
        self.fig = plt.figure(figsize=(16, 14))
        self.fig.canvas.manager.set_window_title('Live Oscilloscope Monitor')

        self.ax1 = plt.subplot(4, 1, 1)  # Real-time UTC waveform data
        self.ax2 = plt.subplot(4, 1, 2)  # Transfer times
        self.ax3 = plt.subplot(4, 1, 3)  # Sample waveforms (scatter)
        self.ax4 = plt.subplot(4, 1, 4)  # Voltage distribution

        # Initialize plots
        self.ax1.set_xlabel('UTC Time')
        self.ax1.set_ylabel('Voltage (V)')
        self.ax1.set_title('Waveform Data on Real-Time Axis (UTC)')
        self.ax1.grid(True, alpha=0.3)

        self.ax2.set_xlabel('Elapsed Time (s)')
        self.ax2.set_ylabel('Transfer Time (s)')
        self.ax2.set_title('Data Transfer Times (Gap Detection)')
        self.ax2.grid(True, alpha=0.3)

        self.ax3.set_xlabel('Time (us)')
        self.ax3.set_ylabel('Voltage (V)')
        self.ax3.set_title('Sample Waveforms (Last 3 Captures - Scatter)')
        self.ax3.grid(True, alpha=0.3)

        self.ax4.set_xlabel('Voltage (V)')
        self.ax4.set_ylabel('Count')
        self.ax4.set_title('Overall Voltage Distribution')
        self.ax4.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        # Status text
        self.status_text = self.fig.text(0.5, 0.02, '', ha='center', fontsize=10,
                                         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    def capture_and_update(self, retry_count=2):
        """Capture one waveform and update displays"""
        for attempt in range(retry_count):
            try:
                # Capture waveform
                result = capture_waveform(self.scope, self.channel)

                elapsed = time.time() - self.start_time
                result['capture_num'] = self.capture_count
                result['elapsed'] = elapsed

                # Write to CSV immediately
                self._write_capture_to_csv(result)

                # Store capture
                self.captures.append(result)
                if len(self.captures) > self.max_captures:
                    self.captures.pop(0)

                # Update running statistics
                self.capture_count += 1
                self.total_points += len(result['voltages'])
                self.all_voltages.extend(result['voltages'])

                # Print to console
                print(f"[{elapsed:6.1f}s] Capture #{self.capture_count:3d}: "
                      f"{len(result['voltages']):,} pts in {result['transfer_time']:.3f}s | "
                      f"V: {result['v_min']:.3f} to {result['v_max']:.3f}", flush=True)

                # Update plots only every N captures to reduce lag
                if self.capture_count - self.last_plot_update >= self.update_every:
                    self.update_plots()
                    self.last_plot_update = self.capture_count

                return True

            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"ERROR (retry {attempt+1}/{retry_count}): {str(e)[:60]}", flush=True)
                    time.sleep(1.0)  # Wait before retry
                else:
                    print(f"ERROR (giving up): {str(e)[:60]}", flush=True)
                    return False

        return False

    def _write_capture_to_csv(self, result):
        """Write a single capture to CSV file"""
        base_time = result['timestamp']
        dt = result['time_increment']
        capture_num = result['capture_num']
        elapsed = result['elapsed']

        # Write each voltage sample with its UTC timestamp
        for i, voltage in enumerate(result['voltages']):
            sample_time = base_time + timedelta(seconds=i * dt)
            time_offset = i * dt

            self.csv_writer.writerow([
                sample_time.isoformat(),
                f'{time_offset:.9f}',
                f'{voltage:.6f}',
                capture_num,
                f'{elapsed:.3f}'
            ])

        # Flush to ensure data is written to disk immediately
        self.csv_file.flush()

    def update_plots(self):
        """Update all plot panels"""

        if not self.captures:
            return

        # Extract data
        times = [c['elapsed'] for c in self.captures]
        transfer_times = [c['transfer_time'] for c in self.captures]

        # Plot 1: Real-time UTC waveform data
        self.ax1.clear()

        # Plot all voltage samples on UTC timeline
        for cap in self.captures:
            # Calculate UTC time for each sample point
            base_time = cap['timestamp']
            dt = cap['time_increment']

            # Create array of UTC times for this capture
            utc_times = [base_time + timedelta(seconds=i * dt) for i in range(len(cap['voltages']))]

            # Scatter plot showing actual data capture times
            self.ax1.scatter(utc_times, cap['voltages'], s=1, alpha=0.6, c='blue')

        self.ax1.set_xlabel('UTC Time')
        self.ax1.set_ylabel('Voltage (V)')
        self.ax1.set_title('Waveform Data on Real-Time Axis (UTC) - Shows Capture Gaps')
        self.ax1.grid(True, alpha=0.3)

        # Rotate x-axis labels for readability
        self.ax1.tick_params(axis='x', rotation=45)

        # Format x-axis to show time nicely
        import matplotlib.dates as mdates
        self.ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S.%f'))
        self.fig.autofmt_xdate()

        # Plot 2: Transfer times (update scatter)
        self.ax2.clear()
        self.ax2.scatter(times, transfer_times, s=20, alpha=0.6, c='purple')
        self.ax2.set_xlabel('Time (s)')
        self.ax2.set_ylabel('Transfer Time (s)')
        self.ax2.set_title('Data Transfer Times')
        self.ax2.grid(True, alpha=0.3)

        if len(transfer_times) > 1:
            avg_transfer = np.mean(transfer_times)
            self.ax2.axhline(y=avg_transfer, color='red', linestyle='--',
                           linewidth=1, label=f'Avg: {avg_transfer:.3f}s')
            self.ax2.legend()

        # Plot 3: Sample waveforms (scatter plot, last 3 captures)
        self.ax3.clear()

        num_samples = min(3, len(self.captures))
        indices = [-3, -2, -1][-num_samples:]  # Last 3
        colors = ['blue', 'green', 'red'][-num_samples:]
        labels = ['3rd Last', '2nd Last', 'Latest'][-num_samples:]

        for idx, color, label in zip(indices, colors, labels):
            if idx >= -len(self.captures):
                cap = self.captures[idx]
                wf_times = np.arange(len(cap['voltages'])) * cap['time_increment'] * 1e6

                # Use scatter instead of plot
                self.ax3.scatter(wf_times, cap['voltages'], s=1, alpha=0.6,
                               c=color, label=label)

        self.ax3.set_xlabel('Time (us)')
        self.ax3.set_ylabel('Voltage (V)')
        self.ax3.set_title('Sample Waveforms (Last 3 Captures - Scatter)')
        self.ax3.legend(markerscale=10)
        self.ax3.grid(True, alpha=0.3)

        # Plot 4: Voltage distribution
        self.ax4.clear()

        if len(self.all_voltages) > 0:
            voltages_array = np.array(self.all_voltages)
            self.ax4.hist(voltages_array, bins=50, color='purple',
                         alpha=0.7, edgecolor='black')

        self.ax4.set_xlabel('Voltage (V)')
        self.ax4.set_ylabel('Count')
        self.ax4.set_title(f'Voltage Distribution (Last {len(self.all_voltages):,} samples)')
        self.ax4.grid(True, alpha=0.3, axis='y')

        # Update status text
        elapsed = time.time() - self.start_time
        rate = self.total_points / elapsed if elapsed > 0 else 0
        status = (f"Captures: {self.capture_count} | "
                 f"Total Points: {self.total_points:,} | "
                 f"Runtime: {elapsed:.1f}s | "
                 f"Rate: {rate:,.0f} pts/s")
        self.status_text.set_text(status)

        # Redraw
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def run(self, duration_sec=60, capture_interval=0.3):
        """Run live monitoring for specified duration"""

        print("="*70)
        print("LIVE OSCILLOSCOPE MONITOR")
        print("="*70)
        print(f"Duration: {duration_sec} seconds")
        print(f"Capture interval: {capture_interval} seconds")
        print(f"Channel: {self.channel}")
        print("\nStarting capture... (Close plot window to stop)")
        print("="*70)
        print()

        end_time = time.time() + duration_sec

        try:
            while time.time() < end_time and plt.fignum_exists(self.fig.number):
                # Capture and update
                success = self.capture_and_update()

                # Wait before next capture
                if success:
                    time.sleep(capture_interval)
                else:
                    time.sleep(capture_interval * 3)  # Much longer delay on error to let scope recover

        except KeyboardInterrupt:
            print("\n\nStopped by user")

        # Final update
        self.update_plots()

        # Save final plot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'../../plots/live_monitor_{timestamp}.png'
        self.fig.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n\nFinal plot saved: {filename}")

        # Close CSV file
        self.csv_file.close()
        print(f"CSV data saved: {self.csv_filename}")

        # Keep plot window open
        print("Close plot window to exit...")
        plt.ioff()
        plt.show()

    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'csv_file') and not self.csv_file.closed:
            self.csv_file.close()

def main():
    print("DS1054Z Live Monitor\n")

    scope = connect_scope()
    if not scope:
        print("ERROR: Could not connect to oscilloscope")
        return 1

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}\n")

    monitor = None
    try:
        # Initialize scope - clear any busy state
        print("Initializing oscilloscope...")
        scope.write(':STOP')
        time.sleep(0.5)
        scope.write('*CLS')  # Clear status
        time.sleep(0.5)

        # Check current timebase
        timebase = scope.query(':TIMebase:MAIN:SCALe?').strip()
        print(f"Current timebase: {float(timebase)*1e6:.1f} us/div")
        print("Oscilloscope ready.\n")

        # Create and run live monitor
        monitor = LiveMonitor(scope, channel=1, max_captures=100)
        monitor.run(duration_sec=60, capture_interval=0.5)  # Increased interval to reduce timeouts

        print("\n" + "="*70)
        print("MONITORING COMPLETE")
        print("="*70)
        print(f"Total captures: {monitor.capture_count}")
        print(f"Total points: {monitor.total_points:,}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Ensure CSV file is closed
        if monitor:
            monitor.cleanup()

        scope.close()
        print("\nConnection closed.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
