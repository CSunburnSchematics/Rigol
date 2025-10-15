"""
Set Power Supplies from Config
Reads master config file and sets all power supplies to specified voltages/currents.
Supports both Rigol and Nice Power supplies with per-channel configuration.
"""

import sys
import json
import os
import time
from rigol_usb_locator import RigolUsbLocator
from nice_power_usb_locator import NicePowerLocator


def set_power_supplies(config_file="default_config.json"):
    """
    Set all power supplies from config file

    Args:
        config_file: Path to JSON config file (relative to Configs/ directory)
    """
    config_path = os.path.join("Configs", config_file)

    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)

    print(f"=== Setting Power Supplies from {config_file} ===\n")

    # Initialize locators
    rigol_loc = RigolUsbLocator(verbose=False)
    nice_loc = NicePowerLocator(verbose=False)
    nice_loc.refresh()
    rigol_loc.refresh()

    # Track all supply objects for cleanup
    all_psus = []

    try:
        # === Configure Rigol Power Supply ===
        rigol_psu = rigol_loc.get_power_supply()
        if rigol_psu:
            all_psus.append(rigol_psu)
            print("Rigol Power Supply (DP832A):")

            try:
                for ch in [1, 2, 3]:
                    psu_config = config["power_supplies"]["rigol"]["DP8B261601128"]["channels"][str(ch)]
                    voltage = psu_config["vout"]
                    current = psu_config["iout_max"]

                    # Set values
                    rigol_psu.turn_channel_on(ch)
                    rigol_psu.set_voltage(ch, voltage)
                    rigol_psu.set_current_limit(ch, current)

                    # Wait for voltage to rise and stabilize
                    time.sleep(2)

                    # Read back and verify
                    v_meas, i_meas, p_meas = rigol_psu.read_power_supply_channel(ch)

                    # Check if voltage is within tolerance
                    v_error = abs(v_meas - voltage)
                    status = "[OK]" if v_error < 0.1 else "[WARN]"

                    print(f"  CH{ch}: {status} Set={voltage}V/{current}A, Measured={v_meas:.4f}V/{i_meas:.4f}A")

                print()
            except Exception as e:
                print(f"  [FAIL] Error configuring Rigol: {e}\n")
        else:
            print("Rigol Power Supply: [SKIP] Not found\n")

        # === Configure Nice Power Supplies ===
        nice_psu_list = nice_loc.get_power_supplies()

        if nice_psu_list:
            print(f"Nice Power Supplies ({len(nice_psu_list)} found):")
        else:
            print("Nice Power Supplies: [SKIP] None found\n")

        for com_port, device_type, addr, psu in nice_psu_list:
            all_psus.append(psu)

            try:
                # Get config: D2001 by type, Modbus by COM port
                psu_config = None
                psu_id = None

                if device_type == "d2001":
                    psu_config = config["power_supplies"]["nice_power"]["SPPS_D2001_232"]
                    psu_id = "SPPS_D2001_232"
                else:  # modbus - match by COM port
                    for psu_name, psu_cfg in config["power_supplies"]["nice_power"].items():
                        if psu_cfg.get("com_port") == com_port:
                            psu_config = psu_cfg
                            psu_id = psu_name
                            break

                if not psu_config:
                    print(f"  {com_port} ({device_type}): [SKIP] No config found")
                    continue

                voltage = psu_config["vout"]
                current = psu_config["iout_max"]

                # Set values using reliable configure method with verification
                # This is especially important for Modbus supplies (SPPS_D8001/D6001)
                if device_type == "modbus" and hasattr(psu, 'configure_voltage_current'):
                    # Use robust configure method with retry logic
                    psu.configure_voltage_current(voltage, current, verify=True, max_retries=3, tol=0.2)
                else:
                    # Fallback for D2001 or older supplies
                    psu.set_remote(True)
                    psu.set_current_limit(current)
                    psu.set_voltage(voltage)
                    if voltage > 0:
                        psu.turn_on()

                # Wait for voltage to rise and stabilize
                time.sleep(2)

                # Read back and verify
                v_meas = psu.measure_voltage()
                i_meas = psu.measure_current()

                # Check if voltage is within tolerance
                v_error = abs(v_meas - voltage)
                status = "[OK]" if v_error < 0.2 else "[WARN]"

                print(f"  {psu_id} ({com_port}): {status} Set={voltage}V/{current}A, Measured={v_meas:.4f}V/{i_meas:.4f}A")

            except Exception as e:
                print(f"  {com_port} ({device_type}): [FAIL] {e}")

        print("\n=== All Power Supplies Configured ===")

    finally:
        # Close all connections
        for psu in all_psus:
            try:
                psu.close()
            except:
                pass


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python set_power_supplies.py <config_file.json>")
        print("\nAvailable configs in Configs/:")
        config_dir = "Configs"
        if os.path.exists(config_dir):
            configs = [f for f in os.listdir(config_dir) if f.endswith('.json')]
            for cfg in sorted(configs):
                print(f"  - {cfg}")
        print("\nExample:")
        print("  python set_power_supplies.py default_config.json")
        print("  python set_power_supplies.py experiment_268.json")
        sys.exit(1)

    config_file = sys.argv[1]
    set_power_supplies(config_file)


if __name__ == "__main__":
    main()
