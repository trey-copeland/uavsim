# uavsim results showcase (React)

Single-page React app that rolls up the **portfolio base case** into one document:

| Card | Study | Story |
|------|--------|--------|
| Gentle square — LQR | `configs/studies/gentle_square.yaml` | Waypoint tracking + min-snap |
| Gentle square — PID | `configs/studies/compare_lqr_vs_pid.yaml` | Second controller on same mission |
| Hover MC smoke | `configs/studies/hover_mc_smoke.yaml` | Seeded parametric robustness |

Data lives in `data/showcase.json` (browser-safe, downsampled). No build step: React + Plotly load from CDN.

## Regenerate data

From the repo root:

```bash
uv sync --extra dev
uv run uavsim gallery --base-case
# writes docs/showcase/data/showcase.json (+ copies SPA files)
```

Serve locally:

```bash
# any static server from docs/showcase
python -m http.server 8765 --directory docs/showcase
# open http://127.0.0.1:8765/
```

## Host on GitHub Pages

Workflow: [`.github/workflows/pages-showcase.yml`](../../.github/workflows/pages-showcase.yml).

### One-time setup (required)

If you see **Setup Pages** fail with *Get Pages site failed*, Pages is not
wired to Actions yet:

1. Open the repo on GitHub → **Settings → Pages**
2. Under **Build and deployment → Source**, choose **GitHub Actions** (not “Deploy from a branch”)
3. Re-run the failed workflow: **Actions → Pages showcase → Re-run jobs**  
   (or push a no-op change / use **Run workflow**)

No separate “build” is required; this folder is already static.

### After it works

| | |
|--|--|
| Site URL | `https://trey-copeland.github.io/uavsim/` |
| Local | `python -m http.server 8765 --directory docs/showcase` |

**Note:** The first deploy may also prompt to approve the `github-pages`
environment under **Settings → Environments** if protection rules are on.

## What’s in the UI

- **Overview** — metric cards for each base-case run  
- **Flight 3D** — rotate/zoom path, scrub time, velocity vector, strip charts  
- **Metrics** — full metric table + feasibility  
- **Monte Carlo** — hist, CDF, mass–RMSE scatter  
- **Compare** — LQR vs PID metric deltas + path overlay  
