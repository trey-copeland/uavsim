# uavsim flight results (React)

Single-page React app that rolls up the **base case** into one document:

| Card | Study | Story |
|------|--------|--------|
| Figure-eight — LQR | `configs/studies/figure_eight.yaml` | Elevated lemniscate tracking (soft-checked vs ME590 LQR band) |
| Figure-eight — PID | `configs/studies/figure_eight_pid.yaml` | Second controller on the same mission |
| Figure-eight Monte Carlo | `configs/studies/figure_eight_mc.yaml` | N≈200 mass/inertia/arm robustness |

Mission: [`configs/missions/figure_eight.yaml`](../../configs/missions/figure_eight.yaml) — constant yaw, ≥4 s segments, altitude undulation.  
(Path-tangent auto-yaw on this class of path is a known failure mode; see `figure_eight_auto_yaw` for that stress case.)

Data lives in `data/showcase.json` (browser-safe, downsampled). No build step: React + Plotly load from CDN.

## Regenerate data

From the repo root:

```bash
uv sync --extra dev
uv run uavsim gallery --base-case
# writes docs/showcase/data/showcase.json (+ SPA files)
# optional: --n-mc-trials 8 for a quick smoke rebuild
```

Serve locally:

```bash
python -m http.server 8765 --directory docs/showcase
# open http://127.0.0.1:8765/
```

## Host on GitHub Pages

Workflow: [`.github/workflows/pages-showcase.yml`](../../.github/workflows/pages-showcase.yml)  
publishes this folder to the **`gh-pages`** branch (not the Actions Pages API).

### Site URL

**https://trey-copeland.github.io/uavsim/**

### If the live site is stuck on old JS

Symptoms: `app.js` on the site is smaller / older than `origin/gh-pages:app.js`, or
`last-modified` does not move after a green **Pages showcase** run.

1. Confirm **Settings → Pages → Source** is **Deploy from a branch**, branch **`gh-pages`**, folder **`/` (root)**. Save again if unsure (this triggers a rebuild).
2. Wait 1–2 minutes, then hard-refresh (or open `app.js?v=<newsha>`).
3. Workflow now **cache-busts** `app.js` / `styles.css` / `showcase.json` query strings and calls the Pages **request build** API after each deploy.

### Why deploys can look “successful” but the site stays old

Pushing to `gh-pages` only updates the branch. GitHub Pages must be **enabled and
pointed at that branch** to publish. The workflow tries to create/update that
config with `GITHUB_TOKEN`; if the token lacks permission, set Source in the UI.

## What’s in the UI

- **Overview** — metric cards for each base-case run  
- **Flight 3D** — rotate/zoom path, scrub time, velocity vector, strip charts  
- **Metrics** — full metric table + feasibility  
- **Monte Carlo** — summary, RMSE hist/CDF, correlation bars, multi-metric distribution grid, parameter sensitivity grid  
- **Compare** — LQR vs PID metric deltas + path overlay  
