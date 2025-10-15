"""
UTi 260B Thermal Camera Recorder
- Auto-detects thermal camera
- Validates configuration
- Records video with UTC timestamps
- Live preview window
- Frame-accurate timestamp logging
"""

import cv2
import time
import sys
import json
from datetime import datetime, timezone

class ThermalRecorder:
    def __init__(self):
        self.thermal_camera_index = None
        self.cap = None
        self.video_writer = None
        self.timestamp_log = []
        self.recording = False
        self.frame_count = 0

    def detect_thermal_camera(self):
        """
        Detect UTi 260B thermal camera by resolution signature
        UTi 260B outputs 240x321 in USB camera mode
        """
        print("Searching for thermal camera...")
        print("-" * 60)

        for i in range(5):  # Check first 5 camera indices
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                print(f"Camera {i}: {width}x{height}", end="")

                # UTi 260B signature: 240x321 resolution
                if width == 240 and height == 321:
                    # Verify it's actually a thermal camera by capturing a test frame
                    ret, frame = cap.read()
                    if ret:
                        print(" -> UTi 260B DETECTED!")
                        cap.release()
                        self.thermal_camera_index = i
                        return True
                    else:
                        print(" -> Can't read frames")
                else:
                    print(" -> Not thermal camera")

                cap.release()

        print("-" * 60)
        return False

    def validate_configuration(self):
        """
        Validate that the thermal camera is properly configured
        """
        print("\nValidating thermal camera configuration...")

        self.cap = cv2.VideoCapture(self.thermal_camera_index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            print("ERROR: Cannot open thermal camera")
            return False

        # Get properties
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"  Resolution: {width}x{height}")
        print(f"  FPS: {fps if fps > 0 else 'Unknown (will measure)'}")

        # Capture test frame
        ret, frame = self.cap.read()
        if not ret:
            print("ERROR: Cannot capture test frame")
            self.cap.release()
            return False

        print(f"  Color mode: {frame.shape[2]} channels (BGR)")
        print("  Status: READY")

        return True

    def start_recording(self, output_filename=None):
        """
        Start recording with live preview and frame-accurate timestamps
        """
        if output_filename is None:
            utc_now = datetime.now(timezone.utc)
            timestamp = utc_now.strftime("%Y%m%d_%H%M%S_UTC")
            output_filename = f"thermal_recording_{timestamp}.avi"

        # Get frame dimensions
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        target_fps = 30  # Target FPS for output video
        self.video_writer = cv2.VideoWriter(output_filename, fourcc, target_fps, (width, height))

        # Initialize timestamp log
        self.timestamp_log = []
        self.frame_count = 0
        self.recording = True

        # Recording metadata
        start_time_utc = datetime.now(timezone.utc)
        recording_metadata = {
            'start_time_utc': start_time_utc.isoformat(),
            'start_timestamp_unix': start_time_utc.timestamp(),
            'video_file': output_filename,
            'resolution': f"{width}x{height}",
            'target_fps': target_fps,
            'camera_index': self.thermal_camera_index
        }

        print("\n" + "=" * 60)
        print("RECORDING STARTED")
        print("=" * 60)
        print(f"Output file: {output_filename}")
        print(f"Start time (UTC): {start_time_utc.isoformat()}")
        print(f"Resolution: {width}x{height}")
        print("\nControls:")
        print("  Press 'q' or 'ESC' to stop recording")
        print("  Press 's' to save current frame as image")
        print("=" * 60)

        recording_start = time.time()
        last_fps_update = recording_start
        fps_frame_count = 0
        current_fps = 0.0

        try:
            while self.recording:
                ret, frame = self.cap.read()
                if not ret:
                    print("\nWarning: Failed to read frame")
                    continue

                # Record exact capture timestamp
                capture_time_utc = datetime.now(timezone.utc)
                capture_timestamp_unix = capture_time_utc.timestamp()

                # Write frame to video
                self.video_writer.write(frame)
                self.frame_count += 1
                fps_frame_count += 1

                # Log timestamp
                self.timestamp_log.append({
                    'frame_number': self.frame_count,
                    'utc_time': capture_time_utc.isoformat(),
                    'unix_timestamp': capture_timestamp_unix,
                    'elapsed_seconds': capture_timestamp_unix - recording_metadata['start_timestamp_unix']
                })

                # Calculate actual FPS
                current_time = time.time()
                if current_time - last_fps_update >= 1.0:
                    current_fps = fps_frame_count / (current_time - last_fps_update)
                    fps_frame_count = 0
                    last_fps_update = current_time

                # Create display frame with overlay info
                display_frame = frame.copy()

                # Overlay info
                elapsed = capture_timestamp_unix - recording_metadata['start_timestamp_unix']
                info_lines = [
                    f"REC {int(elapsed//60):02d}:{int(elapsed%60):02d}",
                    f"Frame: {self.frame_count}",
                    f"FPS: {current_fps:.1f}"
                ]

                y_pos = 30
                for line in info_lines:
                    cv2.putText(display_frame, line, (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    y_pos += 25

                # Add recording indicator (red circle)
                cv2.circle(display_frame, (width - 20, 20), 8, (0, 0, 255), -1)

                # Show live preview
                cv2.imshow('UTi 260B Thermal Recorder - RECORDING', display_frame)

                # Handle key presses
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q') or key == 27:  # 'q' or ESC
                    print("\n\nStopping recording...")
                    self.recording = False

                elif key == ord('s'):  # Save snapshot
                    snapshot_time = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
                    snapshot_filename = f"snapshot_frame{self.frame_count}_{snapshot_time}.png"
                    cv2.imwrite(snapshot_filename, frame)
                    print(f"\nSnapshot saved: {snapshot_filename}")

        except KeyboardInterrupt:
            print("\n\nRecording interrupted by user")
            self.recording = False

        # Calculate final statistics
        end_time_utc = datetime.now(timezone.utc)
        total_duration = end_time_utc.timestamp() - recording_metadata['start_timestamp_unix']
        actual_fps = self.frame_count / total_duration if total_duration > 0 else 0

        recording_metadata.update({
            'end_time_utc': end_time_utc.isoformat(),
            'end_timestamp_unix': end_time_utc.timestamp(),
            'total_frames': self.frame_count,
            'duration_seconds': total_duration,
            'actual_fps': actual_fps
        })

        # Save timestamp log
        timestamp_filename = output_filename.replace('.avi', '_timestamps.json')
        with open(timestamp_filename, 'w') as f:
            json.dump({
                'metadata': recording_metadata,
                'frames': self.timestamp_log
            }, f, indent=2)

        # Save summary text file
        summary_filename = output_filename.replace('.avi', '_summary.txt')
        with open(summary_filename, 'w') as f:
            f.write("UTi 260B Thermal Recording Summary\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Video File: {output_filename}\n")
            f.write(f"Timestamp Data: {timestamp_filename}\n\n")
            f.write(f"Recording Start (UTC): {recording_metadata['start_time_utc']}\n")
            f.write(f"Recording End (UTC):   {recording_metadata['end_time_utc']}\n")
            f.write(f"Duration: {total_duration:.2f} seconds\n\n")
            f.write(f"Total Frames: {self.frame_count}\n")
            f.write(f"Target FPS: {target_fps}\n")
            f.write(f"Actual FPS: {actual_fps:.2f}\n\n")
            f.write(f"Resolution: {recording_metadata['resolution']}\n")
            f.write(f"Camera Index: {self.thermal_camera_index}\n\n")
            f.write("Frame Timestamp Lookup:\n")
            f.write("-" * 60 + "\n")
            f.write("To find the timestamp of a specific frame, see the JSON file:\n")
            f.write(f"  {timestamp_filename}\n")

        print("\n" + "=" * 60)
        print("RECORDING STOPPED")
        print("=" * 60)
        print(f"Video saved: {output_filename}")
        print(f"Timestamps saved: {timestamp_filename}")
        print(f"Summary saved: {summary_filename}")
        print(f"\nRecording Statistics:")
        print(f"  Duration: {total_duration:.2f} seconds")
        print(f"  Frames captured: {self.frame_count}")
        print(f"  Actual FPS: {actual_fps:.2f}")
        print("=" * 60)

    def cleanup(self):
        """Release resources"""
        if self.video_writer:
            self.video_writer.release()
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()


def main():
    recorder = ThermalRecorder()

    # Step 1: Detect thermal camera
    if not recorder.detect_thermal_camera():
        print("\nERROR: UTi 260B thermal camera not detected!")
        print("\nTroubleshooting:")
        print("  1. Make sure UTi 260B is connected via USB-C")
        print("  2. Close Uti-Live Screen software if running")
        print("  3. Set UTi 260B to 'USB Camera' mode (not USB Disk)")
        print("  4. Make sure device is showing thermal image (not menu)")
        return 1

    # Step 2: Validate configuration
    if not recorder.validate_configuration():
        print("\nERROR: Thermal camera configuration invalid!")
        return 1

    # Step 3: Start recording
    print("\n" + "=" * 60)
    print("Starting recording in 3 seconds...")
    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    print("Recording started!")

    try:
        recorder.start_recording()
    finally:
        recorder.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
