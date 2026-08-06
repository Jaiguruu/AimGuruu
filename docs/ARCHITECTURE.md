# AimGuruu — Architecture Reference (Index)

**Status:** living technical reference · **Scope:** the codebase as it exists today (`ui_main.py` + `core/*.py`).

## 1. Purpose & Documentation Index

This is the entry point into AimGuruu's full documentation set. Each document below is a single source of truth for its topic — nothing is restated across files, only linked, so numbers and diagrams can't drift out of sync with each other.

| Document | Covers |
|---|---|
| **[`PROBLEM_STATEMENT.md`](./PROBLEM_STATEMENT.md)** | The problem being solved, with researched (not estimated) SCATT/SIUS pricing and real participation numbers (ISSF, CMP, NCAA). |
| **[`TARGET_PERSONAS.md`](./TARGET_PERSONAS.md)** | Who this serves today vs. what's on the roadmap — honestly split, not overclaimed. |
| **[`HLD.md`](./HLD.md)** | High-level design: system context, component diagram, deployment view, concurrency/threading model. |
| **[`LLD.md`](./LLD.md)** | Low-level design: a responsibility/algorithm/failure-mode/performance breakdown for every module. |
| **[`USER_WORKFLOW.md`](./USER_WORKFLOW.md)** | The actual end-to-end user journey — setup, connect, calibrate, practice, review — including what the user experiences when things go wrong. |
| **[`DATA_FLOW.md`](./DATA_FLOW.md)** | Three full sequence diagrams tracing every corner of the runtime behavior. |
| §2–§5 below | Architectural tradeoffs, decision records, gap analysis/roadmap, and the ground-truth numbers appendix — content that doesn't belong to any single module or diagram, so it stays here. |
| **[`INTERVIEW_PREP.md`](./INTERVIEW_PREP.md)** | Short, spoken-format cheat sheet for defending this architecture live. |
| **[`PITCH.md`](./PITCH.md)** | The enterprise/commercial case, with a detailed SCATT-vs-AimGuruu gap analysis. |
| **[`FDE_WALKTHROUGH.md`](./FDE_WALKTHROUGH.md)** | The build narrative, told through a Forward Deployed Engineer's working method. |
| **[`ALTERNATIVE_ARCHITECTURES.md`](./ALTERNATIVE_ARCHITECTURES.md)** | Full whole-system alternatives (cloud vs. local, mobile-native, event-bus, SQLite, etc.) and why each was or wasn't chosen. |

If you only read one thing before an interview, read `HLD.md` §4 (Concurrency Model) and `DATA_FLOW.md` — they're where most real interview questions land.

*(All diagrams across this documentation set are Mermaid, embedded as fenced code blocks. GitHub, GitLab, and most modern Markdown viewers render these natively; in VS Code, install the "Markdown Preview Mermaid Support" extension if your preview shows raw text instead of a diagram.)*

---

## 2. Architectural Tradeoffs

Component-level decisions already made, with the alternative that was considered and the condition under which the decision should be revisited. (For *whole-system* alternatives — cloud vs. local, event-bus vs. monolith — see `ALTERNATIVE_ARCHITECTURES.md` instead; this table is one level more granular.)

