# Intercept demo — UX specification (L0 + Monte Carlo)

| Field | Value |
|-------|--------|
| **Status** | Design **R3** (top transport · attitude pane · battery · pad/GE story) |
| **Audience** | Hiring GNC reviewers + peers; teaching intercept + plant-MC robustness + energy |
| **Location** | `docs/demos/intercept/` (independent of portfolio showcase) |
| **Hosting** | Static GitHub Pages; no build step preferred |
| **Stack** | HTML + vanilla JS (or React-via-CDN like showcase) + Plotly CDN |
| **Story** | Pad takeoff + climb (ground effect), open-loop ownship path, scripted target, NDI; capture if `min_range ≤ 1 m`; plant MC on success recipe; battery SOC/power when enabled |

This is a **thin single-mission dashboard**, not a matrix gallery. Reuse **visual language and interaction patterns** from [`docs/showcase/`](../../showcase/) (dark research chrome, **sticky transport near header**, Flight **trajectory + attitude** dual-pane, MC histograms). Do **not** rebuild the controller × sensor portfolio.

Related product intent: [`plan/ONLINE_INTERCEPT_AND_BATTERY.md`](../../../plan/ONLINE_INTERCEPT_AND_BATTERY.md) §5, §7; heritage of scrub/MC/3D in [`docs/showcase/UI_SPEC.md`](../../showcase/UI_SPEC.md).

**R2 product correction (retained):** 3D flight-path visualization and MC trajectory confidence bands are **required acceptance**. Shipping `mc.bands: null` or a 2D-only primary view is **not** UX-satisfied.

**R3 product correction:** Layout and energy/attitude presentation are **hard requirements** (not polish):

1. **Play/scrub transport at the TOP** (sticky under/with header — portfolio showcase pattern), **not** buried under geometry plots.
2. **Attitude plot** (vehicle at origin / dual-pane Flight style) occupies the slot **to the right of primary 3D geometry** (where range-vs-time sat in R2).
3. **Range-vs-time** moves **down**, **side-by-side with top-down (N–E) trajectory**.
4. **MC confidence bands** remain **required and visible by default** on **2D and 3D** when `mc.bands` present.
5. **Battery level indicator** (SOC gauge/bar scrub-synced) + **energy/power time series** when pack includes battery fields.
6. Story copy: mission is **pad climb + ground effect** (takeoff from pad / GE), not abstract free-flight only.

---

## 1. Goals

1. Communicate the **intercept story** in one screenful of hierarchy: **transport first** → geometry (3D + **attitude**) → map + range → battery → capture KPI → MC confidence.
2. Let a reviewer **play/scrub** a nominal success (and fail, if present) chase with ownship + target in **3D plot frame (N/E/up)**, **vehicle attitude at origin**, and supporting map/series — controls always reachable at top.
3. Surface **P(capture)** and **min-range distribution** from plant mass / I / arm scatter without burying the reader in a full metrics dump.
4. Show **toggleable MC confidence bands** on trajectories — **required on 2D N–E**; **required on 3D** (percentile polylines and/or translucent fan); default **ON** when data present.
5. Show **battery SOC + power/energy** when timeseries include `soc` / `power_w` / `energy_wh_remaining`.
6. Ship as a **self-contained static SPA** under `docs/demos/intercept/` with a data pack that **includes** precomputed `mc.bands` (and battery series when the study enables battery).

### Non-goals (summary)

See §7. Notably: no live sim, no multi-mission matrix, no full per-trial 3D cloud of all 500 paths, no wrench HUD required (attitude mesh yes; full rotor-thrust wrench optional). No in-browser re-sim.

---

## 2. Page structure / information hierarchy

Single page, top → bottom. **Header + transport sticky** so play/scrub remains available while scrolling plots (showcase sticky-header pattern).

