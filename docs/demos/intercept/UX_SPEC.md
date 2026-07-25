# Intercept demo — UX specification (L0 + Monte Carlo)

| Field | Value |
|-------|--------|
| **Status** | Design (implement next) |
| **Audience** | Hiring GNC reviewers + peers; teaching intercept + plant-MC robustness |
| **Location** | `docs/demos/intercept/` (independent of portfolio showcase) |
| **Hosting** | Static GitHub Pages; no build step preferred |
| **Stack** | HTML + vanilla JS (or React-via-CDN like showcase) + Plotly CDN |
| **Story** | L0 open-loop ownship path, scripted target, NDI; capture if `min_range ≤ 1 m`; plant MC on success recipe |

This is a **thin single-mission dashboard**, not a matrix gallery. Reuse **visual language and interaction patterns** from [`docs/showcase/`](../../showcase/) (dark research chrome, scrubber, MC histograms). Do **not** rebuild the controller × sensor portfolio.

Related product intent: [`plan/ONLINE_INTERCEPT_AND_BATTERY.md`](../../../plan/ONLINE_INTERCEPT_AND_BATTERY.md) §5, §7; heritage of scrub/MC in [`docs/showcase/UI_SPEC.md`](../../showcase/UI_SPEC.md).

---

## 1. Goals

1. Communicate the **intercept story** in one screenful of hierarchy: geometry → capture KPI → MC confidence.
2. Let a reviewer **play/scrub** a nominal success (and fail, if present) chase with ownship + target.
3. Surface **P(capture)** and **min-range distribution** from plant mass / I / arm scatter without burying the reader in a full metrics dump.
4. Show **toggleable 2D MC confidence bands** on trajectory projections.
5. Ship as a **self-contained static SPA** under `docs/demos/intercept/` with a small data pack.

### Non-goals (summary)

See §7. Notably: no live sim, no multi-mission matrix, no full 3D trial cloud, battery UI optional later.

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
│ PRIMARY: Trajectory 2D       │ SECONDARY: Time series       │
│  N–E top-down (default)      │  range(t) + optional tilt    │
│  optional N–Up toggle        │  scrub-synced cursor         │
│  MC bands toggle             │                              │
│  capture circle              │                              │
│  play / scrub bar (full width under both panes)             │
├──────────────────────────────┴──────────────────────────────┤
│ MC PANEL                                                    │
│  min_range histogram · optional peak_tilt / RMSE sparklines │
│  short “how to read” blurb                                  │
├─────────────────────────────────────────────────────────────┤
│ FOOTER · Simulation only · link to repo / study YAMLs       │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 Header

| Element | Behavior |
|---------|----------|
| **Title** | e.g. `uavsim · intercept L0 (NDI + plant MC)` — mono weight like showcase |
| **Value prop** | One muted line: open-loop intercept path, scripted target, fixed NDI, plant scatter |
| **About** | Collapsed: capture radius, success vs fail recipe, MC perturbations (mass/I/arm), redesign_controller false |
| **Case toggle** | Segmented control: **Success** \| **Fail** (disable or hide Fail if data missing) |
| **KPI chips** | Always visible (from MC summary when available; else nominal-only badges) |

### 2.2 Story strip

Short static copy (from `meta.json` / `demo.json` `ui` block):

- L0 = open-loop ownship reference + scripted target (not closed-loop replan hero yet, if still L0).
- Capture: \(\min_t \|p_{\mathrm{own}}-p_{\mathrm{tgt}}\| \le r_{\mathrm{capture}}\) (default **1 m**).
- MC: plant parameters only; gains fixed.

### 2.3 Primary visual: trajectory 2D

**Default view: North–East top-down** (Plotly 2D).

Traces (nominal case currently selected):

| Layer | Style | Notes |
|-------|--------|------|
| Target path | solid warn/amber | full history |
| Ownship path | solid accent | full history |
| Ownship trail to \(t_i\) | brighter / thicker | scrub-dependent |
| Vehicle marker at \(t_i\) | accent + optional body heading tick | |
| Target marker at \(t_i\) | warn | |
| Capture circle | dashed good/muted at CPA or fixed at min-range ownship pose | radius = `capture_radius_m` in plot units (m) |
| MC bands (optional) | translucent fill 5–95% (or p10–p90) | ownship only; see §4 |

**Secondary projection:** chip or segmented mini-control **N–E \| N–Up** (and optionally **range vs time** as a small sparkline in the right pane instead of a third map).

**Not required v1:** full dual-pane 3D + attitude mesh (showcase Flight 3D). Optional stretch: thin attitude strip (φ,θ vs t) if data cheap.

### 2.4 Time series (right / secondary)

Must:

- **`range_m(t)`** ownship–target Euclidean range; horizontal line at `capture_radius_m`.
- Scrub playhead vertical line.

