# quadrotor-sim (`uavsim`)

Modern **quadrotor simulation and GNC analysis** framework for portfolio-quality demos: flight dynamics (NED), guidance, control, Monte Carlo robustness, and reproducible study pipelines — including containerized and sharded execution.

**Status:** Phase 0 complete — installable package + CLI stubs. Phase 1 (SIL loop) is next.  

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

Simulation commands are stubbed until Phase 1+:

```bash
# Phase 1+
uv run uavsim simulate configs/studies/hover_nominal.yaml
# Phase 3+
uv run uavsim study configs/studies/square_mc.yaml
```
