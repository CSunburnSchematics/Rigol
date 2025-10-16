"""
Power Supply Logger
Sets voltages/currents and logs measurements from all connected power supplies.
Supports both Rigol and Nice Power supplies.
"""

import sys
import json
import os
import time
from datetime import datetime, timezone
from rigol_usb_locator import RigolUsbLocator
from nice_power_usb_locator import NicePowerLocator


class PowerSupplyLogger:
    def __init__(self, config_file="default_config.json"):
        """Initialize logger with config file"""
        # Try multiple possible config locations
        possible_paths = [
            config_file,  # Absolute or relative to current dir
            os.path.join("Configs", config_file),  # Main Configs/ directory
            os.path.join("oscilloscope", "configs", config_file),  # Oscilloscope configs
            os.path.join("..", "Configs", config_file),  # One level up
            os.path.join("..", "oscilloscope", "configs", config_file),  # One level up oscilloscope
        ]

        config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break

        if not config_path:
            raise FileNotFoundError(f"Config file '{config_file}' not found in any expected location")

        with open(config_path, 'r') as f:
            self.config = json.load(f)

        print(f"Using config: {config_file}")

        # Initialize locators
        self.rigol_loc = RigolUsbLocator(verbose=False)
        self.nice_loc = NicePowerLocator(verbose=False)
        self.nice_loc.refresh()
        self.rigol_loc.refresh()

        # Storage for power supplies
        self.rigol_psu = None
        self.nice_psu_list = []

        # Log storage
        self.log_entries = []

    def connect_supplies(self):
        """Connect to all power supplies"""
        print("\n=== Connecting to Power Supplies ===")

        # Find Rigol power supply
        self.rigol_psu = self.rigol_loc.get_power_supply()
        if self.rigol_psu:
            print(f"[OK] Connected to Rigol Power Supply")
        else:
            print("[WARN] No Rigol Power Supply found")

        # Find Nice power supplies
        self.nice_psu_list = self.nice_loc.get_power_supplies()
        print(f"[OK] Found {len(self.nice_psu_list)} Nice Power supply(s)")

    def configure_and_log(self):
        """Configure all power supplies and log initial readings"""
        print("\n=== Configuring Power Supplies ===")
        timestamp = datetime.now(timezone.utc).isoformat()

        # Configure Rigol power supply
        if self.rigol_psu:
            try:
                print("Configuring Rigol Power Supply:")
                for ch in [1, 2, 3]:
                    psu_config = self.config["power_supplies"]["rigol"]["DP8B261601128"]["channels"][str(ch)]
                    voltage = psu_config["vout"]
                    current = psu_config["iout_max"]

                    # Set values
                    self.rigol_psu.turn_channel_on(ch)
                    self.rigol_psu.set_voltage(ch, voltage)
                    self.rigol_psu.set_current_limit(ch, current)

                    # Wait for voltage to rise and stabilize (at least 1 second)
                    time.sleep(2)

                    # Read back
                    v_meas, i_meas, p_meas = self.rigol_psu.read_power_supply_channel(ch)

                    print(f"  CH{ch}: Set={voltage}V/{current}A, Measured={v_meas:.4f}V/{i_meas:.4f}A/{p_meas:.4f}W")

                    # Log entry
                    self.log_entries.append({
                        "timestamp": timestamp,
                        "supply_type": "rigol",
                        "supply_id": "DP8B261601128",
                        "channel": ch,
                        "voltage_set": voltage,
                        "current_set": current,
                        "voltage_measured": v_meas,
                        "current_measured": i_meas,
                        "power_measured": p_meas
                    })
            except Exception as e:
                print(f"  [FAIL] Failed to configure Rigol: {e}")

        # Configure Nice power supplies
        for com_port, device_type, addr, psu in self.nice_psu_list:
            try:
                print(f"Configuring Nice Power Supply ({device_type}): {com_port} (addr {addr})")

                # Get config
                psu_config = None
                psu_id = None
                if device_type == "d2001":
                    psu_config = self.config["power_supplies"]["nice_power"]["SPPS_D2001_232"]
                    psu_id = "SPPS_D2001_232"
                else:  # modbus - match by COM port
                    for psu_name, psu_cfg in self.config["power_supplies"]["nice_power"].items():
                        if psu_cfg.get("com_port") == com_port:
                            psu_config = psu_cfg
                            psu_id = psu_name
                            break

                if not psu_config:
                    print(f"  [WARN] No config found, skipping")
                    continue

                voltage = psu_config["vout"]
                current = psu_config["iout_max"]

                # Set values using reliable configure method with verification
                # This is especially important for Modbus supplies (SPPS_D8001/D6001)
                # which can have communication issues
                if device_type == "modbus" and hasattr(psu, 'configure_voltage_current'):
                    # Use Claire's robust configure method with retry logic
                    psu.configure_voltage_current(voltage, current, verify=True, max_retries=3, tol=0.2)
                else:
                    # Fallback for D2001 or older supplies
                    psu.set_remote(True)
                    psu.set_current_limit(current)
                    psu.set_voltage(voltage)
                    if voltage > 0:
                        psu.turn_on()

                # Wait for voltage to rise and stabilize (at least 1 second)
                time.sleep(2)

                # Read back
                v_meas = psu.measure_voltage()
                i_meas = psu.measure_current()
                p_meas = v_meas * i_meas

                print(f"  Set={voltage}V/{current}A, Measured={v_meas:.4f}V/{i_meas:.4f}A/{p_meas:.4f}W")

                # Log entry
                self.log_entries.append({
                    "timestamp": timestamp,
                    "supply_type": "nice_power",
                    "supply_id": psu_id,
                    "com_port": com_port,
                    "device_type": device_type,
                    "address": addr,
                    "voltage_set": voltage,
                    "current_set": current,
                    "voltage_measured": v_meas,
                    "current_measured": i_meas,
                    "power_measured": p_meas
                })
            except Exception as e:
                print(f"  [FAIL] Failed to configure: {e}")

    def log_measurements(self):
        """Take measurements from all configured supplies and log them"""
        print("\n=== Taking Measurements ===")
        timestamp = datetime.now(timezone.utc).isoformat()

        # Measure Rigol channels
        if self.rigol_psu:
            try:
                for ch in [1, 2, 3]:
                    v_meas, i_meas, p_meas = self.rigol_psu.read_power_supply_channel(ch)

                    print(f"Rigol CH{ch}: {v_meas:.4f}V, {i_meas:.4f}A, {p_meas:.4f}W")

                    self.log_entries.append({
                        "timestamp": timestamp,
                        "supply_type": "rigol",
                        "supply_id": "DP8B261601128",
                        "channel": ch,
                        "voltage_measured": v_meas,
                        "current_measured": i_meas,
                        "power_measured": p_meas
                    })
            except Exception as e:
                print(f"[FAIL] Error reading Rigol: {e}")

        # Measure Nice power supplies
        for com_port, device_type, addr, psu in self.nice_psu_list:
            try:
                # Determine supply ID
                psu_id = None
                if device_type == "d2001":
                    psu_id = "SPPS_D2001_232"
                else:
                    for psu_name, psu_cfg in self.config["power_supplies"]["nice_power"].items():
                        if psu_cfg.get("com_port") == com_port:
                            psu_id = psu_name
                            break

                if not psu_id:
                    continue

                v_meas = psu.measure_voltage()
                i_meas = psu.measure_current()
                p_meas = v_meas * i_meas

                print(f"Nice ({psu_id}): {v_meas:.4f}V, {i_meas:.4f}A, {p_meas:.4f}W")

                self.log_entries.append({
                    "timestamp": timestamp,
                    "supply_type": "nice_power",
                    "supply_id": psu_id,
                    "com_port": com_port,
                    "device_type": device_type,
                    "address": addr,
                    "voltage_measured": v_meas,
                    "current_measured": i_meas,
                    "power_measured": p_meas
                })
            except Exception as e:
                print(f"[FAIL] Error reading {com_port}: {e}")

    def save_log(self, filename=None):
        """Save log to JSON file"""
        if filename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
            filename = f"power_supply_log_{timestamp}.json"

        log_dir = "power_supply_logs"
        os.makedirs(log_dir, exist_ok=True)
        filepath = os.path.join(log_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(self.log_entries, f, indent=2)

        print(f"\n[OK] Log saved to: {filepath}")
        return filepath

    def save_csv_summary(self, filename=None):
        """Save a CSV summary of all measurements"""
        if filename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
            filename = f"power_supply_summary_{timestamp}.csv"

        log_dir = "power_supply_logs"
        os.makedirs(log_dir, exist_ok=True)
        filepath = os.path.join(log_dir, filename)

        with open(filepath, 'w') as f:
            # Header
            f.write("timestamp,supply_type,supply_id,channel,voltage_set,current_set,voltage_meas,current_meas,power_meas\n")

            # Data rows
            for entry in self.log_entries:
                timestamp = entry.get("timestamp", "")
                supply_type = entry.get("supply_type", "")
                supply_id = entry.get("supply_id", "")
                channel = entry.get("channel", "")
                v_set = entry.get("voltage_set", "")
                i_set = entry.get("current_set", "")
                v_meas = entry.get("voltage_measured", "")
                i_meas = entry.get("current_measured", "")
                p_meas = entry.get("power_measured", "")

                f.write(f"{timestamp},{supply_type},{supply_id},{channel},{v_set},{i_set},{v_meas},{i_meas},{p_meas}\n")

        print(f"[OK] CSV saved to: {filepath}")
        return filepath

    def close(self):
        """Close all connections"""
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


def main():
    """Main entry point"""
    # Get config file from command line or use default
    config_file = sys.argv[1] if len(sys.argv) > 1 else "default_config.json"

    logger = PowerSupplyLogger(config_file)

    try:
        # Connect to all supplies
        logger.connect_supplies()

        # Configure and log initial state
        logger.configure_and_log()

        # Optional: Continue logging at intervals
        # Uncomment the following to enable periodic logging
        # print("\n=== Starting Periodic Logging (Press Ctrl+C to stop) ===")
        # try:
        #     while True:
        #         time.sleep(5)  # Log every 5 seconds
        #         logger.log_measurements()
        # except KeyboardInterrupt:
        #     print("\n[OK] Stopped periodic logging")

        # Save logs
        logger.save_log()
        logger.save_csv_summary()

    finally:
        logger.close()
        print("\n[OK] All power supplies closed")


if __name__ == "__main__":
    main()
