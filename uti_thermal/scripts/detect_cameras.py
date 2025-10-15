import cv2

def list_all_cameras(max_cameras=5):
    """List all available cameras with detailed info"""
    print("Detecting all available cameras...")
    print("=" * 60)

    for i in range(max_cameras):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            # Get properties
            backend = cap.getBackendName()
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            # Try to capture a test frame
            ret, frame = cap.read()

            print(f"\nCamera Index: {i}")
            print(f"  Backend: {backend}")
            print(f"  Resolution: {width}x{height}")
            print(f"  FPS: {fps}")
            print(f"  Frame capture: {'SUCCESS' if ret else 'FAILED'}")

            if ret:
                # Save a preview frame
                filename = f"camera_{i}_preview.png"
                cv2.imwrite(filename, frame)
                print(f"  Preview saved: {filename}")

            cap.release()
            print("-" * 60)

if __name__ == "__main__":
    list_all_cameras()