Nice-to-have:

- Peak-relevant: `tilt_rad` or `tilt_deg(t)` for “beyond linear” story.
- Tracking error if reference present.

### 2.5 Transport bar (play + scrub)

Full width under primary row (mirror showcase scrub patterns; **add play** which showcase lacks).

| Control | Behavior |
|---------|----------|
| **Play / Pause** | Toggle; advances frame index at ~real-time or fixed FPS (e.g. 30 fps mapped to `t`) |
| **Scrubber** | Range input 0…N−1; drag updates markers + series cursor |
| **← / →** | Step ±1 frame; Shift = ±10 (ignore when focus is text inputs) |
| **Time readouts** | `t = … s` and `range = … m` tabular nums |
| **Speed** | Optional 0.5× / 1× / 2×; default 1× |

On case toggle: reset to t=0 (or to time-of-min-range if that improves story — default **t=0**, optional “Jump to CPA” button).

### 2.6 Monte Carlo panel

| Widget | Content |
|--------|---------|
| **KPI restatement** | P(capture), n trials, capture radius (same as header chips) |
| **Histogram** | `min_range_m` over trials; vertical line at `capture_radius_m`; optional color split success/fail bins |
| **Secondary stats** | Compact: mean/p50/p95 `min_range_m`; optional mean `peak_tilt_rad` (deg); optional tracking RMSE if columns present |
| **How to read** | 3 bullets: plant scatter only; fixed NDI; capture definition |

Optional collapsed “trial table” (first N rows) — not required for UX pass.

### 2.7 Battery (placeholder — later)

If SOC/power series absent: **omit** the block entirely (no empty chart).

If present later: small SOC gauge + power/SOC vs t scrub-synced under time series. Spec note only; **not acceptance for v1**.

---

## 3. Required views (checklist form)

| # | View | Required | Data dependency |
|---|------|----------|-----------------|
| 1 | KPI: **P(capture)**, **n trials**, capture radius | Yes | `mc.summary` / derived from trials |
| 2 | Success vs fail **nominal case toggle** | Yes if both packs present | `cases.success`, `cases.fail` |
| 3 | Trajectory **2D** (N–E primary) | Yes | nominal timeseries + target path |
| 4 | Optional **MC confidence bands** on 2D path | Yes (toggle; hide control if no band data) | `mc.bands` or precomputed quantiles |
| 5 | **min_range histogram** | Yes if MC present | `trials[].min_range_m` |
| 6 | **Scrub + play** for active nominal | Yes | `timeseries.t` |
| 7 | Battery / energy | Optional later | SOC series |

Empty states:

- No MC → show nominal story only; KPI chips show “MC not in pack”; hide histogram + band toggle.
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

### 4.1 Files served to the browser

| Path | Role |
|------|------|
| `data/demo.json` | **Primary** pack: meta, cases, MC summary, optional downsampled trials + bands |
| `data/meta.json` | Optional thin pointer (version, generated_at) if split from demo |
| `data/trials.csv` | Optional raw MC table (if not inlined); Plotly/JS may parse CSV via `fetch` + simple parser |

**Recommendation:** one `demo.json` ≤ ~2–5 MB with downsampled timeseries and either full trials (500 rows is fine) or a compact histogram pre-bin. Bands as quantile polylines, not full trial clouds.

### 4.2 Top-level `demo.json` schema (v1)

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

`cases.fail` may be `null` or omitted. MC attaches to the **success** recipe by product plan; KPI still shown when viewing fail nominal (caption: “MC on success plant scatter”).

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
| `timeseries.pos_ned` | number[][] | ownship \(N,E,D\) or \(N,E,U\) — **document convention** |
| `timeseries.pos_plot` | number[][] | **preferred plot frame: N, E, up** (match showcase) |
| `timeseries.target_ned` / `target_plot` | number[][] | scripted target, same length as `t` (resampled) |
| `timeseries.range_m` | number[] | \(\|p_{\mathrm{own}}-p_{\mathrm{tgt}}\|\) |
| `timeseries.euler_deg` | number[][] \| optional | φθψ for optional tilt strip |
| `timeseries.vel_ned` | optional | |
| `timeseries.ref_plot` | optional | open-loop reference path |

Convention: **prefer `*_plot` arrays as North, East, Up** so UI never guesses D vs U.

### 4.4 Monte Carlo block

#### From pipeline artifacts (generator input)

**`monte_carlo/trials.csv`** preferred columns (see `uavsim.monte_carlo.io`):

| Column | Role in UI |
|--------|------------|
| `trial_id` | identity |
| `mass_kg`, `ixx_kg_m2`, `iyy_kg_m2`, `izz_kg_m2`, `arm_length_m` | optional sensitivity later |
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

#### Confidence bands (`mc.bands`)

Precompute offline (per sample time or fixed grid). Suggested shape:

