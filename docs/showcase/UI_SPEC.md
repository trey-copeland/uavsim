# Showcase UI specification (as-built)

| Field | Value |
|-------|--------|
| **Status** | As-built (portfolio React SPA) |
| **Synced to** | `main` as of 2026-07-24 (guided walkthrough UX) |
| **Primary implementation** | `docs/showcase/app.js`, `styles.css`, `index.html` |
| **Data contract** | `docs/showcase/data/showcase.json` (schema below) |
| **Builder** | `uavsim gallery --base-case` → `src/uavsim/viz/gallery.py` |
| **Audience** | Hiring GNC reviewers + technical peers (SIL study report, not ground station) |

This document is the **UI product specification** for the static results showcase.  
Rebuild / matrix study lists remain in [README.md](README.md). Honesty bounds: [LIMITATIONS.md](../LIMITATIONS.md).

---

## 1. Product goals

1. Present a **controller × sensor** matrix for a figure-eight SIL study that is **honest** about failure cases.
2. Support **two missions** (baseline vs near-envelope) without duplicating the app shell.
3. Offer a short **walkthrough** for first-time readers; keep power tools (compare, full sweep tables, run metrics) available but secondary.
4. Run with **no build step**: React 18 + Plotly from CDN; data in JSON.

Out of scope: live simulation control, multi-user auth, mobile-first layout.

---

## 2. Information architecture

### 2.1 Global chrome

| Element | Behavior |
|---------|----------|
| **Sticky header** | Title, value prop, **About this study** expand, **Mission** segmented control, version/date |
| **Walkthrough strip** | 4 steps → navigates primary tabs: Overview → Flight → Estimation → Envelope |
| **Tab list** | Story-first order (below); `role=tablist` / `tab` / `tabpanel` |
| **Footer** | “Simulation only”; link to GitHub |

### 2.2 Tab order (as-built)

| Order | Tab id | Label | Role |
|------:|--------|--------|------|
| 1 | `overview` | Overview | Decision matrix + suggested first look |
| 2 | `flight` | Flight 3D | Dual-pane scrubber |
| 3 | `estimation` | Estimation | LQR vs PID bars + scenario table |
| 4 | `envelope` | Envelope | τ-sweep multi-scheme curves + tables |
| 5 | `monte_carlo` | Monte Carlo | MC for active mission |
| 6 | `compare` | Compare | Pairwise metrics / path overlay |
| 7 | `metrics` | Run metrics | Single-run detail (power / linked from Flight) |

Walkthrough labels (strip only): **Matrix · Flight · Laws · Envelope** (Estimation is titled “Laws” in the strip).

### 2.3 Mission model

| Mission id | Short label | Default run | Role |
|------------|-------------|-------------|------|
| `baseline` | Baseline | `figure_eight_lqr` | Constant-yaw portfolio path |
| `envelope_edge` | Envelope edge | `edge_figure_eight_lqr` | τ★≈0.28 + scheduled yaw |

- **Primary control:** segmented buttons in the sticky header only.
- **In-tab:** `Active mission · …` chip (no second full selector).
- Changing mission rebinds matrix metrics, run pickers, MC default, and Compare defaults via `missions[]` + `run_id_by_mission` / `metrics_by_mission`.

---

## 3. Copy contract

| Slot | Source | As-built intent |
|------|--------|-----------------|
| Page title | `ui.display_title` / `title` | `uavsim · controller × sensor flight study` |
| Value prop | `ui.value_prop` | One line: SIL LQR vs PID under shared sensor suites |
| About panel | `ui.about_paragraphs[]` | Four short paragraphs (what / dual mission / intentional fails / MC+envelope+SIL) |
| Walkthrough | SPA constants | Engineering labels; no “hero / filter win” marketing slang |

Fallback constants live in `app.js` if JSON fields are missing.

---

## 4. Screen specifications

### 4.1 Overview

**Must have**

- Suggested first look CTA → Flight on envelope-edge default run.
- Secondary CTAs → Estimation, Envelope.
- Controller × sensor **matrix grid** (2 laws × sensor columns) for active mission.
- Cell content: method, badges, RMSE, pass/fail (bound), max |e|.
- Click cell → set run + open Flight 3D.
- Legend: within bound / exceeds bound / GPS+IMU naive vs KF highlight / click → Flight.
- Toggle: highlight GPS+IMU naive vs KF columns.
- MC (and other non-matrix) cards for the active mission.

**Must not**

- Duplicate full Mission control in the matrix header (chip only).

### 4.2 Flight 3D

**Must have**

- Dual pane: trajectory (N/E/up) + vehicle attitude/wrench at origin.
- Time scrubber; **← / →** frame step (Shift = ±10); ignore when focus is text inputs.
- Trajectory: path, reference, trail, velocity cue, body triad at vehicle.
- Vehicle: X-quad mesh, RGB body axes, thrust (−body *z*) and torque arrows, HUD (F, |τ|, φθψ, |v|).
- Run picker filtered to active mission; link to Run metrics.

**Data fields:** `timeseries.t`, `pos_plot`, `ref_plot`, `euler_deg`, `vel_ned`, `omega`, `u`, `limits`.

### 4.3 Estimation (“Laws” in walkthrough)

**Must have**

- Grouped bar chart: position RMSE by sensor column, series = LQR/LQG vs PID (display cap 5 m).
- **Scenario table** congruent with envelope tables: sticky header, sort, bound filter, search, pass/fail pills, row click → Flight.
- Short “How to read this” list (naive vs KF, LQR vs PID, GPS-denied, naming, envelope pointer).

### 4.4 Envelope

**Must have**