```text
┌─────────────────────────────────────────────────────────────┐
│ HEADER (sticky top)                                         │
│  title · value prop · About · meta                          │
│  [ Success | Fail ]   KPI chips: P(cap) · n · r             │
├─────────────────────────────────────────────────────────────┤
│ TRANSPORT (sticky under header — R3 HARD)                   │
│  Play · scrub · t / range readouts · speed · CPA · bands    │
│  [optional compact SOC bar in transport row]                │
├─────────────────────────────────────────────────────────────┤
│ STORY STRIP                                                 │
│  Pad takeoff + climb (ground effect) · L0 open-loop path ·  │
│  scripted target · fixed NDI · capture criterion            │
├──────────────────────────────┬──────────────────────────────┤
│ PRIMARY A: Trajectory 3D     │ PRIMARY B: Attitude (R3)     │
│  N / E / up (Plotly scene)   │  Vehicle at origin           │
│  ownship + target paths      │  X-quad mesh + body axes     │
│  scrub markers + trail       │  euler from pack / x[3:6]    │
│  MC envelope (toggle)        │  scrub-synced (Flight style) │
│  optional capture sphere     │  (wrench optional)           │
├──────────────────────────────┼──────────────────────────────┤
│ SECONDARY A: Top-down 2D     │ SECONDARY B: Range vs time   │
│  N–E map                     │  range_m(t) + capture line   │
│  paths + capture circle      │  scrub playhead              │
│  MC band fill (required)     │                              │
├──────────────────────────────┴──────────────────────────────┤
│ BATTERY ROW (when data present — R3 HARD)                   │
│  SOC gauge/bar (scrub-synced)  ·  power_w(t) / energy_wh(t) │
├─────────────────────────────────────────────────────────────┤
│ MC PANEL                                                    │
│  min_range histogram · optional peak_tilt stats             │
│  short “how to read” blurb                                  │
├─────────────────────────────────────────────────────────────┤
│ FOOTER · Simulation only · link to repo / study YAMLs       │
└─────────────────────────────────────────────────────────────┘
```

### Preferred layout (R3) — normative

| Slot | Content | R2 was… |
|------|---------|---------|
| **Sticky header** | Title, KPIs, case toggle, About | same |
| **Sticky transport** | Play / scrub / speed / CPA / bands / time+range (+ optional SOC strip) | under geometry ❌ |
| **Left primary** | **3D trajectory** (N, E, up) + MC envelope | same |
| **Right primary** | **Attitude** at origin (Flight dual-pane style) | range(t) |
| **Left secondary** | **2D N–E** + capture circle + **MC bands** | full-width 2D |
| **Right secondary** | **`range_m(t)`** + capture line + playhead | right primary |
| **Battery row** | SOC indicator + power/energy series | optional later ❌ → **required when pack has series** |
| **MC panel** | histogram + how-to-read | same |

**Not acceptable (R3):**

- Transport only under plots (must also be at top; dual placement of transport is OK only if **top sticky** is the primary).
- Range-vs-time still in the right primary slot instead of attitude.
- Attitude omitted when `euler_deg` or state `x` attitude is available in pack.
- MC bands permanently off / missing on 2D when `mc.bands` present.
- Empty battery chrome when series exist; **or** fake empty battery charts when series absent (omit block if no data).
- Story copy that ignores pad takeoff / ground effect for the current mission framing.

### 2.1 Header

| Element | Behavior |
|---------|----------|
| **Title** | e.g. `uavsim · intercept L0 (NDI + plant MC)` — mono weight like showcase |
| **Value prop** | One muted line: pad climb + intercept path, scripted target, fixed NDI, plant scatter (+ battery if enabled) |
| **About** | Collapsed: capture radius; pad takeoff / GE; success vs fail recipe; MC perturbations (mass/I/arm); redesign_controller false; trajectory bands from re-sim percentiles; battery model note if present |
| **Case toggle** | Segmented control: **Success** \| **Fail** (disable or hide Fail if data missing) |
| **KPI chips** | Always visible (from MC summary when available; else nominal-only badges). Optional chip: **SOC final** or **SOC min** when battery metrics exist |

### 2.2 Story strip

Short static copy (from `meta.json` / `demo.json` `ui` block). **R3 must mention pad / GE:**

