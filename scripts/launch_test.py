#!/usr/bin/env python3
"""
Unified Radiation Test Launcher
Launches oscilloscope and webcam, monitors both, stops all when either closes
"""

import os
import sys
import subprocess
import time
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

class UnifiedTestLauncher:
    def __init__(self, config_name, test_name=None):
        self.base_dir = Path(__file__).parent
        self.config_name = config_name
        self.test_name = test_name or "test"

        # Create test directory
        utc_now = datetime.now(timezone.utc)
        timestamp = utc_now.strftime("%Y%m%d_%H%M%S_UTC")
        dir_name = f"{timestamp}_{self.test_name}"

        tests_base = self.base_dir / "radiation_tests"
        tests_base.mkdir(exist_ok=True)
        self.test_dir = tests_base / dir_name
        self.test_dir.mkdir(exist_ok=True)

        self.start_time = utc_now
        self.osc_process = None
        self.webcam_process = None

    def launch_systems(self):
        """Launch both oscilloscope and webcam"""
        print("\n" + "="*70)
        print("RADIATION TEST LAUNCHER")
        print("="*70)
        print(f"Test Directory: {self.test_dir}")
        print(f"Start Time: {self.start_time.isoformat()}")
        print("="*70 + "\n")

        # Paths
        osc_script = self.base_dir / "oscilloscope" / "scripts" / "live_16ch_multiscope_enhanced.py"
        osc_config = self.base_dir / "oscilloscope" / "configs" / self.config_name
        webcam_script = self.base_dir / "uti_thermal" / "scripts" / "dual_recorder.py"

        # Check files exist
        if not osc_script.exists():
            print(f"ERROR: Oscilloscope script not found: {osc_script}")
            return False
        if not osc_config.exists():
            print(f"ERROR: Config not found: {osc_config}")
            return False

        webcam_available = webcam_script.exists()

        # Launch webcam first
        if webcam_available:
            print("Launching webcam recorder...")
            self.webcam_process = subprocess.Popen(
                [sys.executable, str(webcam_script)],
                cwd=str(webcam_script.parent)
            )
            print(f"  PID: {self.webcam_process.pid}")
            print("  Waiting 15 seconds for cameras to initialize...\n")
            time.sleep(15)

        # Launch oscilloscope
        print("Launching oscilloscope capture...")
        self.osc_process = subprocess.Popen(
            [sys.executable, str(osc_script), str(osc_config)],
            cwd=str(osc_script.parent)
        )
        print(f"  PID: {self.osc_process.pid}")
        print(f"  Config: {self.config_name}\n")

        return True

    def monitor_and_wait(self):
        """Monitor both processes - stop all when either exits"""
        print("="*70)
        print("SYSTEMS RUNNING")
        print("="*70)
        print("Both systems are capturing data.")
        print("Press 'q' in EITHER window to stop BOTH systems.")
        print("="*70 + "\n")

        try:
            while True:
                time.sleep(1)

                # Check if oscilloscope stopped
                if self.osc_process and self.osc_process.poll() is not None:
                    print("\n[!] Oscilloscope stopped - stopping webcam...")
                    self.stop_all()
                    break

                # Check if webcam stopped
                if self.webcam_process and self.webcam_process.poll() is not None:
                    print("\n[!] Webcam stopped - stopping oscilloscope...")
                    self.stop_all()
                    break

        except KeyboardInterrupt:
            print("\n\n[!] Ctrl+C detected - stopping all systems...")
            self.stop_all()

    def stop_all(self):
        """Force stop both processes"""
        if self.osc_process and self.osc_process.poll() is None:
            print("  Terminating oscilloscope...")
            self.osc_process.terminate()
            try:
                self.osc_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print("  Force killing oscilloscope...")
                self.osc_process.kill()

        if self.webcam_process and self.webcam_process.poll() is None:
            print("  Terminating webcam...")
            self.webcam_process.terminate()
            try:
                self.webcam_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print("  Force killing webcam...")
                self.webcam_process.kill()

        print("  All processes stopped.")
        time.sleep(2)  # Wait for files to flush

    def organize_files(self):
        """Move all output files into test directory"""
        print("\n" + "="*70)
        print("ORGANIZING FILES")
        print("="*70)

        # Create subdirectories
        (self.test_dir / "oscilloscope_data").mkdir(exist_ok=True)
        (self.test_dir / "oscilloscope_plots").mkdir(exist_ok=True)
        (self.test_dir / "webcam_videos").mkdir(exist_ok=True)
        (self.test_dir / "test_metadata").mkdir(exist_ok=True)

        moved_count = 0

        # Get timestamp from directory name for file matching
        test_timestamp = self.test_dir.name.split('_')[0]  # YYYYMMDD

        # Move oscilloscope CSV files
        print("\nMoving oscilloscope data...")
        data_dir = self.base_dir / "data"
        if data_dir.exists():
            for csv_file in sorted(data_dir.glob("multiscope_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True):
                if test_timestamp in csv_file.name:
                    dest = self.test_dir / "oscilloscope_data" / csv_file.name
                    shutil.move(str(csv_file), str(dest))
                    print(f"  [OK] {csv_file.name}")
                    moved_count += 1

            for perf_file in sorted(data_dir.glob("performance_*.txt"), key=lambda x: x.stat().st_mtime, reverse=True):
                if test_timestamp in perf_file.name:
                    dest = self.test_dir / "oscilloscope_data" / perf_file.name
                    shutil.move(str(perf_file), str(dest))
                    print(f"  [OK] {perf_file.name}")
                    moved_count += 1

        # Move oscilloscope plots
        print("\nMoving oscilloscope plots...")
        plots_dir = self.base_dir / "plots"
        if plots_dir.exists():
            for png_file in sorted(plots_dir.glob("multiscope_*.png"), key=lambda x: x.stat().st_mtime, reverse=True):
                if test_timestamp in png_file.name:
                    dest = self.test_dir / "oscilloscope_plots" / png_file.name
                    shutil.move(str(png_file), str(dest))
                    print(f"  [OK] {png_file.name}")
                    moved_count += 1

        # Move webcam recordings
        print("\nMoving webcam recordings...")
        recordings_dir = self.base_dir / "recordings"
        if recordings_dir.exists():
            recording_folders = sorted(recordings_dir.glob("recording_*"), key=lambda x: x.stat().st_mtime, reverse=True)
            for recording_folder in recording_folders[:1]:  # Just get the most recent
                if test_timestamp in recording_folder.name:
                    for video_file in recording_folder.iterdir():
                        dest = self.test_dir / "webcam_videos" / video_file.name
                        shutil.move(str(video_file), str(dest))
                        print(f"  [OK] {video_file.name}")
                        moved_count += 1
                    try:
                        recording_folder.rmdir()
                    except:
                        pass

        print(f"\nTotal files moved: {moved_count}")
        return moved_count

    def create_manifest(self):
        """Create test manifest with all metadata"""
        print("\nCreating test manifest...")

        end_time = datetime.now(timezone.utc)
        duration = (end_time - self.start_time).total_seconds()

        # Load config
        config_path = self.base_dir / "oscilloscope" / "configs" / self.config_name
        config_data = {}
        channels_info = []

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)

                if 'scopes' in config_data:
                    for scope_serial, scope_config in config_data['scopes'].items():
                        scope_channels = []
                        if 'channels' in scope_config:
                            for ch_num, ch_config in scope_config['channels'].items():
                                if ch_config.get('enabled', True):
                                    scope_channels.append({
                                        "channel": int(ch_num),
                                        "device_name": ch_config.get('name', f'CH{ch_num}'),
                                        "voltage_scale": f"{ch_config.get('scale_volts_per_div', 'N/A')}V/div",
                                        "probe_attenuation": f"{ch_config.get('probe_attenuation', 'N/A')}x"
                                    })

                        channels_info.append({
                            "scope_serial": scope_serial,
                            "channels": scope_channels
                        })
            except Exception as e:
                print(f"  Warning: Could not parse config: {e}")

        # Create manifest
        manifest = {
            "test_session": {
                "test_name": self.test_name,
                "start_time_utc": self.start_time.isoformat(),
                "end_time_utc": end_time.isoformat(),
                "duration_seconds": duration,
                "test_directory": str(self.test_dir),
                "test_type": "radiation_testing"
            },
            "configuration": {
                "oscilloscope_config": self.config_name,
                "config_path": str(config_path),
                "capture_settings": config_data.get('capture_settings', {})
            },
            "oscilloscope_channels": channels_info,
            "data_outputs": {
                "oscilloscope_csv": "oscilloscope_data/*.csv",
                "oscilloscope_screenshots": "oscilloscope_plots/*.png",
                "oscilloscope_performance": "oscilloscope_data/performance_*.txt",
                "webcam_videos": "webcam_videos/*",
                "test_manifest": "test_metadata/test_manifest.json"
            }
        }

        # Save manifest
        manifest_path = self.test_dir / "test_metadata" / "test_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"  [OK] {manifest_path}")

        # Create summary
        summary_path = self.test_dir / "TEST_SUMMARY.txt"
        with open(summary_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write("RADIATION TEST SESSION SUMMARY\n")
            f.write("="*70 + "\n\n")
            f.write(f"Test Name: {self.test_name}\n")
            f.write(f"Configuration: {self.config_name}\n")
            f.write(f"Start Time (UTC): {self.start_time.isoformat()}\n")
            f.write(f"End Time (UTC): {end_time.isoformat()}\n")
            f.write(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)\n\n")

            f.write("Oscilloscope Channels:\n")
            for scope in channels_info:
                f.write(f"\n  Scope: {scope['scope_serial']}\n")
                for ch in scope['channels']:
                    f.write(f"    CH{ch['channel']}: {ch['device_name']} @ {ch['voltage_scale']}\n")

            f.write("\n" + "="*70 + "\n")
            f.write("All data files collected in test directory\n")
            f.write("="*70 + "\n")

        print(f"  [OK] {summary_path}")

    def finalize(self):
        """Print final summary"""
        end_time = datetime.now(timezone.utc)
        duration = (end_time - self.start_time).total_seconds()

        print("\n" + "="*70)
        print("TEST SESSION COMPLETE")
        print("="*70)
        print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"\nAll data saved to:")
        print(f"  {self.test_dir}")
        print("\nKey files:")
        print(f"  - TEST_SUMMARY.txt")
        print(f"  - test_metadata/test_manifest.json")
        print(f"  - oscilloscope_data/*.csv")
        print(f"  - oscilloscope_plots/*.png")
        print(f"  - webcam_videos/*.avi")
        print("="*70 + "\n")


def main():
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python launch_test.py <config_name> [test_name]")
        print("\nExamples:")
        print("  python launch_test.py LT_RAD_TESTCONFIG.json")
        print("  python launch_test.py GAN_HV_TESTCONFIG.json gan_test_1")
        print("\nAvailable configs:")

        base_dir = Path(__file__).parent
        config_dir = base_dir / "oscilloscope" / "configs"
        if config_dir.exists():
            for config in sorted(config_dir.glob("*.json")):
                print(f"  - {config.name}")

        return 1

    config_name = sys.argv[1]
    test_name = sys.argv[2] if len(sys.argv) > 2 else None

    # Create launcher
    launcher = UnifiedTestLauncher(config_name, test_name)

    # Launch both systems
    if not launcher.launch_systems():
        return 1

    # Monitor until either stops
    launcher.monitor_and_wait()

    # Organize all files
    launcher.organize_files()

    # Create manifest and summary
    launcher.create_manifest()

    # Print final summary
    launcher.finalize()

    return 0


if __name__ == "__main__":
    sys.exit(main())
