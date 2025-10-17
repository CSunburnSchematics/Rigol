"""
NICE Power Supply COM Port Verification and Remapping Tool

This script:
1. Detects all NICE Power supplies on COM ports
2. Sets each to a distinctive voltage (2V, 6V, 8V)
3. Asks user to verify which device shows which voltage
4. Updates all config files with correct COM port mappings

Run this after:
- Device power cycles
- USB reconnections
- System reboots
- Any time COM ports may have changed
"""

import sys
import os
import json
import time
from pathlib import Path
import serial.tools.list_ports

# Add Rigol folder to path for NICE Power class import
SCRIPT_DIR = Path(__file__).parent.absolute()
SUNBURN_CODE_DIR = SCRIPT_DIR.parent.parent
RIGOL_DIR = SUNBURN_CODE_DIR / "Rigol"
sys.path.insert(0, str(RIGOL_DIR))

from NICE_POWER_SPPS_D2001_232 import NicePowerSupply

# Expected voltages for identification
TEST_VOLTAGES = {
    'D2001': 2.0,
    'D6001': 6.0,
    'D8001': 8.0
}

def find_nice_power_ports():
    """Find all COM ports with Silicon Labs adapters (NICE Power supplies)."""
    ports = serial.tools.list_ports.comports()
    nice_ports = [p for p in ports if "Silicon Labs" in p.description]
    return nice_ports

def test_port(port_name):
    """Test if a port has a NICE Power supply and return connection status."""
    try:
        psu = NicePowerSupply(port=port_name, device_addr=0, baudrate=9600, timeout=2)
        voltage = psu.measure_voltage()
        if voltage is not None:
            return psu, True
        else:
            psu.close()
            return None, False
    except Exception as e:
        return None, False

def get_current_config():
    """Read current config to see which device is expected on which port."""
    config_path = SUNBURN_CODE_DIR / "Master_Radiation_Test" / "config" / "nice_power_config.json"

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Build mapping of COM port -> device name from config
        port_to_device = {}
        for device_name in ['D2001', 'D6001', 'D8001']:
            if device_name in config['power_supplies']:
                com_port = config['power_supplies'][device_name]['com_port']
                port_to_device[com_port] = device_name

        return port_to_device
    except Exception as e:
        print(f"Warning: Could not read current config: {e}")
        return {}

def set_test_voltages(port_supplies):
    """Set each connected port to test voltage based on expected device."""
    print("\n" + "=" * 70)
    print("Setting test voltages for identification...")
    print("=" * 70)

    # Get current expected mapping from config
    expected_mapping = get_current_config()

    # Define expected voltage for each device type
    device_test_voltages = {
        'D2001': 2.0,
        'D6001': 6.0,
        'D8001': 8.0
    }

    port_voltages = {}
    port_expected_devices = {}

    for port_name, psu in port_supplies.items():
        # Determine which device is expected on this port
        expected_device = expected_mapping.get(port_name, None)

        if expected_device and expected_device in device_test_voltages:
            voltage = device_test_voltages[expected_device]
            print(f"\n[{port_name}] Expected device: {expected_device}")
            print(f"[{port_name}] Setting to {voltage}V...")
            port_expected_devices[port_name] = expected_device
        else:
            # If no mapping found, use sequential voltages as fallback
            fallback_voltages = [2.0, 6.0, 8.0]
            idx = list(port_supplies.keys()).index(port_name)
            voltage = fallback_voltages[idx] if idx < len(fallback_voltages) else 2.0
            print(f"\n[{port_name}] No expected device in config")
            print(f"[{port_name}] Setting to {voltage}V (fallback)...")
            port_expected_devices[port_name] = None

        psu.configure_voltage_current(voltage, 0.1)
        time.sleep(1.0)  # Wait for settling

        # Verify
        v_actual = psu.measure_voltage()
        print(f"[{port_name}] Actual: {v_actual:.3f}V")

        # Store the actual voltage for this port
        port_voltages[port_name] = v_actual

    print("\n" + "=" * 70)
    print("Test voltages set!")
    print("=" * 70)

    return port_voltages, port_expected_devices