```json
"bands": {
  "frame": "plot",
  "percentiles": [5, 50, 95],
  "t": [0.0, 0.05, …],
  "ownship": {
    "N": { "p5": [], "p50": [], "p95": [] },
    "E": { "p5": [], "p50": [], "p95": [] },
    "U": { "p5": [], "p50": [], "p95": [] }
  }
}
```

UI draws N–E band as filled polygon between (E_p5,N_p5)… and (E_p95,N_p95) along time order (or convex envelope of percentile polylines — **prefer paired percentile paths**, not convex hull of all trials). Median optional thin line.

If band export is delayed: ship histogram + KPI first; band toggle disabled with tooltip “bands not in data pack”.

### 4.5 Provenance fields

Optional footer:

- `source_run`, `git_commit`, `seed`, `n_trials`, `perturbation` blurb from study YAML snapshot.

---

## 5. Interaction model

| Action | Result |
|--------|--------|
| **Load** | Fetch `data/demo.json`; default case = `ui.default_case` or `success` |
| **Case toggle Success/Fail** | Swap nominal timeseries + metrics badges; keep MC panel (success study); reset playhead to 0; pause |
| **Play** | `requestAnimationFrame` or `setInterval`; map wall time × speed → nearest index in `t`; loop **off** by default (stop at end) |
| **Pause** | freeze index |
| **Scrub** | set index; update markers, trail, range cursor |
| **Keyboard ←/→** | step frames when not typing |
| **MC bands toggle** | show/hide band traces on 2D plot (default **on** if data present) |
| **Projection N–E / N–Up** | rebind axes; keep playhead |
| **Jump to CPA** (optional) | index nearest `time_of_min_range_s` |

### State (minimal)

```text
caseId: 'success' | 'fail'
frameIndex: number
playing: boolean
speed: number
showBands: boolean
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
| **Plotly** | `paper_bgcolor` / `plot_bgcolor` dark (`#0c1018` / `#111315`); grid `#2a2f36`; `displaylogo: false`; modeBar hover |
| **Capture** | good/green dashed circle; fail nominal path still accent but metrics badge **Miss** in `--bad` |
| **Density** | Prefer one focused page over eight tabs; wide desktop first (showcase honesty: best on wide display) |

Copy tone: engineering, not marketing (“plant scatter, fixed NDI gains” not “hero filter win”).

---

## 7. Out of scope

- Portfolio **controller × sensor matrix**, envelope τ-sweep, compare tab, stack diagram
- Live / WASM simulation or parameter knobs that re-run dynamics in-browser
- Full **3D** multi-trial cloud or dual-pane attitude mesh (showcase Flight parity)
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
2. **Toggle Success/Fail** (if fail pack present) and see ownship + target paths and range(t) update.
3. **Play and scrub** nominal time; vehicle/target markers and range cursor stay synced.
4. **Read capture criterion** (1 m default) on the page and on the range plot as a reference line.
5. **Inspect min_range histogram** with capture-radius marker when MC data present.
6. **Toggle MC bands** on the 2D trajectory when band data present; plot remains legible (nominal bold, target distinct).
7. **Empty/missing data** does not blank the page: controls hide or show honest empty copy.
8. **Visual parity:** dark theme tokens aligned with showcase; no light “default Plotly” flash as the final look.
9. **Independence:** all assets under `docs/demos/intercept/`; no hard dependency on `docs/showcase/data/showcase.json`.
10. **Static:** works with `python -m http.server` or GH Pages (relative `fetch` paths).

Battery UI, 3D attitude, and trial-parameter scatter plots are **not** required for this bar.

---

## 9. Implementation sketch (guidance only)

```text
docs/demos/intercept/
  index.html          # shell + CDN: Plotly (+ React optional)
  app.js              # state, plots, transport
  styles.css          # clone/adapt showcase tokens
  UX_SPEC.md          # this file
  IMPLEMENT_CHECKLIST.md
  data/
    demo.json         # built offline
    README.md         # how to rebuild pack (optional)
```

**Generator (future code, not this design task):** CLI or script that loads success/fail run dirs + MC → writes `demo.json` (downsample, compute `p_capture`, optional bands).

**Pages:** site path e.g. `…/demos/intercept/` linked from README when live.

---

## 10. Open decisions (resolve at implement if needed)

| Topic | Default if undecided |
|-------|----------------------|
| React CDN vs vanilla | Vanilla or minimal React — either OK; prefer **copy showcase patterns** if extracting transport is faster |
| Band percentiles | **5–95** with optional median |
| Trial cloud | **No** in v1 |
| Fail MC | **No**; MC on success only |
| Loop playback | **Off** by default |

---

## Document history

| Date | Note |
|------|------|
| 2026-07-25 | Initial UX spec for L0 intercept MC static dashboard |
