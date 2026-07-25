# Intercept MC demo — UX review (R1)

| Field | Value |
|-------|--------|
| **Iteration** | 1 of max 3 |
| **Reviewed** | `index.html`, `app.js`, `styles.css`, `README.md`, pack `data/demo.json` (structure + summary) vs `UX_SPEC.md` §2–§8 + `IMPLEMENT_CHECKLIST.md` |
| **Pack snapshot** | 500 trials, `p_capture: 1.0` / `n_intercept_success: 500`, min_range max ≈ 0.196 m, `bands: null`, success + fail nominal cases present |

---

## Verdict

**SATISFIED**

The static SPA meets [`UX_SPEC.md` §8](UX_SPEC.md) acceptance for v1. A hiring-style reviewer can open the page (via static server), read capture KPIs immediately, scrub/play Success and Fail nominals, inspect the min-range histogram, and understand that plant MC capture is not tracking `success`. No **must-fix** issues for this iteration.

---

## Blocking issues (must fix)

*None.*

### Acceptance cross-check (§8)

| # | Criterion | Result |
|---|-----------|--------|
| 1 | KPIs visible: P(capture), n trials (or no MC), r capture | **Pass** — header chips; `fmtPct(p_capture)`, `n_trials`, `r capture` |
| 2 | Success \| Fail nominal toggle | **Pass** — both packs present; Fail disabled only if missing |
| 3 | Play + scrub; markers + range cursor synced | **Pass** — transport, RAF play, scrub, space/←/→, Jump to CPA |
| 4 | Capture criterion on page + range plot | **Pass** — story strip, About, dashed `r` on range(t) |
| 5 | min_range histogram + capture marker | **Pass** — split by `intercept_success`; vertical line at r |
| 6 | MC bands toggle when data present | **Pass** — `bands: null` → checkbox disabled + tooltip “Bands not in data pack” |
| 7 | Empty / load error honest | **Pass** — loading text, error card + rebuild hint, no-MC note |
| 8 | Dark theme / no default-Plotly final look | **Pass** — showcase tokens; Plotly paper/plot dark |
| 9 | Independent of showcase data | **Pass** — `./data/demo.json` only |
| 10 | Static host / relative fetch | **Pass** — documented in README |

### MC copy / semantics (explicit review gate)

| Risk | Status |
|------|--------|
| Present tracking `success` (0%) as miss / low capture | **Not present.** KPI uses `summary.p_capture` / `intercept_success`. Badge uses `metrics.intercept_success` only. Histogram bins by `intercept_success`. Stats show `n intercept / n trials`, not `n_success`. |
| Conflate Fail case with MC failure | **Mitigated.** Story strip + About + `how_to_read` state MC is on the success recipe; Fail is geometry contrast only. Chips stay success-study P(capture) when Fail is selected (per spec). |
| Pack numbers vs UI | **Aligned:** 500 trials, P(capture) 100%, all trial min_range ≪ 1 m (max ~0.20 m). |

Nominal packs correctly carry `success: false` with `intercept_success: true` (success case); the UI never surfaces the tracking flag as the capture story.

---

## Non-blocking nits

1. **MC-on-success caption near KPIs when Fail is active** — Story strip already explains this; a one-line muted note under chips (“MC: success plant study”) would reduce glance misread when Fail + P(capture)=100% appear together.
2. **Stats list color classes** — `strong` uses classes `ok` / `fail`, but CSS only styles `.badge.ok` / `.kpi.good`. P(capture) in the MC panel is not tinted green; harmless, slightly unfinished.
3. **Capture circle center** — Drawn on **target at CPA** (reasonable). Spec allows CPA or ownship at min-range; optional note in legend (“circle @ target CPA”) would match engineering expectation.
4. **Full ownship path style** — Spec suggests solid full path; implementation uses muted dotted full path + solid scrub trail. Legible; optional align to “solid full path” if reviewers find the dotted leg confusing.
5. **Histogram when all captures** — Only green “capture” series; fine at P=1. Optional x-axis domain still spanning past `r` helps show headroom (currently data-driven and all left of 1 m).
6. **Project README link to Pages path** — Checklist still open for root README when live; not a demo SPA defect.

---

## What's good

- Clear single-screen hierarchy: sticky header KPIs → story strip → trajectory + range → transport → MC panel → footer.
- **Capture ≠ tracking** is stated in About, how-to-read, summary `note` in pack, and README — critical for this 0% tracking / 100% capture MC.
- Transport is complete (play/pause, scrub, speed, CPA jump, keyboard) and case changes reset playhead + pause.
- Dark research chrome matches showcase tokens; Plotly configured without logo; plot hosts dark before draw.
- Honest empty states for bands and missing MC; load failure explains static-server + exporter.
- Self-contained pack (~histogram + trials, no trial-path bands) with graceful UI degradation.

---

## Document history

| Date | Note |
|------|------|
| 2026-07-25 | R1 UX review — **SATISFIED**; no blocking fixes required |