| Decision | Alternative(s) considered | Why this choice | Cost / limitation | When to revisit |
|---|---|---|---|---|
| ArUco fiducial markers + homography | Deep-learning pose estimation (e.g. YOLO-based marker/target detection) | Purely geometric — zero-lag on CPU, no GPU/model dependency, sub-pixel accurate out of the box | Requires a printed marker sheet in view at all times; can't track an unmarked/generic target | If the product needs to work without a printed target sheet at all |
| Homography reuse-with-decay on occlusion | Strict per-frame re-detection (fail if markers not visible) | Avoids visible stutter/freeze from momentary occlusion (hand, smoke, motion blur) | Up to 5 frames of slightly stale aim data during occlusion | If precision-critical scoring modes need to flag/exclude stale-homography shots |
| O(n²) Extreme Spread (`group_size_mm`) | Convex-hull-based max-distance algorithm (O(n log n)) | Simpler, obviously correct, negligible cost at real session sizes (tens of shots) | Becomes measurably slower at large n; it's also recomputed from scratch after every shot | If session sizes grow into the hundreds, or if this metric needs to run over multi-session aggregates |
| CV processing on the Tkinter main thread | Offload `process_frame` to a worker thread/process, hand results back via queue | Simpler code, no cross-thread synchronization needed for the largest chunk of per-frame work | A slow CV frame directly delays UI responsiveness and audio-queue draining in the same tick | If frame processing time ever approaches or exceeds the 15ms budget on target hardware |
| Cloud LLM (OpenRouter) + rule-based fallback | Local-only SLM (e.g. via Ollama) | No local model download/runtime dependency; free tier keeps cost at zero for a solo project | Requires network access for the "real" AI experience; free-tier model availability isn't guaranteed long-term | If offline range use becomes a requirement, or free-tier terms change |
| Dual persistence: CSV WAL (append) + JSON (full rewrite) | A single embedded database (SQLite) | No schema/migration overhead for a simple two-shape data model; CSV is trivially human-readable/exportable | Two files can fall out of sync on a crash between writes (`LLD.md` §3); no query capability across sessions | Once cross-session analytics or multi-athlete data are needed (Phase 2) |
| Hardcoded global constants (scoring radius, marker/board mm, thresholds) | A config file / settings system | Fastest to build and reason about for a single fixed target spec | Any hardware variant (different target size, different marker layout) requires a code change | Before supporting more than one target/marker configuration |
| `print()` for all diagnostics | Structured logging (`logging` module, levels, log files) | Zero setup, fine for a single-developer console workflow | No log levels, no persistence, no way to diagnose a field issue after the fact | Before any multi-user or remote-support scenario |
| Manual print-and-eyeball harnesses (`phase1/2/3_test.py`) | An automated `pytest` suite with assertions | Fast to write during initial exploratory development | No regression protection — a change can silently break scoring or detection with no test failure | Immediately, before any further feature work (this is the highest-leverage Phase 1 item) |
| `queue.Queue` + `.after()` polling for thread coordination | `asyncio` throughout | Matches Tkinter's synchronous, callback-driven model directly; no need to bridge an event loop into a GUI toolkit that doesn't natively support one | Slightly higher worst-case latency (bounded by the 15ms poll interval) than a push-based design | Unlikely to need revisiting unless the UI framework itself changes |

