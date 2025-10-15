"""
UTi 260B Thermal Camera Capture Script
Supports both live streaming and intermittent captures
"""

import cv2
import time
import sys
import os
from datetime import datetime

class UTiCapture:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None

    def open_camera(self):
        """Open connection to the thermal camera"""
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}")
            return False

        # Get camera properties
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Camera opened successfully: {width}x{height}")
        return True

    def close_camera(self):
        """Close camera connection"""
        if self.cap:
            self.cap.release()
            cv2.destroyAllWindows()

    def capture_single_frame(self, output_path=None):
        """Capture a single frame and optionally save it"""
        if not self.cap or not self.cap.isOpened():
            if not self.open_camera():
                return None

        ret, frame = self.cap.read()
        if not ret:
            print("Error: Failed to capture frame")
            return None

        if output_path:
            cv2.imwrite(output_path, frame)
            print(f"Frame saved to: {output_path}")

        return frame

    def stream_live(self, save_on_key='s'):
        """
        Display live thermal camera feed
        Press 's' to save current frame
        Press 'q' to quit
        """
        if not self.cap or not self.cap.isOpened():
            if not self.open_camera():
                return

        print("\n=== Live Thermal Camera Stream ===")
        print(f"Press '{save_on_key}' to save current frame")
        print("Press 'q' to quit")
        print("=" * 40)

        frame_count = 0
        start_time = time.time()

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Failed to read frame")
                break

            frame_count += 1
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0

            # Add FPS counter to display
            display_frame = frame.copy()
            cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imshow('UTi 260B Thermal Camera', display_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\nQuitting...")
                break
            elif key == ord(save_on_key):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"thermal_capture_{timestamp}.png"
                cv2.imwrite(filename, frame)
                print(f"Saved: {filename}")

        self.close_camera()

    def interval_capture(self, interval_seconds=5, duration_seconds=60, output_dir="thermal_captures"):
        """
        Capture frames at regular intervals

        Args:
            interval_seconds: Time between captures
            duration_seconds: Total capture duration (0 for continuous)
            output_dir: Directory to save captures
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")

        if not self.cap or not self.cap.isOpened():
            if not self.open_camera():
                return

        print(f"\n=== Interval Capture Mode ===")
        print(f"Interval: {interval_seconds}s")
        print(f"Duration: {duration_seconds}s" if duration_seconds > 0 else "Duration: Continuous (Ctrl+C to stop)")
        print(f"Output: {output_dir}")
        print("=" * 40)

        start_time = time.time()
        capture_count = 0

        try:
            while True:
                # Check duration limit
                if duration_seconds > 0 and (time.time() - start_time) > duration_seconds:
                    print("\nDuration limit reached")
                    break

                # Capture frame
                ret, frame = self.cap.read()
                if not ret:
                    print("Error: Failed to capture frame")
                    continue

                # Save with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
                filename = os.path.join(output_dir, f"thermal_{timestamp}.png")
                cv2.imwrite(filename, frame)
                capture_count += 1

                elapsed = time.time() - start_time
                print(f"[{elapsed:.1f}s] Captured #{capture_count}: {filename}")

                # Wait for next interval
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n\nCapture interrupted by user")

        print(f"\nTotal captures: {capture_count}")
        self.close_camera()

    def record_video(self, duration_seconds=30, output_filename="thermal_video.avi", fps=30):
        """
        Record video from thermal camera

        Args:
            duration_seconds: Recording duration
            output_filename: Output video file
            fps: Frames per second
        """
        if not self.cap or not self.cap.isOpened():
            if not self.open_camera():
                return

        # Get frame dimensions
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Define codec and create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))

        print(f"\n=== Recording Video ===")
        print(f"Duration: {duration_seconds}s")
        print(f"Output: {output_filename}")
        print(f"Resolution: {width}x{height} @ {fps}fps")
        print("=" * 40)

        start_time = time.time()
        frame_count = 0

        try:
            while (time.time() - start_time) < duration_seconds:
                ret, frame = self.cap.read()
                if not ret:
                    print("Error: Failed to read frame")
                    break

                out.write(frame)
                frame_count += 1

                elapsed = time.time() - start_time
                progress = (elapsed / duration_seconds) * 100
                print(f"\rRecording: {progress:.1f}% ({frame_count} frames)", end='')

        except KeyboardInterrupt:
            print("\n\nRecording interrupted by user")

        out.release()
        self.close_camera()
        print(f"\n\nVideo saved: {output_filename}")
        print(f"Total frames: {frame_count}")


def print_usage():
    print("""
UTi 260B Thermal Camera Capture Tool
=====================================

Usage: python uti_capture.py [mode] [options]

Modes:
  stream              Live view with manual capture (press 's' to save, 'q' to quit)
  interval [sec]      Capture at intervals (default: 5 seconds)
  duration [sec]      Set duration for interval mode (default: 60 seconds)
  video [sec]         Record video (default: 30 seconds)
  single [filename]   Capture single frame

Examples:
  python uti_capture.py stream
  python uti_capture.py interval 10
  python uti_capture.py interval 5 duration 120
  python uti_capture.py video 60
  python uti_capture.py single my_thermal_image.png
    """)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    uti = UTiCapture(camera_index=1)  # Camera 1 is the UTi 260B thermal camera
    mode = sys.argv[1].lower()

    if mode == "stream":
        uti.stream_live()

    elif mode == "interval":
        interval = 5  # default
        duration = 60  # default

        if len(sys.argv) > 2:
            try:
                interval = int(sys.argv[2])
            except ValueError:
                print("Error: Interval must be a number")
                sys.exit(1)

        if len(sys.argv) > 3 and sys.argv[3].lower() == "duration":
            if len(sys.argv) > 4:
                try:
                    duration = int(sys.argv[4])
                except ValueError:
                    print("Error: Duration must be a number")
                    sys.exit(1)

        uti.interval_capture(interval_seconds=interval, duration_seconds=duration)

    elif mode == "video":
        duration = 30  # default
        if len(sys.argv) > 2:
            try:
                duration = int(sys.argv[2])
            except ValueError:
                print("Error: Duration must be a number")
                sys.exit(1)

        uti.record_video(duration_seconds=duration)

    elif mode == "single":
        filename = "thermal_single.png"
        if len(sys.argv) > 2:
            filename = sys.argv[2]

        uti.capture_single_frame(output_path=filename)
        uti.close_camera()

    else:
        print(f"Unknown mode: {mode}")
        print_usage()
        sys.exit(1)
