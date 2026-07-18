# quadrotor-sim (`uavsim`)

Modern **quadrotor simulation and GNC analysis** framework for portfolio-quality demos: flight dynamics (NED), guidance, control, Monte Carlo robustness, and reproducible study pipelines — including containerized and sharded execution.

**Status:** Phase 5 complete — controller export, `compare`, PID cascade second law; core SIL workflow story is shippable. Post-core: non-waypoint nav (Phase 6), HIL (Phase 7).  

**Intended workflow:** configure vehicle → inject dynamics → design/analyze control in SIL → export controller → (later) HIL → compare runs. Implementation follows `docs/ARCHITECTURE.md`.

> **Simulation only.** This is not flight-critical or certified software.

## Docs

| Document | Role |
|----------|------|
| [`SPEC.md`](SPEC.md) | What we build, scope, acceptance |
| [`ROADMAP.md`](ROADMAP.md) | Phases, milestones, now/next/later |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How we structure code, interfaces, systems |
| [`GROK.md`](GROK.md) | How we work (GSD, tests, heritage rules) |
| [`AGENTS.md`](AGENTS.md) | Agent entrypoint → `GROK.md` |

## Heritage

Domain reference: ME590 MATLAB research (private). This repo is a **redesign**, not a line-for-line port. Runtime does **not** depend on MATLAB or private Drive assets.

## License

[MIT](LICENSE)

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
uv sync --extra dev
uv run uavsim --help
uv run pytest
uv run ruff check src tests
```

```bash
# Closed-loop hover (Phase 1)
uv run uavsim simulate configs/studies/hover_nominal.yaml
uv run uavsim simulate configs/studies/hover_from_offset.yaml

# Waypoint missions (Phase 2)
uv run uavsim simulate configs/studies/hover_waypoints.yaml
uv run uavsim simulate configs/studies/gentle_square.yaml
uv run uavsim simulate configs/studies/gentle_square_interp.yaml
uv run uavsim simulate configs/studies/aggressive_square.yaml

# Monte Carlo robustness (Phase 3)
uv run uavsim study configs/studies/hover_mc_smoke.yaml
uv run uavsim study configs/studies/gentle_square_mc.yaml --n-trials 10
uv run uavsim report runs/<study_id>_<timestamp>/

# Sharded MC + container (Phase 4) — see docs/containers.md
uv run uavsim study configs/studies/hover_mc_smoke.yaml --shards 2
docker build -t uavsim:local -f containers/Dockerfile .
docker run --rm -v "$PWD":/work -w /work uavsim:local \
  study configs/studies/hover_mc_smoke.yaml --output runs

# Export + compare + second controller (Phase 5)
uv run uavsim simulate configs/studies/gentle_square.yaml
uv run uavsim simulate configs/studies/compare_lqr_vs_pid.yaml
uv run uavsim export-controller runs/<lqr_run> --out artifacts/controllers/lqr.yaml
uv run uavsim compare runs/<lqr_run> runs/<pid_run> --figures
```

Run artifacts land under `runs/<study_id>_<timestamp>/` (gitignored). Monte Carlo writes `monte_carlo/trials.csv`, `summary.json`. Figures need `uv sync --extra viz` (or `--extra dev`). Container details: [`docs/containers.md`](docs/containers.md).

