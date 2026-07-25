# Intercept demo — implementer checklist

Design source: [`UX_SPEC.md`](UX_SPEC.md) (**R3**). Thin static SPA under `docs/demos/intercept/`. Do **not** rebuild the showcase matrix.

Implementation notes: [`IMPLEMENT_SUMMARY.md`](IMPLEMENT_SUMMARY.md), [`IMPLEMENT_SUMMARY_R2.md`](IMPLEMENT_SUMMARY_R2.md).  
R2 implementer brief: [`UX_REVIEW_R2_BRIEF.md`](UX_REVIEW_R2_BRIEF.md).  
**R3 implementer brief:** [`UX_REVIEW_R3_BRIEF.md`](UX_REVIEW_R3_BRIEF.md).

Legend: **[R1]** done in first ship · **[R2]** done prior iteration · **[R3]** required this iteration.

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
- [x] **[R2]** Extend `scripts/export_demo_data.py` (or sibling) to **generate band paths**
- [x] **[R2]** Common time grid `bands.t` (downsample ~100–300 pts OK)
- [x] **[R2]** Axis-wise percentiles schema (`ownship.N/E/U.p5|p50|p95`)
- [x] **[R2]** Document rebuild CLI in demo README
- [x] **[R2]** Rebuild `data/demo.json` and verify `mc.bands.ownship.N.p5` length matches `bands.t`
- [x] **[R2]** Pack still &lt; ~5 MB after bands

### B3. Attitude + battery fields (R3)

- [x] **[R3]** Ensure exporter always emits `timeseries.euler_deg` when `x` has attitude (`x[:, 3:6]` rad → deg) for success **and** fail cases
- [x] **[R3]** Pass through battery series when present in nominal timeseries / npz:
  - `soc`
  - `power_w`
  - `energy_wh_remaining`
  - Same downsample index as `t` / `pos_plot`
- [x] **[R3]** Optional metrics pass-through: `soc_final`, `soc_min`, `peak_power_w`, `battery_enabled`
- [x] **[R3]** Optional `timeseries.u` if wrench/rotor viz desired (not required for R3 attitude mesh)
- [x] **[R3]** Update `ui.value_prop` / `ui.about_paragraphs` for **pad climb + ground effect** story
- [x] **[R3]** Rebuild `data/demo.json` after study runs include battery (if enabled); verify keys exist or are honestly absent

## C. Header + KPIs

- [x] **[R1]** Title + value prop + collapsible About
- [x] **[R1]** Case segmented control Success | Fail (hide Fail if missing)
- [x] **[R1]** KPI chips: **P(capture)**, **n trials**, **capture radius**
- [x] **[R1]** Nominal badge: Capture / Miss from active case metrics
- [x] **[R2]** Optional: muted note when Fail active — “MC / bands: success plant study”
- [x] **[R3]** Story strip / About copy: **pad takeoff, climb, ground effect**
- [x] **[R3]** Optional KPI chip: SOC final or SOC min when battery metrics present

## D. Geometry views + transport

### D0. Transport at TOP (R3 — **hard**)

- [x] **[R3]** Move play/scrub transport **under header, above geometry** (not only below 2D/range)
- [x] **[R3]** CSS: sticky stack (header + transport) — mirror showcase `.sticky-header` (dark translucent, high z-index)
- [x] **[R3]** Controls remain: Play/Pause, scrub, CPA, speed, bands toggle, t + range readouts
- [x] **[R3]** Optional compact **SOC strip** in transport when battery data present
- [x] **[R3]** One `frameIndex` still drives **3D + attitude + 2D + range + battery**

### D1. 2D + bands (R1/R2 — keep; position changes in R3)

- [x] **[R1]** Plotly 2D N–E: target path, ownship path, markers at frame, optional trail
- [x] **[R1]** Capture-radius circle cue (dashed) — **keep required**
- [x] **[R1]** Projection toggle N–E | N–Up (if U data present)
- [x] **[R1]** MC bands toggle wired
- [x] **[R1]** Play / Pause, scrubber, time + range readouts
- [x] **[R1]** ←/→ frame step (Shift ±10)
- [x] **[R1]** Case change resets playhead and pauses
- [x] **[R1]** Optional: Jump to CPA
- [x] **[R2]** With non-null bands: default toggle **ON**; draw N–E fill between p5/p95 (+ optional p50 line)
- [x] **[R2]** Bands on N–Up if projection retained (N/U pairs)
- [x] **[R3]** Place **2D N–E** in **secondary row left** (side-by-side with range)

