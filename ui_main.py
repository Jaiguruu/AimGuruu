"""
ui_main.py

ARCHITECTURAL DECISION (Main UI Loop & Threading):
This is the heart of the application. The primary challenge of building a UI for computer vision
and audio processing is keeping the app responsive (Doherty Threshold: <400ms).

1. CustomTkinter provides the Main Loop (`app.mainloop()`).
2. We use `app.after(15, self.update_loop)` to schedule a non-blocking update every 15ms (~60fps).
3. Inside `update_loop`, we:
   a) Grab the latest frame from the Camera (Phase 1).
   b) Check the thread-safe Queue to see if the Audio thread (Phase 3) heard a shot.
   c) If a shot was heard, we record it using Session (Phase 2).
   d) Render the updated Target (core/target.py).

UX DESIGN DECISIONS (Laws of UX):
- Aesthetic-Usability Effect: Dark mode, minimalistic UI.
- Law of Proximity: Grouped the Camera Feed (left) and Target/Scoreboard (right).
- Hick's Law: Removed all unnecessary menus. Just a big "Calibrate Center" button.
"""

import cv2
import queue
import time
import threading
from collections import deque
from PIL import Image
import customtkinter as ctk

from core.tracker import ArucoTracker
from core.session import Session
from core.audio import AudioDetector
from core.target import TargetRenderer
from core.insight import InsightGenerator

