# AimGuruu — Complete Data Flow

*(Part of the documentation set indexed in **[`ARCHITECTURE.md`](./ARCHITECTURE.md)**. Assumes familiarity with **[`HLD.md`](./HLD.md)**'s component diagram and concurrency model, and **[`LLD.md`](./LLD.md)**'s per-module detail.)*

Three sequence diagrams cover every corner of the runtime behavior — a fourth generic "data flow diagram" would only restate `HLD.md` §2's component diagram, so it's deliberately omitted.

## 1. Flow A — Camera frame → aim coordinate

```mermaid
sequenceDiagram
    participant Cam as Camera (cv2.VideoCapture)
    participant Main as Main Thread (update_loop)
    participant Trk as ArucoTracker
    participant UI as Tkinter Canvas

    Main->>Cam: cap.read() [blocking I/O]
    Cam-->>Main: frame (BGR ndarray)
    Main->>Trk: process_frame(frame)
    Trk->>Trk: grayscale + CLAHE
    Trk->>Trk: detectMarkers (ArUco, DICT_4X4_50)
    alt >=1 marker matched to known board corners
        Trk->>Trk: findHomography(RANSAC) -> H, reset age=0
    else 0 markers matched OR homography solve fails
        Trk->>Trk: homography_age += 1
        alt age <= 5 (MAX_HOMOGRAPHY_AGE)
            Trk->>Trk: reuse cached H, quality decays
        else
            Trk-->>Main: aim_mm = None
        end
    end
    Trk->>Trk: perspectiveTransform(image_center, H) -> board_pt
    Trk-->>Main: TrackFrame{aim_mm, quality, frame_display}
    Main->>Main: calibrated_aim = raw_aim_mm - zero_offset_mm
    Main->>UI: render camera feed (CTkImage)
```

Full algorithm detail (CLAHE, subpixel refinement, the "one marker is enough" homography subtlety) is in `LLD.md` §1.

## 2. Flow B — Dry-fire click → recorded shot → disk → UI update

```mermaid
sequenceDiagram
    participant Mic as Microphone
    participant AT as Audio Thread (_audio_callback)
    participant Q as shot_queue (queue.Queue)
    participant Main as Main Thread (update_loop)
    participant Sess as Session
    participant Disk as history/*.csv + *.json
    participant UI as Tkinter Canvas

    Mic->>AT: raw audio chunk (~11.6ms)
    AT->>AT: RMS + peak vs 60th-pct rolling baseline
    alt peak/baseline >= transient_ratio AND peak >= threshold AND cooldown elapsed
        AT->>Q: shot_queue.put(timestamp)  [HANDOFF 1]
    end
    Note over Main: next 15ms tick — independent of exact click instant
    Main->>Q: shot_queue.get_nowait()  [HANDOFF 2, polled]
    Q-->>Main: timestamp
    Note over Main: uses whatever calibrated_aim is CURRENT now,<br/>not the aim at the exact click instant
    alt camera connected (calibrated_aim is not None)
        Main->>Sess: record_shot(calibrated_aim)
        Sess->>Sess: score = f(radius_mm) [99-band formula]
        Sess->>Disk: CSV append [WAL-safe, durable before return]
        Sess-->>Main: Shot DTO
        Main->>Disk: export_summary_json() [full rewrite, NOT WAL-safe]
        Main->>UI: update score label + render bullet hole
    else camera disconnected
        Note over Main: shot silently dropped — no record, no retry, no warning
    end
```

This is the diagram to sketch if an interviewer asks "walk me through what happens between the trigger click and the bullet hole appearing on screen" — see `INTERVIEW_PREP.md`. Handoff mechanics are detailed in `HLD.md` §4; scoring and persistence detail is in `LLD.md` §3.

## 3. Flow C — "Generate AI Coach Report" click → OpenRouter → fallback

*(Note: this is triggered by a button click, not by "session end" — `export_summary_json()` already runs after every shot, so the JSON `InsightGenerator` reads may reflect a session still in progress.)*

```mermaid
sequenceDiagram
    participant User
    participant Main as Main Thread
    participant Worker as daemon Thread (per click)
    participant Insight as InsightGenerator
    participant Disk as history/*.json
    participant API as OpenRouter API

    User->>Main: click "Generate AI Coach Report"
    Main->>Worker: threading.Thread(daemon=True).start()  [HANDOFF 3]
    Worker->>Insight: generate_coach_report()
    Insight->>Disk: glob history/*.json, pick max(mtime)
    Disk-->>Insight: latest session JSON
    Insight->>Insight: analyze_scatt_json(): CoM, fatigue trend, flaw zone
    alt OPENROUTER_API_KEY set
        Insight->>API: POST /chat/completions [timeout=5.0s]
        alt 200 OK
            API-->>Insight: LLM-generated coaching text
        else timeout / non-200 / network error
            Insight->>Insight: fallback_insight(metrics) [same computed metrics]
        end
    else no API key present
        Insight->>Insight: fallback_insight(metrics)
    end
    Insight-->>Worker: report text
    Worker->>Main: self.after(0, update_textbox, report)  [HANDOFF 4, pushed]
    Main->>User: display report in textbox
```

Coaching-engine detail (the metrics computed, the classifier gap, the fallback guarantee) is in `LLD.md` §5.
