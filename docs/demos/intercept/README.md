# Intercept demo (static SPA)

Dashboard for the **pad climb + ground-effect** intercept story: online `intercept_pursue` (G-6) + NDI + MEKF GPS/IMU + battery + plant Monte Carlo (pack rebuilt from online MC runs).

**Tutorials (how we built / how to run):** [T-GUIDE-ONLINE](../tutorials/01_online_intercept.md) · [T-ENERGY](../tutorials/02_battery_energy.md) · [tutorials index](../tutorials/README.md)

- **Spec:** [`UX_SPEC.md`](UX_SPEC.md) (**R3**)
- **Checklist:** [`IMPLEMENT_CHECKLIST.md`](IMPLEMENT_CHECKLIST.md)
- **R3 brief:** [`UX_REVIEW_R3_BRIEF.md`](UX_REVIEW_R3_BRIEF.md)
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

Optional query: `?case=fail` selects the **energy-fail** nominal (SOC depleted) when present.

## What you should see (R3)

| UI | Notes |
|----|--------|
| **Sticky transport** | Play / scrub / CPA / speed / **MC bands** under header (always reachable) |
| KPI chips | **P(capture)** from `intercept_success`, **n trials**, **r capture**, optional **SOC final** |
| Success \| Fail | Nominal geometry + attitude + battery toggle |
| Primary | **3D trajectory** (N/E/up) + **attitude @ origin** (X-quad + body axes) |
| Secondary | **2D N–E** (capture circle + MC fill) \| **range(t)** |
| Battery | SOC gauge + `power_w(t)` + `energy_wh_remaining(t)` when pack has series |
| MC histogram | `min_range_m` with vertical line at capture radius |
| Story | Pad takeoff → climb through **ground effect** → intercept |

**Capture ≠ tracking `success`.** Showcase-style attitude/position bounds often mark `success: false` even when `min_range_m ≤ capture_radius_m`.

## Regenerate `data/demo.json`

Exporter: [`scripts/export_demo_data.py`](scripts/export_demo_data.py).

Passes through **euler_deg**, **soc**, **power_w**, **energy_wh_remaining**, optional **u**, battery metrics, and builds **mc.bands**.

```bash
# from repo root — R3 pack with battery + MC trajectory bands
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/intercept_l0_success_mc_<timestamp> \
  --fail-run runs/intercept_l0_fail_<timestamp> \
  --with-bands \
  --band-max-trials 80 \
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
| `--band-max-trials` | Max trials to re-sim for percentiles (default **100**; 80–100 is fine) |
| `--band-points` | Common time grid length for band polylines (default 160) |
| `--band-seed` | Seed for trial subsample when `band-max-trials < n_trials` |

### Timeseries fields (case packs)

| Field | Source |
|-------|--------|
| `t`, `pos_plot`, `target_plot`, `range_m` | state + scripted target |
| `euler_deg` | `rad2deg(x[:, 3:6])` |
| `soc`, `power_w`, `energy_wh_remaining` | `timeseries.npz` when battery enabled |
| `u` | wrench (optional attitude/rotor viz) |

### How bands are built

1. Load success study `monte_carlo/trials.csv` (or merge shard CSVs).
2. For each selected trial, re-simulate the success recipe with that plant and **fixed NDI**.
3. Convert ownship NED → plot frame (N, E, up); resample onto a common `t` grid.
4. Axis-wise p5 / p50 / p95 → `mc.bands.ownship.{N,E,U}`.

`n_paths_used` is written honestly. Pack stays small (quantile polylines only).

P(capture) is `mean(intercept_success)`.

Example used for the committed **online** pack:

```bash
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/intercept_online_success_mc_20260725T190528Z \
  --fail-run runs/intercept_online_energy_fail_20260725T190528Z \
  --with-bands --band-max-trials 80
# → p_capture ≈ 0.28; tracking RMSE vs commanded x_r (~0.4 m class);
#    fail case = energy-depleted nominal (SOC→0, no thrust derate)
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
  UX_REVIEW_R3_BRIEF.md
  IMPLEMENT_CHECKLIST.md
  IMPLEMENT_SUMMARY_R3.md
```

Independent of [`docs/showcase/`](../../showcase/) portfolio matrix; attitude mesh patterns and sticky chrome are adapted from the showcase Flight tab (no runtime import).
