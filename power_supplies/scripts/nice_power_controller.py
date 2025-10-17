"""
NICE Power Supply Controller for Radiation Testing
Reads configuration from JSON config file (passed as argument).
Controls D2001, D6001, and D8001 power supplies using unified protocol.

Usage:
    python nice_power_controller.py config_file.json

Key Discovery (2025-10-16):
All NICE Power models (D2001, D6001, D8001) respond to the same D2001
custom ASCII protocol, regardless of advertised modbus capability.

WARNING: COM port assignments change after power cycles - verify before use!
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path

# Add Rigol folder to path for NICE Power class import
SCRIPT_DIR = Path(__file__).parent.absolute()
SUNBURN_CODE_DIR = SCRIPT_DIR.parent.parent
RIGOL_DIR = SUNBURN_CODE_DIR / "Rigol"
sys.path.insert(0, str(RIGOL_DIR))

from NICE_POWER_SPPS_D2001_232 import NicePowerSupply
from rigol_usb_locator import RigolUsbLocator
from Rigol_DP832A import RigolPowerSupply

class PowerSupplyController:
    """
    Controller for Rigol and NICE Power supplies.
    - Rigol: Uses USB/VISA (addressed by serial number)
    - NICE: Uses D2001 custom ASCII protocol over serial (all models)
    """

    def __init__(self, config_path=None):
        """
        Initialize controller with config file.

        :param config_path: Path to config JSON file. If None, uses default location.
        """
        if config_path is None:
            config_path = SUNBURN_CODE_DIR / "Master_Radiation_Test" / "config" / "nice_power_config.json"

        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.nice_supplies = {}  # NICE Power supply instances
        self.rigol_supply = None  # Rigol power supply instance
        self.rigol_config = None  # Rigol configuration

    def _load_config(self):
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            return json.load(f)

    def connect_rigol(self):
        """Connect to Rigol power supply using USB locator."""
        if 'rigol' not in self.config['power_supplies']:
            print("[Rigol] No Rigol configuration found, skipping")
            return False

        self.rigol_config = self.config['power_supplies']['rigol']

        print(f"\n[Rigol] Searching for power supply...")
        print(f"  Serial: {self.rigol_config['serial_number']}")
        print(f"  Model: {self.rigol_config['model']}")

        try:
            # Use RigolUsbLocator to find the power supply
            locator = RigolUsbLocator(verbose=False)
            locator.refresh()
            rigol_psu = locator.get_power_supply()

            if rigol_psu:
                self.rigol_supply = rigol_psu
                print(f"  [OK] Connected to Rigol power supply")
                return True
            else:
                print(f"  [WARN] Rigol power supply not found")
                return False

        except Exception as e:
            print(f"  [ERROR] Failed to connect to Rigol: {e}")
            return False

    def connect_nice_supplies(self):
        """Connect to all power supplies defined in config."""
        print("=" * 70)
        print("Connecting to NICE Power Supplies")
        print("=" * 70)

        # Filter out rigol from power_supplies config
        nice_config = {k: v for k, v in self.config['power_supplies'].items() if k != 'rigol'}

        for name, settings in nice_config.items():
            try:
                print(f"\n[{name}] Connecting to {settings['com_port']}...")
                print(f"  Model: {settings['model']}")
                print(f"  Description: {settings['description']}")

                # All models use the D2001 protocol
                psu = NicePowerSupply(
                    port=settings['com_port'],
                    device_addr=settings['device_addr'],
                    baudrate=settings['baudrate'],
                    timeout=2
                )

                # Verify connection
                voltage = psu.measure_voltage()
                current = psu.measure_current()

                if voltage is not None:
                    print(f"  [OK] Connected - Current state: {voltage:.3f}V, {current:.3f}A")
                    self.nice_supplies[name] = {
                        'instance': psu,
                        'settings': settings,
                        'connected': True
                    }
                else:
                    print(f"  [WARN] Connection uncertain - no voltage reading")
                    self.nice_supplies[name] = {
                        'instance': psu,
                        'settings': settings,
                        'connected': False
                    }

            except Exception as e:
                print(f"  [ERROR] Failed to connect: {e}")
                self.nice_supplies[name] = {
                    'instance': None,
                    'settings': settings,
                    'connected': False
                }

        print("\n" + "=" * 70)
        connected_count = sum(1 for s in self.nice_supplies.values() if s['connected'])
        print(f"Connected {connected_count}/{len(self.nice_supplies)} NICE power supplies")
        print("=" * 70)

        return connected_count == len(self.nice_supplies)

    def connect_all(self):
        """Connect to all power supplies (Rigol and NICE)."""
        print("=" * 70)
        print("Power Supply Connection")
        print("=" * 70)

        rigol_ok = self.connect_rigol()
        nice_ok = self.connect_nice_supplies()

        return rigol_ok or nice_ok

    def configure_rigol(self):
        """Configure Rigol power supply channels from config."""
        if not self.rigol_supply or not self.rigol_config:
            print("[Rigol] Not connected, skipping configuration")
            return False

        print("\n" + "=" * 70)
        print("Configuring Rigol Power Supply")
        print("=" * 70)

        try:
            for ch_num, ch_config in self.rigol_config['channels'].items():
                ch = int(ch_num)
                voltage = ch_config['voltage']
                current = ch_config['current']
                enabled = ch_config.get('enabled', True)

                print(f"\n[Rigol CH{ch}] Setting {voltage}V @ {current}A (enabled: {enabled})")

                if enabled and voltage > 0:
                    self.rigol_supply.turn_channel_on(ch)
                    self.rigol_supply.set_voltage(ch, voltage)
                    self.rigol_supply.set_current_limit(ch, current)

                    # Wait for voltage to settle (2 seconds for Rigol settling time)
                    print(f"[Rigol CH{ch}] Waiting 2 seconds for voltage to settle...")
                    time.sleep(2.0)

                    # Verify
                    v, i, p = self.rigol_supply.read_power_supply_channel(ch)
                    print(f"[Rigol CH{ch}] Actual: {v:.3f}V, {i:.3f}A, {p:.3f}W")
                else:
                    self.rigol_supply.turn_channel_off(ch)
                    print(f"[Rigol CH{ch}] Turned OFF")

            print("=" * 70)
            return True

        except Exception as e:
            print(f"[Rigol] Configuration failed: {e}")
            return False

    def set_voltage(self, supply_name, voltage, current=None):
        """
        Set voltage (and optionally current) for a specific NICE supply.

        :param supply_name: Name of supply (e.g., 'D2001', 'D6001', 'D8001')
        :param voltage: Voltage in volts
        :param current: Current limit in amps (uses default if None)
        """
        if supply_name not in self.nice_supplies:
            raise ValueError(f"Unknown supply: {supply_name}")

        supply = self.nice_supplies[supply_name]
        if not supply['connected']:
            raise RuntimeError(f"Supply {supply_name} not connected")

        # Check voltage limit
        max_v = supply['settings']['max_voltage']
        if voltage > max_v:
            raise ValueError(f"Voltage {voltage}V exceeds max {max_v}V for {supply_name}")

        # Use default current if not specified
        if current is None:
            current = supply['settings']['default_current']

        print(f"\n[{supply_name}] Setting {voltage}V @ {current}A...")
        supply['instance'].configure_voltage_current(voltage, current)

        # Wait for voltage to settle (~1 second settling time)
        time.sleep(1.0)

        # Verify
        v_actual = supply['instance'].measure_voltage()
        i_actual = supply['instance'].measure_current()
        print(f"[{supply_name}] Actual: {v_actual:.3f}V, {i_actual:.3f}A")

        return v_actual, i_actual

    def get_status(self, supply_name):
        """
        Get current voltage and current for a NICE supply.

        :param supply_name: Name of supply
        :return: (voltage, current) tuple
        """
        if supply_name not in self.nice_supplies:
            raise ValueError(f"Unknown supply: {supply_name}")

        supply = self.nice_supplies[supply_name]
        if not supply['connected']:
            return None, None

        voltage = supply['instance'].measure_voltage()
        current = supply['instance'].measure_current()
        return voltage, current

    def get_all_status(self):
        """Get status of all connected supplies (Rigol and NICE)."""
        print("\n" + "=" * 70)
        print("Power Supply Status")
        print("=" * 70)

        # Rigol status
        if self.rigol_supply:
            print("\n[Rigol Power Supply]")
            for ch_num in self.rigol_config['channels'].keys():
                ch = int(ch_num)
                try:
                    v, i, p = self.rigol_supply.read_power_supply_channel(ch)
                    print(f"  CH{ch}: {v:.3f}V, {i:.3f}A, {p:.3f}W")
                except:
                    print(f"  CH{ch}: [ERROR reading]")

        # NICE supplies status
        if self.nice_supplies:
            print("\n[NICE Power Supplies]")
            for name, supply in self.nice_supplies.items():
                if supply['connected']:
                    v, i = self.get_status(name)
                    print(f"  {name:8s} ({supply['settings']['com_port']}): {v:.3f}V, {i:.3f}A")
                else:
                    print(f"  {name:8s} ({supply['settings']['com_port']}): [NOT CONNECTED]")

        print("=" * 70)

    def turn_off_all(self):
        """Turn off all connected power supplies (Rigol and NICE)."""
        print("\n" + "=" * 70)
        print("Turning off all power supplies...")
        print("=" * 70)

        # Turn off Rigol channels
        if self.rigol_supply:
            try:
                print("[Rigol] Turning off all channels...")
                for ch in [1, 2, 3]:
                    self.rigol_supply.turn_channel_off(ch)
                    time.sleep(0.2)
                print("[Rigol] All channels off")
            except Exception as e:
                print(f"[Rigol] Error turning off: {e}")

        # Turn off NICE supplies
        for name, supply in self.nice_supplies.items():
            if supply['connected']:
                try:
                    print(f"[{name}] Turning off...")
                    supply['instance'].set_voltage(0.0)
                    time.sleep(0.3)
                    v = supply['instance'].measure_voltage()
                    print(f"[{name}] Off - Voltage: {v:.3f}V")
                except Exception as e:
                    print(f"[{name}] Error turning off: {e}")

        print("=" * 70)

    def close_all(self):
        """Close all connections (Rigol and NICE)."""
        print("\nClosing all connections...")

        # Close Rigol
        if self.rigol_supply:
            try:
                self.rigol_supply.close()
                print("[Rigol] Closed")
            except Exception as e:
                print(f"[Rigol] Error closing: {e}")

        # Close NICE supplies
        for name, supply in self.nice_supplies.items():
            if supply['connected'] and supply['instance']:
                try:
                    supply['instance'].close()
                    print(f"[{name}] Closed")
                except Exception as e:
                    print(f"[{name}] Error closing: {e}")

        self.nice_supplies = {}
        self.rigol_supply = None

def main():
    """
    Main entry point for the NICE Power Controller.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='NICE Power Supply Controller for Radiation Testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Use default config
  python nice_power_controller.py ../../Master_Radiation_Test/config/nice_power_config.json

  # Use custom config
  python nice_power_controller.py my_test_config.json

