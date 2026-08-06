# AimGuruu — Low-Level Design

*(Part of the documentation set indexed in **[`ARCHITECTURE.md`](./ARCHITECTURE.md)**. For the system-level view these modules compose into, see **[`HLD.md`](./HLD.md)**; for how they interact at runtime, see **[`DATA_FLOW.md`](./DATA_FLOW.md)**.)*

Each module below follows the same template: **Responsibility → Inputs/Outputs → Core algorithm (with *why*) → State & lifecycle → Failure modes → Performance → Thread-safety contract.**

## 1. `core/tracker.py` — `ArucoTracker`

**Responsibility.** Convert a raw camera frame into a real-world millimetre offset of the rifle's aim point from the target's true center.

**I/O.** In: a BGR `numpy.ndarray` frame. Out: a `TrackFrame` dataclass — `aim_mm`, `aim_px`, `markers_found`, `frame_display` (annotated copy for the UI), `homography`, `quality` (0.0–1.0).

**Core algorithm.**
1. Convert to grayscale, then apply **CLAHE** (`clipLimit=4.0`, `tileGridSize=(8,8)`) — indoor lighting is uneven, and CLAHE normalizes local contrast so the black/white ArUco pattern stays detectable without needing bright, even lighting. Cost is negligible (~2ms per frame).
2. Detect markers from the `DICT_4X4_50` dictionary with `CORNER_REFINE_SUBPIX` enabled — subpixel refinement analyzes image gradients around each corner to locate it to a fraction of a pixel, which is what makes millimetre-level accuracy possible at all; integer-pixel corners alone would be far too coarse.
3. Match any detected marker IDs (0=TL, 1=TR, 2=BR, 3=BL of a printed A4 sheet) against hardcoded real-world millimetre corner positions, then compute a **homography matrix** via `cv2.findHomography(..., cv2.RANSAC, 5.0)`. RANSAC discards outlier corner detections (e.g., a partially-occluded marker) rather than letting one bad corner wreck the whole transform.
4. `cv2.perspectiveTransform` warps the camera image's exact center pixel through that matrix, yielding where that pixel actually lands on the physical target sheet, in millimetres. Subtract the sheet's known center to get `aim_mm`.

**A subtlety worth stating precisely:** the bail-out condition in code is "zero *markers* matched" (`len(img_pts) < 1`), not "fewer than 4 points." A homography needs ≥4 point correspondences, but each single marker contributes all 4 of its corners — so **one fully-visible marker alone is mathematically sufficient** to solve a homography. This is a real, non-obvious property of the design, not just a threshold picked by feel.

**State & lifecycle.** `_last_homography` and `_homography_age` persist across frames. If zero markers are matched (occlusion, motion blur, hand in frame), the tracker reuses the cached homography for up to `MAX_HOMOGRAPHY_AGE = 5` frames, with `quality` decaying (`max(0.1, 0.5 - age*0.1)`) each frame it's stale. This trades a few frames of slightly-wrong aim position for avoiding a visible freeze/stutter every time a marker is briefly occluded — see `ARCHITECTURE.md` ADR-005.

**Failure modes.** Beyond 5 stale frames with no re-detection, `aim_mm` becomes `None` and the UI simply shows no crosshair — there's no "target lost" message to the user distinguishing "camera unplugged" from "markers occluded too long."

**Performance.** O(1) per frame relative to image size for the marker-matching/homography math; the dominant cost is OpenCV's marker detection itself, plus the ~2ms CLAHE pass. Runs entirely on the Tkinter main thread (see `HLD.md` §4) — there is no dedicated CV thread.

**Thread-safety contract.** Not thread-safe by design, and doesn't need to be — it's only ever called from the main thread's `update_loop`.

## 2. `core/audio.py` — `AudioDetector`

**Responsibility.** Detect the acoustic "click" of a dry-fire trigger break without a real gunshot, while ignoring speech, footsteps, and HVAC noise — without ever blocking or being blocked by the video pipeline.

