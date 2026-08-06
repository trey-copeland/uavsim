---
tutorial_id: T0
title: First run — install, simulate, report
---

# First run — from clone to a closed-loop plot

**Goal:** In about five minutes, install `uavsim`, run one **stock** study, read the metrics, and open a report. No intercept or battery yet.

**Audience:** Brand-new users and interview reviewers who want a green path before deeper guides.

**Prerequisites:** Python **3.11+**, [uv](https://docs.astral.sh/uv/), git.  
**Next:** [Online intercept](01_online_intercept.md) · [Battery / energy](02_battery_energy.md) · [Tutorials index](README.md)

---

## 1. Install

```bash
git clone https://github.com/trey-copeland/uavsim.git
cd uavsim

uv sync --extra dev
# optional: interactive 3D report figures
uv sync --extra viz

uv run uavsim --help
```

You should see subcommands including `simulate`, `study`, `report`, and `compare`.

**Optional once per clone** (lint on commit):

```bash
uv run pre-commit install
```

This project is **simulation only** — not flight software. Honest scope: [LIMITATIONS.md](../LIMITATIONS.md).

---

## 2. Run a simple closed-loop study

**Recipe:** LQR hover from a small position offset — short, deterministic, good metrics.

```bash
# from repo root
uv run uavsim simulate configs/studies/hover_from_offset.yaml
```

The CLI prints a run directory under `runs/`, for example:

```text
runs/hover_from_offset_20260805T120000Z/
```

Set it for the rest of this tutorial:

```bash
RUN=runs/hover_from_offset_<timestamp>   # paste your path
```

### What just ran?

| Piece | This study |
|-------|------------|
| **Vehicle** | `configs/vehicles/default_quadrotor.yaml` |
| **Control** | Hover **LQR** on full state (ideal SIL — no observer noise) |
| **Guidance** | **Hold** at origin for a few seconds |
| **IC** | Small NED offset so the vehicle must **regulate** back to the hold |
| **Outputs** | `nominal/metrics.json`, timeseries, controller artifact, … |

Ideal full-state LQR is an **upper-bound teaching path**, not a claim about flight hardware. See LIMITATIONS (“Ideal full-state is an upper bound”).

---

## 3. Read the metrics

```bash
# pretty-print if you have jq; otherwise open the file in an editor
cat "$RUN/nominal/metrics.json"
```

Useful keys:

| Key | Meaning |
|-----|---------|
| `success` | Tracking pass: peak position error ≤ **3×** study `position_bound_m`, peak attitude error &lt; 45° (SO(3)) |
| `rmse_position_m` | RMSE vs the **commanded** reference |
| `max_position_error_m` | Peak \|e\| over the run |
| `time_in_bounds_frac` | Fraction of samples inside `position_bound_m` |
| `sim_success` | Integrator finished with finite states/controls |

For `hover_from_offset` you should see **`success: true`** and sub-meter RMSE (typically well under 0.1 m after settle). Exact numbers can move with code revision — re-run after upgrades.

**Directory layout (minimal):**

```text
$RUN/
  study_config.yaml          # frozen recipe
  nominal/
    metrics.json             # tracking + sim flags
    timeseries.npz           # t, x, u, …
    controller_artifact.yaml # SIL gains / provenance (not HIL handoff)
  reference/                 # commanded trajectory artifacts
  guidance/                  # backend + feasibility notes
```

---

## 4. Generate a report

Markdown summary + static figures:

```bash
uv run uavsim report "$RUN"
```

Interactive Plotly Flight 3D (needs `uv sync --extra viz`):

```bash
uv run uavsim report "$RUN" --interactive
```

Open whatever path the CLI prints under `$RUN/report/` (e.g. `report.md`, figures, optional `flight_3d.html`).

---

## 5. Optional next five minutes

### Monte Carlo smoke (plant scatter)

```bash
uv run uavsim study configs/studies/hover_mc_smoke.yaml
```

Small \(N\); good check that MC wiring works without a long portfolio run.

### A tracking mission (figure-eight)

```bash
uv run uavsim simulate configs/studies/figure_eight.yaml
uv run uavsim report runs/figure_eight_<timestamp>/ --interactive
```

### Portfolio showcase (local)

Heavy if you rebuild data; for **viewing** committed assets:

```bash
# from repo root
python3 -m http.server 8766 --directory docs/showcase
# open http://127.0.0.1:8766/
```

Live (after deploy): [trey-copeland.github.io/uavsim](https://trey-copeland.github.io/uavsim/)

---

## 6. Where to go next

| If you want… | Open |
|--------------|------|
| Online intercept + capture metrics | [01_online_intercept.md](01_online_intercept.md) |
| Battery SOC / energy-fail story | [02_battery_energy.md](02_battery_energy.md) |
| Live intercept dashboard | [docs/demos/intercept](../demos/intercept/) · [Pages `/intercept/`](https://trey-copeland.github.io/uavsim/intercept/) |
| Extend vehicles / control / estimation | [docs/developer/README.md](../developer/README.md) |
| Honest limits of the SIL | [LIMITATIONS.md](../LIMITATIONS.md) |

---

## Anti-patterns

- Treating ideal-full-state RMSE as flight performance  
- Expecting `uavsim report` interactive 3D without `uv sync --extra viz`  
- Running showcase gallery rebuilds on a laptop as a first step (slow; use committed SPA first)  
- Confusing tracking `success` with **intercept** capture (later tutorials)  
