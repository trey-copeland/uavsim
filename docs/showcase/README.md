# uavsim flight results (React)

Single-page React app for the portfolio base case: a **controller × sensor** matrix (LQR/LQG and PID), Monte Carlo, and a **hover-linearization envelope**.

## Base-case studies

| Cell | Study | Notes |
|------|--------|--------|
| Ideal LQR | `configs/studies/figure_eight.yaml` | Full true state (upper bound) |
| GPS+IMU naive → LQR | `figure_eight_gps_imu_naive.yaml` | `pos`+`omega`, zeros elsewhere → LQR |
| GPS+IMU LQG | `figure_eight_gps_imu_lqg.yaml` | Same sensors → linear KF → LQR |
| AHRS LQG | `figure_eight_ahrs_lqg.yaml` | GPS-denied: `att`+`omega` |
| IMU-only LQG | `figure_eight_imu_only_lqg.yaml` | Rates only — position not observable |
| Ideal PID | `figure_eight_pid.yaml` | Full-state cascade |
| GPS+IMU naive → PID | `figure_eight_gps_imu_naive_pid.yaml` | Same incomplete bus as LQR naive |
| GPS+IMU KF → PID | `figure_eight_gps_imu_kf_pid.yaml` | linear KF → PID (not classical LQG) |
| AHRS KF → PID | `figure_eight_ahrs_kf_pid.yaml` | `att`+`omega` → KF → PID |
| IMU-only KF → PID | `figure_eight_imu_only_kf_pid.yaml` | Rates only → KF → PID |
| MC | `figure_eight_gps_imu_lqg_mc.yaml` | Mass/inertia/arm under GPS+IMU LQG |
| **Overview** tab | matrix grid | Law × sensors RMSE cards |
| **Estimation** tab | grouped bars + table | LQR/LQG vs PID per column |

Mission: [`configs/missions/figure_eight.yaml`](../../configs/missions/figure_eight.yaml) — constant yaw, ≥4 s segments, altitude undulation.

**Naming:** LQG = linear KF + hover LQR. PID+KF is the cascade on \(\hat x\), not classical LQG.

Data lives in `data/showcase.json` (browser-safe, downsampled). No build step: React + Plotly load from CDN.

## Rebuild gallery

```bash
uv run uavsim gallery --base-case
# writes docs/showcase/data/showcase.json (+ SPA files)
```

Smoke (fewer MC trials, skip envelope):

```bash
uv run uavsim gallery --base-case --n-mc-trials 8 --skip-envelope
```

Local preview:

```bash
python -m http.server 8765 --directory docs/showcase
```

## GitHub Pages

Workflow: [`.github/workflows/pages-showcase.yml`](../../.github/workflows/pages-showcase.yml)  
publishes this folder to the **`gh-pages`** branch (not the Actions Pages API).

If the live site looks stale after a green **Pages showcase** run:

1. Hard-refresh / disable cache.
2. Confirm `data/meta.json` `generated_at` moved.
3. Workflow now **cache-busts** `app.js` / `styles.css` / `showcase.json` query strings and calls the Pages **request build** API after each deploy.

## Tabs

- **Overview** — controller × sensor RMSE grid + MC card  
- **Estimation** — grouped RMSE bars (LQR/LQG vs PID) + scenario table  
- **Flight 3D** — rotate/zoom path, scrub time, velocity vector, strip charts  
- **Metrics / Monte Carlo / Compare / Envelope** — as before  
