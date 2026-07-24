# uavsim flight results (React)

Single-page React app for the portfolio base case: a **guided technical report** with a **controller × sensor** matrix (LQR/LQG and PID) on **two missions** (baseline figure-eight and near-envelope + scheduled yaw), Flight 3D, Monte Carlo, and a **tracking envelope**.

**Walkthrough (header strip):** Matrix → Flight → Laws (LQR vs PID) → Envelope.  
**Mission** is a segmented control in the sticky header (rebinds all tabs).  
**Suggested first look** opens Flight on the envelope-edge mission.

## Base-case studies

| Cell | Study | Notes |
|------|--------|--------|
| Ideal LQR | `configs/studies/figure_eight.yaml` | Full true state (upper bound) |
| GPS+IMU naive → LQR | `figure_eight_gps_imu_naive.yaml` | `pos`+`omega`, zeros elsewhere → LQR |
| GPS+IMU LQG | `figure_eight_gps_imu_lqg.yaml` | Same sensors → linear KF → LQR |
| AHRS LQG | `figure_eight_ahrs_lqg.yaml` | GPS-denied: `att`+`omega` |
| **Flow+alt LQG** | **`figure_eight_flow_alt_lqg.yaml`** | **`body_vel`+`alt`+`omega` → KF → LQR** |
| IMU-only LQG | `figure_eight_imu_only_lqg.yaml` | Rates only — position not observable |
| Ideal PID | `figure_eight_pid.yaml` | Full-state cascade |
| GPS+IMU naive → PID | `figure_eight_gps_imu_naive_pid.yaml` | Same incomplete bus as LQR naive |
| GPS+IMU KF → PID | `figure_eight_gps_imu_kf_pid.yaml` | linear KF → PID (not classical LQG) |
| AHRS KF → PID | `figure_eight_ahrs_kf_pid.yaml` | `att`+`omega` → KF → PID |
| **Flow+alt KF → PID** | **`figure_eight_flow_alt_kf_pid.yaml`** | **Same flow+alt stack → PID** |
| IMU-only KF → PID | `figure_eight_imu_only_kf_pid.yaml` | Rates only → KF → PID |
| MC | `figure_eight_gps_imu_lqg_mc.yaml` | Mass/inertia/arm under GPS+IMU LQG |
| **Overview** tab | matrix grid | Law × sensors RMSE cards |
| **Estimation** tab | grouped bars + table | LQR/LQG vs PID per column |

Mission: [`configs/missions/figure_eight.yaml`](../../configs/missions/figure_eight.yaml) — constant yaw, ≥4 s segments, altitude undulation.

**Naming:** LQG = linear KF + hover LQR. PID+KF is the cascade on \(\hat x\), not classical LQG.  
**Full honesty list:** [docs/LIMITATIONS.md](../LIMITATIONS.md).  
**Flow+alt:** body-frame velocity (optical-flow *proxy*) + NED \(z\) altitude + gyro — practical GPS-denied teaching column.

Data lives in `data/showcase.json` (browser-safe, downsampled). No build step: React + Plotly load from CDN.

### Flight tab

Dual-pane scrubber view:

| Panel | Content |
|-------|---------|
| **Trajectory** (left) | Path + reference, trail, velocity arrow, body triad at the vehicle |
| **Vehicle attitude & wrench** (right) | X-quad mesh at origin, RGB body axes, thrust (−body \(z\)) and torque arrows scaled by magnitude, numeric HUD for \(F\), \(\|\tau\|\), \(\phi\theta\psi\), \(\|v\|\) |

Uses existing timeseries fields (`euler_deg`, `u`, `vel_ned`, `omega`, `limits`) — no gallery rebuild required for the UI.

## Rebuild gallery

```bash
uv run uavsim gallery --base-case
# writes docs/showcase/data/showcase.json (+ SPA files)
```

Smoke (fewer MC trials, skip envelope and/or edge mission):

```bash
uv run uavsim gallery --base-case --n-mc-trials 8 --skip-envelope
uv run uavsim gallery --base-case --n-mc-trials 2 --skip-envelope --skip-edge-mission
```

### Dual missions

| Mission | Path | Yaw | Role |
|---------|------|-----|------|
| **Baseline** | `configs/missions/figure_eight.yaml` | constant | Calm matrix teaching |
| **Envelope edge** | `configs/missions/figure_eight_envelope_edge.yaml` (τ★≈0.28) | `from_waypoints` scheduled ±~50° | Near hover-LQR linearization edge; full matrix twin |

UI: global **Mission** selector rebinds Overview matrix, Estimation bars/table, Flight/Metrics run list, MC, and Compare defaults.

### Envelope tab (τ sweep)

Sweeps **all 12 matrix schemes** (not only ideal LQR) over time-scale τ on the constant-yaw figure-eight:

- LQR row: ideal, GPS+IMU naive, GPS+IMU LQG, AHRS, flow+alt, IMU-only  
- PID row: same sensor stacks with cascade PID  

Shared position bound for comparable success. UI filters: All / LQR family / PID only + per-scheme toggles. Solid lines = LQR family, dashed = PID.

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
- **Metrics / Monte Carlo / Envelope** — as before  
- **Compare** — pick any two runs (A/B) for metric deltas + path overlay  