- Family chips: All / LQR family / PID only / Recommended set.
- Per-scheme visibility toggles (color swatches).
- Recommended default series (not all 12): ideal LQR, ideal PID, GPS+IMU LQG, flow+alt LQG, GPS+IMU naive LQR.
- Plots: RMSE vs τ; RMSE vs peak tilt — with **axis caps** (y RMSE 1e-4…5 m; tilt x ≤ 75°; off-scale tilt as edge markers).
- Solid = LQR family; dashed = PID.
- **Breakdown by scheme** table (sortable).
- **Full sweep data** collapsed by default; expandable sortable/filterable table.

**Data:** `envelope.points[]`, `envelope.schemes[]`, `envelope.boundary`.

### 4.5 Monte Carlo

- Prefer `missions[i].mc_run_id` for active mission.
- Existing MC visualizations (summary + trials payload).

### 4.6 Compare

- Default pair from mission `compare_ids` (baseline: naive vs LQG).
- Caption: same-sensor naive vs KF/LQG, not vague “filter win.”
- Metrics B−A; optional 3D path overlay when both have timeseries.

### 4.7 Run metrics

- Secondary: full metric dump for selected run.
- Entry from Flight toolbar; de-emphasized in tab order.

---

## 5. Data contract (`showcase.json`)

### 5.1 Top-level

| Key | Type | Notes |
|-----|------|--------|
| `schema_version` | int | Gallery schema (currently `1`) |
| `title` | string | Document title |
| `description` | string | Long description (may join about paragraphs) |
| `generated_at` | ISO string | Build time |
| `uavsim_version` | string | Package version |
| `runs` | array | Flat list of run cards |
| `missions` | array | Mission catalog (required for dual-mission UX) |
| `estimation_matrix` | object | Columns, rows, scenarios |
| `envelope` | object \| null | τ-sweep document |
| `compare` | object \| null | Default A/B for compare tab |
| `ui` | object | SPA defaults and copy |

### 5.2 `ui`

| Key | Type | Notes |
|-----|------|--------|
| `default_mission` | string | e.g. `baseline` |
| `default_run` | string | Gallery run id |
| `tabs` | string[] | Preferred order (SPA has its own fixed list today) |
| `display_title` | string | Header H1 override |
| `value_prop` | string | One-line subtitle |
| `about_paragraphs` | string[] | About panel body |

### 5.3 `missions[]`

| Key | Type | Notes |
|-----|------|--------|
| `id` | string | `baseline` \| `envelope_edge` |
| `label` / `short_label` | string | Segmented control text |
| `description` | string | Mission hint |
| `mission_file` | string | Config path |
| `yaw_mode` | string | e.g. `constant`, `from_waypoints` |
| `time_scale` | number | 1.0 or τ★ |
| `default_run` | string | |
| `compare_ids` | [string, string] | |
| `mc_run_id` | string | |
| `run_ids` | string[] | Membership filter |

### 5.4 `runs[]` (gallery entry)

Must include: `id`, `label`, `role`, `mission_id`, `metrics`, optional `timeseries`, optional `mc`.

### 5.5 `estimation_matrix.scenarios[]`

| Key | Type | Notes |
|-----|------|--------|
| `id`, `column`, `controller`, `label`, `sensors`, `method`, `lesson` | | |
| `role` | string | Shared across missions |
| `run_id` | string | Baseline default |
| `run_id_by_mission` | map | mission id → run id |
| `metrics` | object | Baseline metrics slice |
| `metrics_by_mission` | map | mission id → metrics slice |

### 5.6 `envelope` (schema_version 2)

- `schemes[]`: `{ id, label, family, sensors, study, method }`
- `points[]`: one per (τ, scheme) with `law` = scheme id, RMSE, success, tilts, …
- `boundary`: per scheme last-ok / first-fail τ
- Plot UX may clip extremes; raw point values remain in JSON

---

## 6. Visual / interaction design (as-built)

| Token / pattern | Spec |
|-----------------|------|
| Theme | Dark ops console (`--bg`, `--panel`, `--accent` blue) |
| Pass / fail | Green / red text + pills; fail rows tinted |
| Badges | Law / sensor family chips on matrix cells |
| Tables | `.data-table` sticky head, sort carets, toolbar filters |
| Desktop | Preferred; note in About; Flight stacks ≤960px |
| Keyboard | Flight scrub ←/→ (Shift ×10) |
| A11y | Mission `aria-pressed`; tabs `aria-selected`; walkthrough `aria-current` |

---

## 7. Build & deploy

| Action | Command / path |
|--------|----------------|
| Full rebuild | `uv run uavsim gallery --base-case` |
| Smoke | `--n-mc-trials N --skip-envelope` and/or `--skip-edge-mission` |
| Local serve | `python -m http.server 8765 --directory docs/showcase` |
| Cache bust | Query string on `app.js` / `styles.css` in `index.html` (bump on SPA edits) |
| Pages | `.github/workflows/pages-showcase.yml` → `gh-pages` |

**Stale-data risk:** `showcase.json` can lag code. Rebuild before demos ([LIMITATIONS.md](../LIMITATIONS.md)).

---

## 8. Non-goals / deferred

| Item | Status |
|------|--------|
| Full interactive control of live sim from the SPA | Out of scope |
| Offline-vendored React/Plotly | Deferred (CDN dependency) |
| Mobile-optimized matrix | Deferred (dense by design) |
| Server-side auth / multi-study browser | Out of scope |

---

## 9. Sync policy

When changing UX behavior or the JSON contract:

1. Update **this file** in the same PR.
2. Update `docs/showcase/README.md` only for rebuild recipes / study tables if those change.
3. Prefer driving copy via `ui.*` in `gallery.py` so rebuilds stay consistent with the SPA fallbacks in `app.js`.

**Last as-built review:** 2026-07-24 — dual mission, full matrix envelope, guided walkthrough, About paragraphs, Estimation data table.
