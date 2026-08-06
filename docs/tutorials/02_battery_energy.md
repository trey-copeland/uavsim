---
tutorial_id: T-ENERGY
title: Battery and energy feasibility
---

# Battery / energy — opt-in endurance story

**Goal:** Enable the **battery** block on a vehicle, run a short mission, read SOC / energy metrics, and understand what the model **does not** claim.

**Prerequisites:** same as [T-GUIDE-ONLINE](01_online_intercept.md). Vehicle clone pattern: [T-VEH-YAML](04_vehicle_yaml.md).  
**Contracts:** [vehicles.md](../developer/vehicles.md) · [LIMITATIONS.md](../LIMITATIONS.md)

---

## 1. Why this exists

Intercept and endurance demos need a **feasibility signal** (did we run out of energy?) without forcing every study to carry battery state.

Design rules:

1. **Default off** — omit `battery:` or `enabled: false` → no SOC columns, old YAMLs unchanged.  
2. **Proxy power**, not a cell model.  
3. **Side integrator** on commanded thrust after the closed-loop step — not a plant ODE state in v1.  
4. **No thrust derate** when empty (SOC hits 0; vehicle can still fly).

---

## 2. Schema

```yaml
# on a vehicle YAML, e.g. configs/vehicles/tutorials/intercept_quadrotor.yaml
battery:
  enabled: true
  capacity_wh: 8.0
  initial_soc: 1.0
  model: hover_scaled
  hover_power_w: 220.0      # nominal power at hover thrust
  thrust_power_exp: 1.5     # P = idle + P_hover * (F / mg)^k
  idle_power_w: 8.0
```

**Power map (`hover_scaled`):**

\[
P = P_{\mathrm{idle}} + P_{\mathrm{hover}}\left(\frac{F}{mg}\right)^{k}
\]

Energy is integrated in Wh along the control history; \(\mathrm{SOC} = E / E_{\mathrm{capacity}}\).

---

## 3. Run: success energy margin

Uses the **online intercept** stack with a full battery:

```bash
uv run uavsim simulate configs/studies/tutorials/intercept_online_success.yaml
```

In `runs/.../nominal/metrics.json` look for:

| Key | Typical success intercept |
|-----|---------------------------|
| `battery_enabled` | `true` |
| `soc_final` | e.g. ~0.9 (depends on path) |
| `energy_used_wh` | fraction of capacity |
| `energy_depleted` | `false` |
| `peak_power_w` | peak of the proxy |

In `nominal/timeseries.npz`:

- `soc` — time series  
- `power_w`  
- `energy_wh_remaining`  

```bash
uv run python - <<'PY'
import numpy as np, json, sys
from pathlib import Path
run = Path(sys.argv[1])
m = json.loads((run / "nominal/metrics.json").read_text())
d = np.load(run / "nominal/timeseries.npz")
print({k: m.get(k) for k in ["soc_final","energy_used_wh","energy_depleted","peak_power_w"]})
print("soc[0], soc[-1]", float(d["soc"][0]), float(d["soc"][-1]))
PY
# usage: ... runs/intercept_online_success_<ts>
```

---

## 4. Run: intentional energy fail

Same mission geometry; **tiny** capacity:

```bash
uv run uavsim simulate configs/studies/tutorials/intercept_online_energy_fail.yaml
```

Vehicle: `configs/vehicles/tutorials/intercept_quadrotor_low_battery.yaml` (`capacity_wh: 0.12`).

Expect:

| Key | Typical |
|-----|---------|
| `energy_depleted` | **`true`** |
| `soc_final` | **~0** |
| `intercept_success` | may still be **true** |

That last point is deliberate: **empty battery does not cut thrust** in v1. The fail story is “energy budget exhausted,” not “aircraft fell out of the sky.” If you need capture failure from energy, you would add derate later (out of current scope).

---

## 5. Defaults do not break old studies

```bash
# no battery key → enabled false
uv run uavsim simulate configs/studies/hover_nominal.yaml
```

`timeseries.npz` will **not** include `soc` / `power_w` unless the vehicle enables battery.

Unit coverage: `tests/unit/test_battery.py`.

---

## 6. Where it lives in code

| Location | Role |
|----------|------|
| `VehicleParams.battery` / `BatteryParams` | Schema |
| `uavsim/vehicles/battery.py` | Power map + integrate |
| `sim/closed_loop.py` | Attach series after integrate |
| `results/run_dir.write_nominal_timeseries` | Optional keys |
| Study metrics | `soc_final`, `energy_depleted`, … |

---

## 7. Demo SPA

The intercept dashboard shows SOC gauge + power / energy series when the pack includes battery fields. Fail case is the **energy-fail** nominal.

See [demo README](../demos/intercept/README.md) and [T-GUIDE-ONLINE](01_online_intercept.md) §7 for export.

---

## 8. Honesty checklist

| Do say | Don’t say |
|--------|-----------|
| SIL power proxy from thrust | Validated Wh from a lab cell |
| SOC for feasibility storytelling | ESC / thermal / Peukert fidelity |
| Optional on vehicle YAML | Required for all studies |
| Empty → flag / metrics | Automatic failsafe thrust cut (not implemented) |

---

## Next

- [T-GUIDE-ONLINE](01_online_intercept.md) — full intercept stack  
- [vehicles.md](../developer/vehicles.md) — battery field table  
- Plan: [ONLINE_INTERCEPT_AND_BATTERY.md](../../plan/ONLINE_INTERCEPT_AND_BATTERY.md) §4  
