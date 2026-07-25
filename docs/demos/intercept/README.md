# Intercept L0 demo (static SPA)

Thin single-mission dashboard for the L0 open-loop intercept + plant Monte Carlo story.

- **Spec:** [`UX_SPEC.md`](UX_SPEC.md)
- **Checklist:** [`IMPLEMENT_CHECKLIST.md`](IMPLEMENT_CHECKLIST.md)
- **Stack:** HTML + vanilla JS + Plotly CDN (no npm build)
- **Data:** [`data/demo.json`](data/demo.json) (offline pack; never reads `runs/` in the browser)

## Open the demo

Prefer a local static server (relative `fetch` of `data/demo.json` is blocked under many `file://` browsers):

```bash
# from this directory
cd docs/demos/intercept
python -m http.server 8765
# open http://127.0.0.1:8765/
```

Or from the repo root:

```bash
python -m http.server 8765
# open http://127.0.0.1:8765/docs/demos/intercept/
```

Optional query: `?case=fail` selects the miss nominal when present.

## What you should see

| UI | Notes |
|----|--------|
| KPI chips | **P(capture)** from `intercept_success`, **n trials**, **r capture** |
| Success \| Fail | Nominal geometry toggle (Fail hidden if not in pack) |
| N–E trajectory | Ownship + target, capture circle at CPA, scrub markers |
| Play / scrub | Transport bar; ←/→ step frames (Shift = ±10); space play/pause |
| Range(t) | Horizontal line at capture radius |
| MC histogram | `min_range_m` with vertical line at 1 m (or pack radius) |
| MC bands toggle | Shown only when `mc.bands` is present (skipped when only trial tables exist) |

**Capture ≠ tracking `success`.** Showcase-style attitude/position bounds often mark `success: false` even when `min_range_m ≤ capture_radius_m`.

## Regenerate `data/demo.json`

Exporter: [`scripts/export_demo_data.py`](scripts/export_demo_data.py).

```bash
# from repo root
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/intercept_l0_success_mc_<timestamp> \
  --fail-run runs/intercept_l0_fail_<timestamp> \
  --out docs/demos/intercept/data/demo.json
```

Arguments:

| Flag | Role |
|------|------|
| `--success-run` | Success study dir with `nominal/` and optional `monte_carlo/` |
| `--fail-run` | Optional miss nominal for case toggle |
| `--target-mission` | Scripted target YAML (default: `configs/missions/tutorials/intercept_l0_target.yaml`) |
| `--capture-radius-m` | Fallback radius if metrics omit it (default 1.0) |
| `--max-points` | Timeseries downsample (default 320) |

MC loading order:

1. `monte_carlo/trials.csv` if present
2. else merge `monte_carlo/shards/shard_*/trials.csv`

P(capture) is `mean(intercept_success)`. Trajectory percentile **bands** are only emitted when per-trial paths exist; table-only MC packs still get histogram + KPIs.

Example used for the committed pack (paths may differ on your machine):

```bash
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/intercept_l0_success_mc_20260725T153348Z \
  --fail-run runs/intercept_l0_fail_20260725T140842Z
```

## Files

```text
docs/demos/intercept/
  index.html
  app.js
  styles.css
  data/demo.json
  scripts/export_demo_data.py
  README.md
  UX_SPEC.md
  IMPLEMENT_CHECKLIST.md
```

Independent of [`docs/showcase/`](../../showcase/) portfolio matrix; visual tokens are aligned with the showcase dark research aesthetic.
