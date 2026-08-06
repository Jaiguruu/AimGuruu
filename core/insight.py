import os
import glob
import json
import numpy as np
import requests
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

def analyze_scatt_json(session_data):
    if "shots" not in session_data or not session_data["shots"]:
        return None
        
    shots = session_data["shots"]
    x_coords = [s["x"] for s in shots]
    y_coords = [s["y"] for s in shots]
    scores = [s["score"] for s in shots]
    
    # 1. Calculate Center of Mass (CoM) / Zero Displacement
    mean_x = np.mean(x_coords)
    mean_y = np.mean(y_coords)
    
    # 2. Identify Chronological Drift (Split session into Start vs End)
    midpoint = len(shots) // 2
    early_coor = np.mean(scores[:midpoint]) if midpoint > 0 else np.mean(scores)
    late_coor = np.mean(scores[midpoint:]) if midpoint > 0 else np.mean(scores)
    fatigue_trend = "Degrading" if late_coor < early_coor else "Improving/Stable"
    
    # 3. Categorise Directional Bias per bad shot (< 8.0)
    biases = []
    for s in shots:
        if s["score"] < 8.0:
            if s["x"] < -5 and abs(s["y"]) < 5: biases.append("Left (Canting/Eye strain)")
            elif s["x"] > 5 and s["y"] > 5: biases.append("Top-Right (Heeling/Anticipation)")
            elif s["y"] > 5: biases.append("High (Breathing control error)")
            elif s["y"] < -5: biases.append("Low (Jerking trigger)")
            
    dominant_flaw = max(set(biases), key=biases.count) if biases else "Inconsistent"

    return {
        "total_shots": len(shots),
        "average_score": np.mean(scores),
        "group_size_mm": session_data.get("group_size_mm", 0.0),
        "center_of_mass": {"x": round(mean_x, 2), "y": round(mean_y, 2)},
        "fatigue_trend": fatigue_trend,
        "dominant_flaw_zone": dominant_flaw,
        "early_avg": round(early_coor, 2),
        "late_avg": round(late_coor, 2)
    }

class InsightGenerator:
    def __init__(self, history_dir="history"):
        self.history_dir = history_dir
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")

    def get_latest_session_data(self):
        if not os.path.exists(self.history_dir):
            return None
            
        json_files = glob.glob(os.path.join(self.history_dir, "*.json"))
        if not json_files:
            return None
            
        latest_file = max(json_files, key=os.path.getmtime)
        with open(latest_file, "r") as f:
            return json.load(f)

    def build_prompt(self, metrics):
        return f"""### SYSTEM
You are an elite Olympic-level Shooting Coach AI. Analyze the session parameters provided. Diagnose the invisible biomechanical flaws. Give brief, actionable adjustments. Never repeat raw statistical scores or coordinates back to the shooter. Speak directly to them.

### USER SESSION DATA
- Total Shots: {metrics['total_shots']}
- Average Score: {round(metrics['average_score'], 2)} (Target standard: 10.0+)
- Group Size: {metrics['group_size_mm']} mm
- Chronological Trend: Early Avg {metrics['early_avg']} -> Late Avg {metrics['late_avg']} ({metrics['fatigue_trend']})
- Group Center of Mass: X = {metrics['center_of_mass']['x']}, Y = {metrics['center_of_mass']['y']}
- Dominant Flaw: {metrics['dominant_flaw_zone']}

### RESPONSE
"""

    def generate_coach_report(self):
        session_data = self.get_latest_session_data()
        if not session_data:
            return "No session data found. Fire a few shots first!"
            
        metrics = analyze_scatt_json(session_data)
        if not metrics:
            return "Not enough data in the latest session to analyze."
            
        prompt = self.build_prompt(metrics)
        
        # SLM Inference via OpenRouter API
        if not self.api_key:
            return "Error: OPENROUTER_API_KEY environment variable not set.\n\n" + self.fallback_insight(metrics)
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/AimGuruu",
                "X-Title": "AimGuruu",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            # Slightly longer timeout for external cloud API
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"API Error ({response.status_code}): {response.text}\n\n" + self.fallback_insight(metrics)
        except requests.exceptions.RequestException:
            # Graceful Fallback if OpenRouter is unreachable
            return self.fallback_insight(metrics)

    def fallback_insight(self, metrics):
        """Rule-based pseudo-SLM fallback if local LLM is offline."""
        insight = "Coach's Diagnosis:\n"
        if metrics['fatigue_trend'] == "Degrading":
            insight += "Your session shows a performance drop-off towards the end, indicating rapid physical fatigue or a loss of visual focus.\n\n"
        else:
            insight += "Your endurance is stable, but there is room for improvement in overall precision.\n\n"
            
        if metrics['dominant_flaw_zone'] != "Inconsistent":
            insight += f"The Core Issue: Your primary error bias is {metrics['dominant_flaw_zone']}.\n\n"
        else:
            insight += "The Core Issue: Your shots are widely dispersed without a clear directional bias, indicating fundamental instability.\n\n"
            
        insight += "Immediate Correction: Rest your eyes between shots. Focus heavily on maintaining a level rifle axis to stabilize your groupings."
        return insight
