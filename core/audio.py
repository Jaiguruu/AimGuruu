"""
core/audio.py

ARCHITECTURAL DECISION (Multithreading & Audio Processing):
A critical problem in building a virtual shooting range is detecting the 'click' of the dry-fire
without causing the Computer Vision loop to stutter. 

If we process audio in the main thread, the camera feed will lag. 
To solve this, I designed the AudioDetector to run in a completely separate daemon thread 
using the 'sounddevice' library. 

MATHEMATICAL DECISION (Transient Detection vs Volume Threshold):
At first, I tried a simple volume threshold (if volume > X, register a shot). 
This failed terribly. If someone talked or a car drove by, it triggered a false shot.
To fix this, I implemented a 'Transient Detection' algorithm:
1. It constantly calculates the ambient room volume using a rolling baseline RMS (Root Mean Square).
2. It looks for a 'transient ratio' spike—meaning the sound must be a sharp, percussive click 
   that is N times louder than the baseline, rather than just a generally loud noise.
3. This perfectly isolates the sharp 'snap' of a dry-fire while ignoring background talking or AC noise.
"""

import threading
import time
import collections
import numpy as np
from typing import Callable, Optional, Deque

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False


class AudioDetector:
    """
    Runs in a background thread continuously sampling the microphone.
    """

    def __init__(
        self,
        threshold: float = 0.15,          # Absolute minimum volume floor
        transient_ratio: float = 6.0,     # The peak must be 6x louder than ambient noise
        cooldown_ms: int = 800,           # Prevent double-fires (mechanical echo)
        sample_rate: int = 44100,         # Standard audio sampling rate
        chunk_size: int = 512,            # Process audio in ~12ms chunks for ultra-low latency
        device_index: Optional[int] = None,
        on_shot: Optional[Callable] = None, # The callback function to trigger when a shot is heard
    ):
        self.threshold = threshold
        self.transient_ratio = transient_ratio
        self.cooldown_s = cooldown_ms / 1000.0
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.on_shot = on_shot

        self._stream = None
        self._last_trigger_time: float = 0.0
        self._running = False
        self._paused = False
        
        # Thread safety lock so the main CV thread can pause/resume audio without crashing
        self._lock = threading.Lock()

        # Analytics for UI monitoring
        self.current_level: float = 0.0       
        self.current_peak: float = 0.0        
        self.current_baseline: float = 0.0    
        
        # We use a deque (double-ended queue) to maintain a rolling window of the last 40 chunks (~0.5 seconds)
        self._baseline_buf: Deque[float] = collections.deque([0.001] * 40, maxlen=40)

    def start(self):
        """Spawns the background audio processing stream."""
        if not SD_AVAILABLE:
            print("[ERROR] 'sounddevice' library not available. Please install it.")
            return
        if self._running:
            return
            
        self._running = True
        self._paused = False
        
        try:
            # This automatically spawns a C-level background thread that calls _audio_callback
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                device=self.device_index,
                channels=1,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            print(f"[ERROR] Could not start audio stream: {e}")
            self._running = False

    def stop(self):
        """Safely shuts down the audio thread."""
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def pause(self, paused: bool):
        """Thread-safe way for the main app to ignore audio (e.g., when in menus)."""
        with self._lock:
            self._paused = paused

    # ── Core Detection Logic (Runs in Background Thread) ──────────────────────────

    def _audio_callback(self, indata, frames, time_info, status):
        """
        This function is called by the sounddevice thread hundreds of times a second.
        It must be EXTREMELY fast and efficient.
        """
        # If no audio data is coming in, skip
        if not any(indata):
            return

        # Flatten the audio chunk into a 1D numpy array
        audio = indata[:, 0].astype(np.float32)

        # Calculate Root Mean Square (average volume of this chunk)
        rms = float(np.sqrt(np.mean(audio ** 2)))
        # Find the absolute loudest single sample in this chunk
        peak = float(np.max(np.abs(audio)))

        # Update our rolling baseline (the ambient noise of the room)
        self._baseline_buf.append(rms)
        # We use the 60th percentile of recent volume as our baseline. 
        # This prevents a single loud noise from permanently ruining the baseline.
        baseline = float(np.percentile(list(self._baseline_buf), 60))

        # Update stats for the UI to read
        self.current_level = rms
        self.current_peak = peak
        self.current_baseline = baseline

        # Thread-safe check if the app is paused
        with self._lock:
            paused = self._paused
        if paused:
            return

        # ── The Transient Detection Algorithm ──
        # How many times louder is this peak compared to the room baseline?
        ratio = peak / max(baseline, 1e-6)
        
        # A shot is valid if:
        # 1. It is louder than the absolute minimum threshold
        # 2. It is a sharp transient (ratio > transient_ratio)
        if peak >= self.threshold and ratio >= self.transient_ratio:
            now = time.time()
            # Enforce mechanical cooldown to prevent double-fires from the gun's spring vibrating
            if now - self._last_trigger_time >= self.cooldown_s:
                self._last_trigger_time = now
                
                # Fire the callback function back to the main thread!
                if self.on_shot:
                    try:
                        self.on_shot(now)
                    except Exception as e:
                        print(f"[Audio] Callback execution failed: {e}")

    @staticmethod
    def list_devices():
        """Helper to let the user select their microphone."""
        if not SD_AVAILABLE:
            return []
        devs = []
        try:
            for i, d in enumerate(sd.query_devices()):
                if d["max_input_channels"] > 0:
                    devs.append((i, d["name"]))
        except Exception:
            pass
        return devs