**I/O.** In: a continuous microphone stream via `sounddevice.InputStream`. Out: calls `on_shot(timestamp)` exactly once per detected shot (subject to cooldown).

**Core algorithm — why not a volume threshold.** A naive "if volume > X, it's a shot" approach was explicitly rejected (per the code's own architectural comment) because it falsely triggers on any generally loud sound (talking, a passing car). Instead:
1. Each ~11.6ms audio chunk (`chunk_size=512` samples @ `sample_rate=44100`) yields an RMS (average loudness) and a peak (loudest single sample).
2. RMS values are pushed into a rolling `deque` of the last 40 chunks (≈0.5s of audio). The **60th percentile** of that window — not the mean — is used as the ambient baseline. Percentile-based baselining is deliberately robust to a single loud outlier briefly appearing in the window; a mean would drag the baseline up and make the detector temporarily less sensitive right after any loud noise.
3. `ratio = peak / baseline`. A shot fires only if **both** `peak >= threshold` (an absolute floor) **and** `ratio >= transient_ratio` (a sharp *relative* spike) — the AND of both conditions is what distinguishes "sharp percussive click" from "someone is talking loudly."
4. A `cooldown_ms` window (default 800ms) suppresses re-triggering, because a real trigger mechanism's spring can produce a secondary mechanical vibration that would otherwise register as a second shot.

**Runtime values actually used differ from the class defaults** — see the ground-truth table in `ARCHITECTURE.md` §5 (Appendix); `ui_main.py` overrides `threshold` and `transient_ratio` but not `cooldown_ms`, `sample_rate`, or `chunk_size`.

**State & lifecycle.** `_baseline_buf` (deque), `_last_trigger_time`, and the `_paused`/`_lock` pair persist for the life of the `AudioDetector` instance, which is created once at app startup and lives until `stop()` is called on window close.

**Failure modes.** If `sounddevice` isn't installed, `start()` prints an error and silently does nothing further — the app keeps running with no audio detection and no visible warning in the UI itself, only a console `print()`. If the input stream throws during `start()` (e.g., no microphone present), the same silent-degradation pattern applies.

**Performance.** `_audio_callback` must be fast because it runs on PortAudio's real-time audio thread; the work per call is O(1) (a percentile over a fixed 40-element window, a few comparisons) — no per-call allocation of note beyond the numpy cast.

**Thread-safety contract.** `_audio_callback` runs entirely on the PortAudio callback thread (`HLD.md` §4, Thread 2) and never touches Tkinter state — it only ever writes to instance attributes read elsewhere for UI monitoring (`current_level`, `current_peak`, `current_baseline`, currently unused by the UI) and calls `on_shot`, which does nothing but `queue.put()`. The `_lock` guards only the `_paused` flag, the one piece of state the main thread is allowed to mutate via `pause()`.

## 3. `core/session.py` — `Session` & `Shot`

**Responsibility.** Score each shot, hold the session's shot history in memory, and persist it to disk immediately and durably enough that a crash mid-session loses nothing already fired.

**I/O.** In: `record_shot(aim_mm)`. Out: a `Shot` dataclass (`index`, `timestamp`, `aim_mm`, `score`, computed `radius_mm` via Pythagorean distance) plus two files per session under `history/`.

**Core algorithm — scoring.** The scoring radius (`22.75mm` default) is divided into 99 equal-width bands (`band_w = 22.75/99 ≈ 0.2298mm`). A shot's score is `round(10.9 - band_n * (9.9/98), 1)`, where `band_n = min(int(radius/band_w), 98)` — i.e., a linear decimal scoring scale from 10.9 (dead center) down to roughly 1.0 at the outer edge of the scoring rings, matching ISSF-style decimal scoring rather than integer ring scoring. Anything beyond the scoring radius scores exactly `0.0`.

**Core algorithm — Extreme Spread.** `group_size_mm` is the maximum pairwise Euclidean distance across *all* recorded shots, computed with a **double nested loop — O(n²)**. This is a genuine, known complexity tradeoff (see `ARCHITECTURE.md` §2, row 3), not an oversight: at realistic session sizes (tens of shots) it's imperceptible, and it's simpler and more obviously correct than a convex-hull-based approach.

**Persistence — Write-Ahead Logging.** The CSV file is opened and header-written once in `__init__`, then opened in append mode and immediately flushed on every single `record_shot()` call — this is genuinely WAL-style: each shot is durable on disk before the function returns, independent of anything else happening in the app. `export_summary_json()`, by contrast, is a **full file rewrite** every time it's called (which happens after *every* shot, not just at session end — see the correction in `DATA_FLOW.md`, Flow B) — this file is *not* crash-safe in the same sense: if the process dies mid-write, the JSON can be left truncated or reflect a slightly stale shot count, even though the CSV for the same session is always fully correct up to the last completed shot.

**Failure modes.** No exception handling around any file I/O — if the `history/` directory becomes unwritable mid-session (disk full, permissions), `record_shot()` will raise and the shot's score is lost from persistence even though it may still show on-screen.

**Performance.** `record_shot` is O(1) amortized (one score calc, one disk append). `group_size_mm` is O(n²) per *call*, and it's called after every shot to refresh the scoreboard — meaning total work across an n-shot session is O(n³) in the worst case (recomputed from scratch each time). Fine at real session sizes; the tradeoffs table flags where it would stop being fine.

**Thread-safety contract.** `Session` is only ever touched from the main thread — no locks, none needed under current usage.

## 4. `core/target.py` — `TargetRenderer`

**Responsibility.** Draw the ISSF-style target face, the live crosshair, all recorded shot holes, and a fading color-coded trajectory trace, at up to ~66Hz, without redrawing static geometry every frame.

**Core algorithm — static/dynamic layer caching.** The ten concentric rings (real ISSF 10m air-rifle radii, rings 4–9 painted black per spec) are rendered exactly once into `_static_bg` at construction time. Every `render()` call copies that cached background and composites the live crosshair, shot holes, and trace polyline on top — avoiding the cost of redrawing static geometry 60+ times per second.

**Core algorithm — trace coloring.** Each point in `trace_history` is colored by its age relative to *now*, not by any absolute timestamp: `>3.0s` → dropped, `>1.0s` → green (approach), `>0.2s` → yellow (hold), `≤0.2s` → red (trigger break) — reproducing SCATT's standard visual convention for stability analysis (see `PITCH.md` §4, which independently confirms this against SCATT's own documentation). `trace_history` is a `deque(maxlen=200)` filled once per 15ms tick, so 200 entries ≈ 3 seconds of history, matching the 3.0s fade cutoff by construction.