Config files should be in Master_Radiation_Test/config/ folder.
        '''
    )
    parser.add_argument(
        'config',
        type=str,
        help='Path to configuration JSON file'
    )

    args = parser.parse_args()

    print("NICE Power Supply Controller for Radiation Testing")
    print("=" * 70)
    print(f"Config: {args.config}")
    print("=" * 70)

    # Create controller with specified config
    try:
        controller = PowerSupplyController(config_path=args.config)
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("\nAvailable configs in Master_Radiation_Test/config/:")
        config_dir = SUNBURN_CODE_DIR / "Master_Radiation_Test" / "config"
        if config_dir.exists():
            for f in config_dir.glob("*.json"):
                print(f"  - {f.name}")
        sys.exit(1)

    try:
        # Connect to all supplies
        if not controller.connect_all():
            print("\n[WARNING] Not all supplies connected - proceeding anyway")

        # Get initial status
        controller.get_all_status()

        # Configure Rigol from config
        controller.configure_rigol()

        # Set NICE supplies to default voltages from config
        print("\n" + "=" * 70)
        print("Setting NICE supplies to default voltages from config...")
        print("=" * 70)
        for name in controller.nice_supplies.keys():
            settings = controller.nice_supplies[name]['settings']
            if controller.nice_supplies[name]['connected']:
                controller.set_voltage(name, settings['default_voltage'])

        # Get final status
        controller.get_all_status()

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Shutting down...")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always turn off and close
        controller.turn_off_all()
        controller.close_all()
        print("\nDone.")

if __name__ == "__main__":
    main()
