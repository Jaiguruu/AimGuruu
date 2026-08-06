# AimGuruu — Enterprise & Commercial Case

**For:** club owners, coaches, potential partners/investors, non-engineering stakeholders.
**Engineering due diligence:** every technical claim about AimGuruu itself is backed by **[`ARCHITECTURE.md`](./ARCHITECTURE.md)** — link it, don't restate it.
**Build story:** for how this was actually built and what that process says about the engineer, see **[`FDE_WALKTHROUGH.md`](./FDE_WALKTHROUGH.md)**.

> **On the numbers in this document:** every SCATT, SIUS, ISSF, CMP, NCAA, and market-size figure below is from a live web search against the vendors' own sites, official federation pages, or named market-research publishers — sourced, not estimated. They're listed in **§7 Sources** with the exact page. Two numbers are explicitly *not* real research: the "Illustrative Pricing Model" in §5 is a proposed model for AimGuruu's own future pricing, not a researched competitor figure, and is labeled as such inline.

---

## 1. The Problem — With Real Numbers

Electronic shot-tracking trainers — the two names that come up in every conversation about this are **SCATT** (Russian-made, the de facto standard for dry-fire training) and **SIUS** (Swiss-made, ISSF's official competition-timing/target partner) — let a shooter dry-fire indoors and see exactly where each shot would have landed, with a live trace of the barrel's movement before, during, and after the trigger break. Actual current pricing, checked against the vendors' own sites:

| System | Actual price | Source |
|---|---|---|
| SCATT Basic (entry, dry-fire + live-fire, 5–50m) | **$947** | scatt.com |
| SCATT MX-02 | **$1,851** | scatt.com |
| SCATT MX-W2 (wireless, dry- and live-fire) | **$1,999** (scattusa.com) – **$2,351** (scatt.com) | official SCATT sites, prices differ by distributor/region |
| SIUS HS10 + SIUSLANE (home system) | **~$2,000** | siususa.com |
| SIUS HS10 / LS10 (competition-grade, historical quotes) | **$3,357 / $5,857** | TargetTalk forum, SIUS is otherwise "tailor-made" pricing on request |

**So the real range is roughly $950–$6,000+, not a flat "$3–8k."** The low end (SCATT Basic) is genuinely reachable for a serious individual; the gap AimGuruu actually closes is between "$0, using a webcam or phone you already own" and "$950 minimum for any dedicated electronic trainer at all" — which matters most for the buyer who can't clear that first $950, not the one comparing $2,000 vs $6,000.

**Who that buyer actually is, with real participation data:**
- **ISSF** (the sport's global governing body) has **163 member federations across 149 countries** — a global, not niche, sport.
- In the U.S. alone, the **Civilian Marksmanship Program (CMP)** sanctioned **228 state/regional Three-Position Air Rifle competitions for over 16,500 junior competitors** in a recent season, and an estimated **~250,000 youth** participate in 3-position air rifle nationally (mostly through CMP-affiliated clubs and JROTC) — a large base of juniors training on tight or no personal equipment budgets.
- **NCAA rifle**, by contrast, is a small elite tier: **30 varsity programs across 28 institutions**, with only 8 teams / 48 individual shooters at the actual NCAA championship — useful context for how narrow the "already has access to pro equipment" tier really is.
- The broader **shooting sports equipment market** is sized at **$36.5B (2023) → $53.9B (2030), 5.8% CAGR** by Grand View Research; a narrower "shooting sports equipment" segment definition from a second publisher puts it at **$3.2B (2024) → $5.1B (2033), 5.5% CAGR** — the two numbers use different scope definitions (one is broad including firearms/ammunition, the other narrower), cited separately rather than reconciled, because reconciling them would require the underlying methodology, not something a two-line citation should paper over.

**AimGuruu's actual claim:** not "as good as a $6,000 SIUS system" — it doesn't claim that, and shouldn't (see §4). The claim is "closes the $0-to-$950 gap for the ~250,000-strong junior/CMP-adjacent population and the much larger recreational base who currently have no electronic feedback loop at all," using hardware they already own.

## 2. Who This Is For Today — and Who It Isn't Yet

| Persona | Fits today? | Why |
|---|---|---|
| **The Priced-Out Competitor** — junior/collegiate ISSF or CMP-affiliated air-rifle shooter, part of that ~250,000-strong U.S. 3PAR youth population | **Yes** | The current single-user, single-machine build is exactly this athlete's training setup. |
| **The Home Hobbyist** — casual airgun/dry-fire enthusiast | **Yes** | Same technical fit; different motivation, relevant to how the free/paid tiers below should be framed. |
| **The Club/Academy Coach** — manages a squad of 6–15 athletes | **Not yet — Phase 2** | Needs accounts and per-athlete data separation, which don't exist today. This is the single highest-value near-term expansion. |
| **The Federation / Talent-ID Program** — standardized analytics across locations, the kind ISSF's 163 federations or CMP's national network could plausibly want | **Not yet — Phase 3, aspirational** | Needs a real multi-tenant backend. Long-horizon, not a near-term claim. |

Being upfront about this split is a feature of this pitch, not a weakness: it shows exactly which investment unlocks which customer, rather than overclaiming what a solo-built MVP already does.

## 3. How It Works (Plain-Language View)

```mermaid
flowchart LR
    A["Point a webcam or phone<br/>at a printed target sheet"] --> B["Software tracks exactly<br/>where the rifle is aimed,<br/>in real-world millimetres"]
    C["A microphone listens<br/>for the trigger click"] --> D["The system captures the shot<br/>at that instant"]
    B --> D
    D --> E["Score and trajectory are saved<br/>instantly — nothing is lost,<br/>even if the app crashes"]
    E --> F["An AI Coach explains what to fix,<br/>in plain language, after every session"]
```

*(Engineering detail behind each box is in `ARCHITECTURE.md` §3–§5.)*

## 4. SCATT vs. AimGuruu — What the Gap Actually Is

This is the section that matters most for credibility: naming the real gap precisely, instead of a vague "we're cheaper." Researched directly from SCATT's own product pages, FAQ, and user manual.

| Dimension | SCATT (verified) | AimGuruu (today) | The actual gap |
|---|---|---|---|
| **Tracking hardware** | A dedicated optical/IR sensor (30–56g) mounted directly on the gun barrel (most models); the MX-02 model instead uses a camera aimed at the target — architecturally the closest thing to AimGuruu in SCATT's own lineup | A generic webcam or phone (via IP-Webcam), camera fixed off-gun, aimed at a printed ArUco target sheet | AimGuruu needs zero dedicated hardware; SCATT's non-MX-02 models need a sensor physically fitted to the specific gun |
| **Shot detection** | A microphone *built into the gun-mounted sensor*, registering the trigger click at point-blank range | A room-placed microphone using rolling-baseline transient-ratio detection (§4.2 of `ARCHITECTURE.md`) | Same underlying principle (acoustic click detection) — SCATT's mic sits millimetres from the source and gets a cleaner signal; AimGuruu's ambient mic has to work harder to reject room noise |
| **Trajectory visualization** | Color-coded time-phased trace — SCATT's own documentation describes green (settling)/yellow (~1s before the shot)/red (post-shot follow-through), with a 4th (blue) phase noted in at least one version of the software | Color-coded trace: green (>1s, approach) / yellow (0.2–1s, hold) / red (≤0.2s, trigger break) | **Not a gap — a validation point.** AimGuruu converged on essentially the same visual language independently; the code's own comments cite "SCATT Standard" explicitly. Worth stating plainly in an interview or pitch: this wasn't guessed, it was built to match the industry convention. |
| **Live-fire support** | Yes — SCATT Basic is rated for dry-fire *and* live-fire, indoors or outdoors, up to 50m | Dry-fire only; there is no design today for correlating a tracked aim point with an actual bullet's point of impact | Real, currently unaddressed gap — tracked in the roadmap (§6) |
| **Precision transparency** | Not publicly disclosed — sampling rate and angular accuracy don't appear in SCATT's public FAQ, product pages, or user manual for the MX-W2 | Every parameter is open and in source: ~66Hz UI tick, ArUco sub-pixel corner refinement, homography via RANSAC (`ARCHITECTURE.md` §4.1, §9) | Neither a win nor a loss — a genuine difference in posture: SCATT is a closed, presumably well-calibrated proprietary instrument; AimGuruu is a fully inspectable pipeline whose actual precision hasn't been independently benchmarked against a reference system yet |
| **Software maturity** | Decades-old product line; SCATT Basic software runs cross-platform (Windows/Mac/Linux, plus a mobile "SCATT Expert" app); the more advanced SCATT Pro software is Windows-only (Mac requires a VM); supports up to 4 shooters simultaneously from one PC | Single-machine, single-session desktop app; one AI-generated coaching report, no training-program library, no elite-shooter benchmark comparisons | Real, large gap — SCATT's software depth is the product of years of iteration; closing it is a roadmap item, not a weekend fix |
| **Price** | $947–$2,351 (SCATT) to $2,000–$5,857+ (SIUS), verified above | ~$0 incremental hardware cost for anyone who owns a webcam or phone | This is the actual pitch — not "better," cheaper by a wide, verifiable margin |
| **Track record** | Established manufacturer, used across many national federations for years | Solo-built, pre-revenue software project | Real gap in trust/credibility that no amount of feature-matching closes by itself — addressed in the roadmap through packaging, testing, and (eventually) third-party validation, not by claiming otherwise |

## 5. Illustrative Pricing Model *(AimGuruu's own proposed pricing — not a researched competitor figure)*

| Tier | Proposed price | Who it's for | What it needs (see Roadmap) |
|---|---|---|---|
| **Free** | $0 | Home Hobbyist, single device | Nothing new — this is close to today's build |
| **Pro** | ~$9–15/mo | Priced-Out Competitor who wants cloud backup + session history across devices | Phase 2: cloud sync |
| **Club/Academy** | ~$99–199/mo per club | Coach managing a squad | Phase 2: accounts, multi-athlete dashboards |
| **Federation** | Custom / enterprise contract | Talent-ID and standardized cross-location analytics | Phase 3: multi-tenant backend, compliance/security hardening |

Even the Club/Academy tier still undercuts a single SCATT Basic unit ($947) within the first year for any club fielding more than one or two athletes — the pricing logic follows directly from §1's real numbers, not from a made-up TAM.

## 6. Roadmap — Now Informed by the Real Competitive Gap

```mermaid
timeline
    title From Solo Build to Enterprise Platform
    Phase 0 — Hygiene : Close the secrets-exposure gap : Fix dependency drift : Centralize config : Structured logging
    Phase 1 — Reliability : Automated test suite : CI pipeline : Installer for non-technical users
    Phase 2 — Scale : Accounts and multi-athlete data : Cloud sync : Coach dashboards
    Phase 3 — Close the SCATT gap : Live-fire correlation : Independently benchmarked precision : Training-program library : Optional offline local AI model
```

- **Phase 0 — Hygiene** *(cheap, fast, table stakes)*: closes real, already-identified gaps — an unprotected API key path, a dependency mismatch, hardcoded config, `print()`-only diagnostics. Full list in `ARCHITECTURE.md` §8.
- **Phase 1 — Reliability** *(unlocks: trustworthy releases)*: a real test suite and CI mean features can ship without re-manually-verifying the vision and scoring math every time; a packaged installer means the Home Hobbyist and Priced-Out Competitor personas can actually install this without a Python environment.
- **Phase 2 — Scale** *(unlocks: the Club/Academy Coach persona and the Pro/Club pricing tiers above)*: turns a single-player tool into a multi-seat product with recurring revenue.
- **Phase 3 — Close the SCATT gap directly** *(unlocks: credible comparison against real competitors, not just price)*: this phase is now scoped from §4's actual findings, not a generic wishlist — live-fire point-of-impact correlation, a published precision benchmark against a reference system (closing the "precision transparency" row honestly, in either direction), a training-program library comparable to SCATT Pro's, and an offline local-model option to remove the free-tier LLM dependency named directly in §1's software-maturity row.

## 7. Sources

- SCATT pricing and specs: [scatt.com](https://www.scatt.com/) (MX-W2, MX-02, Basic product pages, FAQs), [scattusa.com](https://scattusa.com/) (official North American distributor, pricing and FAQ), [olympicpistol.com MX-W2 manual](https://www.olympicpistol.com/mxw2man/)
- SIUS pricing: [siususa.com](https://www.siususa.com/), historical quotes via [TargetTalk forum](https://www.targettalk.org/viewtopic.php?t=61091)
- ISSF federation count: [issf-sports.org member federations](https://www.issf-sports.org/issf/organisation/member-federations)
- CMP junior participation: [thecmp.org Three-Position National Postal Competition](https://thecmp.org/three-position-national-postal-competition/)
- NCAA rifle programs: [Wikipedia — List of NCAA rifle programs](https://en.wikipedia.org/wiki/List_of_NCAA_rifle_programs)
- Market sizing: [Grand View Research — Shooting Sports Equipment Market](https://www.grandviewresearch.com/industry-analysis/shooting-sports-equipment-market-report), [DataHorizzon Research — Shooting Sports Equipment Market](https://datahorizzonresearch.com/shooting-sports-equipment-market-25712)
- Forward Deployed Engineer role: [Wikipedia — Forward Deployed Engineer](https://en.wikipedia.org/wiki/Forward_Deployed_Engineer), [Palantir Engineering Blog](https://blog.palantir.com/a-day-in-the-life-of-a-palantir-forward-deployed-software-engineer-45ef2de257b1)

## Appendix

Full engineering due diligence lives in **[`ARCHITECTURE.md`](./ARCHITECTURE.md)**. The build narrative lives in **[`FDE_WALKTHROUGH.md`](./FDE_WALKTHROUGH.md)**.
