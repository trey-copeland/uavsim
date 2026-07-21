# GROK.md — Project working agreements

Agent and human conventions for `quadrotor-sim` (UAVSIM).  
Keep this file **short and actionable**. Language-specific rules land later.

---

## 1. What we are building

Public **quadrotor simulation & GNC framework** for portfolio-quality demos: dynamics, trajectory, control, Monte Carlo, reproducible results.

- **Product intent:** `SPEC.md` (living contract; not a frozen ICD).
- **Domain reference:** ME590 MATLAB at  
  `D:\Users\Trey\My Drive\Grad School UTK\Course Work\ME590\code`  
  (WSL: `/mnt/d/Users/Trey/My Drive/Grad School UTK/Course Work/ME590/code`).
- **Not** a line-for-line MATLAB port. Keep physics/GNC capability; redesign architecture, APIs, and results pipeline.
- Runtime must **not** depend on the MATLAB tree.

### Document map

| Doc | Role |
|-----|------|
| `SPEC.md` | What/why: workflow, user stories, MoSCoW, acceptance (v0.2+) |
| `ROADMAP.md` | Sequencing, milestones, now/next/later |
| `GROK.md` | How we work (this file) |
| `docs/ARCHITECTURE.md` | How: packages, protocols, SIL/HIL seams, results/compare |
| `docs/developer/` | How-to extend (vehicles, dynamics, control, estimation, guidance, …) |
| `README.md` | Human entry / features / CLI / doc index |
| Language convention notes (TBD) | Idioms, tooling, lint/format per language (after skeleton) |

**Product workflow to honor in design reviews:**  
vehicle → dynamics → SIL design/analyze → export controller → HIL → compare (SPEC §1.3).

---

## 2. GSD Workflow (Get Shit Done)

**Always follow this structured flow** unless explicitly agreed otherwise.

#### Roadmapping & Prioritization
- Start with a clear **Problem / Opportunity Statement**.
- Define **Success Criteria** (measurable outcomes).
- Break into small, shippable increments.
- Identify risks, dependencies, and effort level.
- Output: Update **`ROADMAP.md`** (milestones / now-next-later); keep `SPEC.md` for requirements.

#### SPEC / Design Phase (Mandatory for non-trivial work)
- Update or create relevant section in `SPEC.md`.
- Cover: Goal, Requirements, Non-goals, Design decisions, API contracts, Test strategy, Validation/Rollout plan.
- Get human alignment before heavy implementation.
- Keep `SPEC.md` living — update as you learn.

#### Development Workflows

**New Feature**
1. Create branch: `feature/<kebab-name>`
2. Write failing test(s) first when practical.
3. Implement smallest viable piece.
4. Pass tests → Refactor → Update docs/SPEC.
5. Open focused PR.

**Feature Extension**
1. Understand current implementation.
2. Add minimal change to support new behavior.
3. Maintain compatibility where reasonable.
4. Add/update tests.

**Bug Fix**
1. Reproduce the bug (add regression test if missing).
2. Fix root cause.
3. Verify fix + regression test passes.
4. Update SPEC if behavior was ambiguous.

**General Development Rules**
- One logical change per PR.
- Leave the project in a working state after every meaningful commit.
- Update `GROK.md` or `SPEC.md` when process or architecture decisions are made.

#### Review & Merge
- Self-review for tests, cleanliness, edge cases, and SPEC alignment before opening PR.
- PR description must link relevant SPEC section and summarize changes + testing done.
- Address feedback promptly and merge when approved.

---

## 3. Default working style

### Research before execute

Before writing non-trivial code or making design choices:

1. **Read** the relevant SPEC section and any existing architecture notes.
2. **Consult heritage** (ME590) when domain behavior is unclear — equations, control structure, feasibility rules, metrics definitions — not for directory layout or script spaghetti.
3. **Survey** standard practice (libraries, numerical methods, GNC conventions) when the SPEC is open or silent.
4. **Summarize the plan** for multi-step or ambiguous work; get alignment on open decisions before a large implementation pass.

Do not invent new physics, coordinate conventions, or metric definitions without checking heritage + SPEC first.

### Prefer redesign with intent

When porting capability:

- Preserve **engineering meaning** (NED, state order, trim/LQR story, feasibility ideas).
- Prefer **clean interfaces and config-driven studies** over reproducing ME590 structure.
- Explicitly avoid porting the paper-figure / ad-hoc output tangle.