- Ownship **takes off from a pad**, climbs through **ground effect**, then pursues a **scripted target** on an **open-loop** reference (L0 — not closed-loop replan hero yet if still L0).
- Capture: \(\min_t \|p_{\mathrm{own}}-p_{\mathrm{tgt}}\| \le r_{\mathrm{capture}}\) (default **1 m**).
- MC: plant parameters only; gains fixed; bands = spatial envelope of ownship under plant scatter.
- Battery (if enabled): SOC/power logged; demo shows scrub-synced energy story.

Exporter / `ui` strings should be updated so About + value_prop match (not only hard-coded HTML).

### 2.3 Transport bar (play + scrub) — **TOP, sticky (R3 hard)**

Place **immediately under the header** (same sticky stack as showcase `sticky-header` / Flight toolbar feel). Do **not** leave transport only below secondary plots.

| Control | Behavior |
|---------|----------|
| **Play / Pause** | Toggle; advances frame index at ~real-time or fixed FPS (e.g. 30 fps mapped to `t`) |
| **Scrubber** | Range input 0…N−1; drag updates **all** markers (3D + 2D + attitude + range cursor + battery gauge) |
| **← / →** | Step ±1 frame; Shift = ±10 (ignore when focus is text inputs) |
| **Time readouts** | `t = … s` and `range = … m` tabular nums |
| **Speed** | Optional 0.5× / 1× / 2×; default 1× |
| **MC bands toggle** | Global for 2D + 3D envelopes; default **on** when data present |
| **Jump to CPA** | Optional; index nearest `time_of_min_range_s` |
| **SOC strip** | Optional compact bar in transport showing `soc[i]` when battery present |

On case toggle: reset to t=0; pause; rebind all plots to active `CasePack`.

**Frame sync rule:** one `frameIndex` drives every view. Prefer Plotly `restyle` for marker/trail/attitude updates on scrub; full `newPlot` only on case change, projection change, or band toggle.

**CSS:** `position: sticky; top: 0` (or under fixed header height); `z-index` above plots; dark translucent background + border like showcase `.sticky-header` (`backdrop-filter` optional).

### 2.4 Primary visual A: trajectory 3D (required)

**Plot frame: North–East–Up** (Plotly `scatter3d`), matching showcase Flight **path** pane ([`docs/showcase/UI_SPEC.md`](../../showcase/UI_SPEC.md) §4.2).

| Layer | Style | Notes |
|-------|--------|------|
| Target path | solid warn/amber | full history |
| Ownship path | solid / muted accent | full history |
| Ownship trail to \(t_i\) | brighter / thicker | scrub-dependent |
| Vehicle marker at \(t_i\) | accent | |
| Target marker at \(t_i\) | warn | |
| **MC envelope (toggle)** | translucent percentile polylines (p5/p50/p95) and/or soft fan | ownship only; **required visible when bands on** |
| Capture sphere (optional) | faint dashed / translucent sphere radius `capture_radius_m` at CPA | nice-to-have |

**Camera / scene:** fixed bounds from nominal paths (+ band extents if larger); dark scene bg; aspectmode manual; preserve camera on scrub via `uirevision` + restyle of markers/trail. User may orbit/zoom; scrub must not reset camera.

### 2.5 Primary visual B: attitude at origin (**R3 hard**)

Right of 3D — **Flight dual-pane attitude** pattern from [`docs/showcase/app.js`](../../showcase/app.js) (`VehicleAttitudeView` / `vehicleGeom`, ~lines 429–530, 857–1040):

| Concern | Guidance |
|---------|----------|
| **Frame** | Vehicle fixed at **origin**; plot axes N / E / up (body rotated into plot frame) |
| **Mesh** | X-quad airframe segments + motor hubs |
| **Body axes** | RGB (or accent triad) body +x/+y/+z |
| **Attitude source** | Prefer `timeseries.euler_deg[i]` (φθψ deg); else derive from state if exporter stores `x` columns 3:6 rad |
| **Wrench / rotor thrust** | **Optional** for R3 (showcase draws `u` mix); attitude mesh + axes alone **satisfies** if `u` not in pack |
| **FOV** | Fixed cube ~±1 m visual span; `uirevision` stable; **restyle** on scrub |
| **Sync** | Same `frameIndex` as 3D / 2D / range / battery |

