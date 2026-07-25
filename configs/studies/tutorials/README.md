# Tutorial / intercept study recipes

## L0 feasibility (open-loop intercept, truth state, NDI)

| Study | Vehicle | Intent | Capture (≤1 m) |
|-------|---------|--------|----------------|
| `intercept_l0_success.yaml` | `intercept_quadrotor` (T/W≈4.5) | Hard CPA at t=3 s | **yes** (~0.04 m) |
| `intercept_l0_fail.yaml` | `intercept_quadrotor_underpowered` (T/W≈1.15) | Same geometry, starved thrust | **no** (~3.8 m) |

```bash
uv run uavsim simulate configs/studies/tutorials/intercept_l0_success.yaml
uv run python scripts/intercept_capture_metrics.py runs/intercept_l0_success_<timestamp>
uv run uavsim simulate configs/studies/tutorials/intercept_l0_fail.yaml
uv run python scripts/intercept_capture_metrics.py runs/intercept_l0_fail_<timestamp>
```

Target mission for range: `configs/missions/tutorials/intercept_l0_target.yaml`.

Next ladder steps (plan): online replan (L1), GPS+IMU/MEKF (L2), battery (L3), MC (L4).
