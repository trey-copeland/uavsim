# Intercept MC demo — UX review (R2)

| Field | Value |
|-------|--------|
| **Iteration** | 2 of max 3 (product gap: 3D path + MC confidence bands) |
| **Reviewed** | `index.html`, `app.js`, `styles.css`, `IMPLEMENT_SUMMARY_R2.md`, pack `data/demo.json` (structure + `mc.bands`) vs `UX_SPEC.md` §3 / §8 + `UX_REVIEW_R2_BRIEF.md` |
| **Pack snapshot** | 500 trials, `p_capture: 1.0` / `n_intercept_success: 500`; `mc.bands` **non-null**, `n_paths_used: 100`, `len(t) = 160` matching all `ownship.{N,E,U}.{p5,p50,p95}`; success + fail nominals present; pack ~832 KB |

---

## Verdict

**SATISFIED**

R2 closes the product gap from R1: the SPA presents a scrub-synced **3D** N/E/up trajectory, ships a real **`mc.bands`** envelope (not `null`), and applies a **single toggle** to **2D fill + 3D percentile fan**. Capture criterion, 2D capture circle, histogram, and P(capture) KPIs remain clear and correctly defined. No **must-fix** items for this iteration.

---

## Blocking (must fix)

*None.*

### Acceptance cross-check (UX_SPEC §8 + R2 gates)

| # | Criterion | Result |
|---|-----------|--------|
| 1 | KPIs: P(capture), n trials, r capture | **Pass** — header chips; `fmtPct(p_capture)`, `n_trials`, `r capture`; `intercept_success` badge |
| 2 | Success \| Fail nominal toggle | **Pass** — both packs; Fail resets playhead; geometry swaps; MC chips stay success-study |
| 3 | Play + scrub; markers + range cursor synced **across 3D / 2D / range** | **Pass** — one `frameIndex`; scrub/play/keyboard/CPA call `drawTraj3d` + `drawTraj2d` + `drawRange`; 3D uses `Plotly.restyle` for trail + markers |
| 4 | Capture criterion on page + range plot; **capture circle on 2D** | **Pass** — story strip + About; dashed r on range(t); dashed circle on 2D at target CPA |
| 5 | min_range histogram + capture marker | **Pass** — bins by `intercept_success`; vertical line at r |
| 6 | **3D flight path** N/E/up; orbit; scrub without destroying scene | **Pass** — `scatter3d` ownship + target + trail/markers; dark scene; axes N/E/up; `uirevision: intercept3d-<case>`; bounds include bands |
| 7 | **Toggle MC bands** default ON: 2D p5–p95 fill + 3D percentile envelope; legible | **Pass** — `#bands-toggle` default checked when `hasBands()`; 2D fill @ ~18% accent + p50; 3D p5/p50/p95 lines; OFF clears both |
| 8 | Shipped pack **`mc.bands` non-null** with schema §4.4 | **Pass** — see pack check below (`bands: null` would fail) |
| 9 | Empty / load error honest | **Pass** — error card + rebuild hint; no-MC note path retained |
| 10 | Dark theme / no default-Plotly final look | **Pass** — showcase tokens; 2D + 3D dark paper/scene |
| 11 | Independent of showcase data | **Pass** — `./data/demo.json` only |
| 12 | Static host / relative fetch | **Pass** — CDN Plotly; relative fetch |

### Pack check: `mc.bands`

Verified against `docs/demos/intercept/data/demo.json` (static inspection + array line spans):

| Field | Value |
|-------|--------|
| `mc.bands` | Object (not `null`) |
| `frame` | `"plot"` |
| `percentiles` | `[5, 50, 95]` |
| `method` | `axiswise_percentile` |
| `n_paths_used` | `100` (≥100; documented in how-to) |
| `t` length | **160** (0…8 s grid) |
| `ownship.N/E/U` × `p5/p50/p95` | Present; each series spans **160** samples (aligned with `t`) |
| Notes | Axis-wise honesty + fixed NDI stated in pack `notes` + UI how-to |
| KPI regression | `n_trials: 500`, `n_intercept_success: 500`, `p_capture: 1.0` unchanged in meaning |

### Focus gates (review brief)

| Focus | Status |
|-------|--------|
| 3D present and scrub-synced | **Met** — primary row left; restyle path on scrub/play |
| Bands non-null and toggleable on **2D + 3D** | **Met** — one checkbox drives both |
| Capture still clear | **Met** — circle, range line, story/About, Capture/Miss badge |
| No regression on P(capture) KPIs | **Met** — still `summary.p_capture` / `intercept_success`; Fail note “MC / bands: success plant study” |

### Layout vs brief

Preferred layout shipped:

```text
3D trajectory | range(t)
2D N–E (full width, bands + capture circle)
shared transport
MC histogram
```

CSS: `.primary-row` two-column (~1.15 / 0.85); stacks under 960px; dark tokens intact.

---

## Non-blocking nits

1. **Bands control placement** — Spec/brief show the toggle on the **transport** bar; R2 places it in the **3D card** tools. Functionally correct (applies to 2D + 3D); moving a duplicate or primary control next to scrub would match the wireframe and stay visible when 3D is scrolled off-screen.
2. **2D scrub cost** — 3D correctly `restyle`s; 2D and range still full `Plotly.react` every frame (R1 pattern). Acceptable at current sample counts; restyle-only 2D would smooth high-FPS play.
3. **Capture sphere on 3D** — Optional in R2; not drawn. 2D circle remains the required capture cue.
4. **Axis-wise band geometry** — 2D fill pairs (E_p5, N_p5)…(E_p95, N_p95); honest for demo but can look boxy vs joint tubes. How-to and pack notes already disclose method — keep that visible if reviewers zoom the fan.
5. **Subsample 100 / 500** — Within ≥100 rule; KPI/histogram still full 500. Optional: label on the band legend (“n=100 paths”) in-plot, not only MC stats.
6. **Carry-over R1 nits** (still true, still non-blocking): dotted full ownship path vs solid full-path wording; MC-panel `strong.ok` color classes without CSS; optional “circle @ target CPA” legend gloss.
7. **Fold density** — Primary 3D + range at `min-height: 380px` each is appropriate; 2D secondary may sit below the fold on shorter laptops — preferred hierarchy is still correct.

---

## What's good

- **R2 product bar met:** 3D is first-class, not a stretch; bands are generated offline and shipped, not disabled forever with `null`.
- **Single frame state** drives 3D markers/trail, 2D markers/trail, and range playhead; case change rebuilds shell and resets to t=0.
- **Camera stability** via `uirevision` + restyle matches showcase Flight path practice; band extents expand scene bounds.
- **Capture story intact:** KPIs, circle, range reference, histogram split, and explicit “not tracking success” copy — Fail geometry contrast without redefining P(capture).
- **Toggle UX:** default ON when data present; disabled + tooltip path still exists if a broken pack omits bands.
- **Dark research chrome** and static/CDN independence preserved; pack stays well under 5 MB (quantile polylines only).
- Implementer summary, exporter flags, and how-to bullets document band method and n_paths — good provenance for hiring reviewers.

---

## Document history

| Date | Note |
|------|------|
| 2026-07-25 | R2 UX review — **SATISFIED**; 3D + non-null toggleable bands; no blocking fixes |
