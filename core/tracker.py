"""
core/tracker.py

ARCHITECTURAL DECISION:
We use ArUco markers (ArucoDetector) because contour detection (finding the black target circle) 
is highly susceptible to lighting changes and shadows. ArUco markers provide sub-pixel accuracy 
and, critically, carry unique IDs (0=TL, 1=TR, 2=BR, 3=BL). This guarantees we know the exact 
orientation of the target even if the camera is mounted upside down or at a severe angle.

MATHEMATICAL DECISION (Homography):
If a camera looks at a target at an angle, the pixel coordinates are distorted (Perspective Distortion).
We define the *real world* coordinates of the printed markers on the A4 sheet (e.g. 210mm x 297mm).
By mapping the 4 detected pixel corners to the 4 known physical millimetre corners, we compute a 
Homography Matrix (`cv2.findHomography`). We then use this matrix to mathematically warp the center 
of the camera image (our "aiming point") into exact real-world millimetres relative to the target center.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List

# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class TrackFrame:
    """
    Data Transfer Object (DTO) containing the results of processing one single video frame.
    This ensures all components (UI, Audio, Scoring) have access to a clean, immutable state per frame.
    """
    aim_mm: Optional[Tuple[float, float]] = None   # The calculated (x, y) coordinates in millimetres from the target center
    aim_px: Optional[Tuple[int, int]] = None        # Pixel location of the aim point on the DISPLAY image
    markers_found: int = 0                          # Number of ArUco markers detected (0-4)
    frame_display: Optional[np.ndarray] = None      # The annotated video frame to be shown in the UI
    homography: Optional[np.ndarray] = None         # The mathematical Perspective Transform Matrix
    quality: float = 0.0                            # 0.0 to 1.0 confidence score based on how many markers were found

class ArucoTracker:
    """
    The Core Computer Vision Engine for tracking the camera's aim point.
    """

    def __init__(
        self,
        board_width_mm: float = 210.0,   # Standard A4 paper width
        board_height_mm: float = 297.0,  # Standard A4 paper height
        marker_size_mm: float = 40.0,    # Size of the printed ArUco square
        aruco_dict_name: str = "DICT_4X4_50", # We use a 4x4 dictionary for faster processing than 6x6
        margin_mm: float = 8.0,
        use_clahe: bool = True,          # Contrast Limited Adaptive Histogram Equalization
        clahe_clip: float = 4.0,
    ):
        self.board_width_mm = board_width_mm
        self.board_height_mm = board_height_mm
        self.marker_size_mm = marker_size_mm
        self.margin_mm = margin_mm

        # 1. Initialize the ArUco Detector
        # We use a Predefined Dictionary to ensure the engine only looks for valid patterns.
        dict_id = getattr(cv2.aruco, aruco_dict_name, cv2.aruco.DICT_4X4_50)
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(dict_id)
        self.detector_params = cv2.aruco.DetectorParameters()
        
        # Subpixel refinement is critical. It calculates corners down to fractions of a pixel 
        # by analyzing image gradients, giving us extreme millimeter accuracy.
        self.detector_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.detector_params)

        # 2. CLAHE (Contrast Limited Adaptive Histogram Equalisation)
        # ARCHITECTURAL DECISION: Users will practice indoors where lighting is uneven. 
        # CLAHE normalizes local contrast, making the black-and-white ArUco markers pop 
        # even in terrible lighting conditions. Cost is negligible (~2ms).
        self.use_clahe = use_clahe
        self._clahe = cv2.createCLAHE(clipLimit=float(clahe_clip), tileGridSize=(8, 8))

        # 3. Define the True Physical Coordinates of the printed sheet (in millimetres)
        # Origin (0,0) is the Top-Left of the paper.
        m = marker_size_mm
        mg = margin_mm
        bw = board_width_mm
        bh = board_height_mm

        # ID 0: Top-Left, ID 1: Top-Right, ID 2: Bottom-Right, ID 3: Bottom-Left
        self._board_corners = {
            0: np.array([[mg,       mg      ], [mg+m,    mg      ], [mg+m,    mg+m   ], [mg,      mg+m   ]], dtype=np.float32),
            1: np.array([[bw-mg-m,  mg      ], [bw-mg,   mg      ], [bw-mg,   mg+m   ], [bw-mg-m, mg+m   ]], dtype=np.float32),
            2: np.array([[bw-mg-m,  bh-mg-m ], [bw-mg,   bh-mg-m], [bw-mg,   bh-mg  ], [bw-mg-m, bh-mg  ]], dtype=np.float32),
            3: np.array([[mg,       bh-mg-m ], [mg+m,    bh-mg-m], [mg+m,    bh-mg  ], [mg,      bh-mg  ]], dtype=np.float32),
        }

        # The true center of the physical target (what we are aiming at)
        self.target_centre_mm = np.array([bw / 2, bh / 2], dtype=np.float32)

        # Caching the Homography. If a hand blocks a marker for a few frames, 
        # we can reuse the last known perspective transform to prevent stutter.
        self._last_homography: Optional[np.ndarray] = None
        self._homography_age: int = 0
        self.MAX_HOMOGRAPHY_AGE = 5 

    def process_frame(self, frame: np.ndarray) -> TrackFrame:
        """
        The main processing pipeline executed every single video frame.
        """
        result = TrackFrame()
        result.frame_display = frame.copy()

        # Step 1: Pre-process the frame to Grayscale and apply CLAHE for contrast enhancement
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.use_clahe:
            gray = self._clahe.apply(gray)
            
        # Step 2: Detect ArUco Markers
        corners, ids, rejected = self.detector.detectMarkers(gray)

        # If no markers are found, attempt to use stale homography (cache)
        if ids is None or len(ids) == 0:
            result.markers_found = 0
            self._homography_age += 1
            self._try_reuse_homography(result, frame)
            return result

        ids_flat = ids.flatten()
        result.markers_found = len(ids_flat)

        # Draw the detected green squares on the display frame so the user sees it working
        cv2.aruco.drawDetectedMarkers(result.frame_display, corners, ids)

        # Step 3: Match Camera Pixels to Physical Millimetres
        img_pts: List[np.ndarray] = []
        brd_pts: List[np.ndarray] = []

        for i, mid in enumerate(ids_flat):
            if mid in self._board_corners:
                img_pts.append(corners[i][0])          
                brd_pts.append(self._board_corners[mid])

        if len(img_pts) < 1:
            self._homography_age += 1
            self._try_reuse_homography(result, frame)
            return result

        img_pts_all = np.concatenate(img_pts, axis=0)
        brd_pts_all = np.concatenate(brd_pts, axis=0)

        # Step 4: Calculate the Homography Matrix
        # RANSAC is used to mathematically discard outliers if a corner is misdetected
        H, mask = cv2.findHomography(img_pts_all, brd_pts_all, cv2.RANSAC, 5.0)

        if H is None:
            self._homography_age += 1
            self._try_reuse_homography(result, frame)
            return result

        self._last_homography = H
        self._homography_age = 0
        result.homography = H
        result.quality = min(1.0, len(img_pts) / len(self._board_corners))

        # Step 5: Compute the actual aiming coordinates
        self._compute_aim(result, frame)
        return result

    def _try_reuse_homography(self, result: TrackFrame, frame: np.ndarray):
        """Fallback to cached matrix if markers are temporarily obscured by smoke/hands."""
        if self._last_homography is not None and self._homography_age <= self.MAX_HOMOGRAPHY_AGE:
            result.homography = self._last_homography
            result.quality = max(0.1, 0.5 - self._homography_age * 0.1)
            self._compute_aim(result, frame)

    def _compute_aim(self, result: TrackFrame, frame: np.ndarray):
        """
        Applies the Perspective Transform to the dead center of the camera feed.
        """
        H = result.homography
        if H is None:
            return

        h, w = frame.shape[:2]
        # The crosshair is always perfectly centered in the camera feed
        img_centre = np.array([[[w / 2, h / 2]]], dtype=np.float32)

        # MATHEMATICAL MAGIC: Map the camera's center pixel through the matrix 
        # to find out EXACTLY where that pixel lands on the physical paper in millimetres.
        board_pt = cv2.perspectiveTransform(img_centre, H)[0][0]

        # Calculate offset from the actual center of the printed target
        aim_mm = (
            float(board_pt[0] - self.target_centre_mm[0]),
            float(board_pt[1] - self.target_centre_mm[1]),
        )
        result.aim_mm = aim_mm
        result.aim_px = (int(w / 2), int(h / 2))

        # Draw a live crosshair and aim coordinates on the display frame
        cx, cy = int(w / 2), int(h / 2)
        color = (0, 255, 0) if result.quality > 0.5 else (0, 165, 255)
        cv2.line(result.frame_display, (cx - 20, cy), (cx + 20, cy), color, 2)
        cv2.line(result.frame_display, (cx, cy - 20), (cx, cy + 20), color, 2)
        cv2.circle(result.frame_display, (cx, cy), 8, color, 1)

        txt = f"Aim: ({aim_mm[0]:+.1f}, {aim_mm[1]:+.1f}) mm"
        cv2.putText(result.frame_display, txt, (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
