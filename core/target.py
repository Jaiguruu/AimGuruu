"""
core/target.py

ARCHITECTURAL DECISION (Rendering the Target):
Instead of drawing complex concentric circles natively in Tkinter (which can be slow and hard to scale),
we use OpenCV to draw the target onto a NumPy array. OpenCV is written in C++ and optimized for geometry.
Once drawn, we convert the NumPy array to a PIL Image, which CustomTkinter can display instantly.
This ensures a buttery smooth 60fps refresh rate (Doherty Threshold).
"""

import cv2
import time
import numpy as np

class TargetRenderer:
    def __init__(self, size: int = 500):
        self.size = size
        self.center = (size // 2, size // 2)
        
        # Standard ISSF 10m Air Rifle target dimensions (in mm)
        self.target_diameter_mm = 45.5
        self.ring_radii_mm = [
            22.75, # 1 ring
            20.25, # 2 ring
            17.75, # 3 ring
            15.25, # 4 ring
            12.75, # 5 ring
            10.25, # 6 ring
            7.75,  # 7 ring
            5.25,  # 8 ring
            2.75,  # 9 ring
            0.25   # 10 ring
        ]
        
        # Scaling factor: how many pixels per millimeter?
        # We want the outer ring (45.5mm diameter) to fill about 90% of the canvas.
        self.pixels_per_mm = (self.size * 0.90) / self.target_diameter_mm
        
        # Pre-render the static target background so we don't redraw it every frame
        self._static_bg = self._draw_static_target()

    def _draw_static_target(self) -> np.ndarray:
        """Draws the rings of the target once."""
        # Create a dark gray background
        img = np.full((self.size, self.size, 3), (30, 30, 35), dtype=np.uint8)
        
        # Draw from the outside in (1 ring to 10 ring)
        for i, radius_mm in enumerate(self.ring_radii_mm):
            radius_px = int(radius_mm * self.pixels_per_mm)
            
            # Rings 4 through 9 are filled with black. The rest are white.
            is_black_zone = (3 <= i <= 8)
            fill_color = (15, 15, 15) if is_black_zone else (230, 230, 230)
            line_color = (200, 200, 200) if is_black_zone else (20, 20, 20)
            
            # Draw filled circle
            cv2.circle(img, self.center, radius_px, fill_color, -1)
            # Draw ring boundary
            cv2.circle(img, self.center, radius_px, line_color, 1)

        return img

    def render(self, live_aim_mm: tuple = None, shots: list = None, trace_history: list = None) -> np.ndarray:
        """
        Renders the current frame by taking the static background and drawing 
        the live crosshair, trace history, and all recorded shots on top of it.
        """
        # Start with a fresh copy of the static background
        canvas = self._static_bg.copy()
        
        # Draw the trajectory trace (SCATT style)
        if trace_history and len(trace_history) > 1:
            now = time.time()
            for i in range(1, len(trace_history)):
                ts1, x1, y1 = trace_history[i-1]
                ts2, x2, y2 = trace_history[i]
                
                age = now - ts2
                # Color coding based on age (SCATT Standard)
                if age > 3.0:
                    continue # Too old, fade out
                elif age > 1.0:
                    color = (0, 200, 0) # Green (Approach)
                elif age > 0.2:
                    color = (0, 255, 255) # Yellow (Hold)
                else:
                    color = (0, 0, 255) # Red (Trigger break)
                    
                px1 = int(self.center[0] + (x1 * self.pixels_per_mm))
                py1 = int(self.center[1] + (y1 * self.pixels_per_mm))
                px2 = int(self.center[0] + (x2 * self.pixels_per_mm))
                py2 = int(self.center[1] + (y2 * self.pixels_per_mm))
                
                cv2.line(canvas, (px1, py1), (px2, py2), color, 2, cv2.LINE_AA)
        
        # Draw recorded shots (bullet holes)
        if shots:
            for shot in shots:
                x_px = int(self.center[0] + (shot.aim_mm[0] * self.pixels_per_mm))
                y_px = int(self.center[1] + (shot.aim_mm[1] * self.pixels_per_mm))
                
                # Draw a bright red hole for the shot
                shot_radius = int((4.5 / 2.0) * self.pixels_per_mm) # 4.5mm calibre pellet
                cv2.circle(canvas, (x_px, y_px), shot_radius, (0, 0, 255), -1)
                
                # Draw the shot number text
                cv2.putText(canvas, str(shot.index), (x_px + 10, y_px - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        # Draw the live crosshair (where the gun is currently pointing)
        if live_aim_mm:
            x_px = int(self.center[0] + (live_aim_mm[0] * self.pixels_per_mm))
            y_px = int(self.center[1] + (live_aim_mm[1] * self.pixels_per_mm))
            
            # Draw an elegant green crosshair (Law of Prägnanz - keep it simple)
            ch_size = 15
            cv2.line(canvas, (x_px - ch_size, y_px), (x_px + ch_size, y_px), (0, 255, 0), 2)
            cv2.line(canvas, (x_px, y_px - ch_size), (x_px, y_px + ch_size), (0, 255, 0), 2)
            
        return canvas
