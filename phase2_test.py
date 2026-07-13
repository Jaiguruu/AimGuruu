"""
phase2_test.py

This script simulates a short shooting session to test our Session class.
We will feed it 3 fake coordinates to see how it calculates the math, 
scores the shots, and saves them to disk.
"""

from core.session import Session

def main():
    print("--- Starting Simulated Shooting Session ---\n")
    
    # Initialize the session
    session = Session(name="Test_Session_001")
    
    # Shot 1: Perfect Dead Center (0, 0)
    print("Simulating Shot 1: Perfect Center (0, 0)")
    shot1 = session.record_shot(aim_mm=(0.0, 0.0))
    print(f"Result -> Score: {shot1.score}, Distance from center: {shot1.radius_mm}mm\n")

    # Shot 2: Slightly off to the right and down (5mm right, 5mm down)
    print("Simulating Shot 2: Slightly off (5.0, -5.0)")
    shot2 = session.record_shot(aim_mm=(5.0, -5.0))
    print(f"Result -> Score: {shot2.score}, Distance from center: {shot2.radius_mm:.2f}mm\n")

    # Shot 3: Very bad shot, way outside the bullseye (20mm left, 10mm up)
    print("Simulating Shot 3: Very bad shot (-20.0, 10.0)")
    shot3 = session.record_shot(aim_mm=(-20.0, 10.0))
    print(f"Result -> Score: {shot3.score}, Distance from center: {shot3.radius_mm:.2f}mm\n")

    # End the session and export the JSON for the SLM Insight engine
    print("--- Session Complete ---")
    print(f"Total Score: {session.total_score}")
    print(f"Average Score: {session.average_score}")
    print(f"Group Size (Extreme Spread): {session.group_size_mm}mm")
    
    session.export_summary_json()
    print(f"\nAll data has been saved to '{session.filepath}' and its corresponding .json file!")

if __name__ == "__main__":
    main()
