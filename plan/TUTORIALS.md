# Plan: Tutorials, demos & teaching surfaces

| Field | Value |
|-------|--------|
| **Status** | **In progress on `feature/tutorials`** — T0 first-run shipped; T-GUIDE-ONLINE + T-ENERGY already on main; T-GUIDE-PLUGIN next |
| **Goal** | Ship **runnable configs**, **developer Markdown where useful**, and **interactive hosted demos** (GitHub Pages) that teach how to use and extend `uavsim` |
| **Priority product** | Online intercept + battery + live demo — [`ONLINE_INTERCEPT_AND_BATTERY.md`](ONLINE_INTERCEPT_AND_BATTERY.md) |
| **Airframe for hero demo** | **Sized-up X-quadrotor** (not trirotor) |
| **Control for hero demo** | **NDI only**, beyond-linear attitude intercept |
| **Audience** | Research users, contributors, hiring reviewers |

Portfolio **showcase** stays tabled as a broad matrix. This track owns **targeted demos** and teaching—not a second estimation matrix.

---

## 0. Locked decisions (2026-07-25)

| Topic | Decision |
|-------|----------|
| **Done** | Code shipped **and** demo **live on GitHub** **and** README / related docs **synced** |
| **Hero vehicle** | Quadrotor (sized up for power). **Not** trirotor / new layout epic |
| **Hero control** | NDI only; attitude beyond hover-linear (no forced ~90°) |
| **Git branch** | Do **not** develop on `main` — e.g. `feature/intercept-guidance-battery` |
| **Actuation teaching default** | Body wrench as today; “beyond wrench” deferred to **future plans**, not this track’s hero |
| **Format** | **Not Markdown-only.** Markdown = how-to / extension notes. **Primary “wow” = interactive Pages demo** (scrub + **play**, 3D path, attitude, battery, energy series) |
| **UI reuse** | Extract showcase Flight-like pieces into **reusable components**; add play + battery/energy for intercept demo |
| **Monte Carlo** | **In scope** for ship: P(capture), trajectory confidence bands (2D toggle), success + fail nominal cases |

---

## 1. Product intent

### 1.1 One-sentence story

> Users can **open a live intercept demo** in the browser, scrub/play the chase, watch attitude and battery, then clone the repo and re-run the same studies; optional Markdown guides explain the guidance/battery extension seams.

### 1.2 Two layers (both ship)

| Layer | Role | Hosting |
|-------|------|---------|
| **A. Interactive demo** | Visual + time-synced teaching of intercept + energy | GitHub Pages (JS/HTML/Plotly pattern like showcase) |
| **B. Markdown guides** | Extension checklists, CLI recipes, config walkthroughs | Repo `docs/tutorials/*.md` rendered on GitHub |

Layer A is **required** for the intercept epic done criteria. Layer B supports “how do I rebuild / extend this?” without replacing A.

### 1.3 Explicit non-goals

- Replacing the portfolio showcase matrix  
- Jupyter as the primary path  
- Trirotor / multi-layout integration tutorial as hero (cancelled for this track)  
- LQR/PID intercept law grid  
- Full multi-vehicle  

---

## 2. Scope map

| ID | Surface | Depends on | Status intent |
|----|---------|------------|----------------|
| **D-INTERCEPT** | Live interactive intercept demo | ONLINE_INTERCEPT_AND_BATTERY Phases B–E | **Hero — must ship** |
| **T-GUIDE-ONLINE** | Markdown: online guidance / G-6 / config | Same product | **Done** — `docs/tutorials/01_online_intercept.md` |
| **T-ENERGY** | Markdown: battery opt-in / proxies | Battery phase | **Done** — `docs/tutorials/02_battery_energy.md` |
| **T0** | First run CLI (Markdown) | Nothing | **Done** — `docs/tutorials/00_first_run.md` |
| **T-VEH-YAML** | Optional short: “point a study at a new quad YAML” | Nothing | Optional contrast; **not** a layout plugin story — may fold into intercept vehicle section of T-GUIDE-ONLINE |
| **T-GUIDE-PLUGIN** | How intercept (or a stub) registers as guidance | G-5 preferred | Extension appendix |
| ~~T-EXT-AIR trirotor~~ | Multi-layout extension map | — | **Out of this track** (revisit only under a future airframe plan) |

Deprioritized as primary content (already portfolio-covered): estimation matrix, envelope sweeps, full law×sensor showcase.

---

## 3. Interactive demo requirements (D-INTERCEPT)

Aligned with product plan §5.

### 3.1 Must have

- **Success / fail case switch** — deterministic successful vs unsuccessful intercept  
- **Capture criterion** — within ~**1 m** of scripted point-mass target (config-driven)  
- **3D flight path** — ownship + scripted target  
- **Attitude pane** — vehicle attitude (showcase dual-pane pattern)  
- **Time scrubber** — drag history  
- **Play / pause** — auto-advance (new vs current showcase)  
- **Battery level indicator** — SOC vs scrub index (gauge or bar)  
- **Energy time series** — power and/or SOC/energy remaining; scrub-synced  
- **MC confidence** — toggleable **2D** percentile bands / envelopes; **P(capture)** readout 

### 3.2 Engineering

