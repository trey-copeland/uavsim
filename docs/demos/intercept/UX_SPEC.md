# Intercept demo — UX specification (L0 + Monte Carlo)

| Field | Value |
|-------|--------|
| **Status** | Design R2 (3D + MC bands required) |
| **Audience** | Hiring GNC reviewers + peers; teaching intercept + plant-MC robustness |
| **Location** | `docs/demos/intercept/` (independent of portfolio showcase) |
| **Hosting** | Static GitHub Pages; no build step preferred |
| **Stack** | HTML + vanilla JS (or React-via-CDN like showcase) + Plotly CDN |
| **Story** | L0 open-loop ownship path, scripted target, NDI; capture if `min_range ≤ 1 m`; plant MC on success recipe |

This is a **thin single-mission dashboard**, not a matrix gallery. Reuse **visual language and interaction patterns** from [`docs/showcase/`](../../showcase/) (dark research chrome, scrubber, Flight 3D scene, MC histograms). Do **not** rebuild the controller × sensor portfolio.

Related product intent: [`plan/ONLINE_INTERCEPT_AND_BATTERY.md`](../../../plan/ONLINE_INTERCEPT_AND_BATTERY.md) §5, §7; heritage of scrub/MC/3D in [`docs/showcase/UI_SPEC.md`](../../showcase/UI_SPEC.md).

**R2 product correction:** 3D flight-path visualization and MC trajectory confidence bands are **required acceptance**, not stretch / nullable. Shipping `mc.bands: null` or a 2D-only primary view is **not** UX-satisfied for this iteration.

---

## 1. Goals

1. Communicate the **intercept story** in one screenful of hierarchy: geometry (3D + 2D) → capture KPI → MC confidence.
2. Let a reviewer **play/scrub** a nominal success (and fail, if present) chase with ownship + target in **3D plot frame (N/E/up)** and supporting series/projections.
3. Surface **P(capture)** and **min-range distribution** from plant mass / I / arm scatter without burying the reader in a full metrics dump.
4. Show **toggleable MC confidence bands** on trajectories — **required on 2D N–E at minimum**; 3D shows nominal + envelope (percentile polylines and/or translucent tube-like fan).
5. Ship as a **self-contained static SPA** under `docs/demos/intercept/` with a data pack that **includes** precomputed `mc.bands` (re-sim trials offline if needed).

### Non-goals (summary)

See §7. Notably: no live sim, no multi-mission matrix, no full per-trial 3D cloud of all 500 paths, dual-pane attitude/wrench mesh optional, battery UI optional later.

---

## 2. Page structure / information hierarchy

Single page, top → bottom (sticky header + one scrollable body; optional light section anchors — **no multi-tab matrix**).

```text
┌─────────────────────────────────────────────────────────────┐
│ HEADER (sticky)                                             │
│  title · one-line value prop · About (expand) · meta        │
│  [ Success | Fail ] case toggle   KPI chips: P(cap) · n · r │
├─────────────────────────────────────────────────────────────┤
│ STORY STRIP (1–2 sentences + capture criterion)             │
├──────────────────────────────┬──────────────────────────────┤
│ PRIMARY A: Trajectory 3D     │ PRIMARY B: companion pane    │
│  N / E / up (Plotly scene)   │  Prefer: range(t)  OR        │
│  ownship + target paths      │  2D N–E with bands + circle  │
│  scrub markers + trail       │  (if range moved elsewhere)  │
│  MC envelope (toggle)        │                              │
│  optional capture sphere     │                              │
├──────────────────────────────┴──────────────────────────────┤
│ SECONDARY ROW (if range not in primary B)                   │
│  2D N–E map with MC bands + capture circle  ·  range(t)     │
│  (layout may combine: 3D | range on top; 2D bands full-width)│
│  play / scrub bar (full width under primary geometry)       │
├─────────────────────────────────────────────────────────────┤
│ MC PANEL                                                    │
│  min_range histogram · optional peak_tilt / RMSE sparklines │
│  short “how to read” blurb                                  │
├─────────────────────────────────────────────────────────────┤
│ FOOTER · Simulation only · link to repo / study YAMLs       │
└─────────────────────────────────────────────────────────────┘
```

### Preferred layout (R2)

**Default recommendation** (desktop wide):

