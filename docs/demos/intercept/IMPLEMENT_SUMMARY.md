# Intercept demo — implementation summary

| Field | Value |
|-------|--------|
| **Date** | 2026-07-25 |
| **Branch** | `feature/intercept-guidance-battery` |
| **Status** | SPA + exporter + sample pack shipped |
| **Location** | `docs/demos/intercept/` |

## Delivered

### Static SPA

| File | Role |
|------|------|
| [`index.html`](index.html) | Shell; Plotly CDN only (no React, no bundler) |
| [`app.js`](app.js) | State, transport, Plotly trajectory / range / histogram |
| [`styles.css`](styles.css) | Dark research tokens aligned with showcase (`--bg`, `--accent`, `--good`, …) |
| [`data/demo.json`](data/demo.json) | Offline pack (~783 KB) from real L0 success MC + fail nominal |

### Exporter

[`scripts/export_demo_data.py`](scripts/export_demo_data.py):

- Loads success (and optional fail) run dirs
- Downsamples nominal timeseries to ~320 pts with `pos_plot` / `target_plot` (N, E, up), `range_m`, optional ref
- Rebuilds target path from scripted mission YAML via `WaypointsGuidance`
- Merges `monte_carlo/trials.csv` or `shards/shard_*/trials.csv`
- Computes **`p_capture` / `n_intercept_success` from `intercept_success` only** (does not use tracking `success`)
- Emits compact trial rows for histogram; **`bands: null`** when no per-trial trajectories (UI hides band control)

### Data pack used for commit

| Source | Content |
|--------|---------|
| `runs/intercept_l0_success_mc_20260725T153348Z` | Nominal success + 500 plant MC trials (shards 0–7) |
| `runs/intercept_l0_fail_20260725T140842Z` | Miss nominal (min range ~3.78 m) |

Observed KPIs in pack:

- **P(capture) = 1.0** (500/500 `intercept_success`)
- Nominal success min range ~0.039 m; tracking `success` still **false** (attitude bounds) — intentional teaching point
- Fail min range ~3.78 m

## UX features (vs [`UX_SPEC.md`](UX_SPEC.md) §8)

| Acceptance | Status |
|------------|--------|
| KPI chips: P(capture), n, r | Done |
| Success \| Fail toggle | Done (both in pack) |
| 2D N–E trajectory + optional N–Up | Done |
| Capture circle at CPA target | Done |
| Play + scrub + time/range readouts | Done |
| ←/→ frame step, Shift ±10, space play | Done |
| Jump to CPA | Done |
| Range(t) + capture line + playhead | Done |
| min_range histogram + r line | Done |
| MC bands toggle | Wired; control disabled when `bands` absent |
| Empty / load error states | Done |
| Independent of showcase.json | Done |
| Static relative paths | Done |

## How to open

```bash
cd docs/demos/intercept && python -m http.server 8765
# http://127.0.0.1:8765/
```

## How to regenerate

```bash
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/<success_or_success_mc_run> \
  --fail-run runs/<fail_run> \
  --out docs/demos/intercept/data/demo.json
```

## Explicit non-goals (unchanged)

- Portfolio controller × sensor matrix
- Live re-sim, battery UI, full 3D trial cloud
- Per-trial MC trajectory bands (requires richer MC artifacts than trials.csv)

## Follow-ups (optional)

- Merge shard trials into `monte_carlo/trials.csv` at end of study pipeline for simpler loaders
- If MC stores per-trial paths, extend exporter to fill `mc.bands` (p5/p50/p95 polylines)
- Link demo from root `README.md` when GitHub Pages path is published
