# Intercept L0 demo (static SPA)

Thin single-mission dashboard for the L0 open-loop intercept + plant Monte Carlo story.

- **Spec:** [`UX_SPEC.md`](UX_SPEC.md)
- **Checklist:** [`IMPLEMENT_CHECKLIST.md`](IMPLEMENT_CHECKLIST.md)
- **R2 brief:** [`UX_REVIEW_R2_BRIEF.md`](UX_REVIEW_R2_BRIEF.md)
- **Stack:** HTML + vanilla JS + Plotly CDN (no npm build)
- **Data:** [`data/demo.json`](data/demo.json) (offline pack; never reads `runs/` in the browser)

## Live (GitHub Pages)

When `main` updates `docs/demos/intercept/**` (or the Pages workflow is dispatched), CI assembles the site and publishes:

| URL | Content |
|-----|---------|
| […/uavsim/](https://trey-copeland.github.io/uavsim/) | Portfolio showcase (root) |
| […/uavsim/intercept/](https://trey-copeland.github.io/uavsim/intercept/) | **This intercept demo** |

Workflow: [`.github/workflows/pages-site.yml`](../../../.github/workflows/pages-site.yml) (showcase + intercept together so one does not wipe the other).

Committed `data/demo.json` is what Pages serves — regenerate offline after MC runs, commit the pack, merge to `main`.

## Open the demo locally

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
| **3D trajectory** | Ownship + target paths, scrub markers/trail, optional MC p5/p50/p95 fan |
| **2D N–E** | Paths + capture circle at CPA + **MC band fill** (default ON when present) |
| Play / scrub | Shared transport; ←/→ step frames (Shift = ±10); space play/pause |
| Range(t) | Horizontal line at capture radius; scrub playhead |
| MC histogram | `min_range_m` with vertical line at 1 m (or pack radius) |
| MC bands toggle | Global for 2D fill + 3D percentile polylines |

**Capture ≠ tracking `success`.** Showcase-style attitude/position bounds often mark `success: false` even when `min_range_m ≤ capture_radius_m`.

## Regenerate `data/demo.json`

Exporter: [`scripts/export_demo_data.py`](scripts/export_demo_data.py).

```bash
# from repo root — full R2 pack with MC trajectory bands
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/intercept_l0_success_mc_<timestamp> \
  --fail-run runs/intercept_l0_fail_<timestamp> \
  --with-bands \
  --band-max-trials 100 \
  --out docs/demos/intercept/data/demo.json
```

Arguments:

| Flag | Role |
|------|------|
| `--success-run` | Success study dir with `nominal/` and optional `monte_carlo/` |
| `--fail-run` | Optional miss nominal for case toggle |
| `--target-mission` | Scripted target YAML (default: `configs/missions/tutorials/intercept_l0_target.yaml`) |
| `--capture-radius-m` | Fallback radius if metrics omit it (default 1.0) |
| `--max-points` | Nominal timeseries downsample (default 320) |
| `--with-bands` / `--no-with-bands` | Re-sim plant trials for `mc.bands` (default **on** when trials exist) |
| `--band-max-trials` | Max trials to re-sim for percentiles (default **100**; can use 200–500) |
| `--band-points` | Common time grid length for band polylines (default 160) |
| `--band-seed` | Seed for trial subsample when `band-max-trials < n_trials` |

### How bands are built

1. Load success study `monte_carlo/trials.csv` (plant columns: `mass_kg`, `ixx/iyy/izz`, `arm_length_m`, …).
2. For each selected trial, re-simulate the success recipe with that plant and **fixed NDI** (`redesign_controller: false`).
3. Convert ownship NED → plot frame (N, E, up); resample onto a common `t` grid.
4. Axis-wise p5 / p50 / p95 → `mc.bands.ownship.{N,E,U}`.

`n_paths_used` is written honestly (may be less than full MC if subsampled). Pack stays small (quantile polylines only — no full trial path dump).

MC loading order for the scalar table:

1. `monte_carlo/trials.csv` if present
2. else merge `monte_carlo/shards/shard_*/trials.csv`

P(capture) is `mean(intercept_success)`.

Example used for the committed pack:

```bash
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/intercept_l0_success_mc_20260725T153348Z \
  --fail-run runs/intercept_l0_fail_20260725T140842Z \
  --with-bands --band-max-trials 100
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
  UX_REVIEW_R2_BRIEF.md
  IMPLEMENT_CHECKLIST.md
  IMPLEMENT_SUMMARY_R2.md
```

Independent of [`docs/showcase/`](../../showcase/) portfolio matrix; visual tokens and 3D path patterns are aligned with the showcase dark research aesthetic.