| Slot | Content |
|------|---------|
| **Left primary** | **3D trajectory** (N, E, up) — ownship + target nominals, scrub markers, optional MC fan |
| **Right primary** | **`range_m(t)`** with capture line + playhead |
| **Secondary full width** | **2D N–E** with **MC bands** (required when data present), capture circle, scrub markers |
| **Under geometry** | Shared **play / scrub** transport |

**Acceptable alternate:** left **3D**, right **2D N–E with bands**; range(t) as a third row full-width card. Keep total density readable — do not force three equal tall plots if the viewport collapses.

**Not acceptable:** 2D-only primary with 3D omitted; bands permanently absent from the shipped pack.

### 2.1 Header

| Element | Behavior |
|---------|----------|
| **Title** | e.g. `uavsim · intercept L0 (NDI + plant MC)` — mono weight like showcase |
| **Value prop** | One muted line: open-loop intercept path, scripted target, fixed NDI, plant scatter |
| **About** | Collapsed: capture radius, success vs fail recipe, MC perturbations (mass/I/arm), redesign_controller false; note that trajectory bands come from re-sim / percentile paths |
| **Case toggle** | Segmented control: **Success** \| **Fail** (disable or hide Fail if data missing) |
| **KPI chips** | Always visible (from MC summary when available; else nominal-only badges) |

### 2.2 Story strip

Short static copy (from `meta.json` / `demo.json` `ui` block):

- L0 = open-loop ownship reference + scripted target (not closed-loop replan hero yet, if still L0).
- Capture: \(\min_t \|p_{\mathrm{own}}-p_{\mathrm{tgt}}\| \le r_{\mathrm{capture}}\) (default **1 m**).
- MC: plant parameters only; gains fixed; bands = spatial envelope of ownship under plant scatter.

### 2.3 Primary visual A: trajectory 3D (required)

**Plot frame: North–East–Up** (Plotly `scatter3d`), matching showcase Flight path conventions ([`docs/showcase/UI_SPEC.md`](../../showcase/UI_SPEC.md) §4.2 trajectory pane — **path only**, not full attitude/wrench dual-pane).

| Layer | Style | Notes |
|-------|--------|------|
| Target path | solid warn/amber | full history |
| Ownship path | solid / muted accent | full history |
| Ownship trail to \(t_i\) | brighter / thicker | scrub-dependent |
| Vehicle marker at \(t_i\) | accent | |
| Target marker at \(t_i\) | warn | |
| MC envelope (toggle) | translucent percentile polylines (p5/p50/p95) and/or soft mesh-like fan | ownship only; see §4.4 |
| Capture sphere (optional) | faint dashed / translucent sphere radius `capture_radius_m` centered at target at CPA (or ownship at CPA) | **nice-to-have**; 2D circle remains required |

**Camera / scene:** fixed bounds from nominal paths (+ band extents if larger); dark scene bg; aspectmode manual; preserve camera on scrub via `uirevision` + restyle of markers/trail (showcase pattern). User may orbit/zoom via Plotly; scrub must not reset camera.

**Attitude mesh dual-pane** (X-quad, rotor thrust): **optional nice-to-have**, not R2 acceptance.

### 2.4 Primary visual B / secondary: 2D trajectory + bands (required)

**Default 2D: North–East top-down** (Plotly 2D).

| Layer | Style | Notes |
|-------|--------|------|
| Target path | solid warn/amber | full history |
| Ownship path | solid accent | full history |
| Ownship trail to \(t_i\) | brighter / thicker | scrub-dependent |
| Vehicle / target markers | at \(t_i\) | |
| **Capture circle** | dashed good/muted | radius = `capture_radius_m`; center at target at CPA (or documented CPA pose) — **required on 2D** |
| **MC bands** | translucent fill between p5–p95 paired paths in N–E | ownship only; **required** when `mc.bands` present (default **ON**) |

**Optional projection chip:** N–E \| N–Up on the 2D card (bands on N–Up use N/U percentile pairs). Bands **must** work on N–E at minimum.

### 2.5 Time series (companion)

Must:

- **`range_m(t)`** ownship–target Euclidean range; horizontal line at `capture_radius_m`.
- Scrub playhead vertical line.

Nice-to-have:

- Peak-relevant: `tilt_rad` or `tilt_deg(t)` for “beyond linear” story.
- Tracking error if reference present.

