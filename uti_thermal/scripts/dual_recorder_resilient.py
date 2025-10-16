"""
Dual Camera Recorder - RESILIENT VERSION
- Auto-detects both cameras
- Records synchronized videos
- Continues recording if one camera drops
- Works even if only one camera is detected
- UTC timestamps for frame-accurate sync
"""

import cv2
import time
import sys
import json
import os
import numpy as np
from datetime import datetime, timezone

class ResilientDualCameraRecorder:
    def __init__(self):
        self.thermal_camera_index = None
        self.webcam_index = None
        self.thermal_cap = None
        self.webcam_cap = None
        self.thermal_writer = None
        self.webcam_writer = None
        self.combined_writer = None
        self.timestamp_log = []
        self.recording = False
        self.frame_count = 0
        self.thermal_active = False
        self.webcam_active = False
        self.thermal_failures = 0
        self.webcam_failures = 0

    def detect_cameras(self, preferred_webcam_index=None):
        """
        Detect thermal camera and/or regular webcam
        RESILIENT: Returns True if at least ONE camera is found
        """
        print("Searching for cameras...")
        print("-" * 60)

        cameras_found = []

        for i in range(10):  # Check first 10 camera indices
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                camera_info = {
                    'index': i,
                    'width': width,
                    'height': height,
                    'megapixels': (width * height) / 1_000_000,
                    'type': 'unknown'
                }

                print(f"Camera {i}: {width}x{height} ({camera_info['megapixels']:.1f}MP)", end="")

                # UTi 260B signature: 240x321 resolution
                if width == 240 and height == 321:
                    # Verify it's actually thermal
                    ret, frame = cap.read()
                    if ret:
                        print(" -> UTi 260B Thermal Camera")
                        camera_info['type'] = 'thermal'
                        self.thermal_camera_index = i
                        cameras_found.append(camera_info)
                    else:
                        print(" -> Can't read frames")
                else:
                    # Check if it's a working webcam
                    ret, frame = cap.read()
                    if ret:
                        # Try to identify camera type by resolution
                        if width >= 1920 and height >= 1080:
                            print(f" -> High-res Webcam (likely external 4K)")
                        else:
                            print(f" -> Standard Webcam (likely built-in)")
                        camera_info['type'] = 'webcam'
                        cameras_found.append(camera_info)
                    else:
                        print(" -> Not accessible")

                cap.release()

        print("-" * 60)

        # Select webcam
        webcams = [cam for cam in cameras_found if cam['type'] == 'webcam']
        if webcams:
            if preferred_webcam_index is not None and preferred_webcam_index in [w['index'] for w in webcams]:
                self.webcam_index = preferred_webcam_index
                print(f"\nUsing specified webcam: Camera {self.webcam_index}")
            else:
                # Auto-select by testing for highest resolution
                print(f"\nTesting webcams for highest resolution...")
                best_cam = None
                best_pixels = 0

                for cam in webcams:
                    test_cap = cv2.VideoCapture(cam['index'], cv2.CAP_DSHOW)
                    if test_cap.isOpened():
                        # Try 4K first
                        test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
                        test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
                        w = int(test_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(test_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                        # If 4K didn't work, try 1080p
                        if w < 1920:
                            test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                            test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                            w = int(test_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            h = int(test_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                        pixels = w * h
                        print(f"  Camera {cam['index']}: Max {w}x{h}")
                        test_cap.release()

                        if pixels > best_pixels:
                            best_pixels = pixels
                            best_cam = cam
                            best_cam['actual_max'] = f"{w}x{h}"

                if best_cam:
                    self.webcam_index = best_cam['index']
                    print(f"\nAuto-selected: Camera {self.webcam_index} ({best_cam.get('actual_max', 'Unknown')})")
                else:
                    # Fallback - just use the first webcam found
                    webcams.sort(key=lambda x: x['width'] * x['height'], reverse=True)
                    self.webcam_index = webcams[0]['index']
                    print(f"\nFallback: Using Camera {self.webcam_index} (any resolution)")
        else:
            print("\nWARNING: No webcam detected!")

        if self.thermal_camera_index is not None:
            print(f"\nSelected thermal: Camera {self.thermal_camera_index} (240x321)")
        else:
            print("\nWARNING: No thermal camera detected!")

        # RESILIENT: Success if at least one camera found
        has_camera = self.thermal_camera_index is not None or self.webcam_index is not None

        if has_camera:
            print("\n✓ At least one camera found - proceeding with recording")

        return has_camera

    def validate_configuration(self):
        """
        Validate camera configuration
        RESILIENT: Opens whatever cameras are available
        """
        print("\nValidating camera configuration...")

        max_retries = 3

        # Open thermal camera if available
        if self.thermal_camera_index is not None:
            print(f"Opening thermal camera (index {self.thermal_camera_index})...")
            for attempt in range(max_retries):
                if attempt > 0:
                    print(f"  Retry {attempt}/{max_retries}...")
                    time.sleep(1)

                self.thermal_cap = cv2.VideoCapture(self.thermal_camera_index, cv2.CAP_DSHOW)
                if self.thermal_cap.isOpened():
                    ret_t, frame_t = self.thermal_cap.read()
                    if ret_t:
                        thermal_width = int(self.thermal_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        thermal_height = int(self.thermal_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        print(f"  Thermal: {thermal_width}x{thermal_height} - READY")
                        self.thermal_active = True
                        break
                    else:
                        self.thermal_cap.release()
                        self.thermal_cap = None

            if not self.thermal_active:
                print("  WARNING: Cannot open thermal camera - will record without it")
        else:
            print("  Thermal camera not detected - skipping")

        # Open webcam if available
        if self.webcam_index is not None:
            print(f"Opening webcam (index {self.webcam_index})...")
            for attempt in range(max_retries):
                if attempt > 0:
                    print(f"  Retry {attempt}/{max_retries}...")
                    time.sleep(1)

                self.webcam_cap = cv2.VideoCapture(self.webcam_index, cv2.CAP_DSHOW)
                if self.webcam_cap.isOpened():
                    # Try to set highest resolution
                    self.webcam_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
                    self.webcam_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)

                    ret_w, frame_w = self.webcam_cap.read()
                    if ret_w:
                        webcam_width = int(self.webcam_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        webcam_height = int(self.webcam_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        print(f"  Webcam:  {webcam_width}x{webcam_height} - READY")
                        self.webcam_active = True
                        break
                    else:
                        self.webcam_cap.release()
                        self.webcam_cap = None

            if not self.webcam_active:
                print("  WARNING: Cannot open webcam - will record without it")
        else:
            print("  Webcam not detected - skipping")

        # RESILIENT: Success if at least one camera is active
        if self.thermal_active or self.webcam_active:
            print(f"\n  Status: READY ({self.thermal_active and 'Thermal' or ''}{' + ' if self.thermal_active and self.webcam_active else ''}{self.webcam_active and 'Webcam' or ''})")
            return True
        else:
            print("\n  ERROR: No cameras available for recording!")
            return False

    def start_recording(self, output_base_dir=None, output_prefix=None):
        """
        Start recording from available cameras
        RESILIENT: Continues even if one camera fails
        """
        # If no output directory specified, use default recordings folder
        if output_base_dir is None:
            recordings_base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "recordings")
        else:
            recordings_base = os.path.abspath(output_base_dir)

        os.makedirs(recordings_base, exist_ok=True)

        if output_prefix is None:
            utc_now = datetime.now(timezone.utc)
            timestamp = utc_now.strftime("%Y%m%d_%H%M%S_UTC")
            output_prefix = f"recording_{timestamp}"
            output_dir = os.path.join(recordings_base, f"recording_{timestamp}")
            os.makedirs(output_dir, exist_ok=True)
            print(f"Created output directory: {output_dir}")
        else:
            output_dir = os.path.join(recordings_base, output_prefix)
            os.makedirs(output_dir, exist_ok=True)

        # Setup video writers for active cameras
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        target_fps = 10

        # Get dimensions
        if self.thermal_active:
            thermal_width = int(self.thermal_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            thermal_height = int(self.thermal_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            thermal_filename = os.path.join(output_dir, f"{os.path.basename(output_prefix)}_thermal.avi")
            self.thermal_writer = cv2.VideoWriter(thermal_filename, fourcc, target_fps, (thermal_width, thermal_height))
        else:
            thermal_width, thermal_height = 240, 321  # Default thermal size for layout

        if self.webcam_active:
            webcam_width = int(self.webcam_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            webcam_height = int(self.webcam_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        else:
            webcam_width, webcam_height = 1920, 1080  # Default webcam size for layout

        # Combined video dimensions
        display_thermal_width = 480
        display_thermal_height = 642
        display_webcam_width = 856
        display_webcam_height = 642
        combined_width = display_thermal_width + display_webcam_width
        combined_height = display_thermal_height

        combined_filename = os.path.join(output_dir, f"{os.path.basename(output_prefix)}_combined.avi")
        self.combined_writer = cv2.VideoWriter(combined_filename, fourcc, target_fps, (combined_width, combined_height))

        # Initialize recording
        self.timestamp_log = []
        self.frame_count = 0
        self.recording = True

        start_time_utc = datetime.now(timezone.utc)
        recording_metadata = {
            'start_time_utc': start_time_utc.isoformat(),
            'start_timestamp_unix': start_time_utc.timestamp(),
            'thermal_active': self.thermal_active,
            'webcam_active': self.webcam_active,
            'thermal_file': thermal_filename if self.thermal_active else None,
            'combined_file': combined_filename,
            'target_fps': target_fps,
            'thermal_camera_index': self.thermal_camera_index,
            'webcam_camera_index': self.webcam_index,
        }

        print("\n" + "=" * 60)
        print("RESILIENT RECORDING STARTED")
        print("=" * 60)
        if self.thermal_active:
            print(f"Thermal:  {thermal_filename}")
        else:
            print("Thermal:  DISABLED (camera not available)")
        print(f"Combined: {combined_filename}")
        if not self.webcam_active:
            print("Webcam:   DISABLED (camera not available)")
        print(f"Start time (UTC): {start_time_utc.isoformat()}")
        print(f"Target FPS: {target_fps}")
        print("\nControls:")
        print("  Press 'q' or 'ESC' to stop recording")
        print("  Press 's' to save current frames as images")
        print("=" * 60)

        recording_start = time.time()
        last_fps_update = recording_start
        fps_frame_count = 0
        current_fps = 0.0

        # Create blank frames for missing cameras
        blank_thermal = np.zeros((thermal_height, thermal_width, 3), dtype=np.uint8)
        cv2.putText(blank_thermal, "THERMAL", (50, thermal_height // 2), cv2.FONT_HERSHEY_SIMPLEX, 1, (128, 128, 128), 2)
        cv2.putText(blank_thermal, "OFFLINE", (50, thermal_height // 2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (128, 128, 128), 2)

        blank_webcam = np.zeros((webcam_height, webcam_width, 3), dtype=np.uint8)
        cv2.putText(blank_webcam, "WEBCAM OFFLINE", (webcam_width // 2 - 200, webcam_height // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (128, 128, 128), 3)

        try:
            while self.recording:
                capture_time_utc = datetime.now(timezone.utc)
                capture_timestamp_unix = capture_time_utc.timestamp()

                # Capture from thermal (with resilience)
                frame_thermal = None
                if self.thermal_active:
                    ret_thermal, frame_thermal = self.thermal_cap.read()
                    if not ret_thermal:
                        self.thermal_failures += 1
                        if self.thermal_failures >= 10:
                            print("\nWARNING: Thermal camera has failed multiple times - marking as offline")
                            self.thermal_active = False
                        frame_thermal = blank_thermal.copy()
                    else:
                        self.thermal_failures = 0  # Reset counter on success
                else:
                    frame_thermal = blank_thermal.copy()

                # Capture from webcam (with resilience)
                frame_webcam = None
                if self.webcam_active:
                    ret_webcam, frame_webcam = self.webcam_cap.read()
                    if not ret_webcam:
                        self.webcam_failures += 1
                        if self.webcam_failures >= 10:
                            print("\nWARNING: Webcam has failed multiple times - marking as offline")
                            self.webcam_active = False
                        frame_webcam = blank_webcam.copy()
                    else:
                        self.webcam_failures = 0  # Reset counter on success
                else:
                    frame_webcam = blank_webcam.copy()

                # Write thermal frame if active
                if self.thermal_writer and frame_thermal is not None:
                    self.thermal_writer.write(frame_thermal)

                self.frame_count += 1
                fps_frame_count += 1

                # Log timestamp
                self.timestamp_log.append({
                    'frame_number': self.frame_count,
                    'utc_time': capture_time_utc.isoformat(),
                    'unix_timestamp': capture_timestamp_unix,
                    'elapsed_seconds': capture_timestamp_unix - recording_metadata['start_timestamp_unix'],
                    'thermal_active': self.thermal_active,
                    'webcam_active': self.webcam_active
                })

                # Calculate FPS
                current_time = time.time()
                if current_time - last_fps_update >= 1.0:
                    current_fps = fps_frame_count / (current_time - last_fps_update)
                    fps_frame_count = 0
                    last_fps_update = current_time

                # Create combined display
                display_thermal = cv2.resize(frame_thermal, (display_thermal_width, display_thermal_height))
                display_webcam = cv2.resize(frame_webcam, (display_webcam_width, display_webcam_height))
                display_combined = cv2.hconcat([display_thermal, display_webcam])

                # Overlay info
                elapsed = capture_timestamp_unix - recording_metadata['start_timestamp_unix']
                info_lines = [
                    f"REC {int(elapsed//60):02d}:{int(elapsed%60):02d}",
                    f"Frame: {self.frame_count}",
                    f"FPS: {current_fps:.1f}"
                ]

                y_pos = 30
                for line in info_lines:
                    cv2.putText(display_combined, line, (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    y_pos += 35

                # Add status labels
                thermal_label = "THERMAL" + ("" if self.thermal_active else " [OFF]")
                webcam_label = "WEBCAM" + ("" if self.webcam_active else " [OFF]")
                thermal_color = (255, 255, 255) if self.thermal_active else (128, 128, 128)
                webcam_color = (255, 255, 255) if self.webcam_active else (128, 128, 128)

                cv2.putText(display_combined, thermal_label, (170, 620),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, thermal_color, 2)
                cv2.putText(display_combined, webcam_label, (650, 620),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, webcam_color, 2)

                # Recording indicator
                cv2.circle(display_combined, (display_combined.shape[1] - 30, 30), 12, (0, 0, 255), -1)

                # Write combined video
                self.combined_writer.write(display_combined)

                # Show preview
                cv2.imshow('Resilient Dual Camera Recorder (Press Q to Exit)', display_combined)

                # Handle keys
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    print("\n\nStopping recording...")
                    self.recording = False
                elif key == ord('s'):
                    snapshot_time = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
                    if self.thermal_active and frame_thermal is not None:
                        thermal_snap = os.path.join(output_dir, f"snapshot_thermal_frame{self.frame_count}_{snapshot_time}.png")
                        cv2.imwrite(thermal_snap, frame_thermal)
                        print(f"\nSnapshot saved: {os.path.basename(thermal_snap)}")
                    if self.webcam_active and frame_webcam is not None:
                        webcam_snap = os.path.join(output_dir, f"snapshot_webcam_frame{self.frame_count}_{snapshot_time}.png")
                        cv2.imwrite(webcam_snap, frame_webcam)
                        print(f"Snapshot saved: {os.path.basename(webcam_snap)}")

        except KeyboardInterrupt:
            print("\n\nRecording interrupted by user")
            self.recording = False

        # Finalize
        end_time_utc = datetime.now(timezone.utc)
        total_duration = end_time_utc.timestamp() - recording_metadata['start_timestamp_unix']
        actual_fps = self.frame_count / total_duration if total_duration > 0 else 0

        recording_metadata.update({
            'end_time_utc': end_time_utc.isoformat(),
            'end_timestamp_unix': end_time_utc.timestamp(),
            'total_frames': self.frame_count,
            'duration_seconds': total_duration,
            'actual_fps': actual_fps,
            'thermal_failures': self.thermal_failures,
            'webcam_failures': self.webcam_failures
        })

        # Save logs
        timestamp_filename = os.path.join(output_dir, f"{os.path.basename(output_prefix)}_timestamps.json")
        with open(timestamp_filename, 'w') as f:
            json.dump({'metadata': recording_metadata, 'frames': self.timestamp_log}, f, indent=2)

        summary_filename = os.path.join(output_dir, f"{os.path.basename(output_prefix)}_summary.txt")
        with open(summary_filename, 'w') as f:
            f.write("Resilient Dual Camera Recording Summary\n")
            f.write("=" * 60 + "\n\n")
            if self.thermal_writer:
                f.write(f"Thermal Video:  {thermal_filename}\n")
            f.write(f"Combined Video: {combined_filename}\n")
            f.write(f"Timestamp Data: {timestamp_filename}\n\n")
            f.write(f"Recording Start (UTC): {recording_metadata['start_time_utc']}\n")
            f.write(f"Recording End (UTC):   {recording_metadata['end_time_utc']}\n")
            f.write(f"Duration: {total_duration:.2f} seconds\n\n")
            f.write(f"Total Frames: {self.frame_count}\n")
            f.write(f"Actual FPS: {actual_fps:.2f}\n\n")
            f.write(f"Thermal Camera: {'Active' if self.thermal_active else 'Inactive'} (Failures: {self.thermal_failures})\n")
            f.write(f"Webcam: {'Active' if self.webcam_active else 'Inactive'} (Failures: {self.webcam_failures})\n")

        print("\n" + "=" * 60)
        print("RECORDING STOPPED")
        print("=" * 60)
        if self.thermal_writer:
            print(f"Thermal video:  {thermal_filename}")
        print(f"Combined video: {combined_filename}")
        print(f"Timestamps:     {timestamp_filename}")
        print(f"Summary:        {summary_filename}")
        print(f"\nRecording Statistics:")
        print(f"  Duration: {total_duration:.2f} seconds")
        print(f"  Frames captured: {self.frame_count}")
        print(f"  Actual FPS: {actual_fps:.2f}")
        print(f"  Thermal failures: {self.thermal_failures}")
        print(f"  Webcam failures: {self.webcam_failures}")
        print("=" * 60)

    def cleanup(self):
        """Release resources"""
        if self.thermal_writer:
            self.thermal_writer.release()
        if self.webcam_writer:
            self.webcam_writer.release()
        if self.combined_writer:
            self.combined_writer.release()
        if self.thermal_cap:
            self.thermal_cap.release()
        if self.webcam_cap:
            self.webcam_cap.release()
        cv2.destroyAllWindows()


def load_camera_mapping():
    """Load camera mapping from file if it exists"""
    mapping_file = 'camera_mapping.json'
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r') as f:
                return json.load(f)
        except:
            return None
    return None


def main():
    recorder = ResilientDualCameraRecorder()

    # Parse command line arguments
    preferred_webcam = None
    output_directory = None

    if len(sys.argv) > 1:
        if sys.argv[1].replace('\\', '/').startswith(('C:/', '/', '.', 'rad_test')):
            output_directory = sys.argv[1]
            print(f"Output directory: {output_directory}")
            if len(sys.argv) > 2:
                try:
                    preferred_webcam = int(sys.argv[2])
                    print(f"User specified webcam index: {preferred_webcam}")
                except ValueError:
                    print(f"Invalid camera index: {sys.argv[2]}")
                    return 1
        else:
            try:
                preferred_webcam = int(sys.argv[1])
                print(f"User specified webcam index: {preferred_webcam}")
                if len(sys.argv) > 2:
                    output_directory = sys.argv[2]
                    print(f"Output directory: {output_directory}")
            except ValueError:
                print(f"Invalid argument: {sys.argv[1]}")
                print("Usage: python dual_recorder_resilient.py [output_directory] [webcam_index]")
                return 1

    if preferred_webcam is None:
        mapping = load_camera_mapping()
        if mapping:
            webcams = [c for c in mapping if c['type'] != 'thermal']
            if webcams:
                best_webcam = max(webcams, key=lambda x: x.get('max_pixels', 0))
                preferred_webcam = best_webcam['index']
                print(f"Auto-detected from mapping: Using Camera {preferred_webcam} ({best_webcam['name']})")

    # RESILIENT: Detect cameras (at least one required)
    if not recorder.detect_cameras(preferred_webcam_index=preferred_webcam):
        print("\nERROR: No cameras detected at all!")
        print("\nTroubleshooting:")
        print("  1. Make sure at least one camera is connected")
        print("  2. Close Uti-Live Screen software if using thermal camera")
        print("  3. Set UTi 260B to 'USB Camera' mode (not USB Disk)")
        return 1

    print("\nWaiting for cameras to initialize...")
    time.sleep(2)

    # RESILIENT: Validate configuration (opens whatever is available)
    if not recorder.validate_configuration():
        print("\nERROR: No cameras could be opened!")
        return 1

    # Start recording
    print("\n" + "=" * 60)
    print("Starting recording in 3 seconds...")
    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    print("Recording started!")

    try:
        recorder.start_recording(output_base_dir=output_directory)
    finally:
        recorder.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
