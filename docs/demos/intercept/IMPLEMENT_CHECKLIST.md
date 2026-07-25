# Intercept demo — implementer checklist

Design source: [`UX_SPEC.md`](UX_SPEC.md). Thin static SPA under `docs/demos/intercept/`. Do **not** rebuild the showcase matrix.

Implementation notes: [`IMPLEMENT_SUMMARY.md`](IMPLEMENT_SUMMARY.md).  
R2 implementer brief: [`UX_REVIEW_R2_BRIEF.md`](UX_REVIEW_R2_BRIEF.md).

Legend: **[R1]** done in first ship · **[R2]** required this iteration.

---

## A. Scaffold

- [x] **[R1]** Create `docs/demos/intercept/{index.html,app.js,styles.css}`
- [x] **[R1]** Copy dark CSS tokens from `docs/showcase/styles.css` (`--bg`, `--panel`, `--accent`, `--good`, `--bad`, `--warn`, …)
- [x] **[R1]** Load Plotly from CDN; no bundler required
- [x] **[R1]** Relative fetch to `./data/demo.json` (works on GH Pages subpath)
- [x] **[R1]** Loading + error empty states

## B. Data pack (offline builder)

### B1. Nominal + MC scalars (R1 — keep)

- [x] **[R1]** Identify success / fail nominal run dirs + success MC (`monte_carlo/trials.csv`, `summary.json`)
- [x] **[R1]** Emit `data/demo.json` with `schema_version`, `ui`, `cases`, `mc`
- [x] **[R1]** Downsample timeseries (~200–400 pts): `t`, `pos_plot` (N,E,up), `target_plot`, `range_m`
- [x] **[R1]** Case metrics: `min_range_m`, `time_of_min_range_s`, `intercept_success`, `capture_radius_m`
- [x] **[R1]** MC: inline `trials` with `min_range_m`, `intercept_success`, optional plant columns + `peak_tilt_rad`
- [x] **[R1]** Compute explicit `mc.summary.p_capture`, `n_intercept_success`, `n_trials` (do not confuse with tracking `success`)
- [x] **[R1]** Keep pack size browser-friendly (prefer &lt; ~5 MB)

### B2. MC trajectory bands (R2 — **required**; was nullable)

- [x] **[R2]** **Do not ship** primary demo with `"bands": null`
- [x] **[R2]** Extend `scripts/export_demo_data.py` (or sibling) to **generate band paths**:
  - Prefer **offline re-sim** of success-recipe mission per trial plant params (`mass_kg`, `ixx/iyy/izz`, `arm_length_m`, …) from `trials.csv`
  - Same controller gains / open-loop reference as study (`redesign_controller: false`)
  - Record ownship position vs time; convert to **plot frame (N, E, up)**
  - Optional: subsample ≥100 trials if full 500 is too slow; set `n_paths_used`
- [x] **[R2]** Common time grid `bands.t` (downsample ~100–300 pts OK)
- [x] **[R2]** Axis-wise percentiles into schema:

```json
"bands": {
  "frame": "plot",
  "percentiles": [5, 50, 95],
  "t": [],
  "n_paths_used": 0,
  "method": "axiswise_percentile",
  "notes": "…",
  "ownship": {
    "N": { "p5": [], "p50": [], "p95": [] },
    "E": { "p5": [], "p50": [], "p95": [] },
    "U": { "p5": [], "p50": [], "p95": [] }
  }
}
```

- [x] **[R2]** Document rebuild CLI in demo README (flags for band re-sim, sample count, seed)
- [x] **[R2]** Rebuild `data/demo.json` and verify `mc.bands.ownship.N.p5` length matches `bands.t`
- [x] **[R2]** Pack still &lt; ~5 MB after bands (quantile polylines only — **no** full trial path dump)

## C. Header + KPIs

- [x] **[R1]** Title + value prop + collapsible About
- [x] **[R1]** Case segmented control Success | Fail (hide Fail if missing)
- [x] **[R1]** KPI chips: **P(capture)**, **n trials**, **capture radius**
- [x] **[R1]** Nominal badge: Capture / Miss from active case metrics
- [x] **[R2]** Optional: muted note when Fail active — “MC / bands: success plant study”

