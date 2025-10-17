"""
Master Radiation Test Launcher

Launches all three recording systems concurrently:
1. Thermal camera + webcam recording (resilient)
2. Power supply live monitoring and logging
3. 16-channel oscilloscope capture

Usage:
    python launch_radiation_test.py <power_supply_config> <oscilloscope_config> [webcam_index]

Examples:
    python launch_radiation_test.py config/ltc_rad_test_board_config.json config/SCOPE_LT_RAD_TESTCONFIG.json 1
    python launch_radiation_test.py config/ltc_rad_test_board_config.json config/SCOPE_LT_RAD_TESTCONFIG.json 0
"""

import sys
import os
import subprocess
import time
import signal
from pathlib import Path
from datetime import datetime, timezone

# Get script directory
SCRIPT_DIR = Path(__file__).parent.absolute()
MASTER_RAD_TEST_DIR = SCRIPT_DIR.parent
SUNBURN_CODE_DIR = MASTER_RAD_TEST_DIR.parent

# Paths to the three scripts
THERMAL_SCRIPT = SUNBURN_CODE_DIR / "uti_thermal" / "scripts" / "dual_recorder_resilient.py"
POWER_SUPPLY_SCRIPT = SUNBURN_CODE_DIR / "Power_Supplies" / "scripts" / "power_supply_live_monitor.py"
OSCILLOSCOPE_SCRIPT = SUNBURN_CODE_DIR / "oscilloscope" / "scripts" / "live_16ch_multiscope_enhanced.py"

# Global list to track subprocesses
processes = []

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n[MASTER] Received interrupt signal, stopping all processes...")
    cleanup()
    sys.exit(0)

