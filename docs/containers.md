# Containers and sharded Monte Carlo

Phase 4 systems path: one primary image runs `uavsim`, and MC trials can be
partitioned across workers then merged into a single trial table + summary.

## Build

From the repository root:

```bash
docker build -t uavsim:local -f containers/Dockerfile .
```

The package installs under `/opt/uavsim` so mounting the host repo at `/work`
does not overwrite the image virtualenv.

Override image name with `UAVSIM_DOCKER_IMAGE` if desired.

## Single-container study

```bash
docker run --rm -v "$PWD":/work -w /work uavsim:local \
  study configs/studies/hover_mc_smoke.yaml --output runs
```

Or via CLI orchestration (builds image if missing):

```bash
uv run uavsim study configs/studies/hover_mc_smoke.yaml \
  --backend docker --output runs
```

## Local sharded MC (no Docker)

Same seed + trial index mapping as a single process; intermediate shards under
`monte_carlo/shards/`:

```bash
uv run uavsim study configs/studies/hover_mc_smoke.yaml --shards 2 --output runs
```

Merged `trials.csv` / `summary.json` must match an unsharded run for the same
seed and `n_trials` (within floating-point tolerance).

## Worker + merge CLI

```bash
# Worker
uv run uavsim mc-shard configs/studies/hover_mc_smoke.yaml \
  --shard-id 0 --shards 2 --output /tmp/shard0

# Merge
uv run uavsim mc-merge /tmp/shard0 /tmp/shard1 \
  --output /tmp/merged --n-trials 4 --seed 7
```

## Compose demo (2 shards + merge)

```bash
docker compose -f containers/docker-compose.yml build
docker compose -f containers/docker-compose.yml run --rm merge
# → runs/compose_shards/merged/{trials.csv,summary.json}
```

## Design notes

| Topic | Policy |
|-------|--------|
| Trial RNG | `SeedSequence([base_seed, trial_id])` — pure function of seed + id |
| Controller | Designed on **nominal** vehicle; plant parameters perturbed (default) |
| Shard failure | Missing `trials.csv` or wrong trial count → merge **fails** the study |
| Docker role | Optional packaging; local path remains the fast laptop loop |

See `SPEC.md` §10 and `docs/ARCHITECTURE.md` §11.
