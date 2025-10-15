#!/usr/bin/env python3
"""
Power Supply Continuous Logger with Live Plotting
Real-time graphical monitoring of power supply voltages/currents with CSV logging.
Press 'q' to quit and save data.
"""

import sys
import os
import time
import csv
import json
import threading
import queue
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime, timezone
from collections import deque
from rigol_usb_locator import RigolUsbLocator
from nice_power_usb_locator import NicePowerLocator


class PowerSupplyMonitorLive:
    def __init__(self, config_file, sample_interval_ms=1000, max_display_time_seconds=10):
        """
        Initialize live power supply monitor

        Args:
            config_file: JSON configuration file
            sample_interval_ms: Sampling interval in milliseconds
            max_display_time_seconds: Maximum time to display on graphs (seconds)
        """
        self.config_file = config_file
        self.sample_interval = sample_interval_ms / 1000.0
        self.max_display_time = max_display_time_seconds
        self.config = self._load_config()

        # Initialize locators
        self.rigol_loc = RigolUsbLocator(verbose=False)
        self.nice_loc = NicePowerLocator(verbose=False)
        self.nice_loc.refresh()
        self.rigol_loc.refresh()

        # Storage for power supply objects
        self.rigol_psu = None
        self.nice_psu_list = []

        # CSV file handles
        self.csv_files = {}
        self.csv_writers = {}

        # Data storage for plotting (time series)
        self.times_rigol = [deque(maxlen=10000) for _ in range(3)]  # 3 channels
        self.voltages_rigol = [deque(maxlen=10000) for _ in range(3)]
        self.currents_rigol = [deque(maxlen=10000) for _ in range(3)]

        self.times_nice = []  # Will be populated based on number of supplies
        self.voltages_nice = []
        self.currents_nice = []

        # Statistics
        self.start_time = None
        self.sample_count = 0
        self.stop_event = threading.Event()
        self.data_queue = queue.Queue(maxsize=1000)

    def _load_config(self):
        """Load configuration from JSON file"""
        possible_paths = [
            self.config_file,
            os.path.join("Configs", self.config_file),
            os.path.join("oscilloscope", "configs", self.config_file),
            os.path.join("..", "Configs", self.config_file),
            os.path.join("..", "oscilloscope", "configs", self.config_file),
        ]

        config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break

        if not config_path:
            raise FileNotFoundError(f"Config file '{self.config_file}' not found")

        with open(config_path, 'r') as f:
            config = json.load(f)

        print(f"Loaded config: {self.config_file}")
        return config

    def connect_supplies(self):
        """Connect to all power supplies"""
        print("\n=== Connecting to Power Supplies ===")

        self.rigol_psu = self.rigol_loc.get_power_supply()
        if self.rigol_psu:
            print("[OK] Connected to Rigol Power Supply")
        else:
            print("[WARN] No Rigol Power Supply found")

        self.nice_psu_list = self.nice_loc.get_power_supplies()
        print(f"[OK] Found {len(self.nice_psu_list)} Nice Power supply(s)")

        # Initialize Nice Power data storage
        for _ in self.nice_psu_list:
            self.times_nice.append(deque(maxlen=10000))
            self.voltages_nice.append(deque(maxlen=10000))
            self.currents_nice.append(deque(maxlen=10000))

    def setup_csv_files(self):
        """Setup single unified CSV file for all power supplies"""
        timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')
        log_dir = "power_supply_logs"
        os.makedirs(log_dir, exist_ok=True)

        print("\n=== Setting up CSV log file ===")

        # Build column headers
        headers = ['UTC_Timestamp', 'Elapsed_s', 'Sample_Num']

        # Add Rigol columns if present
        if self.rigol_psu:
            headers.extend(['Rigol_CH1_V', 'Rigol_CH1_A', 'Rigol_CH1_W',
                           'Rigol_CH2_V', 'Rigol_CH2_A', 'Rigol_CH2_W',
                           'Rigol_CH3_V', 'Rigol_CH3_A', 'Rigol_CH3_W'])

        # Add Nice Power columns
        self.nice_psu_ids = []  # Store IDs for later use
        for idx, (com_port, device_type, addr, psu) in enumerate(self.nice_psu_list):
            psu_id = None
            if device_type == "d2001":
                psu_id = "SPPS_D2001_232"
            else:
                for psu_name, psu_cfg in self.config["power_supplies"]["nice_power"].items():
                    if psu_cfg.get("com_port") == com_port:
                        psu_id = psu_name
                        break

            if psu_id:
                self.nice_psu_ids.append(psu_id)
                # Use short names: D2001, D6001, D8001
                short_name = psu_id.split('_')[1]
                headers.extend([f'{short_name}_V', f'{short_name}_A', f'{short_name}_W'])
            else:
                self.nice_psu_ids.append(None)

        # Create single CSV file
        filename = os.path.join(log_dir, f"all_power_supplies_{timestamp_str}.csv")
        csv_file = open(filename, 'w', newline='')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(headers)

        self.csv_files['unified'] = csv_file
        self.csv_writers['unified'] = csv_writer
        print(f"[OK] Unified log: {filename}")

    def configure_supplies(self):
        """Configure all power supplies to initial setpoints"""
        print("\n=== Configuring Power Supplies ===")

        if self.rigol_psu:
            print("Rigol Power Supply (DP832A):")
            try:
                for ch in [1, 2, 3]:
                    psu_config = self.config["power_supplies"]["rigol"]["DP8B261601128"]["channels"][str(ch)]
                    voltage = psu_config["vout"]
                    current = psu_config["iout_max"]
                    enabled = psu_config.get("enabled", True)

                    if not enabled:
                        self.rigol_psu.turn_channel_off(ch)
                        self.rigol_psu.set_voltage(ch, 0.0)
                        print(f"  CH{ch}: [OFF] Disabled")
                        continue

                    self.rigol_psu.turn_channel_on(ch)
                    self.rigol_psu.set_voltage(ch, voltage)
                    self.rigol_psu.set_current_limit(ch, current)
                    time.sleep(2)

                    v_meas, i_meas, p_meas = self.rigol_psu.read_power_supply_channel(ch)
                    print(f"  CH{ch}: [OK] Set={voltage}V/{current}A, Measured={v_meas:.4f}V/{i_meas:.4f}A")
                print()
            except Exception as e:
                print(f"  [FAIL] Error configuring Rigol: {e}\n")

        if self.nice_psu_list:
            print(f"Nice Power Supplies ({len(self.nice_psu_list)} found):")

        for com_port, device_type, addr, psu in self.nice_psu_list:
            try:
                psu_config = None
                psu_id = None

                if device_type == "d2001":
                    psu_config = self.config["power_supplies"]["nice_power"]["SPPS_D2001_232"]
                    psu_id = "SPPS_D2001_232"
                else:
                    for psu_name, psu_cfg in self.config["power_supplies"]["nice_power"].items():
                        if psu_cfg.get("com_port") == com_port:
                            psu_config = psu_cfg
                            psu_id = psu_name
                            break

                if not psu_config:
                    print(f"  {com_port}: [SKIP] No config")
                    continue

                voltage = psu_config["vout"]
                current = psu_config["iout_max"]
                enabled = psu_config.get("enabled", True)

                if not enabled:
                    psu.set_voltage(0.0)
                    if hasattr(psu, 'turn_off'):
                        psu.turn_off()
                    print(f"  {psu_id} ({com_port}): [OFF] Disabled")
                    continue

                if device_type == "modbus" and hasattr(psu, 'configure_voltage_current'):
                    psu.configure_voltage_current(voltage, current, verify=True, max_retries=3, tol=0.2)
                else:
                    psu.set_remote(True)
                    psu.set_current_limit(current)
                    psu.set_voltage(voltage)
                    if voltage > 0:
                        psu.turn_on()

                time.sleep(2)

                v_meas = psu.measure_voltage()
                i_meas = psu.measure_current()
                print(f"  {psu_id} ({com_port}): [OK] Set={voltage}V/{current}A, Measured={v_meas:.4f}V/{i_meas:.4f}A")

            except Exception as e:
                print(f"  {com_port}: [FAIL] {e}")

        print()

    def sampling_thread(self):
        """Background thread for sampling power supplies"""
        print("[Thread] Starting sampling thread...")
        self.start_time = time.time()

        while not self.stop_event.is_set():
            sample_start = time.time()
            timestamp = datetime.now(timezone.utc)
            elapsed = time.time() - self.start_time
            self.sample_count += 1

            data_point = {
                'timestamp': timestamp,
                'elapsed': elapsed,
                'sample_num': self.sample_count,
                'rigol': None,
                'nice': []
            }

            # Build unified CSV row
            row = [timestamp.isoformat(), f'{elapsed:.3f}', self.sample_count]

            # Sample Rigol
            if self.rigol_psu:
                try:
                    ch_data = []
                    all_valid = True
                    for ch in [1, 2, 3]:
                        v, i, p = self.rigol_psu.read_power_supply_channel(ch)
                        if v is None or i is None or p is None:
                            all_valid = False
                            break
                        ch_data.append({'v': v, 'i': i, 'p': p})

                    if all_valid and len(ch_data) == 3:
                        data_point['rigol'] = ch_data
                        # Add to CSV row
                        for ch in ch_data:
                            row.extend([f'{ch["v"]:.6f}', f'{ch["i"]:.6f}', f'{ch["p"]:.6f}'])
                    else:
                        # Add empty columns if read failed
                        row.extend([''] * 9)

                except Exception as e:
                    print(f"[ERROR] Rigol sampling: {e}")
                    row.extend([''] * 9)

            # Sample Nice Power
            for idx, (com_port, device_type, addr, psu) in enumerate(self.nice_psu_list):
                try:
                    v = psu.measure_voltage()
                    i = psu.measure_current()
                    p = v * i

                    data_point['nice'].append({'v': v, 'i': i, 'p': p})

                    # Add to CSV row
                    row.extend([f'{v:.6f}', f'{i:.6f}', f'{p:.6f}'])

                except Exception as e:
                    print(f"[ERROR] Nice {com_port} sampling: {e}")
                    row.extend(['', '', ''])

            # Write unified CSV row
            if 'unified' in self.csv_writers:
                try:
                    self.csv_writers['unified'].writerow(row)

                    if self.sample_count % 10 == 0:
                        self.csv_files['unified'].flush()
                except Exception as e:
                    print(f"[ERROR] CSV write: {e}")

            # Queue for plotting
            try:
                self.data_queue.put_nowait(data_point)
            except queue.Full:
                pass

            # Maintain sample rate
            sample_duration = time.time() - sample_start
            sleep_time = max(0, self.sample_interval - sample_duration)
            time.sleep(sleep_time)

        print("[Thread] Sampling thread stopped")

    def run_live(self):
        """Run with live plotting"""
        print("\n=== Starting Live Monitoring ===")
        print(f"Sample interval: {self.sample_interval*1000:.0f} ms ({1/self.sample_interval:.1f} Hz)")
        print("Press 'q' in plot window to stop\n")

        # Start sampling thread
        sampling_thread = threading.Thread(target=self.sampling_thread, daemon=True)
        sampling_thread.start()
        time.sleep(0.5)  # Let thread initialize

        # Setup plot
        plt.ion()
        plt.rcParams['figure.facecolor'] = '#f5f3ef'
        plt.rcParams['axes.facecolor'] = '#f5f3ef'

        fig = plt.figure(figsize=(20, 12))
        fig.canvas.manager.set_window_title('Power Supply Monitor (Press Q to Quit)')

        # Layout: 6 graphs on left (3 Nice, 3 Rigol), histograms and stats on right
        gs = GridSpec(6, 3, figure=fig, hspace=0.4, wspace=0.3,
                      width_ratios=[3.0, 1.0, 0.4])

        # Create axes for Nice Power supplies (top 3 rows) - dual y-axis
        nice_axes = []  # List of (voltage_ax, current_ax) tuples
        nice_titles = ["DPPS-D8001", "DPPS-D6001", "DPPS-D2001"]  # Will be updated if supplies found
        for idx in range(3):
            ax_v = fig.add_subplot(gs[idx, 0])
            ax_i = ax_v.twinx()  # Create twin axis for current
            nice_axes.append((ax_v, ax_i))

            ax_v.set_ylabel('Voltage (V)', fontsize=8, color='black')
            ax_v.tick_params(axis='y', labelsize=7, labelcolor='black')
            ax_v.grid(True, alpha=0.3)
            ax_v.tick_params(axis='x', labelsize=7)

            ax_i.set_ylabel('Current (A)', fontsize=8, color='black')
            ax_i.tick_params(axis='y', labelsize=7, labelcolor='black')
            ax_i.yaxis.set_label_position("right")

        # Create axes for Rigol channels (bottom 3 rows) - dual y-axis
        rigol_axes = []  # List of (voltage_ax, current_ax) tuples
        for ch in range(3):
            ax_v = fig.add_subplot(gs[ch + 3, 0])
            ax_i = ax_v.twinx()  # Create twin axis for current
            rigol_axes.append((ax_v, ax_i))

            ax_v.set_title(f'Rigol DP832A CH{ch+1}', fontsize=9, fontweight='bold', color='black')
            ax_v.set_ylabel('Voltage (V)', fontsize=8, color='black')
            ax_v.tick_params(axis='y', labelsize=7, labelcolor='black')
            ax_v.grid(True, alpha=0.3)
            ax_v.tick_params(axis='x', labelsize=7)

            ax_i.set_ylabel('Current (A)', fontsize=8, color='black')
            ax_i.tick_params(axis='y', labelsize=7, labelcolor='black')
            ax_i.yaxis.set_label_position("right")

            if ch == 2:
                ax_v.set_xlabel('Time (s)', fontsize=8)

        # Histogram axes (column 1)
        hist_v_ax = fig.add_subplot(gs[0:3, 1])
        hist_i_ax = fig.add_subplot(gs[3:6, 1])

        hist_v_ax.set_title('Voltage Distribution', fontsize=9, fontweight='bold')
        hist_v_ax.set_ylabel('Count', fontsize=7)
        hist_v_ax.tick_params(labelsize=7)

        hist_i_ax.set_title('Current Distribution', fontsize=9, fontweight='bold')
        hist_i_ax.set_xlabel('Current (A)', fontsize=7)
        hist_i_ax.set_ylabel('Count', fontsize=7)
        hist_i_ax.tick_params(labelsize=7)

        # Stats panel (column 2)
        stats_ax = fig.add_subplot(gs[0:6, 2])
        stats_ax.axis('off')
        stats_text = stats_ax.text(0.02, 0.98, '', transform=stats_ax.transAxes,
                                   fontsize=6, verticalalignment='top', family='monospace')

        # Key handler
        def on_key(event):
            if event.key == 'q':
                print("\n'q' pressed - stopping...")
                self.stop_event.set()
                plt.close('all')

        fig.canvas.mpl_connect('key_press_event', on_key)

        plt.subplots_adjust(top=0.98, bottom=0.05, left=0.06, right=0.98)
        plt.show(block=False)
        plt.pause(0.1)

        # Main update loop
        last_update = time.time()
        update_interval = 0.1  # 10 FPS

        try:
            while plt.fignum_exists(fig.number) and not self.stop_event.is_set():
                # Process queue
                data_processed = False
                while not self.data_queue.empty():
                    try:
                        data = self.data_queue.get_nowait()

                        # Update Rigol data
                        if data['rigol']:
                            for ch in range(3):
                                self.times_rigol[ch].append(data['elapsed'])
                                self.voltages_rigol[ch].append(data['rigol'][ch]['v'])
                                self.currents_rigol[ch].append(data['rigol'][ch]['i'])

                        # Update Nice data
                        for idx, nice_data in enumerate(data['nice']):
                            if idx < len(self.times_nice):
                                self.times_nice[idx].append(data['elapsed'])
                                self.voltages_nice[idx].append(nice_data['v'])
                                self.currents_nice[idx].append(nice_data['i'])

                        data_processed = True

                    except queue.Empty:
                        break

                # Update plot
                current_time = time.time()
                if data_processed and (current_time - last_update) > update_interval:
                    # Update time series graphs
                    # Define colors for Rigol channels: CH1=yellow, CH2=blue, CH3=magenta
                    rigol_colors = ['yellow', 'blue', 'magenta']
                    rigol_edge_colors = ['orange', 'darkblue', 'purple']

                    # Define colors for Nice Power supplies: D8001=red, D6001=yellow, D2001=green
                    nice_color_map = {
                        'SPPS_D8001_232': ('red', 'darkred'),
                        'SPPS_D6001_232': ('yellow', 'orange'),
                        'SPPS_D2001_232': ('green', 'darkgreen')
                    }

                    # Clear all axes
                    for ax_v, ax_i in nice_axes + rigol_axes:
                        ax_v.clear()
                        ax_i.clear()

                    # Determine overall time range from all data
                    max_time = 0
                    for ch in range(3):
                        if len(self.times_rigol[ch]) > 0:
                            max_time = max(max_time, self.times_rigol[ch][-1])
                    for idx in range(len(self.nice_psu_list)):
                        if len(self.times_nice[idx]) > 0:
                            max_time = max(max_time, self.times_nice[idx][-1])

                    min_time = max(0, max_time - self.max_display_time)

                    # Plot Nice Power supplies (top 3 graphs)
                    for idx, (com_port, device_type, addr, psu) in enumerate(self.nice_psu_list):
                        if idx < len(self.times_nice) and len(self.times_nice[idx]) > 0 and idx < 3:
                            # Get supply ID and color
                            psu_id = None
                            if device_type == "d2001":
                                psu_id = "SPPS_D2001_232"
                            else:
                                for psu_name in ["SPPS_D6001_232", "SPPS_D8001_232"]:
                                    if psu_name in self.config["power_supplies"]["nice_power"]:
                                        if self.config["power_supplies"]["nice_power"][psu_name].get("com_port") == com_port:
                                            psu_id = psu_name
                                            break

                            if psu_id and psu_id in nice_color_map:
                                color, edge_color = nice_color_map[psu_id]
                                times = np.array(self.times_nice[idx])
                                voltages = np.array(self.voltages_nice[idx])
                                currents = np.array(self.currents_nice[idx])

                                mask = times >= min_time

                                ax_v, ax_i = nice_axes[idx]

                                # Set title with supply name
                                short_name = psu_id.split("_")[1]  # D2001, D6001, D8001
                                ax_v.set_title(f'DPPS-{short_name}', fontsize=9, fontweight='bold', color='black')

                                # Voltage plot (left y-axis)
                                ax_v.plot(times[mask], voltages[mask], '-o', linewidth=1.5, markersize=4,
                                        color=color, markerfacecolor=color,
                                        markeredgecolor=edge_color, label='Voltage')
                                ax_v.set_ylabel('Voltage (V)', fontsize=8, color='black')
                                ax_v.tick_params(axis='y', labelcolor='black', labelsize=7)
                                ax_v.set_xlim(min_time, max_time if max_time > 0 else 1)
                                ax_v.grid(True, alpha=0.3)
                                ax_v.tick_params(axis='x', labelsize=7)

                                # Current plot (right y-axis)
                                ax_i.plot(times[mask], currents[mask], '-s', linewidth=1.5, markersize=4,
                                        color='red', markerfacecolor='red',
                                        markeredgecolor='darkred', label='Current')
                                ax_i.set_ylabel('Current (A)', fontsize=8, color='black')
                                ax_i.tick_params(axis='y', labelcolor='black', labelsize=7)
                                ax_i.yaxis.set_label_position("right")

                    # Plot Rigol channels (bottom 3 graphs)
                    for ch in range(3):
                        if len(self.times_rigol[ch]) > 0:
                            times = np.array(self.times_rigol[ch])
                            voltages = np.array(self.voltages_rigol[ch])
                            currents = np.array(self.currents_rigol[ch])

                            # Filter to max display time
                            mask = times >= min_time

                            ax_v, ax_i = rigol_axes[ch]

                            # Set title
                            ax_v.set_title(f'Rigol DP832A CH{ch+1}', fontsize=9, fontweight='bold', color='black')

                            # Voltage plot (left y-axis)
                            ax_v.plot(times[mask], voltages[mask], '-o', linewidth=1.5, markersize=4,
                                    color=rigol_colors[ch], markerfacecolor=rigol_colors[ch],
                                    markeredgecolor=rigol_edge_colors[ch], label='Voltage')
                            ax_v.set_ylabel('Voltage (V)', fontsize=8, color='black')
                            ax_v.tick_params(axis='y', labelcolor='black', labelsize=7)
                            ax_v.set_xlim(min_time, max_time if max_time > 0 else 1)
                            ax_v.grid(True, alpha=0.3)
                            ax_v.tick_params(axis='x', labelsize=7)

                            # Current plot (right y-axis)
                            ax_i.plot(times[mask], currents[mask], '-s', linewidth=1.5, markersize=4,
                                    color='red', markerfacecolor='red',
                                    markeredgecolor='darkred', label='Current')
                            ax_i.set_ylabel('Current (A)', fontsize=8, color='black')
                            ax_i.tick_params(axis='y', labelcolor='black', labelsize=7)
                            ax_i.yaxis.set_label_position("right")

                            if ch == 2:
                                ax_v.set_xlabel('Time (s)', fontsize=8)

                    # Update histograms
                    hist_v_ax.clear()
                    hist_i_ax.clear()

                    all_voltages = []
                    all_currents = []

                    for ch in range(3):
                        all_voltages.extend(list(self.voltages_rigol[ch]))
                        all_currents.extend(list(self.currents_rigol[ch]))

                    for idx in range(len(self.nice_psu_list)):
                        all_voltages.extend(list(self.voltages_nice[idx]))
                        all_currents.extend(list(self.currents_nice[idx]))

                    if len(all_voltages) > 0:
                        hist_v_ax.hist(all_voltages, bins=50, color='blue', alpha=0.7, edgecolor='black')
                    if len(all_currents) > 0:
                        hist_i_ax.hist(all_currents, bins=50, color='red', alpha=0.7, edgecolor='black')

                    hist_v_ax.set_title('Voltage Distribution', fontsize=9, fontweight='bold')
                    hist_v_ax.set_ylabel('Count', fontsize=7)
                    hist_v_ax.tick_params(labelsize=7)

                    hist_i_ax.set_title('Current Distribution', fontsize=9, fontweight='bold')
                    hist_i_ax.set_xlabel('Current (A)', fontsize=7)
                    hist_i_ax.set_ylabel('Count', fontsize=7)
                    hist_i_ax.tick_params(labelsize=7)

                    # Update stats
                    elapsed = time.time() - self.start_time if self.start_time else 0
                    rate = self.sample_count / elapsed if elapsed > 0 else 0

                    stats_str = f"=== STATS ===\n"
                    stats_str += f"Samples: {self.sample_count}\n"
                    stats_str += f"Rate: {rate:.2f} Hz\n"
                    stats_str += f"Time: {elapsed:.1f}s\n\n"

                    stats_str += "=== RIGOL ===\n"
                    for ch in range(3):
                        if len(self.voltages_rigol[ch]) > 0:
                            v_last = self.voltages_rigol[ch][-1]
                            i_last = self.currents_rigol[ch][-1]
                            stats_str += f"CH{ch+1}:\n"
                            stats_str += f" {v_last:.3f}V\n"
                            stats_str += f" {i_last:.3f}A\n"

                    if len(self.nice_psu_list) > 0:
                        stats_str += "\n=== NICE ===\n"
                        for idx, (com_port, device_type, addr, psu) in enumerate(self.nice_psu_list):
                            if idx < len(self.voltages_nice) and len(self.voltages_nice[idx]) > 0:
                                v_last = self.voltages_nice[idx][-1]
                                i_last = self.currents_nice[idx][-1]

                                # Get supply ID
                                psu_id = "NICE"
                                if device_type == "d2001":
                                    psu_id = "D2001"
                                else:
                                    for psu_name in ["SPPS_D6001_232", "SPPS_D8001_232"]:
                                        if psu_name in self.config["power_supplies"]["nice_power"]:
                                            if self.config["power_supplies"]["nice_power"][psu_name].get("com_port") == com_port:
                                                psu_id = psu_name.split('_')[1]
                                                break

                                stats_str += f"{psu_id}:\n {v_last:.1f}V\n {i_last:.3f}A\n"

                    stats_text.set_text(stats_str)

                    fig.canvas.draw_idle()
                    fig.canvas.flush_events()
                    last_update = current_time

                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\nInterrupted by user")

        # Stop sampling
        self.stop_event.set()
        sampling_thread.join(timeout=2.0)

    def close(self):
        """Close all connections and files"""
        for csv_file in self.csv_files.values():
            try:
                csv_file.close()
            except:
                pass

        if self.rigol_psu:
            try:
                self.rigol_psu.close()
            except:
                pass

        for _, _, _, psu in self.nice_psu_list:
            try:
                psu.close()
            except:
                pass

        print("\n[OK] All connections closed")

    def print_summary(self):
        """Print final summary"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            rate = self.sample_count / elapsed if elapsed > 0 else 0

            print("\n" + "="*70)
            print("LOGGING COMPLETE")
            print("="*70)
            print(f"Config file:      {self.config_file}")
            print(f"Total samples:    {self.sample_count}")
            print(f"Duration:         {elapsed:.1f} seconds")
            print(f"Average rate:     {rate:.2f} Hz")
            print(f"Sample interval:  {self.sample_interval*1000:.0f} ms")
            print("\nUnified CSV file saved in: power_supply_logs/")
            print("="*70)


def main():
    """Main entry point"""
    print("="*70)
    print("POWER SUPPLY CONTINUOUS LOGGER - LIVE PLOTTING")
    print("="*70)

    if len(sys.argv) < 2:
        print("\nUsage: python power_supply_continuous_logger_live.py <config_file> [sample_interval_ms]")
        print("\nArguments:")
        print("  config_file         - JSON configuration file (required)")
        print("  sample_interval_ms  - Sampling interval in ms (default: 1000ms = 1Hz)")
        print("\nExamples:")
        print("  python power_supply_continuous_logger_live.py GAN_HV_TESTCONFIG.json")
        print("  python power_supply_continuous_logger_live.py LT_RAD_TESTCONFIG.json 500")
        return 1

    config_file = sys.argv[1]
    sample_interval_ms = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    monitor = PowerSupplyMonitorLive(config_file, sample_interval_ms)

    try:
        monitor.connect_supplies()
        monitor.setup_csv_files()
        monitor.configure_supplies()
        monitor.run_live()

    finally:
        monitor.print_summary()
        monitor.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
