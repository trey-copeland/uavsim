# quadrotor-sim (`uavsim`)

**Software-in-the-loop (SIL) quadrotor GNC** — configure a vehicle and mission, close the loop with LQR or PID, run Monte Carlo, estimate state with optional KF/MEKF, export controllers, and compare runs. Built for research demos and portfolio-quality analysis, with HIL seams planned but not flight-critical software.

| | |
|--|--|
| **Live results showcase** | **[trey-copeland.github.io/uavsim](https://trey-copeland.github.io/uavsim/)** |
| **Install** | Python 3.11+ · [uv](https://docs.astral.sh/uv/) · `uv sync --extra dev` |
| **Heritage** | Redesign of **[quad_uav](https://github.com/trey-copeland/quad_uav)** (ME590 MATLAB) — not a line-for-line port |
| **License** | [MIT](LICENSE) |

> **Simulation only.** Not flight-critical or certified software.

---

## Features

### Plant & vehicles
- Nonlinear **6-DoF** rigid-body dynamics (NED, body wrench)
- **Euler** (default) or **unit-quaternion** plant (`sim.attitude: quat`) via pluggable [`DynamicsModel`](docs/developer/dynamics.md)
- Optional **mixer + first-order motors** (`sim.plant: motors`) — control allocation uses arm length / \(c_T,c_Q\)
- YAML vehicles: mass, inertia, arm length, limits, propulsion — [vehicles guide](docs/developer/vehicles.md)

### Guidance
- **Hold** and **waypoint** missions (interp / min-snap / auto)
- Feasibility checks (yaw rates, trajectory stress cases)
- Config-driven missions under `configs/missions/` — [guidance guide](docs/developer/guidance.md)

### Control
- **LQR hover** design on linearization (heritage Q/R style)
- **LQG path**: same LQR on KF estimates from realistic partial sensors
- **PID cascade** for controller compare studies
- **SO(3) attitude error** in LQR/PID/metrics (not naive Euler subtract)
- **Linearization envelope**: time-scale sweep for limits of *idealized* hover LQR
- Controller **export** + reload artifacts — [control guide](docs/developer/control.md)

### Estimation (optional)
- Observer-in-the-loop: plant → noisy measurements → filter → controller
- **`partial_raw`**: naive pack of measured channels (zeros elsewhere) — teaching baseline
- **`linear_kf`** (hover \(A,B\)) and **`mekf`** (error-state / multiplicative attitude)
- Sensor stories: GPS+IMU (`pos`+`omega`), AHRS-like (`att`+`omega`), IMU-only (`omega`)
- Estimates logged as `x_hat` — [estimation guide](docs/developer/estimation.md)

### Studies, robustness & systems
- Config-driven **`simulate` / `study`** pipelines with seed-stable Monte Carlo
- Mass / inertia / arm **parameter scatter**; sharded MC + Docker — [containers](docs/containers.md)
- Versioned **run directories** (metrics, timeseries, manifests, reports)

### Visualization & compare
- Interactive **3D flight** scrubber, strip charts, MC hist/CDF/sensitivity grids — [viz](docs/viz.md)
- **`compare`** two runs (metrics deltas + path overlay)
- **React portfolio showcase** (GitHub Pages) — [showcase](docs/showcase/README.md)

### Extensibility (direction of travel)
- Multi-airframe / flex / motors backlog — [airframes](docs/developer/airframes.md) · [EXTENSIBILITY_TODO](docs/developer/EXTENSIBILITY_TODO.md)
- Architecture & HIL seams — [ARCHITECTURE](docs/ARCHITECTURE.md)

---

## CLI at a glance

| Command | Purpose |
|---------|---------|
| `uavsim simulate` | Nominal closed-loop SIL study |
| `uavsim study` | Nominal + optional Monte Carlo |
| `uavsim report` | Markdown report + figures (optional interactive 3D) |
| `uavsim compare` | Diff two run directories |
| `uavsim export-controller` | Write a versioned controller artifact |
| `uavsim gallery` | Build the React results showcase |
| `uavsim mc-shard` / `mc-merge` | Sharded MC workers |
| `uavsim hil` | HIL session stub (post-core) |

```bash
uv run uavsim --help
```

---

## Documentation

### Start here

| Doc | Role |
|-----|------|
| **[Developer hub](docs/developer/README.md)** | How to extend vehicles, control, guidance, dynamics, estimation |
| **[SPEC.md](SPEC.md)** | Product scope, requirements, acceptance |
| **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Packages, data flow, SIL/HIL seams |
| **[ROADMAP.md](ROADMAP.md)** | Phases, milestones, now / next / later |

### How-to guides

| Doc | Role |
|-----|------|
| [Vehicles](docs/developer/vehicles.md) | YAML vehicle params and limits |
| [Dynamics](docs/developer/dynamics.md) | Euler/quat plant, SO(3) error, `DynamicsModel` |
| [Control](docs/developer/control.md) | LQR, PID, adding a law, export |
| [Guidance](docs/developer/guidance.md) | Missions, waypoints, backends |
| [Estimation](docs/developer/estimation.md) | KF/MEKF, channels, `sim.observer` |
| [Airframes](docs/developer/airframes.md) | Multi-airframe vision + HIL rig notes |
| [Extensibility backlog](docs/developer/EXTENSIBILITY_TODO.md) | What works today vs TODO |
| [Visualization](docs/viz.md) | Report figure pack (§11A) |
| [Showcase / Pages](docs/showcase/README.md) | React demo hosting |
| [Containers](docs/containers.md) | Docker + sharded MC |

### Process

| Doc | Role |
|-----|------|
| [GROK.md](GROK.md) | Working agreements, tests, heritage rules |
| [AGENTS.md](AGENTS.md) | Agent entry → `GROK.md` |

---

## Live showcase

Interactive React rollup of the portfolio **base case** (elevated figure-eight under LQR and PID, multi-hundred-trial Monte Carlo):

**→ [Open the live showcase](https://trey-copeland.github.io/uavsim/)**

| | |
|--|--|
| **Live** | [trey-copeland.github.io/uavsim](https://trey-copeland.github.io/uavsim/) |
| **Local** | `python -m http.server 8765 --directory docs/showcase` → http://127.0.0.1:8765/ |
| **Regenerate** | `uv run uavsim gallery --base-case` · source in [`docs/showcase/`](docs/showcase/) |

Tabs: overview · **estimation matrix** · 3D flight · metrics · MC · **envelope (ideal LQR limits)** · naive vs LQG compare. Details: [showcase README](docs/showcase/README.md).

---

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
uv sync --extra dev
uv run pre-commit install   # once per clone: ruff lint+format on commit
uv run uavsim --help
uv run pytest
uv run ruff check src tests
```

### Representative studies

```bash
# Hover + waypoints
uv run uavsim simulate configs/studies/hover_nominal.yaml
uv run uavsim simulate configs/studies/figure_eight.yaml
uv run uavsim simulate configs/studies/figure_eight_gps_imu_lqg.yaml
uv run uavsim simulate configs/studies/figure_eight_gps_imu_naive.yaml
uv run uavsim simulate configs/studies/figure_eight_pid.yaml

# Monte Carlo (small N for a quick loop)
uv run uavsim study configs/studies/hover_mc_smoke.yaml
uv run uavsim study configs/studies/figure_eight_mc.yaml --n-trials 20
uv run uavsim report runs/<study_id>_<timestamp>/ --interactive

# Quaternion plant stress path
uv run uavsim simulate configs/studies/figure_eight_aggressive.yaml

# Observers (estimates in timeseries as x_hat)
uv run uavsim simulate configs/studies/figure_eight_observer.yaml
uv run uavsim simulate configs/studies/figure_eight_mekf.yaml

# Compare + export
uv run uavsim compare runs/<lqr_run> runs/<pid_run> --figures
uv run uavsim export-controller runs/<lqr_run> --out artifacts/controllers/lqr.yaml

# Portfolio showcase (MC default N≈200 — slow; smoke with --n-mc-trials 8)
uv run uavsim gallery --base-case
python -m http.server 8765 --directory docs/showcase
```

More study YAMLs live under [`configs/studies/`](configs/studies/). Artifacts land in `runs/<study_id>_<timestamp>/` (gitignored): metrics, timeseries, optional MC tables, reports. Viz extras: `uv sync --extra viz` (matplotlib + plotly). Containers: [docs/containers.md](docs/containers.md).

---

## Heritage

Prior implementation and domain reference: **[quad_uav](https://github.com/trey-copeland/quad_uav)** (ME590 quadrotor GNC, MATLAB). This project is a **clean redesign** (architecture, Python packaging, studies pipeline, viz, estimation). Runtime does **not** depend on MATLAB or on that repository.

---

## License

[MIT](LICENSE)