### D2. Trajectory 3D (R2 — keep)

- [x] **[R2]** Plotly `scatter3d` scene: axes **N / E / up**
- [x] **[R2]** Layers: full ownship path, full target path, scrub trail, markers at \(t_i\)
- [x] **[R2]** Fixed scene bounds; dark scene; `uirevision`; restyle on scrub
- [x] **[R2]** Case toggle rebuilds 3D traces
- [x] **[R2]** MC envelope on 3D when bands on: p5/p50/p95 from `mc.bands.ownship`
- [ ] **[R2]** Optional: capture sphere at CPA (nice-to-have)
- [x] **[R3]** Confirm 3D remains **primary left**; bands still visible by default when data present

### D3. Attitude pane (R3 — **hard**)

- [x] **[R3]** Add Plotly attitude view **primary right** (replaces range in that slot)
- [x] **[R3]** Port/adapt showcase patterns from `docs/showcase/app.js`:
  - `rotationBodyToNed` / `bodyToPlot` / `vehicleGeom` (X-quad at origin)
  - Fixed cube FOV; dark scene; body axes
  - `Plotly.restyle` on scrub; `newPlot` on case change
- [x] **[R3]** Drive pose from `timeseries.euler_deg[frameIndex]`
- [x] **[R3]** Wrench / per-rotor thrust **optional** (only if `u` in pack)
- [x] **[R3]** Honest empty state if euler missing

### D4. Secondary: range beside 2D (R3 — **hard**)

- [x] **[R3]** Move `range_m(t)` to **secondary row right**, next to 2D N–E
- [x] **[R1/R2]** Capture line + scrub playhead (retain behavior)
- [x] **[R3]** CSS: `.secondary-row` two-column; stack ≤960px

### D5. Explicitly still skip

- [x] ~~Raw 3D cloud of all trial paths~~
- [ ] ~~Full showcase wrench HUD required~~ (optional only)

## E. Time series + battery

- [x] **[R1]** `range_m(t)` with horizontal line at `capture_radius_m`
- [x] **[R1]** Scrub-synced vertical playhead
- [x] **[R1]** Optional tilt strip — skipped
- [x] **[R2]** Range scrub-synced after layout with 3D
- [x] **[R3]** Battery row when any of `soc` / `power_w` / `energy_wh_remaining` present:
  - [x] SOC gauge/bar scrub-synced
  - [x] `power_w(t)` plot with playhead (if present)
  - [x] `energy_wh_remaining(t)` plot with playhead (if present)
- [x] **[R3]** Omit entire battery block when series absent (no empty charts)

## F. MC panel

- [x] **[R1]** Histogram of `min_range_m` + capture-radius vertical line
- [x] **[R1]** Restate P(capture) / n
- [x] **[R1]** Short “how to read” copy (plant scatter, fixed NDI, capture def)
- [x] **[R1]** Graceful hide if no MC
- [x] **[R2]** How-to-read bullet: bands = ownship spatial percentiles under plant re-sim
- [x] **[R3]** How-to / story consistency with pad climb + GE (one line OK)

## G. Polish + ship

- [x] **[R1]** Footer: simulation-only + repo link
- [x] **[R1]** No dependency on `docs/showcase/data/showcase.json`
- [x] **[R1]** Smoke: open via local static server; play + scrub + histogram + case toggle
- [x] **[R2]** Smoke: 3D orbit + scrub; bands on/off on 2D and 3D; Success/Fail; pack has bands
- [x] **[R2]** Update demo README for 3D + band rebuild
- [x] **[R3]** Smoke: sticky top transport works while scrolling; attitude scrubs; range sits beside 2D; battery updates if data present
- [x] **[R3]** Update demo README for R3 layout + battery export fields
- [ ] Link from project README when Pages path is live

## H. Explicitly skip (product scope)

- [x] ~~Controller × sensor matrix / envelope / compare~~
- [x] ~~In-browser re-sim~~
- [x] ~~Full multi-trial path cloud in JSON~~
- [ ] ~~Require wrench HUD without `u`~~

---

## Done when

All of [`UX_SPEC.md` §8 Acceptance criteria](UX_SPEC.md) (R3) pass on a static host, including:

- **§8.3** Top sticky play/scrub transport  
- **§8.7** Attitude right of 3D  
- **§8.8** Range beside 2D N–E  
- **§8.9–8.10** MC bands visible on 2D + 3D; non-null pack  
- **§8.11** Battery when series present  
- **§8.12** Pad climb / GE story copy  