*(The `pyaudio`-vs-`sounddevice` mismatch between `requirements.txt` and the actual import in `core/audio.py` is deliberately **not** a row here — there's no "why this choice" behind it, it's dependency drift. It's tracked as a Phase 0 hygiene item in §4 instead.)*

---

## 3. Architectural Decision Records

Reserved for decisions with consequences that ripple across modules — everything more local stays in the tradeoffs table above.

### ADR-001: Planar ArUco fiducials + homography for aim tracking
- **Context:** Need real-time, sub-millimetre-precision tracking of a camera's aim point relative to a printed target, on commodity CPUs, with zero acceptable added latency.
- **Decision:** Use OpenCV's ArUco marker detection plus a computed homography matrix, rather than any ML-based approach.
- **Consequences:** Deterministic, explainable, fast on CPU; requires the printed marker sheet to always be in frame; accuracy depends on camera focus/resolution and marker print quality.
- **Alternatives considered:** YOLO/deep-learning-based generic target or barrel-pose detection (rejected: adds latency and a model dependency for no accuracy benefit at this task's precision requirements).

### ADR-002: `queue.Queue` as the sole synchronization primitive between the audio thread and the Tkinter loop
- **Context:** A background audio thread must hand off shot events to a single-threaded GUI toolkit without race conditions or blocking either side.
- **Decision:** The audio callback only ever calls `queue.put()`; the UI loop only ever calls `get_nowait()`. No other shared mutable state crosses this boundary.
- **Consequences:** Simple, correct, well-understood pattern; introduces a bounded latency (up to one 15ms tick) between detection and recording.
- **Alternatives considered:** Direct callback into Tkinter from the audio thread (rejected: Tkinter is not thread-safe, this would risk crashes/corruption); `asyncio` event loop (rejected: doesn't compose cleanly with Tkinter's own loop).

### ADR-003: CSV Write-Ahead-Log + periodic JSON export, deferring a real database
- **Context:** Session data must survive a crash mid-session with minimal complexity for a single-developer, single-user MVP.
- **Decision:** Append each shot to a CSV synchronously; separately maintain a JSON summary rewritten after every shot for the AI Coach to consume.
- **Consequences:** Crash-safe at the per-shot CSV level; the JSON summary is not crash-safe to the same degree (`LLD.md` §3); no cross-session querying.
- **Alternatives considered:** SQLite (rejected for MVP scope: adds schema/migration overhead not justified by a two-shape data model, given the current scope is one user, one machine — though see `ALTERNATIVE_ARCHITECTURES.md` §6 for the honest reassessment of this specific call).

### ADR-004: Cloud LLM coaching with a mandatory, metric-equivalent rule-based fallback
- **Context:** The AI Coach feature should not create a hard dependency on network availability or a specific external service's uptime.
- **Decision:** Always compute the same metrics locally first; attempt the cloud LLM call with a short (5s) timeout; on any failure, fall back to a fully deterministic text generator using those same metrics.
- **Consequences:** The user always receives a coaching report; report quality/nuance is lower in the fallback path than the LLM path, but never absent.
- **Alternatives considered:** Hard-requiring the API key and failing loudly if absent (rejected: makes the feature unusable offline or without setup); local SLM only (rejected for now: adds a runtime dependency, tracked as a Phase 3 roadmap option instead).

### ADR-005: Homography cache-with-decay on marker occlusion
- **Context:** Momentary occlusion of one or more markers (hand, smoke, fast motion) would otherwise cause visible tracking dropout every time it happens.
- **Decision:** Reuse the last known homography for up to 5 frames, with a confidence score that decays each stale frame, rather than immediately reporting "no aim point."
- **Consequences:** Smoother perceived tracking; up to 5 frames of aim data that may be slightly wrong if the camera actually moved during the occlusion.
- **Alternatives considered:** No caching (immediate `None` on any occlusion) — rejected as visibly worse UX for a cost that's usually imperceptible.

### ADR-006: Single-user, single-machine, local-storage scope is an intentional MVP boundary
- **Context:** It would be easy to read the absence of accounts, multi-user support, and cloud storage as an oversight.
- **Decision:** Explicitly scope the current build to one athlete, one machine, local storage — the Coach and Federation personas (`TARGET_PERSONAS.md`) are deferred by design, not missed by omission.
- **Consequences:** Keeps current-state claims (across this documentation set) honest and defensible; makes Phase 2/3 of the roadmap (§4 below) a planned expansion rather than a discovered gap.
- **Alternatives considered:** Building multi-user support into the MVP from the start (rejected: would have delayed validating the core tracking/scoring/coaching loop, which is the actual hard problem — see `FDE_WALKTHROUGH.md` §3 for the risk-first build order this reflects).

---

## 4. Enterprise-Grade Gap Analysis & Roadmap

| Capability Area | Current State | Enterprise Bar | Gap | Phase |
|---|---|---|---|---|
| Secrets & repo hygiene | `.gitignore` excludes only `GEMINI.md`/`INTERVIEW_PREP.md`; does **not** exclude `core/.env` (holds `OPENROUTER_API_KEY`), `__pycache__/`, or `history/*.csv` | Secrets and generated artifacts never enter version control | One `git add .` away from committing a live API key and raw session data | 0 |
| Dependency correctness | `requirements.txt` lists `pyaudio`; `core/audio.py` actually imports `sounddevice` | Declared dependencies match actual imports | A clean-checkout `pip install -r requirements.txt` won't install what the code needs | 0 |
| Configuration | Constants (scoring radius, marker/board mm, thresholds) hardcoded across multiple files | Centralized, environment-aware config | Any hardware/target variant requires a code change | 0 |
| Observability | `print()` only, no levels, no persistence | Structured logging, levels, retrievable logs | Can't diagnose an issue after the fact, especially for a non-developer end user | 0 |
| Error handling | No handling for camera disconnect mid-session, no-camera-on-close crash (`LLD.md` §6), silent shot loss when camera is down (`DATA_FLOW.md` Flow B) | Defined behavior and user-facing messaging for every real failure mode | Users see silent data loss or a crash instead of a clear message | 0–1 |
| Testing | Three manual, assertion-free, print-and-eyeball scripts (`phase1/2/3_test.py`) | Automated test suite with CI gating merges | No regression protection on scoring, tracking, or audio detection logic | 1 |
| Packaging & distribution | Run via `python ui_main.py` from source | Installer / signed executable for non-technical users | Current audience must have Python + dependencies set up manually | 1 |
| Target-sheet provisioning | No generator script in the repo; the printed ArUco sheet must be produced externally (see `USER_WORKFLOW.md` §1) | A one-click "print my target" asset shipped with the app | Real onboarding friction for any user who isn't already comfortable with `cv2.aruco` | 1 |
| Multi-user / accounts | None — one local `history/` folder, no athlete identity | Auth, per-athlete data isolation | Blocks the Coach persona entirely (`TARGET_PERSONAS.md`) | 2 |
| Data platform | Local CSV/JSON files only | Real database, cloud sync, cross-session/cross-athlete queries | Blocks aggregation, backup, and any coach/federation-level view | 2 |
| Commercial packaging | Free/local-only, no licensing or billing | Subscription tiers, hardware bundle options | No path to revenue as currently built | 3 |
| AI Coach resilience at scale | Free-tier cloud model, 5s timeout, single provider | Provider-agnostic, paid-tier or local-model option, no free-tier dependency | Free-tier availability/terms aren't a stable foundation for a commercial product | 3 |

**Phased roadmap:**
- **Phase 0 — Hygiene & Correctness** *(documented here only, not applied to the repo, per explicit decision)*: fix `.gitignore`, fix the `pyaudio`/`sounddevice` mismatch, centralize constants, add structured logging, handle the known crash/silent-loss edge cases in `LLD.md` §6 and `DATA_FLOW.md` Flow B.
- **Phase 1 — Reliability & Testability**: real `pytest` suite replacing the manual harnesses, CI, an installer/packaging story, a target-sheet generator/asset.
- **Phase 2 — Scale & Multi-User**: database-backed storage, accounts/auth, coach dashboards aggregating multiple athletes, cloud sync.
- **Phase 3 — Commercialization & Hardware**: rifle-mount hardware kits, federation-scale analytics, subscription model, an optional on-device local SLM to remove the free-tier cloud dependency entirely for offline range use.

---

## 5. Appendix: Ground-Truth Numbers & Known Issues

Single source for every number used elsewhere in this documentation set — cite this table, don't re-derive numbers from memory.

| Parameter | Value | Source |
|---|---|---|
| UI tick interval | 15ms (≈66.7Hz, loosely described in-code as "~60fps") | `ui_main.py`, `self.after(15, self.update_loop)` |
| UX latency budget cited in code | Doherty Threshold, <400ms | `ui_main.py` module docstring |
| Audio chunk size / rate | 512 samples @ 44,100Hz ≈ 11.6ms/chunk | `AudioDetector` defaults, unchanged by `ui_main.py` |
| Audio rolling baseline window | 40 chunks ≈ 0.46–0.5s | `core/audio.py`, `_baseline_buf` deque |
| Baseline statistic | 60th percentile of the rolling window | `core/audio.py`, `np.percentile(..., 60)` |
| **Audio thresholds — class defaults** | `threshold=0.15`, `transient_ratio=6.0` | `AudioDetector.__init__` defaults |
| **Audio thresholds — actually used at runtime** | `threshold=0.10`, `transient_ratio=4.0` | `ui_main.py` overrides these two only; `cooldown_ms` (800ms), `sample_rate`, `chunk_size` remain default |
| Shot cooldown | 800ms | `AudioDetector` default, unmodified by `ui_main.py` |
| Homography staleness tolerance | 5 frames, confidence decays `max(0.1, 0.5 - age*0.1)` | `core/tracker.py`, `MAX_HOMOGRAPHY_AGE` |
| Target/marker geometry | A4 board 210×297mm, marker 40mm, margin 8mm | `ArucoTracker.__init__` defaults |
| Scoring radius | 22.75mm (matches the outermost/1-ring in `target.py`) | `Session.__init__` default |
| Scoring bands | 99 bands, step = 9.9/98 ≈ 0.1010, max score 10.9 | `Session._calculate_score` |
| Trace history window | `deque(maxlen=200)` × 15ms/tick ≈ 3.0s, matching the 3.0s fade cutoff | `ui_main.py` + `core/target.py` |
| Trace color coding | age >3.0s dropped, >1.0s green, >0.2s yellow, ≤0.2s red | `core/target.py` |
| AI Coach model | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` via OpenRouter | `core/insight.py` |
| AI Coach network timeout | 5.0 seconds | `core/insight.py`, `requests.post(..., timeout=5.0)` |
| Bad-shot classifier threshold | score `< 8.0` | `core/insight.py`, `analyze_scatt_json` |

**Known issues cross-referenced here** (see §4 above for the fuller gap analysis):
1. `.gitignore` doesn't exclude `core/.env`, `__pycache__/`, or `history/*.csv`.
2. `requirements.txt` lists `pyaudio`; the code imports `sounddevice`.
3. Shots are silently dropped if detected while no camera is connected (`LLD.md` §6, `DATA_FLOW.md` Flow B).
4. `on_closing()` crashes with `AttributeError` if the app is closed without ever connecting a camera (`LLD.md` §6).
5. The directional-bias classifier in `analyze_scatt_json` doesn't cover the full plane — some bad shots contribute no vote (`LLD.md` §5).
6. `export_summary_json()`'s full-rewrite isn't crash-safe the way the CSV append is (`LLD.md` §3).
7. No target-sheet generator ships with the repo — real onboarding friction (`USER_WORKFLOW.md` §1).
