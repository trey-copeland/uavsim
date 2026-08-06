# Tutorial / intercept study recipes

Human guides: [`docs/tutorials/`](../../../docs/tutorials/README.md) (T0 · ONLINE · ENERGY · PLUGIN · VEH-YAML).

## Intercept study ladder

| Study | Guidance | Observer | Intent |
|-------|----------|----------|--------|
| `intercept_l0_success.yaml` | open-loop waypoints | none | L0 pad climb + GE |
| `intercept_l0_fail.yaml` | open-loop | none | underpowered miss |
| `intercept_l0_success_mc.yaml` | open-loop | none | L0 plant MC |
| **`intercept_online_success.yaml`** | **`intercept_pursue` (G-6)** | **MEKF GPS+IMU** | L1–L2 hero |
| `intercept_online_energy_fail.yaml` | online | MEKF | L3 battery depleted |
| `intercept_online_success_mc.yaml` | online | MEKF | L4 plant MC on hero |

```bash
# Hero online intercept
uv run uavsim simulate configs/studies/tutorials/intercept_online_success.yaml
# Metrics: intercept_success, n_replans, soc_final (not tracking RMSE)

# Energy-fail (battery empty; capture may still hold — no thrust derate v1)
uv run uavsim simulate configs/studies/tutorials/intercept_online_energy_fail.yaml

# L4 MC (500 trials / 8 shards)
uv run uavsim study configs/studies/tutorials/intercept_online_success_mc.yaml --shards 8
```

Seed climb: `configs/missions/tutorials/intercept_seed_climb.yaml`  
Target: `configs/missions/tutorials/intercept_l0_target.yaml`
