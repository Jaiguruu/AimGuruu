"""
core/session.py

ARCHITECTURAL DECISION (Data Persistence):
A session represents a single shooting practice round. Instead of just keeping scores in RAM, 
we immediately persist every shot to disk (CSV/JSON). If the application crashes during a 
100-shot session, no data is lost. This is called 'Write-Ahead Logging' or 'Live Appending'.

MATHEMATICAL DECISION (Scoring):
Scoring a shot isn't just checking if a pixel is inside a circle. We use Pythagorean Theorem 
to calculate the exact radial distance (in millimetres) from the target's dead center. 
If the distance is within the 10-ring radius, it's a 10. If it's further, we subtract points 
proportionally based on the rings.
"""

import os
import csv
import json
import time
import math
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class Shot:
    """
    Data Transfer Object representing a single recorded bullet hole.
    """
    index: int
    timestamp: float
    aim_mm: Tuple[float, float]  # The (x,y) offset from the bullseye in millimetres
    score: float                 # The calculated score (e.g. 10.5 or 9.0)
    
    @property
    def radius_mm(self) -> float:
        """Pythagorean theorem to find absolute distance from center (0,0)."""
        return math.sqrt(self.aim_mm[0] ** 2 + self.aim_mm[1] ** 2)


class Session:
    """
    Manages the state of the current shooting session, calculates scores,
    and handles saving the data to disk for later SLM (Small Language Model) Insights.
    """

    def __init__(self, name: str = "Training_Session", scoring_radius_mm: float = 22.75):
        self.name = name
        # The radius of the outermost ring on the target. If the shot is outside this, it's a 0.
        self.scoring_radius_mm = scoring_radius_mm
        self.shots: List[Shot] = []
        self.start_time = time.time()
        
        # We will save our data to a 'history' folder
        self.save_dir = "history"
        os.makedirs(self.save_dir, exist_ok=True)
        
        # Setup live CSV writer
        filename = f"session_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        self.filepath = os.path.join(self.save_dir, filename)
        
        # Open in append mode immediately
        with open(self.filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Shot_Index", "Timestamp", "X_mm", "Y_mm", "Radius_mm", "Score"])

    def record_shot(self, aim_mm: Tuple[float, float]) -> Shot:
        """
        Takes the raw (X,Y) millimetre coordinates from the CV Engine, scores it, 
        adds it to RAM, and immediately flushes it to disk.
        """
        # Calculate the score mathematically
        score = self._calculate_score(aim_mm)
        
        shot = Shot(
            index=len(self.shots) + 1,
            timestamp=time.time(),
            aim_mm=aim_mm,
            score=score
        )
        self.shots.append(shot)
        
        # Live append to disk
        with open(self.filepath, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                shot.index, 
                f"{shot.timestamp:.3f}", 
                f"{shot.aim_mm[0]:.3f}", 
                f"{shot.aim_mm[1]:.3f}", 
                f"{shot.radius_mm:.3f}", 
                f"{shot.score:.1f}"
            ])
            
        return shot

    def _calculate_score(self, aim_mm: Tuple[float, float]) -> float:
        """
        The Geometry Engine for Scoring.
        Uses the exact mathematical distance to determine the score band.
        """
        radius = math.sqrt(aim_mm[0]**2 + aim_mm[1]**2)
        
        if radius > self.scoring_radius_mm:
            return 0.0  # Missed the scoring rings entirely
            
        # Standard decimal scoring (10.9 is perfect dead center)
        # We divide the scoring radius into 99 micro-bands.
        n_bands = 99
        step = 9.9 / 98
        band_w = self.scoring_radius_mm / n_bands
        band_n = min(int(radius / band_w), n_bands - 1)
        
        score = round(10.9 - band_n * step, 1)
        return score

    # ── Analytics for SLM ──────────────────────────────────────────────────
    
    @property
    def total_score(self) -> float:
        return round(sum(s.score for s in self.shots), 1)
        
    @property
    def average_score(self) -> float:
        if not self.shots: return 0.0
        return round(self.total_score / len(self.shots), 2)
        
    @property
    def group_size_mm(self) -> float:
        """
        Extreme Spread (ES): The maximum distance between ANY two shots in the session.
        This is a critical metric for precision shooters. 
        A small group size means the shooter is highly consistent, even if the sights are misaligned.
        """
        if len(self.shots) < 2:
            return 0.0
            
        coords = np.array([s.aim_mm for s in self.shots])
        max_dist = 0.0
        for i in range(len(coords)):
            for j in range(i+1, len(coords)):
                dist = np.linalg.norm(coords[i] - coords[j])
                if dist > max_dist:
                    max_dist = dist
        return round(max_dist, 2)
        
    def export_summary_json(self):
        """
        At the end of the session, export a clean JSON file containing all aggregate statistics.
        This file is perfectly formatted to be parsed by Phase 5 (The SLM Insight Engine).
        """
        json_path = self.filepath.replace('.csv', '.json')
        data = {
            "session_name": self.name,
            "total_shots": len(self.shots),
            "total_score": self.total_score,
            "average_score": self.average_score,
            "group_size_mm": self.group_size_mm,
            "shots": [
                {
                    "shot": s.index,
                    "x": round(s.aim_mm[0], 2),
                    "y": round(s.aim_mm[1], 2),
                    "score": s.score
                } for s in self.shots
            ]
        }
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
