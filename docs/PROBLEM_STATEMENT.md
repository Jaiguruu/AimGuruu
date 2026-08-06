# AimGuruu — Problem Statement

*(See also: **[`TARGET_PERSONAS.md`](./TARGET_PERSONAS.md)** for who this serves today vs. on the roadmap; **[`PITCH.md`](./PITCH.md)** for the full commercial framing built on this problem.)*

## The Problem

Olympic-style electronic shot-tracking trainers — **SCATT** (Russian-made, the de facto standard for dry-fire training) and **SIUS** (Swiss-made, ISSF's official competition-timing/target partner) — let a shooter dry-fire indoors and see exactly where each shot would have landed, with a live trace of the barrel's movement before, during, and after the trigger break. This is how competitive air-rifle/air-pistol athletes train between live-range sessions.

That capability isn't cheap. Verified current pricing, checked directly against the vendors' own sites:

| System | Verified price | Source |
|---|---|---|
| SCATT Basic (entry, dry-fire + live-fire, 5–50m) | **$947** | scatt.com |
| SCATT MX-02 | **$1,851** | scatt.com |
| SCATT MX-W2 (wireless, dry- and live-fire) | **$1,999** (scattusa.com) – **$2,351** (scatt.com) | official SCATT sites, prices differ by distributor/region |
| SCATT MX-W2 in India | **₹1,45,000** | Indian distributor (Mahie Industries, IndiaMART) |
| SIUS HS10 + SIUSLANE (home system) | **~$2,000** | siususa.com |
| SIUS HS10 / LS10 (competition-grade, historical quotes) | **$3,357 / $5,857** | TargetTalk forum; SIUS is otherwise "tailor-made" pricing on request |

**So the real range is roughly $950–$6,000+ (₹60,000–₹5,00,000+), not a flat "$3–8k."** The low end (SCATT Basic) is genuinely reachable for a serious individual — the gap that actually matters isn't "$2,000 vs. $6,000," it's the much larger population that can't clear the **first $950 (~₹60,000)** for *any* dedicated electronic trainer at all.

## Who Can't Clear That Gap — With Real Numbers

- **ISSF** (the sport's global governing body) has **163 member federations across 149 countries** — a global, not niche, sport.
- In the U.S. alone, the **Civilian Marksmanship Program (CMP)** sanctioned **228 state/regional Three-Position Air Rifle competitions for over 16,500 junior competitors** in a recent season, and an estimated **~250,000 youth** participate in 3-position air rifle nationally (mostly through CMP-affiliated clubs and JROTC) — a large base of juniors training on tight or no personal equipment budgets.
- **NCAA rifle**, by contrast, is a small elite tier: **30 varsity programs across 28 institutions**, with only 8 teams / 48 individual shooters at the actual NCAA championship — useful context for how narrow the "already has access to pro equipment" tier really is.
- The broader **shooting sports equipment market** is sized at **$36.5B (2023) → $53.9B (2030), 5.8% CAGR** by Grand View Research; a narrower "shooting sports equipment" segment from a second publisher puts it at **$3.2B (2024) → $5.1B (2033), 5.5% CAGR** — the two figures use different scope definitions (one broad, including firearms/ammunition; one narrower) and are cited separately rather than reconciled.

## What AimGuruu Actually Claims

Not "as good as a $6,000 SIUS system" — it doesn't claim that, and the detailed [SCATT-vs-AimGuruu gap analysis in `PITCH.md`](./PITCH.md) says exactly where SCATT still wins (live-fire support, decades of software depth, a purpose-built sensor).

The real claim: **AimGuruu reproduces the core training loop — real-time aim tracking, shot capture, scoring, and trend feedback — using a webcam (or a phone via IP-Webcam) and a microphone instead of proprietary optics and electronics, at close to zero incremental hardware cost.** It closes the $0-to-$950 (₹0-to-₹60,000) gap for the ~250,000-strong U.S. junior/CMP-adjacent population and the much larger recreational base who currently have no electronic feedback loop at all, using hardware most of them already own.

## Where the Detailed Technical Solution Lives

How this problem is actually solved — the vision tracking, acoustic shot detection, scoring, and AI coaching — is documented in **[`HLD.md`](./HLD.md)** (system-level view) and **[`LLD.md`](./LLD.md)** (module-by-module detail).
