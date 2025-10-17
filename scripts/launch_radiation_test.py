#!/usr/bin/env python3
"""
Simple Radiation Test Launcher
Creates a timestamped folder and launches both oscilloscope and webcam scripts independently
"""

import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def main():
    print("\n" + "="*70)
    print("RADIATION TEST LAUNCHER")
    print("="*70)

    # Parse command line arguments
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python launch_radiation_test.py <config_name> [test_name]")
        print("\nExamples:")
        print("  python launch_radiation_test.py LT_RAD_TESTCONFIG.json")
        print("  python launch_radiation_test.py GAN_HV_TESTCONFIG.json gan_test_1")
        print("\nAvailable configs:")

        base_dir = Path(__file__).parent
        config_dir = base_dir / "oscilloscope" / "configs"
        if config_dir.exists():
            for config in sorted(config_dir.glob("*.json")):
                print(f"  - {config.name}")

        return 1

    config_name = sys.argv[1]
    test_name = sys.argv[2] if len(sys.argv) > 2 else None

    # Create timestamped directory
    base_dir = Path(__file__).parent
    utc_now = datetime.now(timezone.utc)
    timestamp = utc_now.strftime("%Y%m%d_%H%M%S_UTC")

    if test_name:
        dir_name = f"{timestamp}_{test_name}"
    else:
        dir_name = timestamp

    # Create test directory
    tests_base = base_dir / "radiation_tests"
    tests_base.mkdir(exist_ok=True)
    test_dir = tests_base / dir_name
    test_dir.mkdir(exist_ok=True)

    print(f"\nTest Directory: {test_dir}")
    print(f"Start Time (UTC): {utc_now.isoformat()}")
    print(f"Config: {config_name}")
    print("="*70)

    # Paths to scripts
    osc_script = base_dir / "oscilloscope" / "scripts" / "live_16ch_multiscope_enhanced.py"
    osc_config = base_dir / "oscilloscope" / "configs" / config_name
    webcam_script = base_dir / "uti_thermal" / "scripts" / "dual_recorder.py"

    # Check if scripts exist
    if not osc_script.exists():
        print(f"\nERROR: Oscilloscope script not found: {osc_script}")
        return 1

    if not osc_config.exists():
        print(f"\nERROR: Config file not found: {osc_config}")
        return 1

    webcam_available = webcam_script.exists()

    print("\nLaunching test systems...")
    print("-" * 70)

    # Launch webcam FIRST (cameras need time to initialize)
    if webcam_available:
        print("1. Launching webcam recorder...")
        if sys.platform == 'win32':
            webcam_cmd = f'start "Webcam - {test_name or "Test"}" /D "{webcam_script.parent}" cmd /k "python {webcam_script.name}"'
            subprocess.Popen(webcam_cmd, shell=True)
        else:
            subprocess.Popen(['python3', str(webcam_script)], cwd=str(webcam_script.parent))

        print(f"   Output: {base_dir / 'recordings'}")
        print("   IMPORTANT: Wait for camera window to appear before continuing!")
        print("\n   Waiting 15 seconds for cameras to initialize...")

        # Give cameras time to fully initialize and start recording
        import time
        for i in range(15, 0, -1):
            print(f"   {i}...", end='\r')
            time.sleep(1)
        print("\n")
    else:
        print("\n1. Webcam script not found - skipping")

    # Launch oscilloscope SECOND (after cameras are running)
    print("2. Launching oscilloscope capture...")
    if sys.platform == 'win32':
        osc_cmd = f'start "Oscilloscope - {test_name or "Test"}" /D "{osc_script.parent}" cmd /k "python {osc_script.name} {osc_config}"'
        subprocess.Popen(osc_cmd, shell=True)
    else:
        subprocess.Popen(['python3', str(osc_script), str(osc_config)], cwd=str(osc_script.parent))

    print(f"   Config: {config_name}")
    print(f"   Output: {base_dir / 'data'} and {base_dir / 'plots'}")

    print("\n" + "="*70)
    print("BOTH SYSTEMS LAUNCHED")
    print("="*70)
    print("\nTwo new windows should have opened:")
    if webcam_available:
        print("  1. Webcam recorder window (launched first)")
        print("  2. Oscilloscope capture window (launched after cameras ready)")
    else:
        print("  1. Oscilloscope capture window")
    print("\nLaunch Order:")
    print("  - Cameras launched FIRST to avoid USB conflicts")
    print("  - Oscilloscope launched SECOND after cameras are recording")
    print("\nPress 'q' in each window when done to stop recording.")
    print("\nIMPORTANT: After you stop both recordings, run:")
    print(f"  python organize_test.py {dir_name}")
    print("to move all files into the test directory.")
    print("="*70 + "\n")

    # Save test info file for the organize script
    info_file = test_dir / "test_info.txt"
    with open(info_file, 'w') as f:
        f.write(f"Test Name: {test_name or 'unnamed'}\n")
        f.write(f"Config: {config_name}\n")
        f.write(f"Start Time: {utc_now.isoformat()}\n")
        f.write(f"Directory: {dir_name}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