If euler missing entirely: show honest empty card (“attitude not in pack”) — **exporter should include `euler_deg`** for success/fail nominals (already partially supported in `export_demo_data.py`).

### 2.6 Secondary row: 2D N–E + range(t) (**R3 hard**)

**Left — Trajectory 2D (North–East top-down):**

| Layer | Style | Notes |
|-------|--------|------|
| Target path | solid warn/amber | full history |
| Ownship path | solid accent | full history |
| Ownship trail to \(t_i\) | brighter / thicker | scrub-dependent |
| Vehicle / target markers | at \(t_i\) | |
| **Capture circle** | dashed good/muted | radius = `capture_radius_m` — **required** |
| **MC bands** | translucent fill between p5–p95 in N–E | ownship only; **required** when `mc.bands` present (default **ON**) |

**Optional projection chip:** N–E \| N–Up on the 2D card (bands on N–Up use N/U pairs). Bands **must** work on N–E at minimum.

**Right — Range vs time:**

- **`range_m(t)`** with horizontal line at `capture_radius_m`.
- Scrub playhead vertical line.
- Nice-to-have: tilt strip (not required).

### 2.7 Battery (**R3 hard when data present**)

When **any** of `timeseries.soc`, `timeseries.power_w`, `timeseries.energy_wh_remaining` exist on the active case:

| Widget | Behavior |
|--------|----------|
| **SOC gauge / bar** | Shows `soc[frameIndex]` (0–1 or 0–100% — label units from data; assume fraction if ≤1.01). Scrub/play updates live. Color: good when high, warn mid, bad near empty (cosmetic thresholds OK). |
| **Power series** | `power_w(t)` vs time + playhead when present |
| **Energy series** | `energy_wh_remaining(t)` vs time + playhead when present |
| **Layout** | One card row: gauge left (~¼), shared or dual time series right; stack on narrow viewports |

When **no** battery series: **omit** the entire battery section (no empty chart, no fake zeros).

Exporter: pass through from nominal `timeseries.npz` / pipeline (`soc`, `power_w`, `energy_wh_remaining` written by `run_dir` / studies pipeline when battery enabled). Downsample with the same index as other series.

### 2.8 Monte Carlo panel

| Widget | Content |
|--------|---------|
| **KPI restatement** | P(capture), n trials, capture radius (same as header chips) |
| **Histogram** | `min_range_m` over trials; vertical line at `capture_radius_m`; optional color split success/fail bins |
| **Secondary stats** | Compact: mean/p50/p95 `min_range_m`; optional mean `peak_tilt_rad` (deg); optional SOC stats if MC columns present |
| **How to read** | 3–4 bullets: plant scatter only; fixed NDI; capture definition; bands = ownship spatial percentiles; pad/GE mission context |

Optional collapsed “trial table” — not required.

---

## 3. Required views (checklist form)

| # | View | Required | Data dependency |
|---|------|----------|-----------------|
| 1 | KPI: **P(capture)**, **n trials**, capture radius | Yes | `mc.summary` / derived from trials |
| 2 | Success vs fail **nominal case toggle** | Yes if both packs present | `cases.success`, `cases.fail` |
| 3 | Trajectory **3D** (N/E/up) ownship + target + scrub | Yes | nominal `*_plot` timeseries |
| 4 | **Attitude at origin** (right primary) | **Yes (R3)** when euler available | `euler_deg` or equivalent |
| 5 | Trajectory **2D** N–E with **capture circle** | Yes | nominal timeseries |
| 6 | **`range_m(t)`** secondary right (with 2D) | Yes | `timeseries.range_m` |
| 7 | **MC confidence bands** on **2D N–E** (toggleable, default ON) | Yes — pack **must** include bands for success MC | `mc.bands` non-null |
| 8 | MC envelope on **3D** (toggleable; shared toggle) | Yes | same `mc.bands` |
| 9 | **Transport sticky at top** (play + scrub) | **Yes (R3)** | `timeseries.t` |
| 10 | **min_range histogram** | Yes if MC present | `trials[].min_range_m` |
| 11 | **Battery SOC + power/energy** | **Yes (R3)** when series in pack | `soc`, `power_w`, `energy_wh_remaining` |
| 12 | Story mentions **pad climb / GE** | **Yes (R3)** | `ui` copy / story strip |