**Failure modes.** None of note — pure rendering, no I/O, no external state beyond what's passed in.

**Performance.** O(rings) once at construction; O(trace points + shots) per frame thereafter, all cheap OpenCV primitive draws.

**Thread-safety contract.** Called only from the main thread; stateless per call aside from the pre-rendered background.

## 5. `core/insight.py` — `analyze_scatt_json()` and `InsightGenerator`

**Responsibility.** Turn raw shot coordinates into a human-readable coaching insight — worthless without this layer, since "x = -4.5, y = 2.1" means nothing to a shooter.

These are two genuinely separable concerns living in one file:

**`analyze_scatt_json(session_data)` — pure function, no I/O.**
- **Center of Mass:** mean of all `x` and `y` — where the group is centered, independent of score.
- **Fatigue trend:** splits shots at the midpoint index; compares the average score of the first half vs. second half; `"Degrading"` if the second half is worse, else `"Improving/Stable"`.
- **Dominant flaw zone:** for shots scoring `< 8.0` only, classifies by position into one of four labeled biases (`Left → Canting/Eye strain`, `Top-Right → Heeling/Anticipation`, `High → Breathing control error`, `Low → Jerking trigger`), then takes the most frequent label.

  **A real gap worth knowing before an interview asks about it:** the four conditions checked (`x<-5 and |y|<5`; `x>5 and y>5`; `y>5`; `y<-5`) don't partition the plane. A bad shot at, say, `x=6, y=2` matches none of them — it still counts toward `total_shots` and drags down `average_score`, but contributes *no vote* to the bias classification, silently. It isn't caught by the `else: "Inconsistent"` path either, because that path only triggers when the `biases` list is empty overall, not per-shot. This is a real, fixable classifier gap, not a design decision — good to name as exactly that if asked.

