# Intercept demo — IMPLEMENT_SUMMARY (R3)

| Field | Value |
|-------|--------|
| **Iteration** | R3 (layout + attitude + battery + pad/GE story) |
| **Date** | 2026-07-25 |
| **Branch** | `feature/intercept-guidance-battery` |
| **Normative** | [`UX_SPEC.md`](UX_SPEC.md) §8 · [`UX_REVIEW_R3_BRIEF.md`](UX_REVIEW_R3_BRIEF.md) |

## Shipped

### Layout / chrome

- **Sticky stack** (`.sticky-chrome`): header + **transport** stay under viewport top while scrolling plots (showcase sticky pattern).
- Transport controls: Play, Jump to CPA, scrub, t/range readouts, speed, **MC bands** toggle, compact **SOC strip**.
- **Primary row:** Trajectory **3D** | **Attitude @ origin**.
- **Secondary row:** Trajectory **2D** N–E | **Range vs time**.
- **Battery row** when `soc` / `power_w` / `energy_wh_remaining` present; omitted otherwise.
- Responsive: rows stack ≤960px.

### Attitude

- Ported showcase helpers into vanilla IIFE: `rotationBodyToNed`, `bodyToPlot`, X-quad `vehicleGeom`, body axes.
- Plotly scene fixed cube ~±1.05 m; restyle airframe/motors/axes on scrub; `uirevision: att-<case>`.
- Driven by `timeseries.euler_deg[frameIndex]`.

### Battery

- SOC gauge (card) + transport strip scrub-synced (fraction → %).
- `power_w(t)` and `energy_wh_remaining(t)` with playhead.
- Optional KPI chip: SOC final from metrics.

### MC bands (retained)

- Default **ON** when `mc.bands` present; shared toggle on transport.
- 2D p5–p95 fill + p50; 3D p5/p50/p95 polylines.

### Story / copy

- Pad takeoff + climb through **ground effect** in value prop, story strip, About, how-to-read.
- `ui.mission_notes = "pad_climb_ground_effect"`.

### Exporter

[`scripts/export_demo_data.py`](scripts/export_demo_data.py):

- Pass-through `soc`, `power_w`, `energy_wh_remaining`, optional `u` (same downsample as `t`).
- Metrics: `soc_final`, `soc_min`, `peak_power_w`, `battery_enabled`.
- Keep `euler_deg` from `x[:, 3:6]`.
- UI strings for pad/GE + battery.
- Bands generation unchanged (works with climb mission study).

### Data pack

```bash
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/intercept_l0_success_mc_20260725T163635Z \
  --fail-run runs/intercept_l0_fail_20260725T163623Z \
  --with-bands --band-max-trials 80 \
  --out docs/demos/intercept/data/demo.json
```

| Check | Result |
|-------|--------|
| Cases | success + fail |
| Battery series | present on both nominals |
| `euler_deg` | present |
| `mc.bands` | non-null; `n_paths_used=80`; t len 160 |
| MC trials | 500; P(capture)=1.0 (this plant scatter set) |
| Pack size | ~1.0 MB |

## Files touched

| Path | Change |
|------|--------|
| `docs/demos/intercept/app.js` | R3 SPA (layout, attitude, battery, sticky transport) |
| `docs/demos/intercept/styles.css` | sticky chrome, primary/secondary rows, SOC/battery |
| `docs/demos/intercept/index.html` | cache bust v=3 |
| `docs/demos/intercept/scripts/export_demo_data.py` | battery + ui pad/GE |
| `docs/demos/intercept/data/demo.json` | rebuilt pack |
| `docs/demos/intercept/README.md` | R3 docs |
| `docs/demos/intercept/IMPLEMENT_CHECKLIST.md` | R3 items checked |
| `docs/demos/intercept/IMPLEMENT_SUMMARY_R3.md` | this file |

## Acceptance (self-check)

1. Transport visible under header without scrolling past plots; sticky while scrolling.
2. Primary = 3D | attitude; secondary = 2D | range.
3. Scrub/play moves markers, attitude mesh, range cursor, SOC + power/energy playheads together.
4. MC bands default ON → 2D fill + 3D percentile curves; toggle clears both.
5. Pack has non-null `mc.bands` with N/E/U p5/p95.
6. Battery card works with series; story mentions pad + ground effect.
7. Success | Fail; P(capture) from intercept_success.
8. Static only — no npm; CDN Plotly; relative `./data/demo.json`.

## Local smoke

```bash
cd docs/demos/intercept && python -m http.server 8765
# http://127.0.0.1:8765/
```

## Out of scope (unchanged)

- In-browser re-sim, full 500-path cloud, required wrench HUD, capture math / MC design changes, portfolio matrix.
