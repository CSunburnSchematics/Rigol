#!/usr/bin/env python3
"""
Organize Test Files
Moves oscilloscope data, plots, and webcam recordings into the test directory
Run this after completing a radiation test session
"""

import os
import sys
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python organize_test.py <test_directory_name>")
        print("\nExample:")
        print("  python organize_test.py 20251015_123456_UTC_gan_test_1")
        print("\nAvailable test directories:")

        base_dir = Path(__file__).parent
        tests_base = base_dir / "radiation_tests"
        if tests_base.exists():
            test_dirs = sorted([d for d in tests_base.iterdir() if d.is_dir()], reverse=True)
            for test_dir in test_dirs[:10]:  # Show last 10
                print(f"  - {test_dir.name}")

        return 1

    test_dir_name = sys.argv[1]
    base_dir = Path(__file__).parent
    test_dir = base_dir / "radiation_tests" / test_dir_name

    if not test_dir.exists():
        print(f"\nERROR: Test directory not found: {test_dir}")
        return 1

    print("\n" + "="*70)
    print("ORGANIZING TEST FILES")
    print("="*70)
    print(f"Test Directory: {test_dir}")
    print("="*70 + "\n")

    # Create subdirectories if they don't exist
    (test_dir / "oscilloscope_data").mkdir(exist_ok=True)
    (test_dir / "oscilloscope_plots").mkdir(exist_ok=True)
    (test_dir / "webcam_videos").mkdir(exist_ok=True)
    (test_dir / "test_metadata").mkdir(exist_ok=True)

    moved_count = 0

    # Move oscilloscope CSV files
    print("Moving oscilloscope data files...")
    data_dir = base_dir / "data"
    if data_dir.exists():
        csv_files = sorted(data_dir.glob("multiscope_*.csv"), key=os.path.getmtime, reverse=True)
        perf_files = sorted(data_dir.glob("performance_*.txt"), key=os.path.getmtime, reverse=True)

        # Get timestamp from test directory name
        test_timestamp = test_dir_name.split('_')[0]  # YYYYMMDD

        for csv_file in csv_files:
            # Check if file timestamp matches test (rough match by date)
            if test_timestamp in csv_file.name:
                dest = test_dir / "oscilloscope_data" / csv_file.name
                shutil.move(str(csv_file), str(dest))
                print(f"  [OK] {csv_file.name}")
                moved_count += 1

        for perf_file in perf_files:
            if test_timestamp in perf_file.name:
                dest = test_dir / "oscilloscope_data" / perf_file.name
                shutil.move(str(perf_file), str(dest))
                print(f"  [OK] {perf_file.name}")
                moved_count += 1

    # Move oscilloscope plots
    print("\nMoving oscilloscope plots...")
    plots_dir = base_dir / "plots"
    if plots_dir.exists():
        png_files = sorted(plots_dir.glob("multiscope_*.png"), key=os.path.getmtime, reverse=True)
        test_timestamp = test_dir_name.split('_')[0]

        for png_file in png_files:
            if test_timestamp in png_file.name:
                dest = test_dir / "oscilloscope_plots" / png_file.name
                shutil.move(str(png_file), str(dest))
                print(f"  [OK] {png_file.name}")
                moved_count += 1

    # Move webcam recordings
    print("\nMoving webcam recordings...")
    recordings_dir = base_dir / "recordings"
    if recordings_dir.exists():
        # Find recording folders that match the test timestamp
        recording_folders = sorted(recordings_dir.glob("recording_*"), key=os.path.getmtime, reverse=True)
        test_timestamp = test_dir_name.split('_')[0]  # YYYYMMDD

        for recording_folder in recording_folders:
            if test_timestamp in recording_folder.name:
                # Move all files from this recording folder
                for video_file in recording_folder.iterdir():
                    dest = test_dir / "webcam_videos" / video_file.name
                    shutil.move(str(video_file), str(dest))
                    print(f"  [OK] {video_file.name}")
                    moved_count += 1

                # Remove empty recording folder
                try:
                    recording_folder.rmdir()
                    print(f"  [OK] Removed empty folder: {recording_folder.name}")
                except:
                    pass

    # Create summary
    print("\nCreating test summary...")
    utc_now = datetime.now(timezone.utc)

    summary_path = test_dir / "TEST_SUMMARY.txt"
    with open(summary_path, 'w') as f:
        f.write("="*70 + "\n")
        f.write("RADIATION TEST SESSION SUMMARY\n")
        f.write("="*70 + "\n\n")
        f.write(f"Test Directory: {test_dir_name}\n")
        f.write(f"Files Organized: {utc_now.isoformat()}\n")
        f.write(f"Total Files Moved: {moved_count}\n\n")

        f.write("Test Directory Structure:\n")
        f.write("  oscilloscope_data/  - CSV data files from all scopes\n")
        f.write("  oscilloscope_plots/ - Screenshot of final waveforms\n")
        f.write("  webcam_videos/      - Thermal + webcam recordings\n")
        f.write("  test_metadata/      - Test configuration and info\n\n")

        # List files
        f.write("Oscilloscope Data Files:\n")
        for csv_file in sorted((test_dir / "oscilloscope_data").glob("*.csv")):
            f.write(f"  - {csv_file.name}\n")

        f.write("\nOscilloscope Plots:\n")
        for png_file in sorted((test_dir / "oscilloscope_plots").glob("*.png")):
            f.write(f"  - {png_file.name}\n")

        f.write("\nWebcam Videos:\n")
        for video_file in sorted((test_dir / "webcam_videos").glob("*")):
            f.write(f"  - {video_file.name}\n")

        f.write("\n" + "="*70 + "\n")
        f.write("Test files organized successfully\n")
        f.write("="*70 + "\n")

    print(f"\n[OK] Test summary created: {summary_path}")

    print("\n" + "="*70)
    print("FILE ORGANIZATION COMPLETE")
    print("="*70)
    print(f"Total files moved: {moved_count}")
    print(f"\nAll data organized in: {test_dir}")
    print("="*70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