Empty states:

- No MC → show nominal geometry + attitude + range; KPI chips show “MC not in pack”; hide histogram + band toggle. (**Shipped product pack is expected to include MC + bands.**)
- Bands missing in a broken pack → disable toggle with honest tooltip; treat as **implementation defect** for the success-MC demo pack.
- No euler → attitude empty card; exporter should fix pack.
- No battery series → omit battery row.
- No fail case → Success only.
- Load error → single card with rebuild instructions.

---

## 4. Data contract

Prefer a **single demo pack** built offline into `docs/demos/intercept/data/` so Pages never reads `runs/`. Source of truth for generation remains study run dirs, e.g.:

```text
runs/intercept_*_success_*/nominal/{timeseries.*, metrics.json}
runs/intercept_*_success_*/monte_carlo/{trials.csv, summary.json}
runs/intercept_*_fail_*/nominal/{timeseries.*, metrics.json}
```

### 4.1 Files served to the browser

| Path | Role |
|------|------|
| `data/demo.json` | **Primary** pack: meta, cases, MC summary, trials, **required `mc.bands`** for success MC demo |
| `data/meta.json` | Optional thin pointer |
| `data/trials.csv` | Optional raw MC table |

**Recommendation:** one `demo.json` ≤ ~2–5 MB with downsampled timeseries (incl. battery + euler), compact trials, **bands as quantile polylines**. Never ship raw multi-trial path clouds.

### 4.2 Top-level `demo.json` schema

```json
{
  "schema_version": 1,
  "title": "uavsim · intercept L0",
  "generated_at": "ISO-8601",
  "uavsim_version": "0.1.0",
  "ui": {
    "value_prop": "Pad climb (ground effect) → open-loop intercept path; scripted target; fixed NDI; plant MC.",
    "about_paragraphs": ["…pad takeoff…", "…capture…", "…MC bands…", "…battery if enabled…"],
    "capture_radius_m": 1.0,
    "default_case": "success",
    "mission_notes": "pad_climb_ground_effect"
  },
  "cases": {
    "success": { "…CasePack…" },
    "fail": { "…CasePack…" }
  },
  "mc": {
    "source_study": "…",
    "n_trials": 500,
    "summary": { },
    "trials": [ ],
    "bands": { }
  }
}
```

`cases.fail` may be `null` or omitted. MC + **bands** attach to the **success** recipe; when Fail nominal is shown, caption: “MC / bands: success plant study”.

### 4.3 `CasePack` (nominal)

| Field | Type | Notes |
|-------|------|--------|
| `id` | string | e.g. `intercept_l0_success` |
| `label` | string | UI label |
| `source_run` | string | run dir name for provenance |
| `metrics` | object | from `nominal/metrics.json` |
| `metrics.min_range_m` | number | |
| `metrics.time_of_min_range_s` | number | |
| `metrics.intercept_success` | bool | |
| `metrics.capture_radius_m` | number | |
| `metrics.peak_tilt_rad` | number \| optional | |
| `metrics.soc_final` / `soc_min` / `peak_power_w` | optional | when battery enabled |
| `timeseries.t` | number[] | seconds, downsampled (~200–400 pts OK) |
| `timeseries.pos_ned` | number[][] | ownship \(N,E,D\) — optional if `pos_plot` present |
| `timeseries.pos_plot` | number[][] | **required plot frame: N, E, up** |
| `timeseries.target_ned` / `target_plot` | number[][] | scripted target, same length as `t` |
| `timeseries.range_m` | number[] | \(\|p_{\mathrm{own}}-p_{\mathrm{tgt}}\|\) |
| `timeseries.euler_deg` | number[][] | **φθψ deg — required for attitude pane (R3)** when available from `x` |
| `timeseries.vel_ned` | optional | |
| `timeseries.ref_plot` | optional | open-loop reference path |
| `timeseries.soc` | number[] \| optional | state of charge (fraction or % — document); **R3 battery** |
| `timeseries.power_w` | number[] \| optional | electrical / propulsive power |
| `timeseries.energy_wh_remaining` | number[] \| optional | residual energy |
| `timeseries.u` | number[][] \| optional | wrench for optional rotor thrust viz |