def get_user_mapping(port_supplies, port_voltages, port_expected_devices):
    """Ask user to identify which device is on which COM port."""
    print("\n" + "=" * 70)
    print("DEVICE IDENTIFICATION")
    print("=" * 70)
    print("\nI will tell you what voltage each COM port is displaying.")
    print("Please look at your physical devices and confirm which device")
    print("(D2001, D6001, or D8001) is showing that voltage.\n")

    device_map = {}
    used_devices = set()

    for port_name, voltage in port_voltages.items():
        print("=" * 70)
        expected_device = port_expected_devices.get(port_name)

        if expected_device:
            print(f"[{port_name}] Expected: {expected_device} (should show ~{voltage:.1f}V)")
            print(f"[{port_name}] Actually displaying: ~{voltage:.1f}V")
        else:
            print(f"[{port_name}] is displaying ~{voltage:.1f}V")

        print("=" * 70)

        remaining_devices = [d for d in ['D2001', 'D6001', 'D8001'] if d not in used_devices]
        print(f"Remaining devices to identify: {', '.join(remaining_devices)}")

        # If there's an expected device and voltage matches, offer it as default
        default_suggestion = None
        if expected_device and expected_device in remaining_devices:
            # Check if voltage matches expected (within 0.5V tolerance)
            expected_voltage = {'D2001': 2.0, 'D6001': 6.0, 'D8001': 8.0}.get(expected_device, 0)
            if abs(voltage - expected_voltage) < 0.5:
                default_suggestion = expected_device

        while True:
            if default_suggestion:
                response = input(f"\nWhich device is showing ~{voltage:.1f}V on {port_name}? [{default_suggestion}]: ").strip().upper()
                if response == "":
                    response = default_suggestion
            else:
                response = input(f"\nWhich device is showing ~{voltage:.1f}V on {port_name}? ").strip().upper()

            # Check if valid device name
            if response in remaining_devices:
                device_map[response] = port_name
                used_devices.add(response)

                # Warn if mapping changed
                if expected_device and expected_device != response:
                    print(f"  ! WARNING: Expected {expected_device}, but you identified {response}")
                    print(f"  ! COM ports may have changed since last configuration")

                print(f"  ✓ {response} = {port_name}")
                break
            elif response in ['D2001', 'D6001', 'D8001']:
                print(f"  ✗ {response} already assigned. Choose from: {', '.join(remaining_devices)}")
            else:
                print(f"  ✗ Invalid device. Enter one of: {', '.join(remaining_devices)}")

        print()

    return device_map

