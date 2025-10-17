"""
Simple Master Radiation Test Launcher

Creates folder, launches thermal camera, power supply monitor, and oscilloscope.
Press 'Q' to stop all systems.

Usage:
    python launch_radiation_test.py <power_supply_config> <oscilloscope_config> [webcam_index]

Example:
    python launch_radiation_test.py config/POWER_SUPPLY_ltc_rad_test_board_config.json config/SCOPE_LT_RAD_TESTCONFIG.json 1
    python launch_radiation_test.py config/POWER_SUPPLY_ltc_rad_test_board_config.json config/SCOPE_LT_RAD_TESTCONFIG.json No
"""

import sys
import os
import subprocess
import time
import msvcrt
from pathlib import Path
from datetime import datetime, timezone

# Get directories
SCRIPT_DIR = Path(__file__).parent.absolute()
MASTER_RAD_TEST_DIR = SCRIPT_DIR.parent
SUNBURN_CODE_DIR = MASTER_RAD_TEST_DIR.parent

# Script paths
THERMAL_SCRIPT = SUNBURN_CODE_DIR / "uti_thermal" / "scripts" / "dual_recorder_resilient.py"
POWER_SUPPLY_SCRIPT = SUNBURN_CODE_DIR / "Power_Supplies" / "scripts" / "power_supply_live_monitor.py"
OSCILLOSCOPE_SCRIPT = SUNBURN_CODE_DIR / "oscilloscope" / "scripts" / "live_16ch_multiscope_enhanced.py"

def main():
    print("=" * 70)
    print("MASTER RADIATION TEST LAUNCHER")
    print("=" * 70)

    # Parse arguments
    if len(sys.argv) < 3:
        print("ERROR: Missing required arguments!")
        print("\nUsage:")
        print("  python launch_radiation_test.py <power_supply_config> <oscilloscope_config> [webcam_index]")
        print("\nExample:")
        print("  python launch_radiation_test.py config/POWER_SUPPLY_ltc_rad_test_board_config.json config/SCOPE_LT_RAD_TESTCONFIG.json 1")
        print("  python launch_radiation_test.py config/POWER_SUPPLY_ltc_rad_test_board_config.json config/SCOPE_LT_RAD_TESTCONFIG.json No")
        return 1

    power_supply_config = sys.argv[1]
    oscilloscope_config = sys.argv[2]
    webcam_index = sys.argv[3] if len(sys.argv) > 3 else "1"

    # Check if thermal camera should be disabled
    skip_thermal = webcam_index.lower() in ['no', 'n', 'none', 'skip']

    # Make configs absolute paths if they're relative
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

    # Create timestamped folder in radiation_tests subdirectory
    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    radiation_tests_dir = MASTER_RAD_TEST_DIR / "radiation_tests"
    session_folder = radiation_tests_dir / f"radiation_test_{timestamp_str}"
    session_folder.mkdir(parents=True, exist_ok=True)

    print(f"\nSession folder: {session_folder}")
    print(f"Power supply config: {os.path.basename(power_supply_config)}")
    print(f"Oscilloscope config: {os.path.basename(oscilloscope_config)}")
    if skip_thermal:
        print(f"Thermal camera: DISABLED")
    else:
        print(f"Webcam index: {webcam_index}")
    print("=" * 70)

    processes = []

    # Launch thermal camera first (if enabled)
    if not skip_thermal:
        print("\n[1/3] Launching thermal camera...")
        thermal_cmd = [
            "python",
            str(THERMAL_SCRIPT),
            str(session_folder),
            webcam_index
        ]
        thermal_proc = subprocess.Popen(
            thermal_cmd,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        processes.append(("Thermal Camera", thermal_proc))
        print(f"      Started (PID: {thermal_proc.pid})")
        print("      Waiting 10 seconds for camera initialization...")
        time.sleep(10)
    else:
        print("\n[SKIP] Thermal camera disabled")

    # Launch power supply monitor
    print("\n[2/3] Launching power supply monitor...")
    power_cmd = [
        "python",
        str(POWER_SUPPLY_SCRIPT),
        power_supply_config,
        "--output-dir", str(session_folder)
    ]
    power_proc = subprocess.Popen(
        power_cmd,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    processes.append(("Power Supply", power_proc))
    print(f"      Started (PID: {power_proc.pid})")
    print("      Waiting 5 seconds...")
    time.sleep(5)

    # Launch oscilloscope
    print("\n[3/3] Launching oscilloscope...")
    scope_cmd = [
        "python",
        str(OSCILLOSCOPE_SCRIPT),
        oscilloscope_config,
        "--output-dir", str(session_folder)
    ]
    scope_proc = subprocess.Popen(
        scope_cmd,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    processes.append(("Oscilloscope", scope_proc))
    print(f"      Started (PID: {scope_proc.pid})")

    # Print summary
    print("\n" + "=" * 70)
    print("ALL SYSTEMS RUNNING")
    print("=" * 70)
    print("\nActive processes:")
    for name, proc in processes:
        print(f"  - {name} (PID: {proc.pid})")
    print("\nPress 'Q' to stop all systems and exit")
    print("=" * 70)

    # Wait for 'Q' key
    try:
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').upper()
                if key == 'Q':
                    print("\n\n'Q' pressed - shutting down all systems...")
                    break

            # Check if all processes have terminated
            all_dead = True
            for name, proc in processes:
                if proc.poll() is None:
                    all_dead = False
                    break

            if all_dead:
                print("\n\nAll processes have terminated.")
                break

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nCtrl+C pressed - shutting down all systems...")

    # Terminate all processes
    print("\nTerminating processes...")
    for name, proc in processes:
        if proc.poll() is None:  # Still running
            print(f"  Stopping {name}...")
            proc.terminate()

    # Wait for graceful shutdown
    print("\nWaiting for processes to shut down gracefully...")
    for name, proc in processes:
        try:
            proc.wait(timeout=10)
            print(f"  {name} stopped")
        except subprocess.TimeoutExpired:
            print(f"  {name} didn't stop, killing...")
            proc.kill()
            proc.wait()

    print("\n" + "=" * 70)
    print("All systems stopped")
    print("=" * 70)

    return 0

if __name__ == "__main__":
    sys.exit(main())
