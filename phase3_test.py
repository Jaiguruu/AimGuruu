"""
phase3_test.py

This script tests the multithreaded audio engine.
It will listen to your microphone and print when it detects a 'dry-fire' click.
"""
import time
from core.audio import AudioDetector

def shot_fired_callback(timestamp):
    """This function is called by the background thread when a shot is heard."""
    print(f"\n[BOOM!] Shot detected at timestamp: {timestamp}")
    print("--------------------------------------------------")

def main():
    print("--- Starting Phase 3 Audio Engine Test ---")
    
    # List available microphones
    devices = AudioDetector.list_devices()
    print("Available Microphones:")
    for idx, name in devices:
        print(f"  [{idx}] {name}")
        
    print("\nStarting the background audio thread...")
    print("Snap your fingers or clap loudly to simulate a dry-fire!")
    print("Talk normally to see how the transient detector ignores your voice.")
    print("(Press Ctrl+C to stop)\n")

    # Initialize the detector
    detector = AudioDetector(
        threshold=0.10,         # Lowered slightly for clapping/snapping testing
        transient_ratio=4.0,    # Must be 4x louder than background noise
        on_shot=shot_fired_callback
    )

    try:
        # Start the background thread
        detector.start()
        
        # The main thread can just sleep or do other things!
        # This proves the multithreading works.
        while True:
            time.sleep(1.0)
            # You can uncomment this to see the raw volume data streaming from the background thread:
            # print(f"Ambient Baseline: {detector.current_baseline:.4f} | Peak: {detector.current_peak:.4f}")
            
    except KeyboardInterrupt:
        print("\nStopping audio engine...")
        detector.stop()
        print("Done.")

if __name__ == "__main__":
    main()
