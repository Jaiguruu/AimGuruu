# Alternative Architectures — Why This One, Not That One

**What this is, and how it differs from what's already in `ARCHITECTURE.md`:** §6 (Tradeoffs) and §7 (ADRs) of `ARCHITECTURE.md` record *component-level* decisions already made — ArUco vs. YOLO, CSV vs. SQLite, and so on — as a factual record. This document operates one level up: **whole-system architectures** that a reasonable engineer, or a skeptical interviewer, might propose instead of what exists — cloud-processed instead of local, mobile-native instead of desktop, event-bus instead of a monolith. Some of it deepens an existing ADR from the "steelman the alternative" angle; some of it is new ground.

**How to use this live in an interview.** When someone proposes "why didn't you just do X instead," the answer that lands is never "I didn't think of that" or a defensive dismissal — it's this three-part shape, used consistently below for every axis:

1. **Acknowledge the real merit** — name specifically what X is actually good at.
2. **Name the specific constraint of *this* problem** that X trades against — not a generic downside, the one that actually applies here.
3. **State the condition under which you'd flip** — this is the part that signals judgment rather than dogma. Every section below ends with one.

One axis (§6, persistence) gets a genuinely different treatment: the honest answer there is "the alternative was probably just better." Interviewers weight that kind of answer more, not less — it's the tell that the rest of the document isn't reflexive self-defense.