### 2.6 Transport bar (play + scrub)

Full width under the primary geometry row (mirror showcase scrub patterns; **add play** which showcase lacks).

| Control | Behavior |
|---------|----------|
| **Play / Pause** | Toggle; advances frame index at ~real-time or fixed FPS (e.g. 30 fps mapped to `t`) |
| **Scrubber** | Range input 0…N−1; drag updates **all** markers (3D + 2D + range cursor) |
| **← / →** | Step ±1 frame; Shift = ±10 (ignore when focus is text inputs) |
| **Time readouts** | `t = … s` and `range = … m` tabular nums |
| **Speed** | Optional 0.5× / 1× / 2×; default 1× |
| **MC bands toggle** | Global for 2D + 3D envelopes; default **on** when data present |
| **Jump to CPA** | Optional; index nearest `time_of_min_range_s` |

On case toggle: reset to t=0; pause; rebind 3D + 2D + range to active `CasePack`.

**Frame sync rule:** one `frameIndex` drives every view. Prefer Plotly `restyle` for marker/trail updates on scrub; full `newPlot` only on case change, projection change, or band toggle.

### 2.7 Monte Carlo panel

| Widget | Content |
|--------|---------|
| **KPI restatement** | P(capture), n trials, capture radius (same as header chips) |
| **Histogram** | `min_range_m` over trials; vertical line at `capture_radius_m`; optional color split success/fail bins |
| **Secondary stats** | Compact: mean/p50/p95 `min_range_m`; optional mean `peak_tilt_rad` (deg); optional tracking RMSE if columns present |
| **How to read** | 3–4 bullets: plant scatter only; fixed NDI; capture definition; bands = ownship spatial percentiles across re-sim trials |

Optional collapsed “trial table” (first N rows) — not required.

### 2.8 Battery (placeholder — later)

If SOC/power series absent: **omit** the block entirely (no empty chart).

If present later: small SOC gauge + power/SOC vs t scrub-synced under time series. Spec note only; **not acceptance for R2**.

---

## 3. Required views (checklist form)

| # | View | Required | Data dependency |
|---|------|----------|-----------------|
| 1 | KPI: **P(capture)**, **n trials**, capture radius | Yes | `mc.summary` / derived from trials |
| 2 | Success vs fail **nominal case toggle** | Yes if both packs present | `cases.success`, `cases.fail` |
| 3 | Trajectory **3D** (N/E/up) ownship + target + scrub | **Yes (R2)** | nominal `*_plot` timeseries |
| 4 | Trajectory **2D** N–E with **capture circle** | Yes | nominal timeseries |
| 5 | **MC confidence bands** on **2D N–E** (toggleable) | **Yes (R2)** — pack **must** include bands for success MC | `mc.bands` non-null |
| 6 | MC envelope on **3D** (toggleable; may share toggle) | **Yes (R2)** — at least percentile polylines or projected envelope | same `mc.bands` |
| 7 | **min_range histogram** | Yes if MC present | `trials[].min_range_m` |
| 8 | **Scrub + play** synced across 3D / 2D / range | Yes | `timeseries.t` |
| 9 | Battery / energy | Optional later | SOC series |

Empty states:

- No MC → show nominal 3D + 2D + range; KPI chips show “MC not in pack”; hide histogram + band toggle. (**Shipped product pack for R2 is expected to include MC + bands.**)
- Bands missing in a broken pack → disable toggle with honest tooltip; treat as **implementation defect** for the success-MC demo pack, not an acceptable permanent state.
- No fail case → Success only (no broken segmented control).
- Load error → single card with path to rebuild instructions.

---

## 4. Data contract

Prefer a **single demo pack** built offline into `docs/demos/intercept/data/` so Pages never reads `runs/`. Source of truth for generation remains study run dirs, e.g.:

```text
runs/intercept_l0_success_*/nominal/{timeseries.*, metrics.json}
runs/intercept_l0_success_*/monte_carlo/{trials.csv, summary.json}
runs/intercept_l0_fail_*/nominal/{timeseries.*, metrics.json}
```

Plus, for bands (if not already stored under MC):

```text
# Offline re-sim outputs (generator-owned paths — example)
runs/intercept_l0_success_*/monte_carlo/trial_paths/   # optional
# or ephemeral arrays only inside export_demo_data.py
```

