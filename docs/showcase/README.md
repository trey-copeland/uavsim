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

**Recommended:** deploy only this folder (workflow in `.github/workflows/pages-showcase.yml`).

After the first successful workflow run, enable Pages:

1. Repo **Settings → Pages**
2. Source: **GitHub Actions**
3. Site URL: `https://<user>.github.io/uavsim/` (root = this showcase)

Alternatively, set Pages source to branch `master` / folder `/docs` and open  
`https://<user>.github.io/uavsim/showcase/`.

## What’s in the UI

- **Overview** — metric cards for each base-case run  
- **Flight 3D** — rotate/zoom path, scrub time, velocity vector, strip charts  
- **Metrics** — full metric table + feasibility  
- **Monte Carlo** — hist, CDF, mass–RMSE scatter  
- **Compare** — LQR vs PID metric deltas + path overlay  