## D. Geometry views + transport

### D1. 2D + transport (R1 — keep; bands become real data)

- [x] **[R1]** Plotly 2D N–E: target path, ownship path, markers at frame, optional trail
- [x] **[R1]** Capture-radius circle cue (dashed) — **keep required**
- [x] **[R1]** Projection toggle N–E | N–Up (if U data present)
- [x] **[R1]** MC bands toggle wired (was disabled when null)
- [x] **[R1]** Play / Pause, scrubber, time + range readouts
- [x] **[R1]** ←/→ frame step (Shift ±10)
- [x] **[R1]** Case change resets playhead and pauses
- [x] **[R1]** Optional: Jump to CPA
- [x] **[R2]** With non-null bands: default toggle **ON**; draw N–E fill between p5/p95 (+ optional p50 line)
- [x] **[R2]** Bands on N–Up if projection retained (N/U pairs)

### D2. Trajectory 3D (R2 — **required**)

- [x] **[R2]** Add Plotly `scatter3d` scene: axes **N / E / up** (showcase Flight path pattern)
- [x] **[R2]** Layers: full ownship path, full target path, scrub trail, markers at \(t_i\)
- [x] **[R2]** Fixed scene bounds from paths (+ band extents); dark scene; `uirevision` so camera survives scrub
- [x] **[R2]** Scrub/play updates markers/trail via **restyle** (not full newPlot every frame)
- [x] **[R2]** Case toggle rebuilds 3D traces for active nominal
- [x] **[R2]** MC envelope on 3D when bands on: p5/p50/p95 polylines (or translucent fan) from `mc.bands.ownship`
- [ ] **[R2]** Optional: capture sphere at CPA (nice-to-have)
- [x] **[R2]** Layout: dual-pane **3D | range(t)** primary; **2D N–E + bands** secondary (or 3D | 2D + range below) — see [`UX_REVIEW_R2_BRIEF.md`](UX_REVIEW_R2_BRIEF.md)
- [x] **[R2]** Shared transport under geometry; one `frameIndex` for 3D + 2D + range

### D3. Explicitly still skip

- [x] ~~Full showcase attitude/wrench dual-pane~~ (optional stretch only)
- [x] ~~Raw 3D cloud of all trial paths~~

## E. Time series

- [x] **[R1]** `range_m(t)` with horizontal line at `capture_radius_m`
- [x] **[R1]** Scrub-synced vertical playhead
- [x] **[R1]** Optional tilt strip — skipped
- [x] **[R2]** Confirm range pane still scrub-synced after layout split with 3D

## F. MC panel

- [x] **[R1]** Histogram of `min_range_m` + capture-radius vertical line
- [x] **[R1]** Restate P(capture) / n
- [x] **[R1]** Short “how to read” copy (plant scatter, fixed NDI, capture def)
- [x] **[R1]** Graceful hide if no MC
- [x] **[R2]** How-to-read bullet: bands = ownship spatial percentiles under plant re-sim (not sensor noise)

## G. Polish + ship

- [x] **[R1]** Footer: simulation-only + repo link
- [x] **[R1]** No dependency on `docs/showcase/data/showcase.json`
- [x] **[R1]** Smoke: open via local static server; play + scrub + histogram + case toggle
- [x] **[R2]** Smoke: 3D orbit + scrub; bands on/off on 2D and 3D; Success/Fail; pack has bands
- [x] **[R2]** Update demo README for 3D + band rebuild
- [ ] Link from project README when Pages path is live

## H. Explicitly skip (unchanged product scope)

- [x] ~~Controller × sensor matrix / envelope / compare~~
- [x] ~~Battery / SOC UI~~ (unless series already in pack)
- [x] ~~In-browser re-sim~~
- [x] ~~Full multi-trial path cloud in JSON~~

---

## Done when

All of [`UX_SPEC.md` §8 Acceptance criteria](UX_SPEC.md) pass on a static host, including:

- **§8.6** 3D flight path present and scrub-synced  
- **§8.7–8.8** MC bands toggleable and **non-null** in shipped success-MC pack  
