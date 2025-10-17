#!/usr/bin/env python3
"""
Radiation Test Launcher - Unified Test System
Combines oscilloscope capture and webcam recording for radiation testing

Features:
- Launches both oscilloscope capture and webcam recording simultaneously
- Creates organized timestamped test folders
- Includes test manifest with device information
- Separate windows for visual monitoring
- All data organized for easy post-test analysis
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime, timezone
from pathlib import Path

class RadiationTestLauncher:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.test_dir = None
        self.test_name = None
        self.config_name = None
        self.oscilloscope_process = None
        self.webcam_process = None

    def create_test_directory(self, test_name=None, config_name=None):
        """
        Create a timestamped test directory with organized structure
        """
        utc_now = datetime.now(timezone.utc)
        timestamp = utc_now.strftime("%Y%m%d_%H%M%S_UTC")

        if test_name:
            self.test_name = test_name
            dir_name = f"{timestamp}_{test_name}"
        else:
            self.test_name = "radiation_test"
            dir_name = timestamp

        self.config_name = config_name

        # Create test directory in radiation_tests/
        tests_base = self.base_dir / "radiation_tests"
        tests_base.mkdir(exist_ok=True)

        self.test_dir = tests_base / dir_name
        self.test_dir.mkdir(exist_ok=True)

        # Create subdirectories
        (self.test_dir / "oscilloscope_data").mkdir(exist_ok=True)
        (self.test_dir / "oscilloscope_plots").mkdir(exist_ok=True)
        (self.test_dir / "webcam_videos").mkdir(exist_ok=True)
        (self.test_dir / "test_metadata").mkdir(exist_ok=True)

        print(f"\n{'='*70}")
        print(f"RADIATION TEST SESSION")
        print(f"{'='*70}")
        print(f"Test Directory: {self.test_dir}")
        print(f"Test Name: {self.test_name}")
        if config_name:
            print(f"Config: {config_name}")
        print(f"Start Time (UTC): {utc_now.isoformat()}")
        print(f"{'='*70}\n")

        return self.test_dir

    def create_test_manifest(self, config_path=None, notes=None, devices_under_test=None):
        """
        Create a test manifest describing the test setup
        """
        utc_now = datetime.now(timezone.utc)

        manifest = {
            "test_session": {
                "test_name": self.test_name,
                "start_time_utc": utc_now.isoformat(),
                "start_timestamp_unix": utc_now.timestamp(),
                "test_directory": str(self.test_dir),
                "test_type": "radiation_testing"
            },
            "configuration": {
                "oscilloscope_config": self.config_name,
                "config_path": str(config_path) if config_path else None
            },
            "devices_under_test": devices_under_test or [],
            "test_notes": notes or "",
            "data_outputs": {
                "oscilloscope_csv": "oscilloscope_data/*.csv",
                "oscilloscope_screenshots": "oscilloscope_plots/*.png",
                "oscilloscope_performance": "oscilloscope_data/performance_*.txt",
                "webcam_videos": "webcam_videos/*",
                "test_manifest": "test_metadata/test_manifest.json"
            }
        }

        # Load config to extract device names
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)

                # Extract channel names from config
                channels_info = []
                if 'scopes' in config:
                    for scope_serial, scope_config in config['scopes'].items():
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

                manifest["oscilloscope_channels"] = channels_info
                manifest["configuration"]["capture_settings"] = config.get('capture_settings', {})

            except Exception as e:
                print(f"Warning: Could not parse config file: {e}")

        # Save manifest
        manifest_path = self.test_dir / "test_metadata" / "test_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"Test manifest created: {manifest_path}\n")
        return manifest

    def launch_oscilloscope_capture(self, config_name):
        """
        Launch oscilloscope capture in a subprocess
        """
        print("Starting oscilloscope capture...")

        # Path to oscilloscope script
        osc_script = self.base_dir / "oscilloscope" / "scripts" / "live_16ch_multiscope_enhanced.py"
        config_path = self.base_dir / "oscilloscope" / "configs" / config_name

        if not osc_script.exists():
            print(f"ERROR: Oscilloscope script not found: {osc_script}")
            return None

        if not config_path.exists():
            print(f"ERROR: Config file not found: {config_path}")
            return None

        # Prepare environment to redirect output
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        # Redirect oscilloscope data and plots to test directory
        original_data_dir = self.base_dir / "data"
        original_plots_dir = self.base_dir / "plots"

        # Create symbolic links or modify config on the fly
        # For now, we'll let the script create files normally and move them after

        try:
            process = subprocess.Popen(
                [sys.executable, str(osc_script), str(config_path)],
                cwd=str(osc_script.parent),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True
            )

            print(f"  [OK] Oscilloscope capture started (PID: {process.pid})")
            print(f"  [OK] Config: {config_name}")
            print(f"  [OK] Output: {self.test_dir / 'oscilloscope_data'}\n")

            return process

        except Exception as e:
            print(f"ERROR launching oscilloscope capture: {e}")
            return None

    def launch_webcam_recording(self):
        """
        Launch webcam recording in a subprocess
        """
        print("Starting webcam recording...")

        # Path to webcam script
        webcam_script = self.base_dir / "uti_thermal" / "scripts" / "dual_recorder.py"

        if not webcam_script.exists():
            print(f"ERROR: Webcam script not found: {webcam_script}")
            return None

        # Prepare environment
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        try:
            # Launch webcam with new console window on Windows
            # Don't capture stdout/stderr so OpenCV window can display
            if sys.platform == 'win32':
                process = subprocess.Popen(
                    [sys.executable, str(webcam_script)],
                    cwd=str(webcam_script.parent),
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                process = subprocess.Popen(
                    [sys.executable, str(webcam_script)],
                    cwd=str(webcam_script.parent),
                    env=env
                )

            print(f"  [OK] Webcam recording started (PID: {process.pid})")
            print(f"  [OK] Output: {self.test_dir / 'webcam_videos'}\n")

            return process

        except Exception as e:
            print(f"ERROR launching webcam recording: {e}")
            return None

    def monitor_processes(self):
        """
        Monitor both processes and handle their output
        """
        print(f"{'='*70}")
        print("TEST IN PROGRESS")
        print(f"{'='*70}")
        print("Both systems are running...")
        print("\nTo stop the test:")
        print("  - Press 'q' in the oscilloscope window to stop scope capture")
        print("  - Press 'q' in the webcam window to stop video recording")
        print("  - Or press Ctrl+C here to stop everything")
        print(f"{'='*70}\n")

        try:
            # Wait for both processes to complete
            osc_running = self.oscilloscope_process is not None
            webcam_running = self.webcam_process is not None

            while osc_running or webcam_running:
                time.sleep(1)

                # Check oscilloscope process
                if osc_running and self.oscilloscope_process.poll() is not None:
                    print("\nOscilloscope capture finished.")
                    osc_running = False

                # Check webcam process
                if webcam_running and self.webcam_process.poll() is not None:
                    print("\nWebcam recording finished.")
                    webcam_running = False

        except KeyboardInterrupt:
            print("\n\nTest interrupted by user. Stopping all processes...")
            self.stop_all_processes()

    def stop_all_processes(self):
        """
        Stop all running processes
        """
        if self.oscilloscope_process and self.oscilloscope_process.poll() is None:
            print("Stopping oscilloscope capture...")
            self.oscilloscope_process.terminate()
            self.oscilloscope_process.wait(timeout=5)

        if self.webcam_process and self.webcam_process.poll() is None:
            print("Stopping webcam recording...")
            self.webcam_process.terminate()
            self.webcam_process.wait(timeout=5)

    def organize_output_files(self):
        """
        Move output files from default locations to test directory
        """
        print("\nOrganizing output files...")

        # Move oscilloscope data files
        data_dir = self.base_dir / "data"
        if data_dir.exists():
            for csv_file in data_dir.glob("multiscope_*.csv"):
                dest = self.test_dir / "oscilloscope_data" / csv_file.name
                csv_file.rename(dest)
                print(f"  [OK] Moved: {csv_file.name}")

            for perf_file in data_dir.glob("performance_*.txt"):
                dest = self.test_dir / "oscilloscope_data" / perf_file.name
                perf_file.rename(dest)
                print(f"  [OK] Moved: {perf_file.name}")

        # Move oscilloscope plots
        plots_dir = self.base_dir / "plots"
        if plots_dir.exists():
            for png_file in plots_dir.glob("multiscope_*.png"):
                dest = self.test_dir / "oscilloscope_plots" / png_file.name
                png_file.rename(dest)
                print(f"  [OK] Moved: {png_file.name}")

        # Move webcam recordings
        recordings_dir = self.base_dir / "recordings"
        if recordings_dir.exists():
            # Find the most recent recording folder
            recording_folders = sorted(recordings_dir.glob("recording_*"), key=os.path.getmtime, reverse=True)
            if recording_folders:
                latest_recording = recording_folders[0]
                for video_file in latest_recording.glob("*"):
                    dest = self.test_dir / "webcam_videos" / video_file.name
                    video_file.rename(dest)
                    print(f"  [OK] Moved: {video_file.name}")

                # Remove empty recording folder
                try:
                    latest_recording.rmdir()
                except:
                    pass

        print("\nAll files organized in test directory.")

    def finalize_test(self):
        """
        Finalize test session with summary
        """
        utc_now = datetime.now(timezone.utc)

        # Update manifest with end time
        manifest_path = self.test_dir / "test_metadata" / "test_manifest.json"
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            manifest["test_session"]["end_time_utc"] = utc_now.isoformat()
            manifest["test_session"]["end_timestamp_unix"] = utc_now.timestamp()

            start_time = manifest["test_session"]["start_timestamp_unix"]
            duration = utc_now.timestamp() - start_time
            manifest["test_session"]["duration_seconds"] = duration

            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)

        # Create summary file
        summary_path = self.test_dir / "TEST_SUMMARY.txt"
        with open(summary_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write("RADIATION TEST SESSION SUMMARY\n")
            f.write("="*70 + "\n\n")
            f.write(f"Test Name: {self.test_name}\n")
            f.write(f"Configuration: {self.config_name}\n")
            f.write(f"Start Time (UTC): {manifest['test_session']['start_time_utc']}\n")
            f.write(f"End Time (UTC): {utc_now.isoformat()}\n")
            f.write(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)\n\n")

            f.write("Test Directory Structure:\n")
            f.write("  oscilloscope_data/  - CSV data files from all scopes\n")
            f.write("  oscilloscope_plots/ - Screenshot of final waveforms\n")
            f.write("  webcam_videos/      - Thermal + webcam recordings\n")
            f.write("  test_metadata/      - Test manifest and configuration\n\n")

            f.write("Oscilloscope Channels:\n")
            for scope in manifest.get('oscilloscope_channels', []):
                f.write(f"\n  Scope: {scope['scope_serial']}\n")
                for ch in scope['channels']:
                    f.write(f"    CH{ch['channel']}: {ch['device_name']} @ {ch['voltage_scale']}\n")

            f.write("\n" + "="*70 + "\n")
            f.write("Test Complete\n")
            f.write("="*70 + "\n")

        print(f"\n{'='*70}")
        print("TEST SESSION COMPLETE")
        print(f"{'='*70}")
        print(f"Test Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"\nAll data saved to: {self.test_dir}")
        print(f"\nKey files:")
        print(f"  - TEST_SUMMARY.txt (this summary)")
        print(f"  - test_metadata/test_manifest.json (detailed test info)")
        print(f"  - oscilloscope_data/*.csv (raw waveform data)")
        print(f"  - webcam_videos/*combined.avi (synchronized video)")
        print(f"{'='*70}\n")


def main():
    print("\n" + "="*70)
    print("RADIATION TEST LAUNCHER")
    print("="*70)

    # Parse command line arguments
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python radiation_test_launcher.py <config_name> [test_name] [notes]")
        print("\nExamples:")
        print("  python radiation_test_launcher.py LT_RAD_TESTCONFIG.json")
        print("  python radiation_test_launcher.py GAN_HV_TESTCONFIG.json gan_test_1")
        print("  python radiation_test_launcher.py GAN_HV_TESTCONFIG.json gan_epc2206 \"Testing EPC2206 devices\"")
        print("\nAvailable configs:")

        config_dir = Path(__file__).parent / "oscilloscope" / "configs"
        if config_dir.exists():
            for config in sorted(config_dir.glob("*.json")):
                print(f"  - {config.name}")

        return 1

    config_name = sys.argv[1]
    test_name = sys.argv[2] if len(sys.argv) > 2 else None
    notes = sys.argv[3] if len(sys.argv) > 3 else None

    # Initialize launcher
    launcher = RadiationTestLauncher()

    # Create test directory
    test_dir = launcher.create_test_directory(test_name=test_name, config_name=config_name)

    # Create test manifest
    config_path = launcher.base_dir / "oscilloscope" / "configs" / config_name
    manifest = launcher.create_test_manifest(config_path=config_path, notes=notes)

    print("Preparing to launch test systems...")
    print("  - Webcam: Dual camera recording (thermal + 4K) - LAUNCHING FIRST")
    print("  - Oscilloscope: 16-channel multi-scope capture - LAUNCHING SECOND")
    print()

    # Launch webcam FIRST to avoid USB conflicts
    launcher.webcam_process = launcher.launch_webcam_recording()

    # Wait 15 seconds for cameras to fully initialize
    print("Waiting 15 seconds for cameras to initialize...")
    for i in range(15, 0, -1):
        print(f"  {i} seconds remaining...", end='\r', flush=True)
        time.sleep(1)
    print("\n")

    # Launch oscilloscope SECOND
    launcher.oscilloscope_process = launcher.launch_oscilloscope_capture(config_name)
    time.sleep(2)  # Brief wait for oscilloscope to start

    # Check if at least oscilloscope started
    if not launcher.oscilloscope_process:
        print("\nERROR: Failed to start oscilloscope capture!")
        launcher.stop_all_processes()
        return 1

    # Warn if webcam didn't start, but continue with oscilloscope only
    if not launcher.webcam_process:
        print("\nWARNING: Webcam recording did not start.")
        print("Continuing with oscilloscope capture only...")
        print("(Make sure cameras are connected and accessible)\n")

    # Monitor processes
    try:
        launcher.monitor_processes()
    finally:
        # Cleanup
        launcher.stop_all_processes()

        # Wait a moment for files to be written
        time.sleep(2)

        # Organize output files
        launcher.organize_output_files()

        # Finalize test
        launcher.finalize_test()

    return 0


if __name__ == "__main__":
    sys.exit(main())