| # | Decision axis | Chosen | Main alternative | Rejected because (this problem) | Flips when |
|---|---|---|---|---|---|
| 1 | Where processing happens | Local desktop, on-device | Cloud-processed (stream video/audio to a backend) | Real deployment rooms have unreliable wifi; adds network latency against the <400ms budget; raw home video to a server is a privacy question nobody asked for | Multi-athlete analytics genuinely needs a server — but for computed shot coordinates, not raw video |
| 2 | Tracking hardware topology | Camera-on-tripod + printed markers | Gun-mounted sensor (SCATT's actual approach) | Bespoke hardware erases the entire "near-zero incremental cost" pitch (`PITCH.md` §1) | A premium hardware add-on product line, sold deliberately upmarket |
| 3 | Vision algorithm | Geometric (ArUco + homography) | Learned (YOLO/deep pose estimation) | No training data/budget; non-deterministic failures are undebuggable in a CPU-only real-time pipeline | The target itself stops being a printed marker sheet (e.g., verifying arbitrary paper targets) |
| 4 | UI/rendering stack | Native desktop (Tkinter/CustomTkinter + OpenCV canvas) | Web UI (Electron/browser) or a game engine | Adds a second runtime or a whole 3D toolchain to solve a 2D-primitive-drawing problem `cv2.circle`/`cv2.line` already solves in milliseconds | 3D trajectory visualization (e.g., outdoor ballistic drop) becomes a real requirement |
| 5 | Concurrency model | Threads + `queue.Queue` polling | `asyncio`, or multiprocessing | Tkinter's mainloop isn't async-native; multiprocessing needs ~60 frames/sec crossing a process boundary for a workload that isn't CPU-bound enough to need it yet | CV processing time approaches the 15ms tick budget on target hardware (already the named trigger in `ARCHITECTURE.md` §6) |
| 6 | Persistence | CSV (WAL) + JSON (full rewrite) | SQLite | **Honest answer: this one probably should have been SQLite from the start** — see below | Already true; this is the first thing to change, not a future one |
| 7 | AI coaching backend | Cloud LLM + deterministic fallback | Local-only SLM, or no AI at all | No-AI is more "correct" but a worse product for a shooter who can't self-diagnose a scatter plot; local-only adds a multi-GB runtime dependency before the feature was even validated as useful | Once coaching is validated as valuable, Phase 3 removes the free-tier dependency with a local-model option (already in `PITCH.md` §6) |
| 8 | Software structure | Monolithic orchestrator (`AimGuruuApp` calls every module) | Event-bus / pub-sub | Textbook premature abstraction at 5 modules and 1 consumer — no payoff yet | A second real consumer of the same events exists (a coach dashboard, Phase 2) |

---

## 1. Where the processing happens: local desktop vs. cloud vs. native mobile

**Chosen:** everything — camera capture, ArUco tracking, audio detection, scoring — runs on the user's own machine. The only network call in the entire system is the on-demand, 5-second-timeout OpenCV coach request.

**Alternative A — cloud-processed:** stream video and audio to a backend, run tracking/detection server-side, stream coordinates back.
- **Real merit:** unlimited compute headroom (could run heavier, more accurate models than a CPU-only desktop budget allows); centralizes logic so updates ship without a client release; a natural precursor to the multi-athlete analytics Phase 2 already wants.
- **Why not here:** the actual deployment environment — a basement, a garage, a gun club — is exactly the kind of place with unreliable or absent wifi. Streaming raw video adds real round-trip latency against the <400ms Doherty budget the code explicitly cites, and it turns a "$0 incremental hardware cost" pitch into "$0 hardware, plus you need reliable broadband," which quietly kills the accessibility thesis for the least-connected part of the target market (see the CMP/junior population in `PITCH.md` §1).
- **Flips when:** the moment there's a real multi-tenant coaching platform (Phase 2/3), server-side aggregation becomes necessary — but the right version of that is uploading *computed shot coordinates* after the session, not streaming raw video during it. Conflating "needs a server eventually" with "needs to stream video now" is the actual mistake this alternative would make.

**Alternative B — native mobile app (iOS/Android):** on-device ML via ARKit/ARCore, fusing camera with the phone's own gyroscope/accelerometer.
- **Real merit:** the phone is often physically mounted on the barrel already (the README's IP-Webcam support exists precisely because this is how people actually use it); IMU fusion could plausibly beat vision-only tracking on stability; app-store distribution reaches more non-technical users than a Python install.
- **Why not here:** two native codebases (iOS + Android) is a real maintenance tax for a solo build; OpenCV's desktop ecosystem is more mature for the kind of fast, iterative CV debugging this project actually did (see `FDE_WALKTHROUGH.md` §3's risk-first build order); and the current phone-as-camera-source approach already captures most of "use the phone you own" without committing to a full native rewrite — a deliberate 80/20 middle path, not an oversight.
- **Flips when:** if IMU-fused stabilization becomes a real precision differentiator against SCATT (the exact "precision transparency" gap named in `PITCH.md` §4) — that specifically requires native sensor access a webcam feed structurally cannot provide.

## 2. Tracking hardware topology: camera-on-tripod vs. gun-mounted sensor

**Chosen:** a stationary camera looks at a printed marker sheet; the gun itself carries no electronics.

**Alternative — a small sensor clipped to the barrel, like SCATT's real hardware** (`PITCH.md` §4 has the verified specs: 30–56g, optical/IR, mounted on the gun).
- **Real merit:** this is the decades-validated, proven approach; the sensor moves with the gun, so there's no "stay inside the camera's frame" constraint at all; it's very likely capable of higher precision than a webcam-and-homography pipeline, matched hardware to task.
- **Why not here:** requiring a bespoke sensor means requiring bespoke hardware — and the entire pitch is "near-zero incremental cost using a webcam or phone you already own" (`PITCH.md` §1). This is the clearest place in the whole project where the technical decision is *downstream of the business model*, not a pure engineering call: the camera-on-tripod architecture isn't "worse tracking, chosen naively," it's the only architecture compatible with the stated price-accessibility thesis. Worth saying exactly that if asked — it reframes what could sound like a technical limitation as a deliberate product constraint.
- **Flips when:** if the product ever adds a premium hardware tier (an "AimGuruu Pro" companion sensor sold as an upsell, not a requirement) — at that point a gun-mounted sensor is a legitimate product-line extension, not a compromise of the free/core tier's promise.

## 3. Vision algorithm: geometric (ArUco + homography) vs. learned (deep pose estimation)

This deepens ADR-001 from the steelman side rather than repeating it.

**Alternative — train or use a pose-estimation/object-detection model to find the target or muzzle directly**, no printed markers required.
- **Real merit:** removes the requirement to print and precisely mount a marker sheet; in principle could generalize to an arbitrary, unmarked target.
- **Why not here:** it needs labeled training data across lighting conditions and backgrounds this project has neither the budget nor the dataset for; inference adds latency and, more importantly, adds *non-deterministic* failure modes. When the homography solve is wrong, the failure is a single debuggable matrix (`ARCHITECTURE.md` §4.1's occlusion-cache logic exists precisely because this failure mode is well-understood and boundable). When a neural net is wrong, the failure surface is much harder to characterize, harder to explain to a user, and harder to fix without retraining — a bad trade for a CPU-only, explainability-matters, zero-latency pipeline.
- **Flips when:** the product needs to work against an arbitrary real target that isn't a printed sheet — for example, verifying actual paper targets already in use at a live-fire range. That's a genuinely different (and harder) problem markers structurally cannot solve, and it would justify the ML investment on its own merits.

## 4. UI/rendering stack: native desktop vs. web UI vs. game engine

**Chosen:** CustomTkinter for the UI shell, OpenCV primitives (`cv2.circle`, `cv2.line`) drawn onto a NumPy canvas for the target/trace visualization (`ARCHITECTURE.md` §4.4's static/dynamic layer-caching pattern).

**Alternative A — a web UI (Electron, or a Flask/websocket backend with a browser frontend).**
- **Real merit:** a much richer UI component ecosystem than Tkinter offers; genuine reuse potential — the exact same frontend stack could become the Phase 2 coach dashboard with far less duplicated effort than a second Tkinter build.
- **Why not here:** it adds a second language/runtime (JavaScript) and a client-server hop *inside a single-machine application*, purely for UI polish, at a moment when the actual bottleneck (§5 below) is a 15ms tick budget that a browser round-trip works against, not for.
- **Flips when:** the moment a real web-based coach dashboard is being built anyway (Phase 2) — at that point, building the local app's UI on the same stack stops being premature and starts being the obvious reuse.

**Alternative B — a game engine (Unity, Godot) for the live-crosshair/trace rendering.**
- **Real merit:** game engines are purpose-built for real-time 60fps rendering with camera overlays — arguably a more natural fit conceptually than compositing OpenCV primitives onto a NumPy array.
- **Why not here:** it pulls in an entire unrelated toolchain to solve a problem that's actually simple 2D primitive drawing — ten circles and a fading polyline — which OpenCV already does in a couple of milliseconds. The rendering workload here was never a 3D scene; reaching for a 3D engine would be solving a problem the project doesn't have.
- **Flips when:** if the product needs genuine 3D visualization — simulating outdoor ballistic drop for rifle disciplines beyond 10m air rifle, for instance — that's a rendering problem a 2D canvas can't serve, and a game engine (or at least a 3D graphics library) becomes the right tool.

## 5. Concurrency model: threads + Queue vs. asyncio vs. multiprocessing

This deepens the tradeoffs-table row in `ARCHITECTURE.md` §6.

**Alternative A — `asyncio` throughout.**
- **Real merit:** a single cooperative event loop avoids explicit locks entirely and gives one consistent concurrency mental model for the whole app.
- **Why not here:** Tkinter's `mainloop()` is not an asyncio event loop. Bridging the two cleanly requires either a third-party shim with its own edge cases or abandoning Tkinter for an async-native UI stack — which is really Alternative A of §4 wearing a different hat, and a full UI rewrite is a disproportionate way to solve a concurrency problem the `Queue` pattern already solves correctly in about five lines (`ARCHITECTURE.md` ADR-002).
- **Flips when:** only alongside a UI stack migration, not on its own.

**Alternative B — multiprocessing** (separate OS processes for CV, audio, and UI).
- **Real merit:** true parallelism across CPU cores; a crash in the CV process can't directly take the UI process down with it.
- **Why not here:** frames would need to cross a process boundary roughly 60 times a second — real serialization or shared-memory engineering for a benefit (multi-core CV throughput) the current workload doesn't need yet, since CV processing isn't actually missing the 15ms tick budget in practice.
- **Flips when:** exactly the condition `ARCHITECTURE.md` §6 already names for offloading CV off the main thread — if frame processing time ever approaches or exceeds the 15ms budget on target hardware, this is the next architecture to reach for, not before.

## 6. Persistence: CSV/JSON vs. SQLite — the honest one

**Chosen:** a per-shot CSV append (write-ahead-log style) plus a full-rewrite JSON summary (`ARCHITECTURE.md` §4.3, ADR-003).

**Alternative — SQLite.**
- **Real merit, stated plainly:** SQLite ships in the Python standard library, requires no server, is a single file exactly like the CSV is — and would have given transactional atomicity for free, which directly eliminates the one real data-integrity gap this project has (`ARCHITECTURE.md` §9, known issue #6: the JSON summary isn't crash-safe the way the CSV is). A single `INSERT` inside a transaction replaces both files and closes the gap entirely.
- **The honest answer, not a defense:** unlike every other row in this document, this isn't "rejected for a good reason that would flip under different conditions" — in hindsight, SQLite was very likely just the better choice even at the original MVP scope, for close to zero extra complexity. If asked "what would you change first, no caveats," this is the answer, not the CSV/JSON design. Being able to say that plainly, instead of retroactively justifying the original choice, is itself the point of including this row.
- **Why the *original* reasoning wasn't unreasonable:** CSV is trivially human-readable and diffable during early development, which mattered when the actual open question was still "does the tracking math work at all" (`FDE_WALKTHROUGH.md` §3) — but that justification stopped applying once the core loop was proven, and the persistence layer was never revisited after that point. That's the real lesson, not the tool choice: the cost was leaving an early-stage decision unrevisited past the point its original justification expired.

## 7. AI coaching backend: cloud + fallback vs. local-only vs. none

This deepens ADR-004.

**Alternative A — no AI at all, just statistical dashboards** (Center of Mass, fatigue trend charts, directly).
- **Real merit:** completely removes the network dependency and the free-tier fragility named in `PITCH.md` §4 and §6; arguably more "honest" engineering with no black-box text generation involved.
- **Why not here:** the target user is a junior shooter, not a data scientist — they don't reliably self-diagnose a scatter plot and a trend line. Natural-language coaching exists specifically to lower that interpretation barrier, which is the actual point of the feature. A dashboard-only version would be more defensible engineering and a measurably worse product.
- **Flips when:** for a power-user/coach-facing view specifically (Phase 2) — a coach reviewing six athletes' sessions probably *does* want the raw charts alongside the narrative summary, not instead of it. This is a "both," not an "either," once that persona exists.

**Alternative B — local-only SLM (e.g., via Ollama), no network call ever.**
- **Real merit:** zero network dependency, no free-tier fragility, and it's the most consistent alternative with the "everything transparent and self-contained" posture that `PITCH.md` §4 already credits AimGuruu with in the precision-transparency row.
- **Why not here, yet:** it adds a real runtime dependency — a multi-gigabyte local model download and inference runtime — to a project whose entire pitch is "uses hardware you already have." For a solo build validating whether AI coaching was even useful *before* investing further, the cloud free-tier was the fastest way to answer that question; committing to a heavier local pipeline before knowing the feature had value would have been optimizing a feature that might not have survived contact with real users.
- **Flips when:** exactly what `PITCH.md` §6 Phase 3 already commits to — once coaching is validated as valuable, a local-model option removes the free-tier dependency for offline range use, where it matters most.

## 8. Software structure: monolithic orchestrator vs. event-bus/pub-sub

**Chosen:** `AimGuruuApp` directly owns and calls every other module — the component diagram in `ARCHITECTURE.md` §3.2 shows one orchestrator talking to five components plus a queue.

**Alternative — an event bus.** Components publish domain events (`FrameProcessed`, `ShotDetected`, `ReportGenerated`); `AimGuruuApp` becomes one subscriber among several instead of the sole coordinator.
- **Real merit:** decouples modules from each other and from the orchestrator; makes it close to free to add a second consumer of the same event stream later — a future coach dashboard subscribing to `ShotDetected` without touching `AimGuruuApp` at all.
- **Why not here:** at five modules and exactly one consumer, this is the textbook premature abstraction — it adds a real layer of indirection with no current payoff, and runs directly against the working principle that three similar lines beat a premature abstraction. An event bus built for a future consumer that doesn't exist yet is speculative architecture, not current necessity.
- **Flips when:** the moment a second real consumer of the same events exists — a coach dashboard (Phase 2) is precisely that. That's the natural point this pattern earns its cost, and not one phase before it.