Convention: **prefer `*_plot` arrays as North, East, Up** so UI never guesses D vs U.

**Attitude derivation:** if only full state is available offline, exporter uses `x[:, 3:6]` rad → `euler_deg` (already in `export_demo_data.py`). UI prefers ready-made `euler_deg`.

### 4.4 Monte Carlo block

#### From pipeline artifacts (generator input)

**`monte_carlo/trials.csv`** preferred columns (see `uavsim.monte_carlo.io`):

| Column | Role in UI |
|--------|------------|
| `trial_id` | identity |
| `mass_kg`, `ixx_kg_m2`, `iyy_kg_m2`, `izz_kg_m2`, `arm_length_m` | **re-sim plant params** for band generation |
| `min_range_m` | **histogram primary** |
| `time_of_min_range_s` | optional |
| `capture_radius_m` | should be constant |
| `intercept_success` | bool → **P(capture)** |
| `peak_tilt_rad` | secondary stat |
| `soc_final`, `soc_min`, `peak_power_w` | optional energy MC columns |
| `success`, `sim_success` | sim health vs capture; **do not conflate** with `intercept_success` |

**P(capture)** definition for KPI:

\[
P(\mathrm{capture}) = \frac{\#\{\texttt{intercept\_success}=\mathrm{true}\}}{n_{\mathrm{trials}}}
\]

Demo exporter **should compute and store**:

```json
"summary": {
  "n_trials": 500,
  "n_intercept_success": 487,
  "p_capture": 0.974,
  "capture_radius_m": 1.0,
  "min_range_m": { "mean": …, "p50": …, "p95": …, "min": …, "max": … },
  "peak_tilt_rad": { "mean": …, "p95": … }
}
```

#### Confidence bands (`mc.bands`) — **required for success-MC pack**

Standard MC exports only write **scalar** trial rows. The demo exporter **must** produce spatial percentiles by offline re-sim (or stored paths), then axis-wise percentiles on a common grid.

**Required schema:**

```json
"bands": {
  "frame": "plot",
  "percentiles": [5, 50, 95],
  "t": [0.0, 0.05, 0.10],
  "n_paths_used": 500,
  "method": "axiswise_percentile",
  "notes": "Ownship position percentiles after plant-param re-sim; fixed NDI / open-loop ref",
  "ownship": {
    "N": { "p5": [], "p50": [], "p95": [] },
    "E": { "p5": [], "p50": [], "p95": [] },
    "U": { "p5": [], "p50": [], "p95": [] }
  }
}
```

| Field | Requirement |
|-------|-------------|
| `frame` | `"plot"` → arrays are N, E, **up** |
| `percentiles` | Include **5 and 95**; **50** recommended |
| `t` | Common time grid (s); length \(T\) |
| `ownship.N/E/U.p5|p50|p95` | Length-\(T\); p5+p95 for N,E min; U for 3D |
| `n_paths_used` | Provenance |
| `method` | e.g. `axiswise_percentile` — not a joint ellipsoidal tube |

**UI rendering:**

| View | How to draw |
|------|-------------|
| **2D N–E** | Filled band: polygon along (E_p5, N_p5) then reverse (E_p95, N_p95); optional thin p50 line |
| **2D N–Up** | Same with N/U |
| **3D** | p5, p50, p95 as `scatter3d` polylines (N,E,U) with decreasing opacity; same global toggle |

**R3 visibility gate:** With bands present and toggle default ON, a reviewer must **see** the 2D fill and 3D percentile curves without hunting for a buried control. Toggle lives in **top transport**.

**Alignment:** Band `t` need not equal nominal `timeseries.t`; bands are full-horizon envelopes (not scrub-dependent geometry). Scrub only moves nominal markers / attitude / series cursors.

### 4.5 Provenance fields

Optional footer / About:

- `source_run`, `git_commit`, `seed`, `n_trials`, pad/GE mission id, battery config blurb.
- Band generation: `n_paths_used`, `method`, CLI flags.

---

## 5. Interaction model

| Action | Result |
|--------|--------|
| **Load** | Fetch `data/demo.json`; default case = `ui.default_case` or `success` |
| **Case toggle Success/Fail** | Swap nominal timeseries + metrics; keep MC panel + bands (success study); reset playhead; pause; rebuild all plots |
| **Play** | Advance index; **stop at end** by default (loop off) |
| **Pause** | freeze index |
| **Scrub** | set index; update 3D trail/markers, attitude mesh, 2D markers/trail, range cursor, battery gauge + series playheads |
| **Keyboard ←/→** | step frames when not typing |
| **MC bands toggle** | show/hide band traces on **2D and 3D** (default **on** if data present) |
| **Orbit 3D / attitude** | Plotly camera free; scrub does not reset eye |
| **Jump to CPA** | index nearest `time_of_min_range_s` |

### State (minimal)

```text
caseId: 'success' | 'fail'
frameIndex: number
playing: boolean
speed: number
showBands: boolean   // default true when mc.bands present
projection: 'NE' | 'NU'   // optional 2D
```

No URL routing required for v1; optional `?case=fail` nice-to-have.

---

## 6. Visual design notes

Match showcase research aesthetic ([`docs/showcase/styles.css`](../../showcase/styles.css)):

| Token | Value (reuse) |
|-------|----------------|
| `--bg` | `#111315` |
| `--panel` | `#1a1d21` |
| `--border` | `#2a2f36` |
| `--text` | `#e8eaed` |
| `--muted` | `#9aa0a6` |
| `--accent` | `#5b9fd4` |
| `--good` | `#3ecf8e` |
| `--bad` | `#f07178` |
| `--warn` | `#e6b450` |

| Pattern | Guidance |
|---------|----------|
| **Typography** | System UI; titles `ui-monospace`; tabular nums for KPIs/time/SOC |
| **Cards** | Panel background, 1px border, 8–12px radius |
| **Sticky chrome** | Header + transport: dark translucent bg, bottom border, z-index ≥ 40 |
| **Segmented controls** | Showcase mission-seg pattern |
| **KPI chips** | Pill/stat blocks; good for high P(capture) |
| **Plotly 2D/3D** | Dark paper/plot; scene bg `#0a0e16`; `displaylogo: false` |
| **Bands** | Accent @ 15–25% opacity; never obscure nominal paths |
| **SOC gauge** | Horizontal bar or radial; high contrast fill; % label |
| **Density** | Wide desktop first; **primary-row** and **secondary-row** each two columns; stack ≤960px |

Copy tone: engineering, not marketing (“pad climb, ground-effect κ, plant scatter, fixed NDI” not “hero win”).

---

## 7. Out of scope

- Portfolio **controller × sensor matrix**, envelope τ-sweep, compare tab, stack diagram
- Live / WASM simulation or parameter knobs that re-run dynamics in-browser
- Full **3D cloud of all MC trial paths**
- **Required** full wrench HUD (rotor thrust arrows) — optional if `u` present
- Closed-loop **online replan** intercept UX (future L1+ story)
- Auth, multi-user, mobile-first layout
- MATLAB or runtime dependency on heritage tree
- Requiring users to open raw `runs/` on Pages
- Build step / bundler **required** (CDN first)
- HIL, multi-vehicle, sensor-noise MC story

---

## 8. Acceptance criteria — “UX satisfied” (R3)

Mark **UX satisfied** when a reviewer can open the static page (local or Pages) and:

1. **See KPIs immediately:** P(capture) and n trials (or explicit “no MC”) without opening a second tab.
2. **Toggle Success/Fail** (if fail pack present) and see ownship + target paths, attitude, range(t), and battery (if present) update.
3. **Play and scrub from the TOP transport** (sticky); vehicle/target markers, attitude, range cursor, and battery gauge stay synced across panes. Transport is **not** only under the plots.
4. **Read capture criterion** on the page and on the range plot; **see capture circle on 2D**.
5. **Inspect min_range histogram** with capture-radius marker when MC data present.
6. **View 3D flight path** (N/E/up) for the active nominal with ownship + target; orbit works; scrub updates markers without destroying the scene.
7. **View attitude at origin** in the **right primary** slot (showcase Flight-style mesh/axes), scrub-synced from `euler_deg` (or documented equivalent).
8. **See range(t) side-by-side with 2D N–E** on the **secondary** row (range not in the primary-right slot).
9. **Toggle MC bands** default ON when present: **2D N–E** shows 5–95% envelope; **3D** shows percentile curves; both clearly visible; toggle in top transport.
10. **Shipped success-MC pack includes non-null `mc.bands`** with documented schema (§4.4).
11. **Battery (when pack includes series):** SOC indicator tracks scrub; power and/or energy_wh series show playhead; no empty battery chrome when data absent.
12. **Story copy** states **pad takeoff / climb** and **ground effect** (story strip and/or `ui` About).
13. **Empty/missing data** does not blank the page: controls hide or show honest empty copy.
14. **Visual parity:** dark theme tokens aligned with showcase; sticky chrome readable over plots.
15. **Independence:** all assets under `docs/demos/intercept/`; no hard dependency on `docs/showcase/data/showcase.json`.
16. **Static:** works with `python -m http.server` or GH Pages (relative `fetch` paths).

---

## 9. Implementation sketch (guidance only)

```text
docs/demos/intercept/
  index.html
  app.js                 # state; sticky transport; 3D + attitude + 2D|range + battery
  styles.css             # sticky header+transport; primary/secondary rows
  UX_SPEC.md             # this file
  IMPLEMENT_CHECKLIST.md
  UX_REVIEW_R3_BRIEF.md  # implementer brief (R3)
  scripts/
    export_demo_data.py  # cases + MC bands + euler + battery fields
  data/
    demo.json
```

**Generator:** pass through battery arrays when present; always emit `euler_deg` from `x` when possible; keep `mc.bands` generation; refresh `ui` copy for pad/GE.

**Reference implementations (read, do not import runtime from showcase):**

- Sticky header: `docs/showcase/styles.css` `.sticky-header`
- Attitude: `docs/showcase/app.js` `rotationBodyToNed`, `vehicleGeom`, `VehicleAttitudeView`
- Path 3D + restyle scrub: intercept `drawTraj3d` / showcase `Flight3DView`

---

## 10. Open decisions (resolve at implement if needed)

| Topic | Default if undecided |
|-------|----------------------|
| React CDN vs vanilla | Keep **vanilla** |
| Layout | **R3 normative:** top sticky transport; **3D \| attitude**; **2D N–E \| range**; battery; MC |
| Band percentiles | **5–95** with median p50 |
| Attitude wrench | **Mesh + body axes required**; rotor thrust if `u` present |
| SOC units | If values ∈ [0, 1.01] treat as fraction → display % |
| Battery absent | **Omit** section |
| Fail MC | **No**; MC + bands on success only |
| Loop playback | **Off** by default |
| Capture sphere on 3D | Optional |

---

## Document history

| Date | Note |
|------|------|
| 2026-07-25 | Initial UX spec for L0 intercept MC static dashboard |
| 2026-07-25 | **R2:** 3D trajectory + MC bands required acceptance; bands data generation / schema mandated |
| 2026-07-25 | **R3:** Top sticky transport; attitude right of 3D; range beside 2D N–E; battery SOC/power required when data present; pad climb + GE story; bands visibility retained |