def update_config_file(config_path, device_map):
    """Update a single config file with new COM port mappings."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Update COM ports for NICE supplies
        updated = False
        for device_name, com_port in device_map.items():
            if device_name in config['power_supplies']:
                old_port = config['power_supplies'][device_name].get('com_port', 'unknown')
                config['power_supplies'][device_name]['com_port'] = com_port

                if old_port != com_port:
                    print(f"  {device_name}: {old_port} → {com_port}")
                    updated = True

        # Save updated config
        if updated:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        else:
            print("  No changes needed")
            return False

    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def update_all_configs(device_map):
    """Update all config files in Master_Radiation_Test/config/."""
    print("\n" + "=" * 70)
    print("Updating configuration files...")
    print("=" * 70)

    config_dir = SUNBURN_CODE_DIR / "Master_Radiation_Test" / "config"

    if not config_dir.exists():
        print(f"Config directory not found: {config_dir}")
        return

    config_files = list(config_dir.glob("*.json"))

    if not config_files:
        print(f"No config files found in {config_dir}")
        return

    for config_file in config_files:
        print(f"\n[{config_file.name}]")
        update_config_file(config_file, device_map)

    print("\n" + "=" * 70)
    print("All config files updated!")
    print("=" * 70)

def save_device_map(device_map):
    """Save device map to Rigol folder for reference."""
    map_file = RIGOL_DIR / "nice_power_device_map.txt"

    try:
        with open(map_file, 'r') as f:
            lines = f.readlines()

        # Update the mapping lines
        new_lines = []
        for line in lines:
            if line.startswith("COM"):
                # Skip old mapping lines
                continue
            elif line.startswith("LAST VERIFIED:"):
                new_lines.append(f"LAST VERIFIED: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            else:
                new_lines.append(line)

            # Add new mappings after header
            if "LAST VERIFIED:" in line:
                new_lines.append("\n")
                for device, port in device_map.items():
                    voltage_range = {"D2001": "200V", "D6001": "600V", "D8001": "800V"}[device]
                    new_lines.append(f"{port} = {device} ({voltage_range} model)\n")

        with open(map_file, 'w') as f:
            f.writelines(new_lines)

        print(f"\nDevice map saved to: {map_file}")

    except Exception as e:
        print(f"\nWarning: Could not update device map file: {e}")

def main():
    print("=" * 70)
    print("NICE Power Supply COM Port Verification and Remapping")
    print("=" * 70)

    # Find all NICE Power COM ports
    print("\nSearching for NICE Power supplies...")
    nice_ports = find_nice_power_ports()

    if len(nice_ports) < 3:
        print(f"\n[WARNING] Found only {len(nice_ports)} Silicon Labs port(s)")
        print("Expected 3 NICE Power supplies. Make sure all are connected via USB.")

        if len(nice_ports) == 0:
            print("\n[ERROR] No NICE Power supplies detected!")
            return

    print(f"\nFound {len(nice_ports)} COM port(s):")
    for port in nice_ports:
        print(f"  - {port.device}: {port.description}")

    # Connect to each port
    print("\n" + "=" * 70)
    print("Testing connections...")
    print("=" * 70)

    port_supplies = {}  # {port_name: psu_instance}

    for port_info in nice_ports:
        port_name = port_info.device
        print(f"\n[{port_name}] Testing...")

        psu, connected = test_port(port_name)
        if connected:
            print(f"[{port_name}] ✓ Connected")
            port_supplies[port_name] = psu
        else:
            print(f"[{port_name}] ✗ No response")

    if len(port_supplies) < 3:
        print(f"\n[WARNING] Only {len(port_supplies)}/3 supplies responding")
        proceed = input("\nProceed anyway? (yes/no): ").strip().lower()
        if proceed not in ['yes', 'y']:
            # Turn off all
            for psu in port_supplies.values():
                psu.set_voltage(0.0)
                psu.close()
            return

    try:
        # Set test voltages and get port->voltage mapping
        port_voltages, port_expected_devices = set_test_voltages(port_supplies)

        # Get user input for mapping
        device_map = get_user_mapping(port_supplies, port_voltages, port_expected_devices)

        # Confirm mapping
        print("\n" + "=" * 70)
        print("CONFIRMED MAPPING:")
        print("=" * 70)
        for device, port in device_map.items():
            actual_voltage = port_voltages[port]
            print(f"  {device} → {port} ({actual_voltage:.1f}V)")

        confirm = input("\nIs this mapping correct? (yes/no): ").strip().lower()

        if confirm in ['yes', 'y']:
            # Update all config files
            update_all_configs(device_map)

            # Save to device map file
            save_device_map(device_map)

            print("\n✓ COM port mapping updated successfully!")
        else:
            print("\nMapping cancelled. No changes made.")

    finally:
        # Turn off all supplies and close connections
        print("\n" + "=" * 70)
        print("Turning off all power supplies...")
        print("=" * 70)

        for port_name, psu in port_supplies.items():
            try:
                print(f"[{port_name}] Turning off...")
                psu.set_voltage(0.0)
                time.sleep(0.3)
                psu.close()
                print(f"[{port_name}] Off and closed")
            except Exception as e:
                print(f"[{port_name}] Error: {e}")

        print("\nDone!")

if __name__ == "__main__":
    main()