# --- App Settings ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AimGuruuApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AimGuruu - Professional Training")
        self.geometry("1100x600")
        
        # --- UI Layout (Law of Common Region) ---
        
        # Left Panel (Camera & CV)
        self.left_frame = ctk.CTkFrame(self, width=500)
        self.left_frame.pack(side="left", fill="y", padx=20, pady=20)
        
        # Camera Input (For DroidCam, Webcams, or Mobile IP)
        self.cam_mode_var = ctk.StringVar(value="0 (Default Webcam)")
        self.cam_dropdown = ctk.CTkOptionMenu(
            self.left_frame, 
            values=["0 (Default Webcam)", "1 (DroidCam / External 1)", "2 (DroidCam / External 2)", "Custom IP URL"],
            variable=self.cam_mode_var,
            command=self._on_cam_mode_change
        )
        self.cam_dropdown.pack(pady=5, fill="x", padx=20)
        
        self.cam_entry = ctk.CTkEntry(self.left_frame, placeholder_text="Enter IP (http://.../video)")
        # We don't pack cam_entry yet, it only shows if "Custom IP URL" is selected
        
        self.connect_btn = ctk.CTkButton(
            self.left_frame, 
            text="Connect Camera", 
            command=self.connect_camera
        )
        self.connect_btn.pack(pady=5, fill="x", padx=20)
        
        self.camera_label = ctk.CTkLabel(self.left_frame, text="Camera Disconnected.")
        self.camera_label.pack(pady=10)
        
        # Camera Resize Slider
        self.cam_scale = 1.0
        self.cam_size_slider = ctk.CTkSlider(self.left_frame, from_=0.5, to=2.0, command=self._on_cam_size_change)
        self.cam_size_slider.set(1.0)
        self.cam_size_slider.pack(pady=5, fill="x", padx=20)
        
        # Big Calibrate Button (Fitts's Law - easy to hit)
        self.calibrate_btn = ctk.CTkButton(
            self.left_frame, 
            text="Calibrate Zero Offset", 
            command=self.calibrate_zero,
            height=50,
            font=("Segoe UI", 16, "bold")
        )
        self.calibrate_btn.pack(pady=10, fill="x", padx=20)
        
        # Right Panel (Target & Scoreboard)
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(0, 20), pady=20)
        
        # Score Header
        self.score_lbl = ctk.CTkLabel(self.right_frame, text="Total Score: 0.0 | Group: 0.00mm", font=("Segoe UI", 24, "bold"))
        self.score_lbl.pack(pady=10)
        
        # Target Canvas
        self.target_label = ctk.CTkLabel(self.right_frame, text="")
        self.target_label.pack(expand=True)
        
        # AI Coach Panel
        self.ai_btn = ctk.CTkButton(
            self.right_frame, 
            text="Generate AI Coach Report (SLM)", 
            command=self.generate_ai_report,
            fg_color="#8a2be2",
            hover_color="#5a189a"
        )
        self.ai_btn.pack(pady=10)
        
        self.ai_textbox = ctk.CTkTextbox(self.right_frame, height=120, font=("Segoe UI", 14))
        self.ai_textbox.pack(pady=5, fill="x", padx=20)
        self.ai_textbox.insert("1.0", "AI Coach is ready. Shoot a session, then request a report.")
        self.ai_textbox.configure(state="disabled")
        
        # --- Initialize Core Engines ---
        
        # 1. Vision Engine (Camera is started via UI button)
        self.cap = None
        self.tracker = ArucoTracker()
        self.target_renderer = TargetRenderer(size=450)
        self.insight_engine = InsightGenerator()
        
        # 2. Scoring Engine
        self.session = Session(name="AimGuruu_Session")
        
        # 3. Audio Engine (with thread-safe queue)
        self.shot_queue = queue.Queue()
        self.audio_detector = AudioDetector(
            threshold=0.10,
            transient_ratio=4.0,
            on_shot=self._on_shot_heard
        )
        self.audio_detector.start()
        
        # State
        self.latest_aim_mm = None
        self.zero_offset_mm = (0.0, 0.0) # Used to calibrate the rifle sights to the camera
        self.trace_history = deque(maxlen=200) # Holds 3 seconds of aiming history for SCATT traces
        
        # Start the 60fps loop
        self.update_loop()

    def _on_shot_heard(self, timestamp: float):
        """Called by the background AUDIO thread. We must NOT update the UI here."""
        # Put the event in a queue so the main thread can handle it safely.
        self.shot_queue.put(timestamp)

    def _on_cam_mode_change(self, choice):
        """Show or hide the IP text entry based on the dropdown choice (Law of Prägnanz - keep UI simple)."""
        if choice == "Custom IP URL":
            self.cam_entry.pack(pady=5, fill="x", padx=20)
        else:
            self.cam_entry.pack_forget()

    def connect_camera(self):
        """Connects to a native webcam (0, 1, 2) or a Mobile IP Camera via URL."""
        choice = self.cam_mode_var.get()
        if choice == "Custom IP URL":
            source = self.cam_entry.get().strip()
        else:
            # Parse the integer from the dropdown (e.g. "1 (DroidCam...)" -> 1)
            source = int(choice.split(" ")[0])
            
        print(f"Attempting to connect to camera: {source}")
        
        if self.cap and self.cap.isOpened():
            self.cap.release()
            
        self.cap = cv2.VideoCapture(source)
        if self.cap.isOpened():
            self.camera_label.configure(text="")
            print("Camera connected successfully!")
        else:
            self.camera_label.configure(text="Failed to connect to camera.")
            print("Failed to connect.")

    def generate_ai_report(self):
        """Fetches the AI Coach report without blocking the UI thread."""
        self.ai_btn.configure(text="Generating...", state="disabled")
        self.ai_textbox.configure(state="normal")
        self.ai_textbox.delete("1.0", "end")
        self.ai_textbox.insert("1.0", "Analyzing biomechanics...\n")
        self.ai_textbox.configure(state="disabled")
        
        # Run in a daemon thread to prevent UI freezing (Doherty Threshold)
        threading.Thread(target=self._fetch_ai_report, daemon=True).start()

    def _fetch_ai_report(self):
        report = self.insight_engine.generate_coach_report()
        
        # Update UI back on the main thread safely
        self.after(0, self._update_ai_textbox, report)
        
    def _update_ai_textbox(self, report):
        self.ai_textbox.configure(state="normal")
        self.ai_textbox.delete("1.0", "end")
        self.ai_textbox.insert("1.0", report)
        self.ai_textbox.configure(state="disabled")
        self.ai_btn.configure(text="Generate AI Coach Report (SLM)", state="normal")

    def _on_cam_size_change(self, value):
        """Allows user to scale the camera feed up or down."""
        self.cam_scale = float(value)

    def calibrate_zero(self):
        """
        When the user clicks 'Calibrate', we take their current aim_mm and set it as the zero point.
        This fixes the offset between where the camera is mounted and where the barrel is pointing.
        """
        if self.latest_aim_mm:
            self.zero_offset_mm = self.latest_aim_mm
            print(f"Zero Calibrated! Offset is now {self.zero_offset_mm}mm")

    def get_calibrated_aim(self, raw_aim_mm):
        """Subtracts the zero offset from the raw camera aim."""
        if not raw_aim_mm: return None
        return (
            raw_aim_mm[0] - self.zero_offset_mm[0],
            raw_aim_mm[1] - self.zero_offset_mm[1]
        )

    def update_loop(self):
        """The heartbeat of the application. Runs every 15ms (Doherty Threshold)."""
        
        # 1. Process Vision (only if camera is connected)
        calibrated_aim = None
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                tf = self.tracker.process_frame(frame)
                if tf is not None:
                    self.latest_aim_mm = tf.aim_mm
                    
                    # Convert OpenCV frame (BGR) to CustomTkinter Image (RGB)
                    rgb_frame = cv2.cvtColor(tf.frame_display, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb_frame)
                    
                    # Apply dynamic resizing based on slider
                    base_w, base_h = 450, 337
                    new_w = int(base_w * self.cam_scale)
                    new_h = int(base_h * self.cam_scale)
                    
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
                    self.camera_label.configure(image=ctk_img, text="")
            
            calibrated_aim = self.get_calibrated_aim(self.latest_aim_mm)
            if calibrated_aim:
                self.trace_history.append((time.time(), calibrated_aim[0], calibrated_aim[1]))
        
        # 2. Check Audio Queue for Shots
        try:
            # Non-blocking get. If empty, raises queue.Empty
            shot_timestamp = self.shot_queue.get_nowait()
            
            # A shot was heard! Record it at the current calibrated aim.
            if calibrated_aim:
                shot = self.session.record_shot(calibrated_aim)
                print(f"Registered Shot {shot.index}: Score {shot.score}")
                
                # Update Scoreboard (Peak-End Rule: emphasize the score)
                self.score_lbl.configure(text=f"Total: {self.session.total_score} | Avg: {self.session.average_score} | Grp: {self.session.group_size_mm}mm")
                
                # Export JSON immediately for SLM analytics
                self.session.export_summary_json()
        except queue.Empty:
            pass
            
        # 3. Render Target (with live crosshair, past shots, and TRACE HISTORY)
        target_img_bgr = self.target_renderer.render(
            live_aim_mm=calibrated_aim, 
            shots=self.session.shots,
            trace_history=list(self.trace_history)
        )
        target_img_rgb = cv2.cvtColor(target_img_bgr, cv2.COLOR_BGR2RGB)
        target_pil = Image.fromarray(target_img_rgb)
        target_ctk = ctk.CTkImage(light_image=target_pil, dark_image=target_pil, size=(450, 450))
        self.target_label.configure(image=target_ctk)
        
        # Schedule the next loop iteration in 15ms
        self.after(15, self.update_loop)

    def on_closing(self):
        """Clean up threads when window closes."""
        print("Shutting down...")
        self.audio_detector.stop()
        if self.cap.isOpened():
            self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = AimGuruuApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
