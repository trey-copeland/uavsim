# Control: LQR, PID, and extending the control set

**Package:** `uavsim.control`  
**Protocol:** `Controller` in `control/base.py`  
**Built-ins:** `lqr_hover`, `pid_cascade`  
**Wiring:** `control/factory.py` + study YAML `controller:` block

---

## Controller contract

Any law used in SIL must satisfy:

```python
class Controller(Protocol):
    id: str
    def compute(
        self,
        t: float,
        measurements: MeasurementBus,  # .t, .x (full state in core)
        reference: ReferenceSample,    # .t, .x_ref
    ) -> ActuatorCommand:              # .u shape (4,)
        ...
```

- **Do not** import guidance or mission types.
- **Do** read limits from `vehicle` (or export artifact) and saturate via `saturate(u, u_min, u_max)`.
- Reference is a **full 12-state** sample (`x_ref`); for hold, velocities/attitudes may be zero except position/yaw.

---

## Using built-in LQR (`lqr_hover`)

Designs continuous LQR about **hover** using `dynamics.hover_linearization`, SciPy CARE.

### Study YAML

```yaml
controller:
  type: lqr_hover
  # Diagonal Q, R (length 12 and 4)
  Q_diag: [100, 100, 100, 10, 10, 1, 10, 10, 10, 1, 1, 0.1]
  R_diag: [0.1, 1.0, 1.0, 1.0]
```

| Weights | Effect |
|---------|--------|
| Large \(Q\) on pos (0:3) | Tight position tracking |
| Large \(Q\) on attitude (3:6) | Less tilt; can fight aggressive trajectories |
| Small \(R\) on thrust | Aggressive thrust use |
| Large \(R\) on torques | Soft attitude effort; helps avoid torque saturation |

### Python

```python
from uavsim.control import design_lqr_hover
from uavsim.vehicles.params import load_vehicle
import numpy as np

v = load_vehicle("configs/vehicles/default_quadrotor.yaml")
ctrl = design_lqr_hover(
    v,
    q_diag=np.array([100, 100, 100, 10, 10, 1, 10, 10, 10, 1, 1, 0.1]),
    r_diag=np.array([0.1, 1.0, 1.0, 1.0]),
)
# Law: u = u_hover - K (x - x_ref), then saturate
```

### Export

Runs write `nominal/controller_artifact.yaml`. CLI:

```bash
uv run uavsim export-controller runs/<run_id> --out artifacts/controllers/lqr.yaml
```

Round-trip: `controller_from_artifact` rebuilds an in-process LQR controller.

### Caveats

- Linearization is **hover / small-angle** — aggressive figure-eights stress validity (use feasibility + MC).
- Gains designed on **nominal** vehicle; MC default is **plant perturbed, K fixed** (`monte_carlo.redesign_controller: false`).

Example studies: `configs/studies/hover_nominal.yaml`, `gentle_square.yaml`, `hover_from_offset.yaml`.

---

## Using built-in PID cascade (`pid_cascade`)

Cascaded PD: position → accel → tilt/thrust; attitude → body torques. Signs match the plant (\(+\theta \Rightarrow -\ddot N\) at hover).

### Study YAML

```yaml
controller:
  type: pid_cascade
  kp_pos: [2.5, 2.5, 6.0]
  kd_pos: [2.0, 2.0, 3.5]
  kp_att: [8.0, 8.0, 2.0]
  kd_rate: [0.8, 0.8, 0.4]
  max_tilt_rad: 0.436   # ~25 deg
```

### Python

```python
from uavsim.control import design_pid_cascade, PidGains
from uavsim.vehicles.params import default_vehicle

ctrl = design_pid_cascade(default_vehicle())  # default gains
# or:
gains = PidGains(
    kp_pos=[3.0, 3.0, 7.0],
    kd_pos=[2.5, 2.5, 4.0],
    kp_att=[10.0, 10.0, 2.5],
    kd_rate=[1.0, 1.0, 0.5],
)
ctrl = design_pid_cascade(default_vehicle(), gains=gains)
```

### Comparison workflow

```bash
uv run uavsim simulate configs/studies/gentle_square.yaml          # LQR
uv run uavsim simulate configs/studies/compare_lqr_vs_pid.yaml     # PID
uv run uavsim compare runs/<lqr_*> runs/<pid_*> --interactive
```

Also: `configs/studies/hover_pid.yaml`.

---

## How to add a new control law

### Checklist

1. **Implement** a class with `id` + `compute(...)` → `ActuatorCommand` (same frames/units).
2. **Do not** import `guidance` or mission file parsers.
3. **Factory:** extend `build_controller_from_mapping` in `control/factory.py`.
4. **Study schema:** add a Pydantic model + `Literal["my_type"]` to the `ControllerConfig` union in `studies/config.py`.
5. **Export (Should):** if you need HIL/export, add `export_*_artifact` + branch in `controller_from_artifact` / `controller_artifact_for`.
6. **Tests:** unit (interface + hover smoke) + integration study YAML on a gentle mission.
7. **Docs:** one example under `configs/studies/`.

### Minimal skeleton

```python
# src/uavsim/control/my_law.py
from dataclasses import dataclass
import numpy as np
from uavsim.control.base import saturate
from uavsim.interfaces import ActuatorCommand, MeasurementBus
from uavsim.reference import ReferenceSample
from uavsim.vehicles.params import VehicleParams

@dataclass
class MyController:
    id: str
    vehicle: VehicleParams
    # gains...

    def compute(self, t, measurements: MeasurementBus, reference: ReferenceSample) -> ActuatorCommand:
        e = measurements.x - reference.x_ref
        u = self.vehicle.u_hover() - 0.0 * e  # replace with your law
        u = saturate(u, self.vehicle.limits.u_min(), self.vehicle.limits.u_max())
        return ActuatorCommand(u=u)
```

Wire `type: my_law` in config + factory `if ctype == "my_law": ...`.

### Optional design API

If the law needs synthesis (like LQR), expose `design_my_law(vehicle, **weights) -> MyController` and call it from the factory.

---

## TODOs / gaps (control)

| Gap | Status |
|-----|--------|
| **Registry** for controllers (parity with `register_guidance`) | **TODO** — factory is manual `if/elif` |
| Plugin discovery (entry points / external packages) | **TODO** |
| Geometric / SE(3) controller | **TODO** (SPEC Should alternate — PID shipped first) |
| Discrete-time / sample-rate aware laws | **TODO** — continuous ODE + hold for now |
| Measurement-based laws / observers | **Done (5d)** — `none \| linear_kf \| mekf \| partial_raw`; channels incl. `body_vel`/`alt`; `x_hat` in timeseries; see [estimation.md](estimation.md) |
| Per-trial redesign of non-LQR laws in MC | Partial — `redesign_controller` re-runs factory; document per law |

See [EXTENSIBILITY_TODO.md](EXTENSIBILITY_TODO.md).
