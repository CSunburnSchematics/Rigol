"""
Test if continuous frame reading keeps the UTi 260B awake
"""
import cv2
import time
from datetime import datetime

print("UTi 260B Keep-Alive Test")
print("=" * 60)
print("This will continuously read from the thermal camera")
print("to see if it prevents auto-shutoff")
print("Press Ctrl+C to stop")
print("=" * 60)

# Open thermal camera
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("ERROR: Cannot open camera")
    exit(1)

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Camera opened: {width}x{height}")

if width != 240 or height != 321:
    print(f"WARNING: This doesn't look like the thermal camera!")
    print(f"Expected 240x321, got {width}x{height}")

start_time = time.time()
frame_count = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"\nERROR: Failed to read frame at {time.time() - start_time:.1f}s")
            break

        frame_count += 1
        elapsed = time.time() - start_time

        # Print status every 10 seconds
        if frame_count % 300 == 0:  # Assuming ~30fps
            print(f"[{elapsed:.0f}s] Still alive - {frame_count} frames captured")

        # Small delay to avoid overwhelming the camera
        time.sleep(0.01)

except KeyboardInterrupt:
    print(f"\n\nTest stopped by user")

elapsed = time.time() - start_time
print(f"\nTotal runtime: {elapsed:.1f} seconds")
print(f"Total frames: {frame_count}")

cap.release()
