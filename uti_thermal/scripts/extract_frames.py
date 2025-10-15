"""
Extract frames from recorded videos with exact UTC timestamps
"""

import cv2
import json
import sys
import os
from datetime import datetime

def extract_frames_with_timestamps(video_file, timestamps_file, output_dir="extracted_frames", frame_interval=None):
    """
    Extract frames from video with their exact UTC timestamps

    Args:
        video_file: Path to the video file
        timestamps_file: Path to the JSON timestamps file
        output_dir: Directory to save extracted frames
        frame_interval: Extract every N frames (None = extract all)
    """

    # Load timestamp data
    print(f"Loading timestamps from: {timestamps_file}")
    with open(timestamps_file, 'r') as f:
        data = json.load(f)

    metadata = data['metadata']
    frame_timestamps = data['frames']

    print(f"\nRecording Info:")
    print(f"  Start time: {metadata['start_time_utc']}")
    print(f"  End time: {metadata['end_time_utc']}")
    print(f"  Duration: {metadata['duration_seconds']:.2f} seconds")
    print(f"  Total frames: {metadata['total_frames']}")
    print(f"  Actual FPS: {metadata['actual_fps']:.2f}")

    # Determine which video file to use
    camera_type = "thermal" if "thermal" in video_file else "webcam"
    print(f"\nExtracting from: {camera_type} video")

    # Open video
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"ERROR: Cannot open video file: {video_file}")
        return

    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    # Extract frames
    extracted_count = 0
    frame_number = 0

    print(f"\nExtracting frames...")
    if frame_interval:
        print(f"  Interval: Every {frame_interval} frame(s)")
    else:
        print(f"  Extracting ALL frames")

    print("-" * 60)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_number += 1

        # Check if we should extract this frame
        if frame_interval and (frame_number % frame_interval != 0):
            continue

        # Get timestamp for this frame
        if frame_number <= len(frame_timestamps):
            frame_info = frame_timestamps[frame_number - 1]
            utc_time = frame_info['utc_time']
            unix_timestamp = frame_info['unix_timestamp']
            elapsed = frame_info['elapsed_seconds']

            # Create filename with UTC timestamp
            # Replace colons and other invalid filename chars
            utc_safe = utc_time.replace(':', '-').replace('.', '_')
            filename = f"{camera_type}_frame{frame_number:05d}_{utc_safe}.png"
            filepath = os.path.join(output_dir, filename)

            # Save frame
            cv2.imwrite(filepath, frame)

            # Save metadata text file
            meta_filename = f"{camera_type}_frame{frame_number:05d}_{utc_safe}.txt"
            meta_filepath = os.path.join(output_dir, meta_filename)
            with open(meta_filepath, 'w') as f:
                f.write(f"Frame Number: {frame_number}\n")
                f.write(f"UTC Time: {utc_time}\n")
                f.write(f"Unix Timestamp: {unix_timestamp}\n")
                f.write(f"Elapsed Seconds: {elapsed:.3f}\n")
                f.write(f"Image File: {filename}\n")
                f.write(f"Camera Type: {camera_type}\n")

            extracted_count += 1

            if extracted_count % 10 == 0 or extracted_count == 1:
                print(f"  Frame {frame_number}: {utc_time} -> {filename}")
        else:
            print(f"WARNING: Frame {frame_number} has no timestamp data")

    cap.release()

    print("-" * 60)
    print(f"\nExtraction complete!")
    print(f"  Total frames extracted: {extracted_count}")
    print(f"  Output directory: {output_dir}")

    # Create index file
    index_file = os.path.join(output_dir, f"{camera_type}_frame_index.csv")
    with open(index_file, 'w') as f:
        f.write("frame_number,utc_time,unix_timestamp,elapsed_seconds,filename\n")

        frame_num = 0
        for frame_info in frame_timestamps:
            frame_num += 1
            if frame_interval and (frame_num % frame_interval != 0):
                continue

            utc_time = frame_info['utc_time']
            unix_timestamp = frame_info['unix_timestamp']
            elapsed = frame_info['elapsed_seconds']
            utc_safe = utc_time.replace(':', '-').replace('.', '_')
            filename = f"{camera_type}_frame{frame_num:05d}_{utc_safe}.png"

            f.write(f"{frame_num},{utc_time},{unix_timestamp},{elapsed:.3f},{filename}\n")

    print(f"  Index file: {index_file}")


def print_usage():
    print("""
Frame Extractor with UTC Timestamps
====================================

Usage: python extract_frames.py <video_file> <timestamps_json> [interval]

Arguments:
  video_file         Path to the video file (thermal or webcam)
  timestamps_json    Path to the timestamps JSON file
  interval           (Optional) Extract every N frames (default: all frames)

Examples:
  # Extract all frames
  python extract_frames.py recording_20251015_023456_UTC_thermal.avi recording_20251015_023456_UTC_timestamps.json

  # Extract every 30 frames (~1 per second at 30fps)
  python extract_frames.py recording_20251015_023456_UTC_thermal.avi recording_20251015_023456_UTC_timestamps.json 30

  # Extract every 300 frames (~1 per 10 seconds at 30fps)
  python extract_frames.py recording_20251015_023456_UTC_webcam.avi recording_20251015_023456_UTC_timestamps.json 300
    """)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    video_file = sys.argv[1]
    timestamps_file = sys.argv[2]

    interval = None
    if len(sys.argv) > 3:
        try:
            interval = int(sys.argv[3])
        except ValueError:
            print(f"ERROR: Interval must be a number, got: {sys.argv[3]}")
            sys.exit(1)

    if not os.path.exists(video_file):
        print(f"ERROR: Video file not found: {video_file}")
        sys.exit(1)

    if not os.path.exists(timestamps_file):
        print(f"ERROR: Timestamps file not found: {timestamps_file}")
        sys.exit(1)

    extract_frames_with_timestamps(video_file, timestamps_file, frame_interval=interval)