**`InsightGenerator` — the I/O and orchestration layer.**
- Finds the most recently modified `*.json` in `history/` (`max(json_files, key=os.path.getmtime)`) — note this means "AI Coach Report" always reflects whatever session file was touched most recently, which is the current session mid-run in practice, not necessarily a "completed" session (see the correction in `DATA_FLOW.md`, Flow C).
- Builds a single fixed prompt template embedding the computed metrics, and calls OpenRouter's chat-completions endpoint with a free-tier model, `timeout=5.0` seconds.
- **Graceful degradation is unconditional and total:** missing API key, non-200 response, or any `requests.exceptions.RequestException` (timeout, DNS failure, connection refused) all route to `fallback_insight(metrics)` — a fully deterministic, rule-based text generator using the *exact same computed metrics* the LLM prompt would have used. The user never sees an error state with no content; the app always produces *some* coaching text.

**Thread-safety contract.** `generate_coach_report()` is a blocking call (disk I/O + up to 5s of network I/O) — `ui_main.py` never calls it directly on the main thread; it's always dispatched to the ephemeral daemon thread described in `HLD.md` §4, Thread 3.

## 6. `ui_main.py` — `AimGuruuApp` (orchestration)

**Responsibility.** Own the UI widgets and be the single place every other module's output converges, once per 15ms tick.

**The `update_loop()` heartbeat, in order, every tick:**
1. If a camera is connected: `cap.read()` (blocking I/O) → `tracker.process_frame()` (CPU-bound, on this same thread) → convert BGR→RGB→`CTkImage` → render camera panel.
2. Apply the calibration offset: `calibrated_aim = raw_aim_mm - zero_offset_mm`, where `zero_offset_mm` was captured once, whenever the user last clicked "Calibrate Zero Offset" (it simply stores whatever `latest_aim_mm` was at that instant as the new zero point — correcting for the camera being mounted slightly off from the barrel's true point of aim).
3. Append `calibrated_aim` to `trace_history` (only if a camera is connected and an aim point exists).
4. Non-blocking drain of `shot_queue`; if a timestamp was waiting **and** `calibrated_aim` is currently available, record the shot, update the scoreboard, and export the JSON summary.
5. Re-render the target canvas via `TargetRenderer.render(...)`.
6. Reschedule itself: `self.after(15, self.update_loop)`.

The full, step-by-step version of this loop as the *user* experiences it — not just what the code does — is in `USER_WORKFLOW.md`.

**A real edge case worth knowing:** if a shot is detected (step 4) while **no camera is connected** — `calibrated_aim` is `None` — the shot timestamp is still dequeued (consumed), but `record_shot()` is never called. **The shot is silently lost**, with no retry, no queued pending-shot state, and no user-facing warning. This is a genuine gap, not a documented design decision.

**Another real edge case:** `on_closing()` calls `self.audio_detector.stop()` then unconditionally `if self.cap.isOpened(): ...` — if the user closes the app without ever clicking "Connect Camera," `self.cap` is still `None`, and `None.isOpened()` raises `AttributeError`. A latent crash-on-clean-exit bug for a specific, plausible user path.
