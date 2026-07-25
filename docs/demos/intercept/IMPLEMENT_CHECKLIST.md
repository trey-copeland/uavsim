# Intercept demo — implementer checklist

Design source: [`UX_SPEC.md`](UX_SPEC.md). Thin static SPA under `docs/demos/intercept/`. Do **not** rebuild the showcase matrix.

Implementation notes: [`IMPLEMENT_SUMMARY.md`](IMPLEMENT_SUMMARY.md).

---

## A. Scaffold

- [x] Create `docs/demos/intercept/{index.html,app.js,styles.css}`
- [x] Copy dark CSS tokens from `docs/showcase/styles.css` (`--bg`, `--panel`, `--accent`, `--good`, `--bad`, `--warn`, …)
- [x] Load Plotly from CDN; no bundler required
- [x] Relative fetch to `./data/demo.json` (works on GH Pages subpath)
- [x] Loading + error empty states

## B. Data pack (offline builder — can be script later)

- [x] Identify success / fail nominal run dirs + success MC (`monte_carlo/trials.csv`, `summary.json`)
- [x] Emit `data/demo.json` with `schema_version`, `ui`, `cases`, `mc`
- [x] Downsample timeseries (~200–400 pts): `t`, `pos_plot` (N,E,up), `target_plot`, `range_m`
- [x] Case metrics: `min_range_m`, `time_of_min_range_s`, `intercept_success`, `capture_radius_m`
- [x] MC: inline `trials` (or CSV) with `min_range_m`, `intercept_success`, optional `peak_tilt_rad`
- [x] Compute explicit `mc.summary.p_capture`, `n_intercept_success`, `n_trials` (do not confuse with tracking `success`)
- [x] Optional: `mc.bands` percentile polylines for ownship N/E/U — **null when only trial table** (UI hides toggle)
- [x] Keep pack size browser-friendly (prefer &lt; ~5 MB) — pack ~0.8 MB

## C. Header + KPIs

- [x] Title + value prop + collapsible About
- [x] Case segmented control Success | Fail (hide Fail if missing)
- [x] KPI chips: **P(capture)**, **n trials**, **capture radius**
- [x] Nominal badge: Capture / Miss from active case metrics

## D. Trajectory 2D + transport

- [x] Plotly 2D N–E: target path, ownship path, markers at frame, optional trail
- [x] Capture-radius circle cue (dashed)
- [x] Projection toggle N–E | N–Up (if U data present)
- [x] MC bands toggle (default on when `mc.bands` exists; disable otherwise)
- [x] Play / Pause, scrubber, time + range readouts
- [x] ←/→ frame step (Shift ±10)
- [x] Case change resets playhead and pauses
- [x] Optional: Jump to CPA (`time_of_min_range_s`)

## E. Time series

- [x] `range_m(t)` with horizontal line at `capture_radius_m`
- [x] Scrub-synced vertical playhead
- [x] Optional: tilt or tracking error strip — skipped v1

## F. MC panel

- [x] Histogram of `min_range_m` + capture-radius vertical line
- [x] Restate P(capture) / n
- [x] Short “how to read” copy (plant scatter, fixed NDI, capture def)
- [x] Graceful hide if no MC

## G. Polish + ship

- [x] Footer: simulation-only + repo link
- [x] No dependency on `docs/showcase/data/showcase.json`
- [x] Smoke: open via local static server; play + scrub + histogram + case toggle
- [x] Document rebuild one-liner in `data/README.md` or parent README when generator exists
- [ ] Link from project README when Pages path is live

## H. Explicitly skip (v1)

- [x] ~~Controller × sensor matrix / envelope / compare~~
- [x] ~~Full Flight 3D dual-pane attitude mesh~~
- [x] ~~Battery / SOC UI~~ (unless series already in pack)
- [x] ~~In-browser re-sim~~
- [x] ~~3D trial cloud~~

---

## Done when

All of [`UX_SPEC.md` §8 Acceptance criteria](UX_SPEC.md) pass on a static host.
