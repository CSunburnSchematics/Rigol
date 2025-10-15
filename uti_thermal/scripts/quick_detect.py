"""Quick camera detection"""
import cv2

print("Quick Camera Detection")
print("-" * 60)

for i in range(10):
    print(f"Testing camera {i}...", end=" ", flush=True)
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)

    if cap.isOpened():
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        megapixels = (width * height) / 1_000_000

        ret, frame = cap.read()
        status = "OK" if ret else "FAIL"

        if width == 240 and height == 321:
            cam_type = "UTi 260B THERMAL"
        elif width >= 1920 and height >= 1080:
            cam_type = "4K/HD Webcam"
        else:
            cam_type = "Standard Webcam"

        print(f"{width}x{height} ({megapixels:.1f}MP) - {cam_type} [{status}]")
        cap.release()
    else:
        print("Not found")

print("-" * 60)
