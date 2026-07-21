# uavsim flight results (React)

Single-page React app for the portfolio base case: **ideal LQR**, an **estimation/LQG sensor matrix**, PID, Monte Carlo, and a **hover-linearization envelope**.

| Card / tab | Study | Story |
|------------|--------|--------|
| Ideal LQR | `configs/studies/figure_eight.yaml` | Full true state (upper bound) |
| GPS+IMU naive | `figure_eight_gps_imu_naive.yaml` | `pos`+`omega`, zeros elsewhere → LQR |
| GPS+IMU LQG | `figure_eight_gps_imu_lqg.yaml` | Same sensors → linear KF → LQR |
| AHRS LQG | `figure_eight_ahrs_lqg.yaml` | GPS-denied: `att`+`omega` |
| IMU-only LQG | `figure_eight_imu_only_lqg.yaml` | Rates only — position not observable |
| PID | `figure_eight_pid.yaml` | Second controller, full state |
| MC | `figure_eight_gps_imu_lqg_mc.yaml` | Mass/inertia/arm under GPS+IMU LQG |
| **Estimation** tab | matrix metadata | Benefit → GPS-denied win → weakness |
| **Envelope** tab | time-scale sweep | Limits of **idealized** hover LQR |

Mission: [`configs/missions/figure_eight.yaml`](../../configs/missions/figure_eight.yaml) — constant yaw, ≥4 s segments, altitude undulation.

### Two different questions

1. **Estimation tab** — *Do we need a filter when sensors are partial?*  
   Same mission and \(K\); change only the measurement bus / observer.
2. **Envelope tab** — *Where does hover-linearized full-state LQR fail as the path gets aggressive?*  
   Time-scale τ compresses the figure-eight; primary curve is ideal LQR (LQG overlay optional).

Data lives in `data/showcase.json` (browser-safe, downsampled). No build step: React + Plotly load from CDN.

## Regenerate data

From the repo root:

```bash
uv sync --extra dev
uv run uavsim gallery --base-case
# writes docs/showcase/data/showcase.json (+ SPA files)
# optional: --n-mc-trials 8 for a quick smoke rebuild
# optional: --skip-envelope to skip the LQR stress sweep
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
- **Estimation** — LQG teaching matrix (RMSE bars + scenario table)  
- **Flight 3D** — rotate/zoom path, scrub time, velocity vector, strip charts  
- **Metrics** — full metric table + feasibility  
- **Monte Carlo** — summary, RMSE hist/CDF, sensitivity (GPS+IMU LQG MC)  
- **Envelope** — ideal LQR time-scale limits (optional LQG overlay)  
- **Compare** — GPS+IMU **naive vs LQG** metric deltas + path overlay  
