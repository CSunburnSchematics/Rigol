import cv2
import numpy as np

def analyze_thermal_frame():
    """Analyze what data we're getting from the thermal camera"""

    # Capture a frame from the thermal camera
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("Error: Cannot open thermal camera")
        return

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Error: Cannot read frame")
        return

    print("Thermal Frame Analysis")
    print("=" * 60)
    print(f"Frame shape: {frame.shape}")
    print(f"Data type: {frame.dtype}")
    print(f"Number of channels: {frame.shape[2] if len(frame.shape) > 2 else 1}")
    print(f"Min pixel value: {frame.min()}")
    print(f"Max pixel value: {frame.max()}")
    print(f"Mean pixel value: {frame.mean():.2f}")
    print()

    # Check if it's color or grayscale
    if len(frame.shape) == 3:
        print("Color channels (BGR):")
        print(f"  Blue   - Min: {frame[:,:,0].min()}, Max: {frame[:,:,0].max()}, Mean: {frame[:,:,0].mean():.2f}")
        print(f"  Green  - Min: {frame[:,:,1].min()}, Max: {frame[:,:,1].max()}, Mean: {frame[:,:,1].mean():.2f}")
        print(f"  Red    - Min: {frame[:,:,2].min()}, Max: {frame[:,:,2].max()}, Mean: {frame[:,:,2].mean():.2f}")
        print()

        # Check if it's actually a color image or just RGB representation of grayscale
        if np.array_equal(frame[:,:,0], frame[:,:,1]) and np.array_equal(frame[:,:,1], frame[:,:,2]):
            print("Note: All channels are identical (grayscale image in RGB format)")
        else:
            print("Note: This is a color image (thermal colormap)")

    # Save the frame for inspection
    cv2.imwrite("thermal_analysis_frame.png", frame)
    print(f"\nSaved frame to: thermal_analysis_frame.png")

    # Sample pixel values from different areas
    h, w = frame.shape[:2]
    print("\nSample pixel values from different regions:")
    print(f"  Top-left corner:     {frame[10, 10]}")
    print(f"  Top-right corner:    {frame[10, w-10]}")
    print(f"  Center:              {frame[h//2, w//2]}")
    print(f"  Bottom-left corner:  {frame[h-10, 10]}")
    print(f"  Bottom-right corner: {frame[h-10, w-10]}")

    print("\n" + "=" * 60)
    print("ANALYSIS:")
    print("=" * 60)
    print("""
The UTi 260B is sending a COLOR IMAGE (RGB/BGR) that represents
the thermal data visually, but NOT raw temperature values.

What we're getting:
- A colorized thermal image (like the purple/yellow/red you see)
- Temperature values rendered as TEXT on the image
- Visual scale bar with colors

What we're NOT getting:
- Raw temperature data per pixel
- Radiometric thermal data
- Direct temperature-to-pixel mapping

To extract temperature data, we would need:
1. Access to the raw thermal sensor data (requires manufacturer SDK)
2. OR: Use OCR to read the temperature text from the image
3. OR: Reverse-engineer the color palette to estimate temperatures
   (very inaccurate and unreliable)

The most reliable approach would be to use UNI-T's official SDK
if they provide one for programmatic access to raw thermal data.
    """)

if __name__ == "__main__":
    analyze_thermal_frame()