### 4.1 Files served to the browser

| Path | Role |
|------|------|
| `data/demo.json` | **Primary** pack: meta, cases, MC summary, trials, **required `mc.bands`** for success MC demo |
| `data/meta.json` | Optional thin pointer (version, generated_at) if split from demo |
| `data/trials.csv` | Optional raw MC table (if not inlined) |

**Recommendation:** one `demo.json` ≤ ~2–5 MB with downsampled timeseries, compact trials (500 rows OK), histogram pre-bin optional, and **bands as quantile polylines** (not full trial clouds). Full 500×T×3 path dumps are too large — **never** ship raw multi-trial path clouds in the SPA pack.

### 4.2 Top-level `demo.json` schema (v1 / R2)

```json
{
  "schema_version": 1,
  "title": "uavsim · intercept L0",
  "generated_at": "ISO-8601",
  "uavsim_version": "0.1.0",
  "ui": {
    "value_prop": "…",
    "about_paragraphs": ["…"],
    "capture_radius_m": 1.0,
    "default_case": "success"
  },
  "cases": {
    "success": { "…CasePack…" },
    "fail": { "…CasePack…" }
  },
  "mc": {
    "source_study": "intercept_l0_success_mc_…",
    "n_trials": 500,
    "summary": { },
    "trials": [ ],
    "bands": { }
  }
}
```

`cases.fail` may be `null` or omitted. MC attaches to the **success** recipe by product plan; KPI still shown when viewing fail nominal (caption: “MC on success plant scatter”). **Bands always describe success-recipe plant MC**, even when Fail nominal geometry is displayed (toggle still applies to success envelope; optional caption “bands: success MC”).

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
| `metrics.rmse_position_m` | number \| optional | |
| `timeseries.t` | number[] | seconds, downsampled (~200–400 pts OK) |
| `timeseries.pos_ned` | number[][] | ownship \(N,E,D\) — optional if `pos_plot` present |
| `timeseries.pos_plot` | number[][] | **required plot frame: N, E, up** (match showcase) |
| `timeseries.target_ned` / `target_plot` | number[][] | scripted target, same length as `t` (resampled) |
| `timeseries.range_m` | number[] | \(\|p_{\mathrm{own}}-p_{\mathrm{tgt}}\|\) |
| `timeseries.euler_deg` | number[][] \| optional | φθψ for optional attitude niceties |
| `timeseries.vel_ned` | optional | velocity cue in 3D if desired |
| `timeseries.ref_plot` | optional | open-loop reference path |

Convention: **prefer `*_plot` arrays as North, East, Up** so UI never guesses D vs U.

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
| `rmse_position_m`, `rmse_attitude_rad`, … | optional secondary |
| `success`, `sim_success` | sim health vs capture; **do not conflate** with `intercept_success` |

**P(capture)** definition for KPI:

