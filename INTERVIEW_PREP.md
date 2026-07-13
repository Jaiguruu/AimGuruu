# AimGuruu Interview Preparation Guide

This guide is designed to help you confidently explain the engineering decisions behind AimGuruu during a technical interview. Senior engineers look for candidates who understand *why* they built something a certain way, not just *how*.

## 1. Concurrency & Threading Architecture (The Most Important Talking Point)
**The Problem:** Computer vision (OpenCV) and UI rendering (CustomTkinter) both need to run on the main thread to update quickly. However, listening to a microphone requires a continuous, unbroken stream of audio data. If you put both on the same thread, the video feed will stutter, or you will drop audio packets and miss the gunshot.

**Your Solution:** 
- You used a **Multi-Threaded Architecture with a Thread-Safe Queue**.
- You isolated the PyAudio stream into a `daemon=True` background thread.
- When the audio thread detects a transient spike (the click of the trigger), it doesn't try to update the UI directly (which causes fatal race conditions in Python). Instead, it drops a timestamp into a `queue.Queue`.
- The main UI loop checks that queue every 15ms. If it finds a timestamp, it safely pulls the current camera coordinates and records the shot.

**Buzzwords to use:** Race Conditions, Daemon Threads, Thread-Safe Queues, Asynchronous Event Handling, Doherty Threshold (<400ms UI latency).

## 2. Computer Vision & Hardware Optimization
**The Problem:** Tracking the exact center of a target while a rifle is moving is extremely difficult and mathematically intensive.

**Your Solution:**
- You used **ArUco Fiducial Markers**. Instead of trying to detect a generic circle, ArUco markers give OpenCV 4 distinct corners, allowing the math to instantly calculate both the 2D offset (X, Y) and the rotation of the camera relative to the target.
- You explicitly avoided heavy deep learning (like YOLO) for the vision engine because it would introduce latency. ArUco is purely geometric, meaning it runs with zero lag on a standard CPU.
- You understand the difference between **Global Shutter** and **Rolling Shutter**. You know that a rolling shutter warps the square marker when the rifle moves (the jello effect), which is why you recommend a Global Shutter monochrome camera (like the OV9281) for perfect edge detection.

**Buzzwords to use:** Fiducial Markers, Perspective Transform, Global Shutter vs Rolling Shutter, Geometric Tracking.

## 3. Data Integrity & State Management
**The Problem:** If the application crashes on shot #19 out of 20, the shooter loses all their session data.

**Your Solution:**
- You implemented **Write-Ahead Logging (WAL)**. Every time the trigger is pulled, the `Session` engine immediately appends the `(x, y)` coordinate to a localized CSV file and updates a JSON summary file *before* the UI even renders the bullet hole. 
- The JSON file structure (Total Shots, Avg Score, Group Size) provides a clean API boundary for future expansion (like a web dashboard).

**Buzzwords to use:** Write-Ahead Logging (WAL), API Boundaries, Data Persistence.

## 4. AI Coaching (Agentic Pipeline Architecture)
**The Problem:** Raw mathematical data (like `x = -4.5`, `y = 2.1`) is useless to a human shooter without analysis.

**Your Solution:**
- You built an **Agentic AI Pipeline**.
- First, the Python Processing Layer (`core/insight.py`) does the heavy math (calculating Center of Mass and directional bias).
- Then, the Prompt Template Engine structures this into a semantic sports context.
- Finally, it connects to a **Local Small Language Model (SLM)** via a REST API (like Ollama). 
- **Crucial Fallback Logic:** You engineered a fallback system where if the local LLM is offline or crashes, the system gracefully degrades to rule-based Python logic to provide the coaching tip anyway. 

**Buzzwords to use:** Agentic Pipeline, Context Injection, Graceful Degradation, Local Inference (SLM vs LLM), Prompt Engineering.

## 5. UI/UX Principles
**The Problem:** Most open-source trainers have highly complex, ugly interfaces with dozens of confusing buttons.

**Your Solution:**
- You designed the interface around the **Laws of UX**.
- **Aesthetic-Usability Effect:** A dark-mode, clean interface makes users perceive the application as higher quality and more stable.
- **Hick's Law:** You removed all unnecessary dropdowns and features from the main screen, leaving only the essential data and a massive "Calibrate" button to minimize cognitive load.
- **Law of Prägnanz:** You hid the complex "Custom IP Address" text box inside a simple dropdown menu, keeping the UI visually simple unless advanced features are specifically requested.

**Buzzwords to use:** Hick's Law, Cognitive Load, Aesthetic-Usability Effect, Law of Prägnanz.
