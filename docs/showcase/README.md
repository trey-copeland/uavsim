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
# writes docs/showcase/data/showcase.json (+ SPA files)
```

Serve locally:

```bash
python -m http.server 8765 --directory docs/showcase
# open http://127.0.0.1:8765/
```

## Host on GitHub Pages

Workflow: [`.github/workflows/pages-showcase.yml`](../../.github/workflows/pages-showcase.yml)  
publishes this folder to the **`gh-pages`** branch (not the Actions Pages API).

### After the first successful workflow run

1. Open the repo → **Settings → Pages**
2. **Build and deployment → Source:** **Deploy from a branch**
3. **Branch:** `gh-pages` / **`/` (root)** → Save
4. Site URL: **`https://trey-copeland.github.io/uavsim/`**

You only need that branch picker once. Later pushes that touch `docs/showcase/**`
update the site automatically.

### Why not “Source: GitHub Actions”?

`actions/configure-pages` calls the Pages REST API and fails with **404 Not Found**
until a Pages site already exists. Branch deploy via `peaceiris/actions-gh-pages`
avoids that chicken-and-egg.

## What’s in the UI

- **Overview** — metric cards for each base-case run  
- **Flight 3D** — rotate/zoom path, scrub time, velocity vector, strip charts  
- **Metrics** — full metric table + feasibility  
- **Monte Carlo** — hist, CDF, mass–RMSE scatter  
- **Compare** — LQR vs PID metric deltas + path overlay  