### Small, verifiable steps

- One concern per change when practical (dynamics, then control, then trajectory, …).
- Leave the tree buildable/testable after each meaningful step.
- Prefer boring, explicit code over clever abstraction until a second controller/vehicle forces the interface.

### Ask when blocked or risky

- Confirm before destructive git ops, force-push, mass deletes, or rewriting large uncommitted work.
- Surface SPEC open decisions rather than silently picking a permanent answer.
- If heritage and modern practice conflict, note both and recommend; do not paper over it.

---

## 4. Testing conventions

Quality bar from SPEC (N4): unit + integration tests; small CI smoke studies later.

### Unit tests

- Pure functions and small modules: dynamics helpers, linearization pieces, metrics, config parsing, trajectory math, feasibility checks.
- Fast, deterministic, no network, no heavy I/O.
- Prefer testing **behavior and invariants** (dimensions, frame conventions, conservation-ish checks, trim consistency) over snapshot spam.

### Integration tests

- Cross-module paths: config → trajectory → closed-loop sim → metrics/artifacts.
- A few **golden-ish** missions (hover, gentle path) with loose numerical tolerances — **not** MATLAB bit-parity.
- Monte Carlo: tiny N smoke (reproducible seed), not full studies in the default suite.

### Test-driven workflow (default for new behavior)

1. **Failing test first** for the behavior or bug (unit if local; integration if wiring).
2. **Minimal implementation** to pass.
3. **Refactor** with tests green.
4. For numerical/GNC work: add a short comment or doc pointer for the equation/source of truth when non-obvious.

Exceptions (write tests immediately after is OK): pure scaffolding, renames, docs-only, spikes clearly labeled throwaway.

### When is “done”?

A change that alters behavior is incomplete without:

- Tests covering the new path or regression, and
- Any CLI/docs touch needed for a stranger to run it (once we have a runnable skeleton).

---

## 5. Engineering principles (until ARCH exists)

Carry these from SPEC §7; architecture doc will refine layout.

1. **Separation of concerns** — trajectory, plant, controller, integrator, metrics, reporting do not share mutable global state.
2. **Controller as interface** — LQR is implementation #1, not the only shape forever.
3. **Config over script spaghetti** — studies as data; thin entrypoints.
4. **Results as a product** — schema-versioned run artifacts; viz consumes, does not own the sim.
5. **Reproducibility by construction** — seeds, dependency identity, config hashes in manifests (when that layer exists).
6. **Earn abstractions** — second controller/vehicle justifies interfaces; first cut stays small.
7. **Polyglot OK, boundaries explicit** — language choices justified and documented; no purity theater.
8. **Simulation only** — never claim flight-critical / certified software.

---

## 6. Interaction with heritage MATLAB

| Do | Don’t |
|----|--------|
| Read for domain correctness | Copy directory layout or globals |
| Reuse metric *concepts* | Require MATLAB at runtime |
| Compare qualitatively when useful | Chase bit-identical outputs |
| Cite ME590 origins in narrative | Ship private Drive materials in the public tree |

---

## 7. Near-term process (stand-up path)

**Done:** SPEC v0.2+, architecture v0.4, `ROADMAP.md`, process docs, MIT license.

**Next:** see **`ROADMAP.md`** (Phase 2 waypoint guidance).

Prefer implementing against `docs/ARCHITECTURE.md`; if reality forces a change, update ARCH + ROADMAP in the same change set.

---

## 8. Python conventions (Phase 0+)

- **Layout:** `src/uavsim/` only; configs under `configs/`; tests under `tests/unit` and `tests/integration`.
- **Tooling:** `uv sync --extra dev` · `uv run pytest` · `uv run ruff check src tests` · `uv run ruff format src tests`.
- **Style:** Ruff lint + format (see `pyproject.toml`); target Python 3.11+.
- **Types:** Prefer type hints on public APIs; `mypy` optional until types stabilize.
- **CLI:** Thin wrappers in `uavsim.cli` — no business logic.
- **Imports:** Honor ARCH §3.2 DAG (`control` ↛ `guidance`, `viz` ↛ `sim` internals).

## 9. Extending this file

Add sections when they earn their keep:

- CLI and config style guide (deeper)
- Numerical tolerance policy
- CI matrix and performance budgets

If a rule is only useful in one language or package, put it there (or in a nested rules file) instead of bloating this root doc.

---
