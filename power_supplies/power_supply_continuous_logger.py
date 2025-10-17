#!/usr/bin/env python3
"""
Power Supply Continuous Logger
Sets power supply voltages/currents from config, then continuously logs measurements over time.
Press Ctrl+C to stop logging and save data.
"""

import sys
import os
import time
import csv
import json
from datetime import datetime, timezone

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from rigol_usb_locator import RigolUsbLocator
from nice_power_usb_locator import NicePowerLocator


class PowerSupplyMonitor:
    def __init__(self, config_file, sample_interval_ms=1000, output_base_dir=None):
        """
        Initialize power supply monitor

        Args:
            config_file: JSON configuration file
            sample_interval_ms: Sampling interval in milliseconds (default 1000ms = 1Hz)
            output_base_dir: Base directory for output (creates timestamped subfolder)
        """
        self.config_file = config_file
        self.sample_interval = sample_interval_ms / 1000.0
        self.output_base_dir = output_base_dir
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

        # Statistics
        self.start_time = None
        self.sample_count = 0

    def _load_config(self):
        """Load configuration from JSON file"""
        # Try multiple possible config locations
        possible_paths = [
            self.config_file,
            os.path.join("Configs", self.config_file),
            os.path.join("configs", self.config_file),
            os.path.join("oscilloscope", "configs", self.config_file),
            os.path.join("..", "Configs", self.config_file),
            os.path.join("..", "configs", self.config_file),
            os.path.join("..", "oscilloscope", "configs", self.config_file),
            os.path.join("..", "..", "configs", self.config_file),
        ]

        config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break

        if not config_path:
            raise FileNotFoundError(f"Config file '{self.config_file}' not found in any expected location")

        with open(config_path, 'r') as f:
            config = json.load(f)

        print(f"Loaded config: {config_path}")
        return config

    def connect_supplies(self):
        """Connect to all power supplies"""
        print("\n=== Connecting to Power Supplies ===")

        # Find Rigol power supply
        self.rigol_psu = self.rigol_loc.get_power_supply()
        if self.rigol_psu:
            print("[OK] Connected to Rigol Power Supply")
        else:
            print("[WARN] No Rigol Power Supply found")

        # Find Nice power supplies with detailed output
        self.nice_psu_list = self.nice_loc.get_power_supplies()
        print(f"\n[INFO] Found {len(self.nice_psu_list)} Nice Power supply(s)")

        if len(self.nice_psu_list) > 0:
            print("[INFO] Detected Nice Power supplies:")
            for com_port, device_type, addr, psu in self.nice_psu_list:
                print(f"  - COM port: {com_port}, Type: {device_type}, Address: {addr}")

                # Try to match with config
                matched = False
                if device_type == "d2001":
                    print(f"    -> Matches config: SPPS_D2001_232")
                    matched = True
                else:
                    for psu_name, psu_cfg in self.config["power_supplies"]["nice_power"].items():
                        config_com = psu_cfg.get("com_port")
                        if config_com == com_port:
                            print(f"    -> Matches config: {psu_name} (COM port matches)")
                            matched = True
                            break

                if not matched:
                    print(f"    -> WARNING: No matching config found for this COM port!")
                    print(f"    -> Config expects COM ports:")
                    for psu_name, psu_cfg in self.config["power_supplies"]["nice_power"].items():
                        expected_com = psu_cfg.get("com_port", "N/A")
                        print(f"       {psu_name}: {expected_com}")
        else:
            print("[WARN] No Nice Power supplies detected on any COM port")

    def setup_csv_files(self):
        """Setup CSV files for each power supply"""
        timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')

        # Create timestamped output directory
        if self.output_base_dir:
            log_dir = os.path.join(os.path.abspath(self.output_base_dir), f'power_supply_log_{timestamp_str}')
        else:
            log_dir = os.path.join("power_supply_logs", f'power_supply_log_{timestamp_str}')

        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = log_dir

        print("\n=== Setting up CSV log files ===")
        print(f"Output directory: {log_dir}")

        # Setup Rigol CSV file
        if self.rigol_psu:
            filename = os.path.join(log_dir, f"rigol_dp832a_{timestamp_str}.csv")
            csv_file = open(filename, 'w', newline='')
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(['UTC_Timestamp', 'Elapsed_s', 'Sample_Num',
                                'CH1_V', 'CH1_A', 'CH1_W',
                                'CH2_V', 'CH2_A', 'CH2_W',
                                'CH3_V', 'CH3_A', 'CH3_W'])
            self.csv_files['rigol'] = csv_file
            self.csv_writers['rigol'] = csv_writer
            print(f"[OK] Rigol log: {filename}")

        # Setup Nice Power CSV files (one per supply)
        for com_port, device_type, addr, psu in self.nice_psu_list:
            # Determine supply ID
            psu_id = None
            if device_type == "d2001":
                psu_id = "SPPS_D2001_232"
            else:
                for psu_name, psu_cfg in self.config["power_supplies"]["nice_power"].items():
                    if psu_cfg.get("com_port") == com_port:
                        psu_id = psu_name
                        break

            if psu_id:
                filename = os.path.join(log_dir, f"nice_{psu_id}_{com_port}_{timestamp_str}.csv")
                csv_file = open(filename, 'w', newline='')
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(['UTC_Timestamp', 'Elapsed_s', 'Sample_Num',
                                    'Voltage_V', 'Current_A', 'Power_W'])
                self.csv_files[f'nice_{com_port}'] = csv_file
                self.csv_writers[f'nice_{com_port}'] = csv_writer
                print(f"[OK] {psu_id} log: {filename}")

    def verify_nice_power_identification(self):
        """
        Verify Nice Power supply identification with user confirmation
        Sets test voltages: D2001=2V, D6001=6V, D8001=8V
        """
        if len(self.nice_psu_list) == 0:
            return True

        print("\n" + "="*70)
        print("NICE POWER SUPPLY IDENTIFICATION VERIFICATION")
        print("="*70)
        print("Setting test voltages to verify supply identification:")
        print("  D2001 -> 2V")
        print("  D6001 -> 6V")
        print("  D8001 -> 8V")
        print("\nPlease visually confirm the voltages on each supply.")
        print("="*70)

        # Set test voltages
        for com_port, device_type, addr, psu in self.nice_psu_list:
            try:
                # Determine which supply this should be
                psu_id = None
                test_voltage = None

                if device_type == "d2001":
                    psu_id = "SPPS_D2001_232"
                    test_voltage = 2.0
                else:
                    for psu_name, psu_cfg in self.config["power_supplies"]["nice_power"].items():
                        if psu_cfg.get("com_port") == com_port:
                            psu_id = psu_name
                            if "D6001" in psu_name:
                                test_voltage = 6.0
                            elif "D8001" in psu_name:
                                test_voltage = 8.0
                            break

                if psu_id and test_voltage:
                    print(f"\nSetting {psu_id} ({com_port}) to {test_voltage}V...")

                    if device_type == "modbus":
                        psu.set_remote(True)
                        psu.set_current_limit(0.1)  # Low current for safety
                        psu.set_voltage(test_voltage)
                        psu.turn_on()
                    else:  # d2001
                        psu.set_remote(True)
                        psu.set_current_limit(0.1)
                        psu.set_voltage(test_voltage)
                        psu.turn_on()

                    time.sleep(1)

                    # Read back
                    v_meas = psu.measure_voltage()
                    i_meas = psu.measure_current()
                    print(f"  Measured: {v_meas:.2f}V / {i_meas:.3f}A")

            except Exception as e:
                print(f"  [ERROR] Failed to set test voltage: {e}")

        # Ask user to confirm
        print("\n" + "="*70)
        print("Please check the power supply displays:")
        print("  - D2001 should show ~2V")
        print("  - D6001 should show ~6V")
        print("  - D8001 should show ~8V")
        print("="*70)

        response = input("Do the voltages match? (yes/no): ").strip().lower()

        if response in ['yes', 'y']:
            print("[OK] Supply identification confirmed!")
            return True
        else:
            print("\n[ERROR] Supply identification mismatch!")
            print("The COM port assignments in the config file may be incorrect.")
            print("Please update the config file and try again.")
            print("\nTurning off all supplies for safety...")

            # Turn off all supplies
            for com_port, device_type, addr, psu in self.nice_psu_list:
                try:
                    psu.set_voltage(0.0)
                    psu.turn_off()
                    psu.set_remote(False)
                except:
                    pass

            return False

    def configure_supplies(self):
        """Configure all power supplies to initial setpoints"""
        print("\n=== Configuring Power Supplies ===")

        # Configure Rigol power supply
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

                    # Set values
                    self.rigol_psu.turn_channel_on(ch)
                    self.rigol_psu.set_voltage(ch, voltage)
                    self.rigol_psu.set_current_limit(ch, current)

                    # Wait for stabilization
                    time.sleep(2)

                    # Verify
                    v_meas, i_meas, p_meas = self.rigol_psu.read_power_supply_channel(ch)
                    print(f"  CH{ch}: [OK] Set={voltage}V/{current}A, Measured={v_meas:.4f}V/{i_meas:.4f}A")

                print()
            except Exception as e:
                print(f"  [FAIL] Error configuring Rigol: {e}\n")

        # Configure Nice power supplies
        if self.nice_psu_list:
            print(f"Nice Power Supplies ({len(self.nice_psu_list)} found):")

        for com_port, device_type, addr, psu in self.nice_psu_list:
            try:
                # Get config
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
                    print(f"  {com_port} ({device_type}): [SKIP] No config found")
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

                # Set values with verification for Modbus supplies
                if device_type == "modbus" and hasattr(psu, 'configure_voltage_current'):
                    psu.configure_voltage_current(voltage, current, verify=True, max_retries=3, tol=0.2)
                else:
                    psu.set_remote(True)
                    psu.set_current_limit(current)
                    psu.set_voltage(voltage)
                    if voltage > 0:
                        psu.turn_on()

                # Wait for stabilization
                time.sleep(2)

                # Verify
                v_meas = psu.measure_voltage()
                i_meas = psu.measure_current()
                print(f"  {psu_id} ({com_port}): [OK] Set={voltage}V/{current}A, Measured={v_meas:.4f}V/{i_meas:.4f}A")

            except Exception as e:
                print(f"  {com_port} ({device_type}): [FAIL] {e}")

        print()

    def log_measurements(self):
        """Log measurements from all power supplies"""
        timestamp = datetime.now(timezone.utc)
        elapsed = time.time() - self.start_time
        self.sample_count += 1

        # Log Rigol measurements
        if self.rigol_psu and 'rigol' in self.csv_writers:
            try:
                ch_data = []
                for ch in [1, 2, 3]:
                    v, i, p = self.rigol_psu.read_power_supply_channel(ch)
                    ch_data.extend([v, i, p])

                row = [timestamp.isoformat(), f'{elapsed:.3f}', self.sample_count] + \
                      [f'{val:.6f}' for val in ch_data]
                self.csv_writers['rigol'].writerow(row)

                # Flush every 10 samples
                if self.sample_count % 10 == 0:
                    self.csv_files['rigol'].flush()

            except Exception as e:
                print(f"[ERROR] Failed to log Rigol: {e}")

        # Log Nice Power measurements
        for com_port, device_type, addr, psu in self.nice_psu_list:
            csv_key = f'nice_{com_port}'
            if csv_key in self.csv_writers:
                try:
                    v = psu.measure_voltage()
                    i = psu.measure_current()
                    p = v * i

                    row = [timestamp.isoformat(), f'{elapsed:.3f}', self.sample_count,
                           f'{v:.6f}', f'{i:.6f}', f'{p:.6f}']
                    self.csv_writers[csv_key].writerow(row)

                    # Flush every 10 samples
                    if self.sample_count % 10 == 0:
                        self.csv_files[csv_key].flush()

                except Exception as e:
                    print(f"[ERROR] Failed to log {com_port}: {e}")

    def print_status(self):
        """Print current status"""
        elapsed = time.time() - self.start_time
        rate = self.sample_count / elapsed if elapsed > 0 else 0

        status_parts = []
        status_parts.append(f"Samples: {self.sample_count}")
        status_parts.append(f"Rate: {rate:.2f} Hz")
        status_parts.append(f"Time: {elapsed:.1f}s")

        # Get latest measurements
        if self.rigol_psu:
            try:
                v1, i1, p1 = self.rigol_psu.read_power_supply_channel(1)
                status_parts.append(f"R-CH1: {v1:.2f}V/{i1:.3f}A")
            except:
                pass

        for com_port, device_type, addr, psu in self.nice_psu_list:
            try:
                v = psu.measure_voltage()
                i = psu.measure_current()
                # Get supply ID for display
                psu_id = "NICE"
                if device_type == "d2001":
                    psu_id = "D2001"
                else:
                    for psu_name in ["SPPS_D6001_232", "SPPS_D8001_232"]:
                        if psu_name in self.config["power_supplies"]["nice_power"]:
                            if self.config["power_supplies"]["nice_power"][psu_name].get("com_port") == com_port:
                                psu_id = psu_name.split('_')[1]  # Extract D6001 or D8001
                                break

                status_parts.append(f"{psu_id}: {v:.1f}V/{i:.3f}A")
            except:
                pass

        print("\r" + " | ".join(status_parts), end="", flush=True)

    def run(self):
        """Main monitoring loop"""
        print("\n=== Starting Continuous Logging ===")
        print(f"Sample interval: {self.sample_interval*1000:.0f} ms ({1/self.sample_interval:.1f} Hz)")
        print("Press Ctrl+C to stop and save data\n")

        self.start_time = time.time()
        last_status_print = time.time()

        try:
            while True:
                sample_start = time.time()

                # Log measurements
                self.log_measurements()

                # Print status every second
                current_time = time.time()
                if current_time - last_status_print >= 1.0:
                    self.print_status()
                    last_status_print = current_time

                # Sleep to maintain sample rate
                sample_duration = time.time() - sample_start
                sleep_time = max(0, self.sample_interval - sample_duration)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n\n[STOP] Interrupted by user")

    def close(self):
        """Close all connections and files"""
        # Close CSV files
        for csv_file in self.csv_files.values():
            try:
                csv_file.close()
            except:
                pass

        # Close power supplies
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
        print(f"\nCSV files saved in: {self.log_dir}")
        print("="*70)


