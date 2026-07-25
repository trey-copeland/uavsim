# Intercept demo — UX R2 implementer brief

| Field | Value |
|-------|--------|
| **Iteration** | 2 (product-gap close) |
| **Audience** | Implementer |
| **Normative design** | [`UX_SPEC.md`](UX_SPEC.md) (R2) · tasks: [`IMPLEMENT_CHECKLIST.md`](IMPLEMENT_CHECKLIST.md) |
| **Do not** | Rebuild showcase matrix; add npm build; ship `bands: null` on primary pack |

---

## Why R2

R1 shipped a solid 2D + histogram SPA and honestly disabled bands when only `trials.csv` existed. Product owners still expect:

1. **3D flight-path visualization** (showcase Flight-style trajectory in N/E/up — path story, not full attitude/wrench dual-pane).
2. **MC confidence bands** on trajectories (toggleable; **2D N–E required**; 3D envelope required).

Those are now **acceptance gates** in UX_SPEC §3 and §8 — not stretch.

---

## Layout change

**Current (R1):** primary row = **2D trajectory | range(t)**; transport; MC histogram.

**Target (R2) preferred:**

```text
┌─────────────────────────────┬─────────────────────────────┐
│  3D trajectory (N/E/up)     │  range(t) + capture line    │
│  ownship + target + markers │  scrub playhead             │
│  MC percentile fan (toggle) │                             │
├─────────────────────────────┴─────────────────────────────┤
│  2D N–E: paths + capture circle + MC band fill (toggle)   │
├───────────────────────────────────────────────────────────┤
│  Play · scrub · CPA · speed · [MC bands ✓]                │
├───────────────────────────────────────────────────────────┤
│  MC histogram + how-to-read                               │
└───────────────────────────────────────────────────────────┘
```

**Acceptable alternate:** top = **3D | 2D N–E (with bands)**; full-width **range(t)** under that; same shared transport.

**CSS:** reuse `.primary-row` two-column cards; add a full-width card for the secondary 2D (or range). Stack to single column under ~960px. Keep dark tokens.

**Skip for R2:** second 3D pane with X-quad mesh / rotor thrust (showcase right pane). Optional later.

---

## Data contract: `mc.bands`

### Problem

Exporter today sets `"bands": null` because MC artifacts are **scalar tables** only. UI already has band drawing helpers — they need real data.

### Generation (implementer-owned, offline)

1. Load success study `monte_carlo/trials.csv` (plant columns + `trial_id`).
2. For each trial (or stratified subsample ≥100): re-simulate the **success recipe** with that plant (mass/I/arm), **fixed NDI**, same open-loop ownship reference / scripted target as L0.
3. Collect ownship position time series → convert to **plot frame (N, E, up)** via existing `ned_to_plot` (or equivalent).
4. Resample all paths onto a common `t` grid; for each \(t_k\) and axis, compute percentiles **5 / 50 / 95**.
5. Write into `demo.json` → `mc.bands` (schema below). Do **not** embed full multi-trial path arrays.

### Required JSON shape

```json
"bands": {
  "frame": "plot",
  "percentiles": [5, 50, 95],
  "t": [0.0, 0.05, 0.10],
  "n_paths_used": 500,
  "method": "axiswise_percentile",
  "notes": "Ownship N/E/U percentiles from plant-param re-sim; fixed gains",
  "ownship": {
    "N": { "p5": [], "p50": [], "p95": [] },
    "E": { "p5": [], "p50": [], "p95": [] },
    "U": { "p5": [], "p50": [], "p95": [] }
  }
}
```

| Rule | Detail |
|------|--------|
| Lengths | Every `p*` array length === `t.length` |
| Frame | `plot` = N, E, **up** (not down) |
| Method note | Axis-wise percentiles ≠ joint ellipsoid; fine for demo honesty if labeled |
| Size | Quantile polylines only; keep pack &lt; ~5 MB |
| Scope | Bands always from **success** plant MC (show even when Fail nominal is selected) |

CLI sketch (document actual flags in demo README):

```bash
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/intercept_l0_success_mc_… \
  --fail-run runs/intercept_l0_fail_… \
  --with-bands \
  --band-max-trials 500 \
  --out docs/demos/intercept/data/demo.json
```

---

## Drawing bands

| Pane | Geometry |
|------|----------|
| **2D N–E** | Closed fill: walk (E_p5, N_p5) along time, reverse (E_p95, N_p95); fill accent @ ~15–25% opacity; optional thin p50 line |
| **2D N–Up** | Same with N/U if projection toggle kept |
| **3D** | Three `scatter3d` lines (p5, p50, p95) in (N,E,U) with decreasing opacity **or** a light multi-percentile fan — not a mesh requirement |
| **Toggle** | One checkbox (existing `#bands-toggle`); default **checked** when `mc.bands` present; applies to **both** 2D and 3D |

Capture **circle** stays on **2D** (required). Capture **sphere** on 3D is optional.

---

## 3D + scrub / play

Mirror showcase Flight path behavior (`docs/showcase/app.js` `Flight3DView`), simplified for intercept:

| Concern | Guidance |
|---------|----------|
| **Traces (static shell)** | Full ownship path, full target path, band polylines (if on), corner/bounds helper if useful |
| **Traces (per frame)** | Ownship trail `0…i`, ownship marker, target marker; optional velocity tick |
| **Update path** | `Plotly.newPlot` on case change / band toggle / first draw; **`Plotly.restyle`** on scrub/play for trail + markers |
| **Camera** | Set initial eye once; set `uirevision` constant per case so orbit is not reset every frame |
| **Bounds** | Fit from nominal ownship + target; expand if band extents exceed |
| **Axes** | Titles `N [m]`, `E [m]`, `up [m]`; dark scene bg (`#0a0e16`-class) |
| **Sync** | Single `frameIndex` already used for 2D + range — wire 3D into the same `drawAll` / play RAF path |
| **Case Fail** | Swap nominal paths; leave MC bands as success envelope (caption optional) |

Do **not** require `euler_deg` or wrench for R2. If euler is already in the pack, a tiny body triad is optional polish only.

---

## Acceptance smoke (implementer self-check)

1. Open via static server → KPIs + **3D path** visible without scrolling past fold on a 1080p desktop if reasonable.
2. Play / scrub → 3D markers, 2D markers, range cursor move together; 3D camera stays put while scrubbing.
3. MC bands **ON** by default → 2D fill visible; 3D percentile curves visible; toggle OFF removes both.
4. `demo.json` has non-null `mc.bands` with p5/p95 for N,E,U.
5. Success | Fail still works; histogram + P(capture) unchanged in meaning (`intercept_success`).
6. No npm; CDN Plotly only; dark theme intact.

---

## Out of scope this pass

- In-browser re-sim or plant knobs  
- Full 500-path cloud in the browser  
- Attitude/wrench dual-pane  
- Battery UI  
- Changing capture math or MC study design  

---

## Document history

| Date | Note |
|------|------|
| 2026-07-25 | R2 brief: layout, bands schema/generation, 3D↔scrub contract |