- Extract reusable modules from `docs/showcase/` (path/attitude/time state) rather than copy-paste forever  
- Separate **small data pack** for intercept studies (not full gallery)  
- Pages path e.g. `…/demos/intercept/` or `…/tutorials/intercept/`  
- README links to live demo when green  

### 3.3 Local rebuild

```text
simulate tutorial studies → export demo JSON → open static page
```

Document in `docs/demos/…/README.md` or tutorials index.

---

## 4. Markdown tutorial catalog (supporting)

```text
docs/tutorials/
  README.md              # index: live demos + guides; ready/blocked badges
  00_first_run.md        # T0
  01_online_intercept.md # T-GUIDE-ONLINE (links live demo)
  02_battery_energy.md   # T-ENERGY
  03_guidance_extension.md  # plugin/registry lessons from intercept
```

```text
configs/vehicles|missions|studies/tutorials/   # intercept + sized quad
docs/demos/intercept/                          # interactive app + data
```

---

## 5. Clarifications (former open questions)

### 5.1 “Thin vs general mixer / geometry table”

**N/A.** Hero airframe is stock **X-quad** allocation. No layout plugin work in this track.

### 5.2 “T-VEH-YAML vs separate airframe tutorial”

That question was: *should “change mass in YAML” be its own mini-tutorial, or only part of a multi-layout guide?*

**Resolution:** No multi-layout guide. At most a **short section** inside intercept docs: “demo vehicle is a sized-up quadrotor YAML (`intercept_quadrotor.yaml`) — clone this pattern for your mass/limits.” Dedicated T-VEH-YAML page is **optional**, not a done-gate.

### 5.3 “Monte Carlo in the tutorial?”

**Resolution (updated):** **Yes — ship with MC.** Deterministic success + fail remain; MC on the success recipe supplies **confidence in interception** (P(capture), min-range distribution, **toggleable 2D trajectory bands**). See product plan §7.

### 5.4 “Whole document Markdown?”

**No.** Markdown is secondary. **Interactive Pages demo is primary** for the hero story.

### 5.5 Beyond wrench-only

This track **does not** teach motor-level control or new plant I/O. Future plans (flex, multi-airframe, richer actuators) should own “how to extend past body wrench.”

---

## 6. Quality bar

| Bar | Requirement |
|-----|-------------|
| **Live demo** | Public GH Pages URL works without local Python |
| **Play + scrub** | Both work; battery/energy follow time index |
| **Runnable offline** | Documented `uv run uavsim simulate` paths recreate data |
| **Honest** | Scripted target; battery proxy; NDI+quat choices stated |
| **Docs sync** | README + LIMITATIONS + guidance/vehicles guides updated |
| **Tests** | Tutorial/demo studies in integration smoke |
| **No showcase rebuild** | Intercept data pack independent of full matrix |

---

## 7. Phases

### Phase 0 — Index stubs

Tutorials README with “blocked on intercept code” + link placeholders.

### Phase 1 — Product epic

Execute [`ONLINE_INTERCEPT_AND_BATTERY.md`](ONLINE_INTERCEPT_AND_BATTERY.md) Phases A–C (plumbing, intercept, battery).

### Phase 2 — Interactive demo

Extract UI components; play; battery/energy; export pipeline; deploy Pages.

### Phase 3 — Markdown sync

T-GUIDE-ONLINE, T-ENERGY, T0; README demo link; developer guide cross-links.

### Phase 4 — Exit gate

All exit criteria in both plans checked; status → **Done**.

---

## 8. Coordination

```text
ONLINE_INTERCEPT_AND_BATTERY          TUTORIALS / DEMOS
        │                                    │
        ├─ sized quad + NDI studies ────────► demo data inputs
        ├─ battery SOC logs ────────────────► battery UI + energy plots
        ├─ target + ownship timeseries ─────► 3D dual path
        └─ docs/LIMITATIONS ────────────────► tutorial honesty banners
                     extract showcase Flight ◄── shared components
                     + play + battery UI
```

**Priority:** product code first, then demo UI, then Markdown polish—but **done** requires all three (code, live demo, docs).

---

## 9. Exit criteria (track v1)

- [x] Intercept product MVP on branch (see product plan §11; Pages pending merge)  
- [x] Interactive demo SPA in-repo (live after merge)  
- [x] Local re-run recipes (tutorials + demo README)  
- [x] **T-GUIDE-ONLINE** + **T-ENERGY** Markdown guides  
- [x] Developer docs / LIMITATIONS synced  
- [x] T0 first-run tutorial (`docs/tutorials/00_first_run.md` on `feature/tutorials`)  
- [ ] T-GUIDE-PLUGIN (guidance registry / extension walkthrough)  
- [ ] Pages live + smoke tests polish  

### Not required / deferred

- Trirotor tutorial  
- Jupyter  
- Full showcase refactor  
- 3D MC trial cloud

---

## 10. Plan pair

| Doc | Owns |
|-----|------|
| [`ONLINE_INTERCEPT_AND_BATTERY.md`](ONLINE_INTERCEPT_AND_BATTERY.md) | G-6, intercept, battery, sized quad, NDI, studies, tests, demo data contracts |
| [`TUTORIALS.md`](TUTORIALS.md) | Hosting/teaching format, interactive UX bar, Markdown catalog, done criteria packaging |

Update **Status** at top when work starts / finishes (same habit as `plan/NDI.md`).
