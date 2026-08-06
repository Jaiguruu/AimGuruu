# AimGuruu — Target Personas

*(Grounded in **[`PROBLEM_STATEMENT.md`](./PROBLEM_STATEMENT.md)**'s real pricing and participation numbers. Reused verbatim, with the "fits today" column intact, in **[`PITCH.md`](./PITCH.md)**.)*

The table below is intentionally honest about *today's* capability vs. what requires roadmap work — a persona this codebase can't yet serve is listed as a roadmap target, not a current fit. That honesty is deliberate: it shows exactly which investment unlocks which customer, rather than overclaiming what a solo-built MVP already does (see `ALTERNATIVE_ARCHITECTURES.md` §2 and `ARCHITECTURE.md`'s ADR-006 for why this scope boundary is a design decision, not an oversight).

| Persona | Fits today? | Why |
|---|---|---|
| **The Priced-Out Competitor** — a junior/collegiate ISSF or CMP-affiliated air-rifle shooter, part of the ~250,000-strong U.S. 3-position air rifle youth population, who wants dry-fire feedback between club sessions but can't justify $947+ hardware | **Yes, as-is** | Single-user, single-machine, local `history/` folder — exactly matches one athlete training alone. This is the current product. |
| **The Home Hobbyist** — a casual airgun/dry-fire enthusiast who wants a feedback loop and score tracking for habit-building, not competition prep | **Yes, as-is** | Identical technical fit to the persona above; differs only in motivation, which matters for pricing/positioning (see `PITCH.md`), not for what the software must do. |
| **The Club/Academy Coach** — manages 6–15 athletes and wants to review sessions across a squad | **No — Phase 2** | There are no accounts, no per-athlete separation beyond manually renaming the app on launch, and no aggregation view. Every athlete's shots land in the same local `history/` folder undifferentiated except by filename timestamp. |
| **The Federation / Talent-ID Program** — wants standardized analytics across multiple locations for talent identification, the kind ISSF's 163 federations or CMP's national network could plausibly want | **No — Phase 3, aspirational** | Requires auth, a real multi-tenant backend, and cloud storage — none of which exist. Belongs in the roadmap, not the current pitch. |

## How Each Persona Actually Uses the App Today

For the two personas the app already serves, the concrete, step-by-step experience — install, connect a camera, calibrate, dry-fire, review — is documented in **[`USER_WORKFLOW.md`](./USER_WORKFLOW.md)**.

## Roadmap Ownership

Which phase unlocks which persona is spelled out in `ARCHITECTURE.md` §4 (Enterprise-Grade Gap Analysis & Roadmap) and reframed as a business investment narrative in `PITCH.md`'s roadmap section.
