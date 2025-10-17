"""
Power Supply Live Monitor for Radiation Testing

This script:
1. Configures all power supplies (Rigol + NICE) from a config file
2. Maintains voltages at set levels
3. Continuously samples voltage/current at 1Hz
4. Logs all data to timestamped CSV file
5. Press 'Q' to stop recording and turn off all supplies

Usage:
    python power_supply_live_monitor.py config_file.json
"""

import sys
import os
import json
import time
import csv
import msvcrt
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add Rigol folder to path for NICE Power class import
SCRIPT_DIR = Path(__file__).parent.absolute()
SUNBURN_CODE_DIR = SCRIPT_DIR.parent.parent
RIGOL_DIR = SUNBURN_CODE_DIR / "Rigol"
sys.path.insert(0, str(RIGOL_DIR))

from NICE_POWER_SPPS_D2001_232 import NicePowerSupply
from rigol_usb_locator import RigolUsbLocator
from Rigol_DP832A import RigolPowerSupply

class PowerSupplyLiveMonitor:
    """
    Live monitoring and logging for Rigol and NICE Power supplies.
    """

    def __init__(self, config_path, output_dir=None):
        """Initialize monitor with config file."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.nice_supplies = {}
        self.rigol_supply = None
        self.rigol_config = None
        self.recording_folder = None
        self.csv_file = None
        self.csv_writer = None
        self.output_dir = Path(output_dir) if output_dir else None

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
        """Connect to all NICE power supplies defined in config."""
        print("=" * 70)
        print("Connecting to NICE Power Supplies")
        print("=" * 70)

        nice_config = {k: v for k, v in self.config['power_supplies'].items() if k != 'rigol'}

        for name, settings in nice_config.items():
            try:
                print(f"\n[{name}] Connecting to {settings['com_port']}...")
                print(f"  Model: {settings['model']}")
                print(f"  Description: {settings['description']}")

                psu = NicePowerSupply(
                    port=settings['com_port'],
                    device_addr=settings['device_addr'],
                    baudrate=settings['baudrate'],
                    timeout=2
                )

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

                    print(f"[Rigol CH{ch}] Waiting 2 seconds for voltage to settle...")
                    time.sleep(2.0)

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

    def configure_nice_supplies(self):
        """Configure all NICE supplies to default voltages from config."""
        print("\n" + "=" * 70)
        print("Setting NICE supplies to default voltages from config...")
        print("=" * 70)

        for name in self.nice_supplies.keys():
            settings = self.nice_supplies[name]['settings']
            if self.nice_supplies[name]['connected']:
                voltage = settings['default_voltage']
                current = settings['default_current']

                print(f"\n[{name}] Setting {voltage}V @ {current}A...")
                psu = self.nice_supplies[name]['instance']
                psu.configure_voltage_current(voltage, current)

                time.sleep(1.0)

                v_actual = psu.measure_voltage()
                i_actual = psu.measure_current()
                print(f"[{name}] Actual: {v_actual:.3f}V, {i_actual:.3f}A")

        print("=" * 70)

    def create_recording_folder(self):
        """Create timestamped folder for recording data."""
        self.start_time = datetime.now(timezone.utc)
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        folder_name = f"power_supply_recording_{timestamp}"

        # Use output_dir if specified, otherwise use default location
        if self.output_dir:
            self.recording_folder = self.output_dir / folder_name
        else:
            master_rad_test_dir = SUNBURN_CODE_DIR / "Master_Radiation_Test"
            self.recording_folder = master_rad_test_dir / folder_name

        self.recording_folder.mkdir(parents=True, exist_ok=True)

        print(f"\n[Recording] Folder created: {self.recording_folder}")
        return self.recording_folder

    def create_manifest(self):
        """Create a manifest file with configuration details."""
        manifest_path = self.recording_folder / "power_supply_manifest.txt"

        with open(manifest_path, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("POWER SUPPLY RECORDING MANIFEST\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Recording Start Time (UTC): {self.start_time.isoformat()}\n")
            f.write(f"Recording Folder: {self.recording_folder.name}\n\n")

            f.write("CONFIGURATION FILE:\n")
            f.write("-" * 70 + "\n")
            f.write(f"Path: {self.config_path}\n")
            f.write(f"Name: {self.config_path.name}\n\n")

            # Rigol configuration
            if self.rigol_supply and self.rigol_config:
                f.write("RIGOL POWER SUPPLY CONFIGURATION:\n")
                f.write("-" * 70 + "\n")
                f.write(f"Model: {self.rigol_config['model']}\n")
                f.write(f"Serial: {self.rigol_config['serial_number']}\n")
                f.write(f"Channels:\n")
                for ch_num, ch_config in self.rigol_config['channels'].items():
                    enabled = ch_config.get('enabled', True)
                    status = "ON" if enabled and ch_config['voltage'] > 0 else "OFF"
                    f.write(f"  CH{ch_num}: {ch_config['voltage']}V @ {ch_config['current']}A ({status})\n")
                f.write("\n")

            # NICE power supplies configuration
            if self.nice_supplies:
                f.write("NICE POWER SUPPLIES CONFIGURATION:\n")
                f.write("-" * 70 + "\n")
                for name in sorted(self.nice_supplies.keys()):
                    supply = self.nice_supplies[name]
                    settings = supply['settings']
                    connected = supply['connected']
                    status = "CONNECTED" if connected else "NOT CONNECTED"
                    f.write(f"{name}:\n")
                    f.write(f"  Model: {settings['model']}\n")
                    f.write(f"  COM Port: {settings['com_port']}\n")
                    f.write(f"  Voltage: {settings['default_voltage']}V\n")
                    f.write(f"  Current: {settings['default_current']}A\n")
                    f.write(f"  Status: {status}\n")
                    f.write(f"  Description: {settings['description']}\n\n")

            f.write("SYSTEM INFORMATION:\n")
            f.write("-" * 70 + "\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Platform: {sys.platform}\n\n")

            f.write("OUTPUT FILES:\n")
            f.write("-" * 70 + "\n")
            f.write(f"CSV Data: power_supply_data.csv\n")
            f.write(f"Sample Rate: 1 Hz\n")
            f.write(f"Manifest: power_supply_manifest.txt\n\n")

            f.write("NOTES:\n")
            f.write("-" * 70 + "\n")
            f.write("- Press 'Q' or Ctrl+C to stop recording\n")
            f.write("- All supplies automatically turn off when recording stops\n")
            f.write("- Timestamps are in UTC timezone\n")

        print(f"[Recording] Manifest created: {manifest_path}")
        return manifest_path

    def setup_csv_file(self):
        """Create CSV file and writer with headers."""
        csv_path = self.recording_folder / "power_supply_data.csv"

        # Build CSV headers
        headers = ["UTC_Timestamp"]

        # Rigol channels
        if self.rigol_supply:
            for ch_num in self.rigol_config['channels'].keys():
                headers.extend([
                    f"Rigol_CH{ch_num}_V",
                    f"Rigol_CH{ch_num}_A",
                    f"Rigol_CH{ch_num}_W"
                ])

        # NICE supplies
        for name in sorted(self.nice_supplies.keys()):
            if self.nice_supplies[name]['connected']:
                headers.extend([
                    f"{name}_V",
                    f"{name}_A"
                ])

        # Open CSV file
        self.csv_file = open(csv_path, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(headers)
        self.csv_file.flush()

        print(f"[Recording] CSV file: {csv_path}")
        print(f"[Recording] Headers: {len(headers)} columns")

        return csv_path

    def read_all_measurements(self):
        """Read voltage/current from all connected power supplies."""
        measurements = {}

        # Read Rigol channels
        if self.rigol_supply:
            measurements['rigol'] = {}
            for ch_num in self.rigol_config['channels'].keys():
                ch = int(ch_num)
                try:
                    v, i, p = self.rigol_supply.read_power_supply_channel(ch)
                    measurements['rigol'][ch] = {'voltage': v, 'current': i, 'power': p}
                except Exception as e:
                    print(f"[ERROR] Failed to read Rigol CH{ch}: {e}")
                    measurements['rigol'][ch] = {'voltage': 0.0, 'current': 0.0, 'power': 0.0}

        # Read NICE supplies
        measurements['nice'] = {}
        for name, supply in self.nice_supplies.items():
            if supply['connected']:
                try:
                    v = supply['instance'].measure_voltage()
                    i = supply['instance'].measure_current()
                    measurements['nice'][name] = {'voltage': v, 'current': i}
                except Exception as e:
                    print(f"[ERROR] Failed to read {name}: {e}")
                    measurements['nice'][name] = {'voltage': 0.0, 'current': 0.0}

        return measurements

    def write_csv_row(self, measurements):
        """Write measurement data to CSV file."""
        timestamp = datetime.now(timezone.utc).isoformat()

        row = [timestamp]

        # Rigol channels
        if self.rigol_supply:
            for ch_num in self.rigol_config['channels'].keys():
                ch = int(ch_num)
                if ch in measurements['rigol']:
                    row.extend([
                        f"{measurements['rigol'][ch]['voltage']:.4f}",
                        f"{measurements['rigol'][ch]['current']:.4f}",
                        f"{measurements['rigol'][ch]['power']:.4f}"
                    ])
                else:
                    row.extend(['0.0000', '0.0000', '0.0000'])

        # NICE supplies
        for name in sorted(self.nice_supplies.keys()):
            if self.nice_supplies[name]['connected']:
                if name in measurements['nice']:
                    row.extend([
                        f"{measurements['nice'][name]['voltage']:.4f}",
                        f"{measurements['nice'][name]['current']:.4f}"
                    ])
                else:
                    row.extend(['0.0000', '0.0000'])

        self.csv_writer.writerow(row)
        self.csv_file.flush()

    def display_measurements(self, measurements, sample_count):
        """Display measurements in terminal."""
        print("\n" + "=" * 70)
        print(f"Sample #{sample_count} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 70)

        # Rigol
        if self.rigol_supply:
            print("\n[Rigol Power Supply]")
            for ch_num in self.rigol_config['channels'].keys():
                ch = int(ch_num)
                if ch in measurements['rigol']:
                    m = measurements['rigol'][ch]
                    print(f"  CH{ch}: {m['voltage']:.3f}V, {m['current']:.3f}A, {m['power']:.3f}W")

        # NICE
        if measurements['nice']:
            print("\n[NICE Power Supplies]")
            for name in sorted(measurements['nice'].keys()):
                m = measurements['nice'][name]
                com_port = self.nice_supplies[name]['settings']['com_port']
                print(f"  {name:8s} ({com_port}): {m['voltage']:.3f}V, {m['current']:.3f}A")

        print("\nPress 'Q' to stop recording and turn off all supplies...")

    def turn_off_all(self):
        """Turn off all connected power supplies."""
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
        """Close all connections."""
        print("\nClosing all connections...")

        if self.rigol_supply:
            try:
                self.rigol_supply.close()
                print("[Rigol] Closed")
            except Exception as e:
                print(f"[Rigol] Error closing: {e}")

        for name, supply in self.nice_supplies.items():
            if supply['connected'] and supply['instance']:
                try:
                    supply['instance'].close()
                    print(f"[{name}] Closed")
                except Exception as e:
                    print(f"[{name}] Error closing: {e}")

        if self.csv_file:
            self.csv_file.close()
            print("[Recording] CSV file closed")

    def run_monitoring_loop(self):
        """Main monitoring loop - sample at 1Hz until 'Q' pressed."""
        print("\n" + "=" * 70)
        print("Starting live monitoring at 1Hz")
        print("Press 'Q' to stop recording")
        print("=" * 70)

        sample_count = 0

        try:
            while True:
                # Read all measurements
                measurements = self.read_all_measurements()

                # Write to CSV
                self.write_csv_row(measurements)

                # Display in terminal
                sample_count += 1
                self.display_measurements(measurements, sample_count)

                # Check for 'Q' keypress
                start_time = time.time()
                while time.time() - start_time < 1.0:
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').upper()
                        if key == 'Q':
                            print("\n\n[STOP] 'Q' pressed - stopping recording...")
                            return
                    time.sleep(0.01)

        except KeyboardInterrupt:
            print("\n\n[STOP] Ctrl+C pressed - stopping recording...")


def main():
    """Main entry point for power supply live monitor."""
    parser = argparse.ArgumentParser(
        description='Power Supply Live Monitor for Radiation Testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Monitor with default config
  python power_supply_live_monitor.py ../../Master_Radiation_Test/config/nice_power_config.json

  # Monitor with LTC Rad Test Board config
  python power_supply_live_monitor.py ../../Master_Radiation_Test/config/ltc_rad_test_board_config.json

Press 'Q' at any time to stop recording and turn off all supplies.
        '''
    )
    parser.add_argument(
        'config',
        type=str,
        help='Path to configuration JSON file'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Optional output directory (default: Master_Radiation_Test/)'
    )

    args = parser.parse_args()

    print("Power Supply Live Monitor for Radiation Testing")
    print("=" * 70)
    print(f"Config: {args.config}")
    if args.output_dir:
        print(f"Output dir: {args.output_dir}")
    print("=" * 70)

    # Create monitor
    try:
        monitor = PowerSupplyLiveMonitor(config_path=args.config, output_dir=args.output_dir)
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    try:
        # Connect to all supplies
        rigol_ok = monitor.connect_rigol()
        nice_ok = monitor.connect_nice_supplies()

        if not (rigol_ok or nice_ok):
            print("\n[ERROR] No power supplies connected!")
            sys.exit(1)

        # Configure all supplies
        monitor.configure_rigol()
        monitor.configure_nice_supplies()

        # Create recording folder, manifest, and CSV
        monitor.create_recording_folder()
        monitor.create_manifest()
        monitor.setup_csv_file()

        # Run monitoring loop
        monitor.run_monitoring_loop()

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Shutting down...")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always turn off and close
        monitor.turn_off_all()
        monitor.close_all()
        print("\nDone.")


if __name__ == "__main__":
    main()
