"""
phase1_test.py

This script proves that our Computer Vision Engine (ArucoTracker) works.
It opens the webcam, reads frames, and passes them to the tracker.
If you hold up the printed target (or point the camera at it), it will draw
green boxes around the ArUco markers and a crosshair showing exactly where it aims.
"""

import cv2
from core.tracker import ArucoTracker

def main():
    print("Initializing Camera...")
    # 0 is usually the default laptop webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    # Initialize our highly-documented Tracker Engine
    tracker = ArucoTracker()
    print("Camera active. Point it at the ArUco markers. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        # Pass the raw frame to our engine. It returns a TrackFrame DTO.
        track_result = tracker.process_frame(frame)

        # Display the annotated frame
        cv2.imshow("Phase 1: Computer Vision Engine", track_result.frame_display)

        # Print the live coordinates if it detects the target
        if track_result.aim_mm:
            print(f"Aim Coordinates (mm): X={track_result.aim_mm[0]:.1f}, Y={track_result.aim_mm[1]:.1f}")

        # Break the loop when 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