def cleanup():
    """Terminate all running subprocesses"""
    print("[MASTER] Terminating all recording processes...")
    for name, proc in processes:
        if proc.poll() is None:  # Process is still running
            print(f"[MASTER] Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"[MASTER] Force killing {name}...")
                proc.kill()
    print("[MASTER] All processes stopped.")

def main():
    print("=" * 70)
    print("MASTER RADIATION TEST LAUNCHER")
    print("=" * 70)

    # Parse arguments
    if len(sys.argv) < 3:
        print("ERROR: Missing required arguments!")
        print("\nUsage:")
        print("  python launch_radiation_test.py <power_supply_config> <oscilloscope_config> [webcam_index]")
        print("\nExamples:")
        print("  python launch_radiation_test.py config/ltc_rad_test_board_config.json config/SCOPE_LT_RAD_TESTCONFIG.json 1")
        print("  python launch_radiation_test.py config/ltc_rad_test_board_config.json config/SCOPE_LT_RAD_TESTCONFIG.json 0")
        return 1

    power_supply_config = sys.argv[1]
    oscilloscope_config = sys.argv[2]
    webcam_index = sys.argv[3] if len(sys.argv) > 3 else "1"

    # Make configs absolute paths if they're relative (resolve from Master_Radiation_Test dir)
    if not os.path.isabs(power_supply_config):
        power_supply_config = os.path.abspath(os.path.join(MASTER_RAD_TEST_DIR, power_supply_config))
    if not os.path.isabs(oscilloscope_config):
        oscilloscope_config = os.path.abspath(os.path.join(MASTER_RAD_TEST_DIR, oscilloscope_config))

    # Verify config files exist
    if not os.path.exists(power_supply_config):
        print(f"ERROR: Power supply config not found: {power_supply_config}")
        return 1
    if not os.path.exists(oscilloscope_config):
        print(f"ERROR: Oscilloscope config not found: {oscilloscope_config}")
        return 1

    # Create master output directory with UTC timestamp in Master_Radiation_Test folder
    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    test_start_time = datetime.now(timezone.utc)
    master_output_dir = MASTER_RAD_TEST_DIR / f"radiation_test_{timestamp_str}"
    master_output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nMaster output directory: {master_output_dir}")
    print(f"Power supply config: {os.path.basename(power_supply_config)}")
    print(f"Oscilloscope config: {os.path.basename(oscilloscope_config)}")
    print(f"Webcam index: {webcam_index}")
    print("=" * 70)

    # Create manifest file
    manifest_path = master_output_dir / "test_manifest.txt"
    with open(manifest_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("RADIATION TEST MANIFEST\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Test Start Time (UTC): {test_start_time.isoformat()}\n")
        f.write(f"Test Folder: {master_output_dir.name}\n\n")

        f.write("CONFIGURATION FILES:\n")
        f.write("-" * 70 + "\n")
        f.write(f"Power Supply Config: {power_supply_config}\n")
        f.write(f"  Basename: {os.path.basename(power_supply_config)}\n")
        f.write(f"Oscilloscope Config: {oscilloscope_config}\n")
        f.write(f"  Basename: {os.path.basename(oscilloscope_config)}\n")
        f.write(f"Webcam Index: {webcam_index}\n\n")

        f.write("LAUNCHED SYSTEMS:\n")
        f.write("-" * 70 + "\n")
        f.write(f"1. Thermal Camera Recorder (Resilient)\n")
        f.write(f"   Script: {THERMAL_SCRIPT}\n")
        f.write(f"   Output: Subfolder 'recording_*' in this directory\n\n")

        f.write(f"2. Power Supply Monitor\n")
        f.write(f"   Script: {POWER_SUPPLY_SCRIPT}\n")
        f.write(f"   Output: 'power_supply_recording_*' in Master_Radiation_Test/\n\n")

        f.write(f"3. Oscilloscope 16-Channel Capture\n")
        f.write(f"   Script: {OSCILLOSCOPE_SCRIPT}\n")
        f.write(f"   Output: 'scope_recording_*' in Master_Radiation_Test/\n\n")

        f.write("SYSTEM INFORMATION:\n")
        f.write("-" * 70 + "\n")
        f.write(f"Python: {sys.version}\n")
        f.write(f"Platform: {sys.platform}\n\n")

        f.write("NOTES:\n")
        f.write("-" * 70 + "\n")
        f.write("- Each subsystem creates its own timestamped output folder\n")
        f.write("- Thermal data is in this folder's recording_* subfolder\n")
        f.write("- Power supply and oscilloscope data are in Master_Radiation_Test/\n")
        f.write("- Press Ctrl+C in master window to stop all systems\n")
        f.write("- If one system crashes, others continue running\n")

    print(f"[MASTER] Manifest created: {manifest_path}")

    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Launch thermal camera recorder FIRST to claim USB devices
    print("\n[MASTER] Launching thermal camera recorder (priority start)...")
    thermal_cmd = [
        "python",
        str(THERMAL_SCRIPT),
        str(master_output_dir),
        webcam_index
    ]
    print(f"[MASTER] Command: {' '.join(thermal_cmd)}")

    # Create log files for thermal output
    thermal_stdout_log = master_output_dir / "thermal_stdout.log"
    thermal_stderr_log = master_output_dir / "thermal_stderr.log"

    thermal_proc = subprocess.Popen(
        thermal_cmd,
        stdout=open(thermal_stdout_log, 'w'),
        stderr=open(thermal_stderr_log, 'w'),
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    processes.append(("Thermal Recorder", thermal_proc))
    print(f"[MASTER] Thermal recorder started (PID: {thermal_proc.pid})")
    print(f"[MASTER] Thermal logs: {thermal_stdout_log} / {thermal_stderr_log}")

    # Wait 10 seconds for thermal/webcam to initialize and claim USB devices
    print(f"[MASTER] Waiting 10 seconds for cameras to initialize...")
    for i in range(10, 0, -1):
        print(f"[MASTER]   {i}...", end='\r')
        time.sleep(1)
    print(f"[MASTER]   Ready!    ")

    # Launch power supply monitor
    print("\n[MASTER] Launching power supply monitor...")
    power_cmd = [
        "python",
        str(POWER_SUPPLY_SCRIPT),
        power_supply_config
    ]
    print(f"[MASTER] Command: {' '.join(power_cmd)}")

    # Create log files for power supply output
    power_stdout_log = master_output_dir / "power_supply_stdout.log"
    power_stderr_log = master_output_dir / "power_supply_stderr.log"

    power_proc = subprocess.Popen(
        power_cmd,
        stdout=open(power_stdout_log, 'w'),
        stderr=open(power_stderr_log, 'w'),
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    processes.append(("Power Supply Monitor", power_proc))
    print(f"[MASTER] Power supply monitor started (PID: {power_proc.pid})")
    print(f"[MASTER] Power supply logs: {power_stdout_log} / {power_stderr_log}")

    # Launch oscilloscope capture (no delay needed between these two)
    print("\n[MASTER] Launching oscilloscope capture...")
    scope_cmd = [
        "python",
        str(OSCILLOSCOPE_SCRIPT),
        oscilloscope_config
    ]
    print(f"[MASTER] Command: {' '.join(scope_cmd)}")

    # Create log files for oscilloscope output
    scope_stdout_log = master_output_dir / "oscilloscope_stdout.log"
    scope_stderr_log = master_output_dir / "oscilloscope_stderr.log"

    scope_proc = subprocess.Popen(
        scope_cmd,
        stdout=open(scope_stdout_log, 'w'),
        stderr=open(scope_stderr_log, 'w'),
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    processes.append(("Oscilloscope Capture", scope_proc))
    print(f"[MASTER] Oscilloscope capture started (PID: {scope_proc.pid})")
    print(f"[MASTER] Oscilloscope logs: {scope_stdout_log} / {scope_stderr_log}")

    # Print summary
    print("\n" + "=" * 70)
    print("ALL SYSTEMS LAUNCHED")
    print("=" * 70)
    print("\nRunning processes:")
    print(f"  1. Thermal Recorder (PID: {thermal_proc.pid})")
    print(f"  2. Power Supply Monitor (PID: {power_proc.pid})")
    print(f"  3. Oscilloscope Capture (PID: {scope_proc.pid})")
    print("\nEach system is running in its own window.")
    print("Press Ctrl+C in THIS window to stop all systems.")
    print("=" * 70)

    # Track which processes have already been reported as terminated
    reported_terminated = set()

    # Monitor processes
    try:
        while True:
            # Check if any process has terminated
            all_terminated = True
            for name, proc in processes:
                if proc.poll() is None:
                    # Process is still running
                    all_terminated = False
                elif name not in reported_terminated:
                    # Process terminated and we haven't reported it yet
                    print(f"\n[MASTER] WARNING: {name} has terminated (exit code: {proc.returncode})")
                    print(f"[MASTER] Other systems continue running. Press Ctrl+C to stop all.")
                    reported_terminated.add(name)

            # If all processes have terminated, exit
            if all_terminated:
                print("\n[MASTER] All processes have terminated. Exiting.")
                break

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n[MASTER] Keyboard interrupt received")
        cleanup()

    # Update manifest with completion info
    test_end_time = datetime.now(timezone.utc)
    test_duration = (test_end_time - test_start_time).total_seconds()

    with open(manifest_path, 'a') as f:
        f.write("\n" + "=" * 70 + "\n")
        f.write("TEST COMPLETION\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Test End Time (UTC): {test_end_time.isoformat()}\n")
        f.write(f"Total Duration: {test_duration:.1f} seconds ({test_duration/60:.1f} minutes)\n\n")

        f.write("PROCESS STATUS:\n")
        f.write("-" * 70 + "\n")
        for name, proc in processes:
            exit_code = proc.poll()
            if exit_code is None:
                f.write(f"{name}: Still running (terminated by master)\n")
            else:
                f.write(f"{name}: Exited with code {exit_code}\n")

    print(f"\n[MASTER] Manifest updated: {manifest_path}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