def main():
    """Main entry point"""
    print("="*70)
    print("POWER SUPPLY CONTINUOUS LOGGER")
    print("="*70)

    if len(sys.argv) < 2:
        print("\nUsage: python power_supply_continuous_logger.py <config_file> <output_directory> [sample_interval_ms]")
        print("\nArguments:")
        print("  config_file         - JSON configuration file (required)")
        print("  output_directory    - Output directory for timestamped logs (required)")
        print("  sample_interval_ms  - Sampling interval in ms (default: 1000ms = 1Hz)")
        print("\nExamples:")
        print("  python power_supply_continuous_logger.py GAN_HV_TESTCONFIG.json C:/Users/andre/Claude/rad_test_data")
        print("  python power_supply_continuous_logger.py LT_RAD_TESTCONFIG.json C:/Users/andre/Claude/rad_test_data 500")
        print("\nCreates timestamped subfolder: output_directory/power_supply_log_YYYYMMDD_HHMMSS_UTC/")
        return 1

    config_file = sys.argv[1]
    output_directory = sys.argv[2] if len(sys.argv) > 2 else None
    sample_interval_ms = int(sys.argv[3]) if len(sys.argv) > 3 else 1000

    # Create monitor
    monitor = PowerSupplyMonitor(config_file, sample_interval_ms, output_directory)

    try:
        # Connect to supplies
        monitor.connect_supplies()

        # Setup CSV files
        monitor.setup_csv_files()

        # Configure supplies to setpoints
        monitor.configure_supplies()

        # Run continuous logging
        monitor.run()

    finally:
        # Print summary
        if monitor.start_time:
            monitor.print_summary()

        # Close everything
        monitor.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
