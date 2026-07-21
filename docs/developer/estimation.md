# Estimation & observers (Phase 5d)

**Package:** `uavsim.estimation`  
**Loop:** plant → noisy measurements → **observer** → controller → plant  

Default SIL remains **full-state** (`sim.observer.type: none`): no noise, controller sees true Euler 12-state. That preserves existing goldens and the portfolio showcase path.

---

## Study config

```yaml
sim:
  dt_s: 0.01
  attitude: euler          # or quat (Phase 5c plant)
  observer:
    type: none             # none | linear_kf | mekf
    seed: 7
    pos_sigma_m: 0.05
    vel_sigma_m_s: 0.05
    att_sigma_rad: 0.02
    omega_sigma_rad_s: 0.05
    process_sigma: 0.02
    channels: [pos, att, vel, omega]   # partial OK, e.g. [pos, omega]
```

| Type | Role |
|------|------|
| `none` | Identity: estimate = (optional noisy) full state; RK45 path when plant is Euler |
| `linear_kf` | 12-state KF using hover \(A,B\) (same linearization as LQR); supports partial \(H\) |
| `mekf` | Error-state filter: nominal \(p,v,q,\omega\) + \([\delta p,\delta v,\delta\theta]\); multiplicative attitude |

**Channels:** `pos`, `att`, `vel`, `omega` (aliases: `position`, `gyro`, …).  
Partial sensing example: `channels: [pos, omega]` (GPS-like + gyro).

---

## Artifacts

`runs/<id>/nominal/timeseries.npz`:

| Key | Content |
|-----|---------|
| `t`, `x`, `u` | True plant (Euler 12-state) and controls |
| `x_hat` | Observer estimate when an observer is active |

Metrics may include `observer_id`, `rmse_estimate_position_m`, `rmse_estimate_attitude_rad`.

---

## Demo studies

| Config | Notes |
|--------|--------|
| `configs/studies/figure_eight.yaml` | Full-state baseline |
| `configs/studies/figure_eight_observer.yaml` | `linear_kf`, full channels |
| `configs/studies/figure_eight_mekf.yaml` | `mekf`, partial `pos` + `omega` |
| `configs/studies/figure_eight_aggressive.yaml` | Stress path; default `attitude: quat` |

```bash
uv run uavsim simulate configs/studies/figure_eight_observer.yaml
uv run uavsim simulate configs/studies/figure_eight_mekf.yaml
```

---

## Related

- Backlog: [`EXTENSIBILITY_TODO.md`](EXTENSIBILITY_TODO.md) (EST-*, C-9/C-11)  
- Plant / quat: [`dynamics.md`](dynamics.md)  
- Control still consumes **Euler 12-state** estimates via `MeasurementBus`  