\[
P(\mathrm{capture}) = \frac{\#\{\texttt{intercept\_success}=\mathrm{true}\}}{n_{\mathrm{trials}}}
\]

Use `intercept_success`, **not** generic tracking `success`, unless the study aliases them (document if aliased).

**`monte_carlo/summary.json`** (`summarize_trials`, schema_version 2):

| Field | Use |
|-------|-----|
| `n_trials` | KPI |
| `n_success` | tracking success count — **label carefully**; may ≠ capture count |
| `metrics` / `metrics_all_trials` | optional RMSE aggregates |
| (demo may add) `n_intercept_success`, `p_capture` | **preferred explicit fields** written by demo exporter |

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

so the UI does not re-implement percentile logic if only summary is present.

#### Confidence bands (`mc.bands`) — **required for R2 success-MC pack**

Standard MC exports only write **scalar** trial rows. That is **insufficient** for R2. The demo exporter **must** produce spatial percentiles by one of:

1. **Offline re-simulation** of each (or a subsample of) MC trial using plant params from `trials.csv` + the same success-recipe mission/controller as the study, recording ownship position vs time; or  
2. Loading pre-stored per-trial paths if the MC pipeline later writes them.

Then downsample onto a common time grid and compute percentiles **per axis, per sample time**.

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
| `frame` | `"plot"` → arrays are N, E, **up** (not down) |
| `percentiles` | Include **5 and 95** (or document p10/p90 if substituted; UI labels must match). **50** (median) recommended |
| `t` | Common time grid (s); length \(T\) same as each percentile array. May match nominal downsample or a coarser MC grid |
| `ownship.N/E/U.p5|p50|p95` | Length-\(T\) arrays; **required** p5 + p95 for N and E at minimum; U required for 3D envelope |
| `n_paths_used` | Provenance |
| `method` | e.g. `axiswise_percentile` (independent percentiles per N/E/U) — document that this is **not** a joint ellipsoidal tube |

**Optional extensions** (not required):

```json
"ownship_joint": {
  "comment": "optional future: PCA tubes or convex slices",
  "p5_path_plot": [[N,E,U], …],
  "p95_path_plot": [[N,E,U], …]
}
```

**UI rendering:**

| View | How to draw |
|------|-------------|
| **2D N–E** | Filled band: polygon along (E_p5, N_p5) then reverse (E_p95, N_p95); optional thin p50 line. Prefer **paired percentile paths**, not convex hull of all trials |
| **2D N–Up** | Same with N/U |
| **3D** | Draw p5, p50, p95 as three `scatter3d` polylines (N,E,U) with decreasing opacity; **or** a light “fan” of a few percentile levels. Full mesh tube is optional. Same global toggle as 2D |

**Subsampling for generation:** If re-sim of 500 trials is expensive, generator may use ≥100 stratified or random successful trials **or** all trials — document `n_paths_used`. Prefer all trials when feasible for honest bands.

**Alignment:** Band `t` need not equal nominal `timeseries.t` exactly; UI interpolates or nearest-neighbor when drawing static bands (bands are full-horizon envelopes, not scrub-dependent geometry). Scrub still only moves nominal markers.

**R2 gate:** Product pack for the success MC demo **must not** ship `"bands": null`. Fail-only or MC-less packs may omit bands; the **primary hiring demo** must include them.

### 4.5 Provenance fields

Optional footer / About:

- `source_run`, `git_commit`, `seed`, `n_trials`, `perturbation` blurb from study YAML snapshot.
- Band generation: `n_paths_used`, `method`, optional CLI flags.

---

## 5. Interaction model

| Action | Result |
|--------|--------|
| **Load** | Fetch `data/demo.json`; default case = `ui.default_case` or `success` |
| **Case toggle Success/Fail** | Swap nominal timeseries + metrics badges; keep MC panel + bands (success study); reset playhead to 0; pause; rebuild 3D/2D paths |
| **Play** | `requestAnimationFrame` or `setInterval`; map wall time × speed → nearest index in `t`; loop **off** by default (stop at end) |
| **Pause** | freeze index |
| **Scrub** | set index; update 3D markers/trail, 2D markers/trail, range cursor |
| **Keyboard ←/→** | step frames when not typing |
| **MC bands toggle** | show/hide band traces on **2D and 3D** (default **on** if data present) |
| **Orbit 3D** | Plotly camera free; scrub does not reset eye |
| **Jump to CPA** (optional) | index nearest `time_of_min_range_s` |

### State (minimal)

```text
caseId: 'success' | 'fail'
frameIndex: number
playing: boolean
speed: number
showBands: boolean   // default true when mc.bands present
// projection optional if 2D N–Up retained
projection: 'NE' | 'NU'
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
| **Typography** | System UI; titles `ui-monospace`; tabular nums for KPIs/time |
| **Cards** | Panel background, 1px border, 8–12px radius |
| **Segmented controls** | Same as showcase mission-seg (active = accent wash) |
| **KPI chips** | Pill or compact stat blocks; good color for high P(capture); bad if low (threshold cosmetic only, e.g. &lt; 0.5) |
| **Plotly 2D** | `paper_bgcolor` / `plot_bgcolor` dark (`#0c1018` / `#111315`); grid `#2a2f36`; `displaylogo: false`; modeBar hover |
| **Plotly 3D** | Scene like showcase Flight: dark bg `#0a0e16`, axis grid muted; height ~400–480px desktop |
| **Bands** | Low-saturation fill (e.g. accent @ 15–25% opacity); never obscure nominal ownship/target |
| **Capture** | good/green dashed circle on 2D; optional sphere on 3D; fail nominal path still accent but metrics badge **Miss** in `--bad` |
| **Density** | Prefer one focused page; wide desktop first; stack cards on narrow viewports |

Copy tone: engineering, not marketing (“plant scatter, fixed NDI gains” not “hero filter win”).

---

## 7. Out of scope

- Portfolio **controller × sensor matrix**, envelope τ-sweep, compare tab, stack diagram
- Live / WASM simulation or parameter knobs that re-run dynamics in-browser
- Full **3D cloud of all MC trial paths** (use percentile envelope only)
- Showcase-parity **attitude + wrench dual-pane** (optional stretch only)
- Closed-loop **online replan** intercept UX (future L1+ story)
- Battery/SOC UI (placeholder only until energy model ships in pack)
- Auth, multi-user, mobile-first layout
- MATLAB or runtime dependency on heritage tree
- Requiring users to open raw `runs/` paths on Pages
- Build step / bundler **required** (optional later; CDN first)
- HIL, multi-vehicle, sensor-noise MC story

---

## 8. Acceptance criteria — “UX satisfied”

Mark **UX satisfied** when a reviewer can open the static page (local or Pages) and:

1. **See KPIs immediately:** P(capture) and n trials (or explicit “no MC”) without opening a second tab.
2. **Toggle Success/Fail** (if fail pack present) and see ownship + target paths and range(t) update in all geometry panes.
3. **Play and scrub** nominal time; vehicle/target markers and range cursor stay synced **across 3D, 2D, and range**.
4. **Read capture criterion** (1 m default) on the page and on the range plot as a reference line; **see capture circle on 2D**.
5. **Inspect min_range histogram** with capture-radius marker when MC data present.
6. **View 3D flight path** (N/E/up) for the active nominal with ownship + target; orbit works; scrub updates markers without destroying the scene.
7. **Toggle MC bands** default ON when present: **2D N–E** shows 5–95% (or labeled p10–p90) ownship envelope; **3D** shows nominal + percentile envelope; plot remains legible (nominal bold, target distinct).
8. **Shipped success-MC pack includes non-null `mc.bands`** with documented schema (§4.4). Shipping `bands: null` fails acceptance for the primary demo.
9. **Empty/missing data** does not blank the page: controls hide or show honest empty copy (broken packs only).
10. **Visual parity:** dark theme tokens aligned with showcase; no light “default Plotly” flash as the final look.
11. **Independence:** all assets under `docs/demos/intercept/`; no hard dependency on `docs/showcase/data/showcase.json`.
12. **Static:** works with `python -m http.server` or GH Pages (relative `fetch` paths).

Battery UI, full attitude/wrench mesh, and trial-parameter scatter plots are **not** required for this bar.

---

## 9. Implementation sketch (guidance only)

```text
docs/demos/intercept/
  index.html          # shell + CDN: Plotly
  app.js              # state, 3D + 2D + transport
  styles.css          # clone/adapt showcase tokens
  UX_SPEC.md          # this file
  IMPLEMENT_CHECKLIST.md
  UX_REVIEW_R2_BRIEF.md
  scripts/
    export_demo_data.py   # cases + MC + band generation
  data/
    demo.json             # built offline — bands required
```

**Generator:** CLI/script loads success/fail run dirs + MC trials → writes `demo.json` (downsample, compute `p_capture`, **re-sim or load paths → `mc.bands`**).

**Pages:** site path e.g. `…/demos/intercept/` linked from README when live.

---

## 10. Open decisions (resolve at implement if needed)

| Topic | Default if undecided |
|-------|----------------------|
| React CDN vs vanilla | Keep **vanilla** (current SPA); extract Flight-like 3D helpers as plain JS |
| Layout | **3D + range** top; **2D N–E with bands** secondary full width |
| Band percentiles | **5–95** with median p50 |
| Band generation | **Re-sim plant params from trials.csv**; subsample ≥100 if cost-bound |
| Trial cloud | **No** raw multi-path dump in pack |
| Fail MC | **No**; MC + bands on success only |
| Loop playback | **Off** by default |
| Capture sphere on 3D | Optional |
| Attitude dual-pane | Optional stretch |

---

## Document history

| Date | Note |
|------|------|
| 2026-07-25 | Initial UX spec for L0 intercept MC static dashboard |
| 2026-07-25 | **R2:** 3D trajectory + MC bands required acceptance; bands data generation / schema mandated; 2D-only + `bands: null` no longer satisfied |
