# Estimation & observers (Phase 5d)

**Package:** `uavsim.estimation`  
**Loop:** plant → noisy measurements → **observer** → controller → plant  

Default SIL remains **full-state** (`sim.observer.type: none`): no noise, controller sees true Euler 12-state. That preserves existing goldens and the portfolio ideal-LQR path.

LQG in this project means **hover LQR on a linear KF estimate** (same \(K\), different bus \(x\)).  
PID + KF is the cascade law on \(\hat x\) — not classical LQG.

---

## Study config

```yaml
sim:
  dt_s: 0.01
  attitude: euler          # or quat (Phase 5c plant)
  observer:
    type: none             # none | partial_raw | linear_kf | mekf
    seed: 7
    pos_sigma_m: 0.05
    vel_sigma_m_s: 0.05
    att_sigma_rad: 0.03
    omega_sigma_rad_s: 0.04
    process_sigma: 0.03
    alt_sigma_m: 0.04              # optional; default = pos_sigma
    body_vel_sigma_m_s: 0.08       # optional; default = vel_sigma
    channels: [pos, omega]         # or body_vel, alt, …
```

| Type | Role |
|------|------|
| `none` | Identity: controller sees true full state; RK45 path when plant is Euler |
| `partial_raw` | **Naive teaching baseline:** noisy measured channels packed into 12-state; **unmeasured = 0** |
| `linear_kf` | 12-state KF using hover \(A,B\) (same linearization as LQR); supports partial \(H\) |
| `mekf` | Error-state filter: nominal \(p,v,q,\omega\) + \([\delta p,\delta v,\delta\theta]\); multiplicative attitude |

### Channels

| Name | Aliases | Meaning | Dim |
|------|---------|---------|-----|
| `pos` | position | NED position | 3 |
| `att` | attitude | ZYX Euler | 3 |
| `vel` | velocity | NED velocity | 3 |
| `omega` | gyro, rate | Body rates | 3 |
| `alt` | z, height, range | NED \(z\) only (baro/range stand-in; \(z+\) down) | 1 |
| `vel_xy` | v_xy | NED north/east velocity | 2 |
| **`body_vel`** | **flow, optical_flow, of** | **Body velocity \(R_{b\to i}^\top v_i\)** (optical-flow proxy) | 3 |

KF \(H\) for `body_vel` uses the **hover-linear** NED velocity block (\(v_b \approx v_i\) at small tilt). Truth measurements still form \(R^\top v\).

### Sensor stories (showcase matrix)

| Story | Channels | Observer | Intent |
|-------|----------|----------|--------|
| Ideal LQR / PID | — (truth) | `none` | Upper bound |
| GPS + IMU naive | `pos`, `omega` | `partial_raw` | Incomplete bus breaks control |
| GPS + IMU + KF | `pos`, `omega` | `linear_kf` | Reconstruction + noise rejection |
| GPS-denied AHRS | `att`, `omega` | `linear_kf` | Attitude reference, no position |
| **GPS-denied flow+alt** | **`body_vel`, `alt`, `omega`** | **`linear_kf`** | **Practical indoor-style stack** |
| GPS-denied IMU-only | `omega` | `linear_kf` | **Honesty:** position not observable; expect drift |

**GPS-denied note:** Rate gyros alone do **not** observe absolute position. AHRS assumes an external attitude source. **Flow+alt** is the recommended teaching “what actually works indoors” column (velocity + height + rates) — still not global XY GPS.

No framework refactor was required: new channels and noise keys plug into the existing plant → measure → filter → control bus.

---

## Artifacts

`runs/<id>/nominal/timeseries.npz`:

| Key | Content |
|-----|---------|
| `t`, `x`, `u` | True plant (Euler 12-state) and controls |
| `x_hat` | Observer estimate when an observer is active |

Metrics may include `observer_id`, `rmse_estimate_position_m`, `rmse_estimate_attitude_rad`, `peak_tilt_rad`,
`time_in_bounds_frac`, `success_pos_limit_m`.

**`success` (tracking):** peak position error ≤ **3×** `metrics.position_bound_m` and peak attitude
error &lt; 45°. This is intentionally tighter than an older 5×/1 m floor that marked multi-meter
AHRS paths as “ok.” `sim_success` still means the plant finished with finite state.

---

## Demo studies

| Config | Notes |
|--------|--------|
| `figure_eight.yaml` | Ideal full-state LQR |
| `figure_eight_gps_imu_naive.yaml` | GPS+IMU naive partial |
| `figure_eight_gps_imu_lqg.yaml` | GPS+IMU LQG (showcase benefit) |
| `figure_eight_ahrs_lqg.yaml` | AHRS-like GPS-denied LQG |
| **`figure_eight_flow_alt_lqg.yaml`** | **Flow + alt + gyro → LQG** |
| `figure_eight_imu_only_lqg.yaml` | Gyro-only honesty case |
| `figure_eight_*_pid.yaml` / `*_kf_pid.yaml` | Same sensors for PID row |
| `figure_eight_gps_imu_lqg_mc.yaml` | MC on GPS+IMU LQG |
| `figure_eight_mekf.yaml` | MEKF partial demo |

```bash
uv run uavsim simulate configs/studies/figure_eight_flow_alt_lqg.yaml
uv run uavsim simulate configs/studies/figure_eight_flow_alt_kf_pid.yaml
```

**Envelope (linearization limits):** `uavsim.studies.envelope` time-scales the mission for ideal LQR (and optional full-channel LQG overlay). Used by the showcase **Envelope** tab — not the sensor-reconstruction story.

---

## Related

- Backlog: [`EXTENSIBILITY_TODO.md`](EXTENSIBILITY_TODO.md) (EST-*, C-9/C-11)  
- Plant / quat: [`dynamics.md`](dynamics.md)  
- Showcase: [`docs/showcase/README.md`](../showcase/README.md)  
- Control still consumes **Euler 12-state** estimates via `MeasurementBus`  
