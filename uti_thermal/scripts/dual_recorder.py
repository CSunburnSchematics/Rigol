"""
Dual Camera Recorder - UTi 260B Thermal + 4K Webcam
- Auto-detects both cameras
- Records synchronized videos
- Same framerate for both cameras
- UTC timestamps for frame-accurate sync
"""

import cv2
import time
import sys
import json
import os
from datetime import datetime, timezone

class DualCameraRecorder:
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

    def detect_cameras(self, preferred_webcam_index=None):
        """
        Detect both thermal camera and regular webcam
        UTi 260B: 240x321
        4K Webcam: Higher resolution
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
                # Verify this camera actually supports high resolution
                test_cap = cv2.VideoCapture(preferred_webcam_index, cv2.CAP_DSHOW)
                if test_cap.isOpened():
                    # Try to set 4K
                    test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
                    test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
                    actual_w = int(test_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_h = int(test_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    test_cap.release()

                    if actual_w >= 1920 and actual_h >= 1080:
                        # This is indeed a high-res camera
                        self.webcam_index = preferred_webcam_index
                        print(f"\nUsing specified webcam: Camera {self.webcam_index} (verified {actual_w}x{actual_h})")
                    else:
                        print(f"\nWARNING: Camera {preferred_webcam_index} doesn't support high resolution")
                        print(f"  Max detected: {actual_w}x{actual_h}")
                        print(f"  Falling back to auto-select")
                        preferred_webcam_index = None
                else:
                    print(f"\nWARNING: Cannot open Camera {preferred_webcam_index}")
                    preferred_webcam_index = None

            if preferred_webcam_index is None or self.webcam_index is None:
                # Auto-select by testing actual 4K capability
                print(f"\nTesting webcams for highest resolution...")
                best_cam = None
                best_pixels = 0

                for cam in webcams:
                    test_cap = cv2.VideoCapture(cam['index'], cv2.CAP_DSHOW)
                    if test_cap.isOpened():
                        # Try 4K
                        test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
                        test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
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
                    # Fallback
                    webcams.sort(key=lambda x: x['width'] * x['height'], reverse=True)
                    self.webcam_index = webcams[0]['index']
                    print(f"\nFallback: Camera {self.webcam_index}")

        if self.thermal_camera_index is not None:
            print(f"\nSelected thermal: Camera {self.thermal_camera_index} (240x321)")

        return self.thermal_camera_index is not None and self.webcam_index is not None

    def validate_configuration(self):
        """
        Validate both cameras are properly configured
        """
        print("\nValidating camera configuration...")

        # Open thermal camera
        self.thermal_cap = cv2.VideoCapture(self.thermal_camera_index, cv2.CAP_DSHOW)
        if not self.thermal_cap.isOpened():
            print("ERROR: Cannot open thermal camera")
            return False

        thermal_width = int(self.thermal_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        thermal_height = int(self.thermal_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"  Thermal: {thermal_width}x{thermal_height}")

        # Open webcam
        self.webcam_cap = cv2.VideoCapture(self.webcam_index, cv2.CAP_DSHOW)
        if not self.webcam_cap.isOpened():
            print("ERROR: Cannot open webcam")
            return False

        # Force webcam to 4K resolution
        self.webcam_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        self.webcam_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)

        webcam_width = int(self.webcam_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        webcam_height = int(self.webcam_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"  Webcam:  {webcam_width}x{webcam_height}")

        # Test frame capture
        ret_t, frame_t = self.thermal_cap.read()
        ret_w, frame_w = self.webcam_cap.read()

        if not ret_t or not ret_w:
            print("ERROR: Cannot capture test frames")
            return False

        print("  Status: READY")
        return True

    def start_recording(self, output_prefix=None):
        """
        Start synchronized recording from both cameras
        """
        # Create recordings directory in Claude folder (two levels up from scripts)
        # scripts -> uti_thermal -> Claude -> recordings
        recordings_base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "recordings")
        os.makedirs(recordings_base, exist_ok=True)

        if output_prefix is None:
            utc_now = datetime.now(timezone.utc)
            timestamp = utc_now.strftime("%Y%m%d_%H%M%S_UTC")
            output_prefix = f"recording_{timestamp}"

            # Create timestamped output directory inside recordings folder
            output_dir = os.path.join(recordings_base, f"recording_{timestamp}")
            os.makedirs(output_dir, exist_ok=True)
            print(f"Created output directory: {output_dir}")
        else:
            output_dir = os.path.join(recordings_base, output_prefix)
            os.makedirs(output_dir, exist_ok=True)

        thermal_filename = os.path.join(output_dir, f"{os.path.basename(output_prefix)}_thermal.avi")
        webcam_filename = os.path.join(output_dir, f"{os.path.basename(output_prefix)}_webcam.avi")
        combined_filename = os.path.join(output_dir, f"{os.path.basename(output_prefix)}_combined.avi")

        # Get frame dimensions
        thermal_width = int(self.thermal_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        thermal_height = int(self.thermal_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        webcam_width = int(self.webcam_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        webcam_height = int(self.webcam_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Calculate combined display dimensions (same as preview)
        display_thermal_width = 480
        display_thermal_height = 642
        display_webcam_width = 856
        display_webcam_height = 642
        combined_width = display_thermal_width + display_webcam_width
        combined_height = display_thermal_height

        # Setup video writers with same FPS
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        target_fps = 10  # Use lower FPS that matches actual capture rate

        self.thermal_writer = cv2.VideoWriter(thermal_filename, fourcc, target_fps,
                                             (thermal_width, thermal_height))
        self.webcam_writer = cv2.VideoWriter(webcam_filename, fourcc, target_fps,
                                            (webcam_width, webcam_height))
        self.combined_writer = cv2.VideoWriter(combined_filename, fourcc, target_fps,
                                              (combined_width, combined_height))

        # Initialize timestamp log
        self.timestamp_log = []
        self.frame_count = 0
        self.recording = True

        # Recording metadata
        start_time_utc = datetime.now(timezone.utc)
        recording_metadata = {
            'start_time_utc': start_time_utc.isoformat(),
            'start_timestamp_unix': start_time_utc.timestamp(),
            'thermal_file': thermal_filename,
            'webcam_file': webcam_filename,
            'combined_file': combined_filename,
            'thermal_resolution': f"{thermal_width}x{thermal_height}",
            'webcam_resolution': f"{webcam_width}x{webcam_height}",
            'combined_resolution': f"{combined_width}x{combined_height}",
            'target_fps': target_fps,
            'thermal_camera_index': self.thermal_camera_index,
            'webcam_camera_index': self.webcam_index
        }

        print("\n" + "=" * 60)
        print("DUAL RECORDING STARTED")
        print("=" * 60)
        print(f"Thermal:  {thermal_filename}")
        print(f"Webcam:   {webcam_filename}")
        print(f"Combined: {combined_filename}")
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

        try:
            while self.recording:
                # Capture from both cameras
                ret_thermal, frame_thermal = self.thermal_cap.read()
                ret_webcam, frame_webcam = self.webcam_cap.read()

                if not ret_thermal or not ret_webcam:
                    print("\nWarning: Failed to read frame from one or both cameras")
                    continue

                # Record exact capture timestamp
                capture_time_utc = datetime.now(timezone.utc)
                capture_timestamp_unix = capture_time_utc.timestamp()

                # Write original frames to individual videos
                self.thermal_writer.write(frame_thermal)
                self.webcam_writer.write(frame_webcam)
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

                # Create combined display (side-by-side)
                # Resize thermal to be larger for visibility
                display_thermal = cv2.resize(frame_thermal, (480, 642))  # 2x scale

                # Resize webcam to match height
                display_webcam = cv2.resize(frame_webcam, (856, 642))  # Match height

                # Combine side by side
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

                # Add labels
                cv2.putText(display_combined, "THERMAL", (200, 620),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display_combined, "WEBCAM", (680, 620),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                # Add recording indicator (red circle)
                cv2.circle(display_combined, (display_combined.shape[1] - 30, 30), 12, (0, 0, 255), -1)

                # Write combined view to video
                self.combined_writer.write(display_combined)

                # Show live preview
                cv2.imshow('Dual Camera Recorder - Thermal + Webcam (Press Q to Exit)', display_combined)

                # Handle key presses
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q') or key == 27:  # 'q' or ESC
                    print("\n\nStopping recording...")
                    self.recording = False

                elif key == ord('s'):  # Save snapshot
                    snapshot_time = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
                    thermal_snap = os.path.join(output_dir, f"snapshot_thermal_frame{self.frame_count}_{snapshot_time}.png")
                    webcam_snap = os.path.join(output_dir, f"snapshot_webcam_frame{self.frame_count}_{snapshot_time}.png")
                    cv2.imwrite(thermal_snap, frame_thermal)
                    cv2.imwrite(webcam_snap, frame_webcam)
                    print(f"\nSnapshots saved: {os.path.basename(thermal_snap)}, {os.path.basename(webcam_snap)}")

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
        timestamp_filename = os.path.join(output_dir, f"{os.path.basename(output_prefix)}_timestamps.json")
        with open(timestamp_filename, 'w') as f:
            json.dump({
                'metadata': recording_metadata,
                'frames': self.timestamp_log
            }, f, indent=2)

        # Save summary
        summary_filename = os.path.join(output_dir, f"{os.path.basename(output_prefix)}_summary.txt")
        with open(summary_filename, 'w') as f:
            f.write("Dual Camera Recording Summary\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Thermal Video:  {thermal_filename}\n")
            f.write(f"Webcam Video:   {webcam_filename}\n")
            f.write(f"Combined Video: {combined_filename}\n")
            f.write(f"Timestamp Data: {timestamp_filename}\n\n")
            f.write(f"Recording Start (UTC): {recording_metadata['start_time_utc']}\n")
            f.write(f"Recording End (UTC):   {recording_metadata['end_time_utc']}\n")
            f.write(f"Duration: {total_duration:.2f} seconds\n\n")
            f.write(f"Total Frames: {self.frame_count}\n")
            f.write(f"Target FPS: {target_fps}\n")
            f.write(f"Actual FPS: {actual_fps:.2f}\n\n")
            f.write(f"Thermal Resolution: {recording_metadata['thermal_resolution']}\n")
            f.write(f"Webcam Resolution:  {recording_metadata['webcam_resolution']}\n")

        print("\n" + "=" * 60)
        print("RECORDING STOPPED")
        print("=" * 60)
        print(f"Thermal video:  {thermal_filename}")
        print(f"Webcam video:   {webcam_filename}")
        print(f"Combined video: {combined_filename}")
        print(f"Timestamps:     {timestamp_filename}")
        print(f"Summary:        {summary_filename}")
        print(f"\nRecording Statistics:")
        print(f"  Duration: {total_duration:.2f} seconds")
        print(f"  Frames captured: {self.frame_count}")
        print(f"  Actual FPS: {actual_fps:.2f}")
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
                cameras = json.load(f)
                return cameras
        except:
            return None
    return None

def main():
    recorder = DualCameraRecorder()

    # Check if user specified a webcam index
    preferred_webcam = None

    if len(sys.argv) > 1:
        try:
            preferred_webcam = int(sys.argv[1])
            print(f"User specified webcam index: {preferred_webcam}")
        except ValueError:
            print(f"Invalid camera index: {sys.argv[1]}")
            return 1
    else:
        # Try to load from camera mapping
        mapping = load_camera_mapping()
        if mapping:
            # Find the best webcam from mapping (highest resolution, not thermal)
            webcams = [c for c in mapping if c['type'] != 'thermal']
            if webcams:
                best_webcam = max(webcams, key=lambda x: x.get('max_pixels', 0))
                preferred_webcam = best_webcam['index']
                print(f"Auto-detected from mapping: Using Camera {preferred_webcam} ({best_webcam['name']})")
                print(f"  Max Resolution: {best_webcam.get('max_resolution', 'Unknown')}")

        if preferred_webcam is None:
            print("No camera mapping found. Run 'python scripts/identify_cameras.py' to create one.")
            print("Or specify a camera index: python dual_recorder.py [camera_index]")

    # Step 1: Detect cameras
    if not recorder.detect_cameras(preferred_webcam_index=preferred_webcam):
        print("\nERROR: Could not detect both cameras!")
        print("\nTroubleshooting:")
        print("  1. Make sure UTi 260B is connected via USB-C")
        print("  2. Make sure 4K webcam is connected")
        print("  3. Close Uti-Live Screen software if running")
        print("  4. Set UTi 260B to 'USB Camera' mode (not USB Disk)")
        return 1

    # Step 2: Validate configuration
    if not recorder.validate_configuration():
        print("\nERROR: Camera configuration invalid!")
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
