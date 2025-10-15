"""
Check if any cameras support 4K resolution
"""
import cv2

print("4K Camera Detection - Testing high-res capability")
print("=" * 60)

for i in range(5):
    print(f"\nCamera {i}:")
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("  Not found")
        continue

    # Get default resolution
    default_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    default_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  Default: {default_width}x{default_height}")

    # Try to set to 4K (3840x2160)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)

    width_4k = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height_4k = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if width_4k != default_width or height_4k != default_height:
        print(f"  4K test: {width_4k}x{height_4k} -> SUPPORTS HIGHER RES!")
    else:
        # Try 1080p
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        width_1080 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height_1080 = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if width_1080 != default_width or height_1080 != default_height:
            print(f"  1080p test: {width_1080}x{height_1080} -> SUPPORTS HIGHER RES!")
        else:
            print(f"  Higher res: Not supported (locked at {default_width}x{default_height})")

    cap.release()

print("=" * 60)
