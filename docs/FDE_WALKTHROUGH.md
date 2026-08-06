# Building AimGuruu — A Forward Deployed Engineer's Walkthrough

**What this is:** a narrative account of how AimGuruu got built, told through the discipline of a Forward Deployed Engineer (FDE) — not the org-chart title, the actual working method. Useful for an interview answer to "walk me through how you built this" or "tell me about a time you worked without a spec."

**Where the term comes from, precisely:** the FDE role, popularized by Palantir, describes an engineer who embeds directly with a customer and owns the full lifecycle of a solution — requirements, architecture, implementation, integration, and deployment — rather than building one general-purpose capability for many anonymous users. The defining contrast, in Palantir's own framing: a traditional engineer builds *one capability for many customers*; an FDE builds *many capabilities for one customer*, in their actual operating environment, under their actual constraints. (Sources: [Wikipedia — Forward Deployed Engineer](https://en.wikipedia.org/wiki/Forward_Deployed_Engineer), [Palantir Engineering Blog](https://blog.palantir.com/a-day-in-the-life-of-a-palantir-forward-deployed-software-engineer-45ef2de257b1).)

There was no client organization here. But the discipline transfers directly if you treat the *actual shooting environment* — an ordinary room, an ordinary webcam, an ordinary microphone, a $3,000–$6,000 hardware gap the shooter can't clear (see `PITCH.md` §1) — as the "customer" whose constraints are non-negotiable and whose environment you build inside of from day one, instead of a lab you control.

---

## 1. Discovery: Defining the Problem Space Before Writing Code

The problem space isn't "build a computer vision app." It's the specific, bounded gap described with real numbers in `PITCH.md` §1: a $947–$6,000+ hardware category (SCATT, SIUS) that a large, well-documented population — ISSF's 163 member federations, the ~250,000 U.S. junior shooters in CMP-affiliated 3-position air rifle — cannot clear. That's the FDE move: don't start from "what can I build," start from "what does the person on the other end of this actually lack, and what do they already have instead." What they already have, in almost every case, is a phone or a webcam and a microphone. The entire architecture follows from taking that constraint as fixed rather than as a limitation to work around later.

## 2. Embedding With the Constraint, Not a Lab

An FDE builds in the customer's actual environment because a solution validated in a clean lab and then "deployed" tends to fail on contact with reality — different lighting, different noise floor, different hardware. The equivalent discipline here: `core/tracker.py`'s CLAHE preprocessing step exists specifically because indoor rooms have uneven lighting, not because a computer-vision textbook recommends it in general. The audio detector's entire design — rolling-baseline percentile detection instead of a fixed volume threshold — exists because a fixed threshold was tried first, against real room noise, and it failed: it fired on talking and passing traffic. That failure and the fix are recorded directly in the code's own architectural comments in `core/audio.py`, not smoothed over in hindsight. This is what a genuine field iteration looks like: build the simple version, put it in the real environment immediately, watch it break, and let the failure mode dictate the next design decision — not a whiteboard session.

## 3. Risk-First Build Order

The three `phaseN_test.py` scripts in the repo root aren't leftover scaffolding — they're a visible fossil record of the actual build order, and the order itself is the FDE tell: **retire the least-certain, highest-consequence risk first.**

1. **Phase 1 — can markerless camera tracking even work, at all, on commodity hardware?** (`phase1_test.py` against `core/tracker.py`.) This was the real open question — everything else in the product is worthless if a $20 webcam can't resolve sub-millimetre aim position. Build this first, alone, with nothing else attached, and prove it against a real camera before investing another line of code elsewhere.
2. **Phase 2 — given a coordinate, does the scoring/persistence model hold up?** (`phase2_test.py` against `core/session.py`.) Lower technical risk than Phase 1 (it's arithmetic and file I/O), but it's the layer that turns "a tracked point" into "a defensible score," which is the part a real shooter will actually judge the product on.
3. **Phase 3 — can a shot be detected acoustically without false-triggering on a real room?** (`phase3_test.py` against `core/audio.py`.) Deliberately last: it's the piece with the most environmental variability (every room's noise floor is different), so it needed the other two pieces already proven before spending iteration cycles on it.

Only after all three risks were independently retired did they get wired together into `ui_main.py`'s single event loop. That sequencing — hardest, most foundational unknown first, integration last — is exactly the FDE habit of proving the load-bearing assumption before building the building on top of it.

## 4. Deployment-Grade Thinking, Applied Solo

An FDE doesn't get to say "it works on my machine" — they own the outcome for the person who depends on it, in production, today. That mindset shows up twice in this codebase even though there was no external deployment yet:

- **Write-ahead logging** (`core/session.py`): every shot is flushed to CSV before the function returns, specifically because a crash on shot #19 of 20 losing an entire session is not an acceptable failure mode for someone who just spent 20 minutes training — the same reasoning an FDE applies when a customer's data loss has a real cost attached to it, not a hypothetical one.
- **Mandatory graceful degradation** (`core/insight.py`): the AI Coach never has a "the feature is down" state. Missing API key, network failure, timeout — all routes converge on `fallback_insight()`, computed from the exact same metrics. An FDE who ships a feature that depends on a third-party service learns fast that the third-party service *will* be unavailable at some point in production, and designs for that from the start rather than treating it as an edge case.

## 5. Naming What's Still Lab-Grade, Not Field-Grade

Part of the FDE discipline is being the one who says "this isn't ready for the next site" before someone else discovers it the hard way. Honestly assessed against `ARCHITECTURE.md` §8 and `PITCH.md` §4:

- No accounts or multi-athlete separation — fine for one shooter, would immediately break at a second "site" (a club with six athletes sharing one machine).
- No live-fire correlation — SCATT's entry-level product already does this; it's a named, real gap, not a hidden one.
- No independently benchmarked precision — every parameter is open and documented (a real advantage in transparency), but "transparent" isn't the same claim as "validated against a reference instrument," and the pitch doesn't conflate the two.
- Secrets hygiene (`core/.env` unprotected by `.gitignore`) and a dependency mismatch (`pyaudio` vs. `sounddevice`) — the kind of thing an FDE fixes before the next environment, not after.

## 6. What Forward-Deploying This to an Actual Second Site Would Look Like Next

If the next step were literally embedding with a real club or coach — the natural FDE next move — the priority order follows directly from what that specific "customer" would hit first, not from a generic backlog:

1. Multi-athlete accounts (Phase 2) — a coach's very first session would break the "one shared `history/` folder" assumption immediately.
2. A packaged installer (Phase 1) — a coach is not going to `pip install` dependencies for six athletes' laptops.
3. Structured logging (Phase 0) — the first time it breaks in someone else's room, "check the console" isn't a viable support model.

That ordering — driven by what the *next real environment* would break first, not by engineering elegance — is the same discipline that produced the Phase 1/2/3 build order in §3. It's the throughline worth naming explicitly in an interview: the entire project, from the first test script to the roadmap in `PITCH.md`, was sequenced by "what does contact with reality break first," which is the actual job of a forward deployed engineer, with or without the title.
