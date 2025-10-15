"""
Capture thermal images from UTi 260B and save as BMP with UTC timestamps
"""

import cv2
import time
import sys
from datetime import datetime, timezone

class UTiBMPCapture:
    def __init__(self, camera_index=1):
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
        print(f"Camera opened: {width}x{height}")
        return True

    def close_camera(self):
        """Close camera connection"""
        if self.cap:
            self.cap.release()

    def capture_single_bmp(self):
        """Capture a single frame and save as BMP with UTC timestamp"""
        if not self.cap or not self.cap.isOpened():
            if not self.open_camera():
                return None

        ret, frame = self.cap.read()
        if not ret:
            print("Error: Failed to capture frame")
            return None

        # Generate UTC timestamp filename
        utc_now = datetime.now(timezone.utc)
        timestamp = utc_now.strftime("%Y%m%d_%H%M%S_UTC")
        filename = f"thermal_{timestamp}.bmp"

        # Save as BMP
        cv2.imwrite(filename, frame)

        # Also save timestamp info to text file
        info_filename = f"thermal_{timestamp}.txt"
        with open(info_filename, 'w') as f:
            f.write(f"Capture Time (UTC): {utc_now.isoformat()}\n")
            f.write(f"Unix Timestamp: {utc_now.timestamp()}\n")
            f.write(f"Image File: {filename}\n")
            f.write(f"Resolution: {frame.shape[1]}x{frame.shape[0]}\n")

        print(f"Saved: {filename}")
        print(f"  UTC Time: {utc_now.isoformat()}")
        print(f"  Info: {info_filename}")

        return filename

    def interval_capture_bmp(self, interval_seconds=5, num_captures=10):
        """
        Capture BMP images at regular intervals with UTC timestamps

        Args:
            interval_seconds: Time between captures
            num_captures: Number of images to capture (0 for continuous)
        """
        if not self.cap or not self.cap.isOpened():
            if not self.open_camera():
                return

        print(f"\n=== Interval BMP Capture Mode ===")
        print(f"Interval: {interval_seconds}s")
        print(f"Number of captures: {num_captures if num_captures > 0 else 'Continuous (Ctrl+C to stop)'}")
        print(f"Timestamp: UTC")
        print("=" * 40)

        capture_count = 0

        try:
            while True:
                # Check if we've reached the target
                if num_captures > 0 and capture_count >= num_captures:
                    print(f"\nCompleted {num_captures} captures")
                    break

                # Capture frame
                ret, frame = self.cap.read()
                if not ret:
                    print("Error: Failed to capture frame, retrying...")
                    time.sleep(1)
                    continue

                # Generate UTC timestamp
                utc_now = datetime.now(timezone.utc)
                timestamp = utc_now.strftime("%Y%m%d_%H%M%S_UTC")
                filename = f"thermal_{timestamp}.bmp"

                # Save as BMP
                cv2.imwrite(filename, frame)
                capture_count += 1

                # Also save timestamp info
                info_filename = f"thermal_{timestamp}.txt"
                with open(info_filename, 'w') as f:
                    f.write(f"Capture Time (UTC): {utc_now.isoformat()}\n")
                    f.write(f"Unix Timestamp: {utc_now.timestamp()}\n")
                    f.write(f"Image File: {filename}\n")
                    f.write(f"Resolution: {frame.shape[1]}x{frame.shape[0]}\n")
                    f.write(f"Capture Number: {capture_count}\n")

                print(f"[{capture_count}] {filename} - {utc_now.isoformat()}")

                # Wait for next interval (unless this was the last capture)
                if num_captures == 0 or capture_count < num_captures:
                    time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print(f"\n\nCapture interrupted by user")

        print(f"\nTotal captures: {capture_count}")
        self.close_camera()


def print_usage():
    print("""
UTi 260B Thermal BMP Capture with UTC Timestamps
=================================================

Usage: python capture_bmp_utc.py [mode] [options]

Modes:
  single              Capture single BMP image
  interval [sec] [n]  Capture at intervals (default: 5s, 10 images)

Examples:
  python capture_bmp_utc.py single
  python capture_bmp_utc.py interval 10 5     # Capture 5 images, 10s apart
  python capture_bmp_utc.py interval 2 20     # Capture 20 images, 2s apart
    """)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    uti = UTiBMPCapture(camera_index=1)  # Camera 1 is the UTi 260B
    mode = sys.argv[1].lower()

    if mode == "single":
        uti.open_camera()
        uti.capture_single_bmp()
        uti.close_camera()

    elif mode == "interval":
        interval = 5  # default
        num_captures = 10  # default

        if len(sys.argv) > 2:
            try:
                interval = int(sys.argv[2])
            except ValueError:
                print("Error: Interval must be a number")
                sys.exit(1)

        if len(sys.argv) > 3:
            try:
                num_captures = int(sys.argv[3])
            except ValueError:
                print("Error: Number of captures must be a number")
                sys.exit(1)

        uti.interval_capture_bmp(interval_seconds=interval, num_captures=num_captures)

    else:
        print(f"Unknown mode: {mode}")
        print_usage()
        sys.exit(1)
