# Intercept MC demo — UX review (R3)

| Field | Value |
|-------|--------|
| **Iteration** | 3 (layout + attitude + battery + pad/GE story) |
| **Reviewed** | `index.html`, `app.js`, `styles.css`, `IMPLEMENT_SUMMARY_R3.md`, pack `data/demo.json` (structure + `mc.bands` + SOC/power/energy) vs `UX_SPEC.md` §8 + hard product gates in § R3 correction / `UX_REVIEW_R3_BRIEF.md` |
| **Pack snapshot** | 500 trials, `p_capture: 1.0`; `mc.bands` **non-null**, `n_paths_used: 80`, percentiles 5/50/95, `frame: plot`, `method: axiswise_percentile`; success + fail nominals with `euler_deg`, `soc`, `power_w`, `energy_wh_remaining`; `ui.mission_notes: pad_climb_ground_effect`; generated `2026-07-25T16:45:00Z` |

---

## Verdict

**SATISFIED**

R3 closes the product layout/energy gap after R2 (3D + bands). Static SPA places **play/scrub transport at the top** inside sticky chrome, puts **attitude @ origin** in the primary-right slot, moves **range vs time** beside **2D N–E**, keeps **MC bands default-on and toggleable** on 2D+3D when data is present, surfaces **battery SOC + power/energy** scrub-synced when series exist, and tells the **pad climb + ground-effect** mission story. No **must-fix** items for this iteration.

---

## Blocking (must fix)

*None.*

### Hard product requirements (review brief)

| # | Gate | Result |
|---|------|--------|
| 1 | Transport sticky at **TOP** | **Pass** — `#transport` lives in `.sticky-chrome` with header (`position: sticky; top: 0; z-index: 40`); not buried under geometry plots |
| 2 | **Attitude** pane (not range) as primary right | **Pass** — `.primary-row`: Trajectory 3D \| Attitude @ origin (`#attitude-plot`); driven by `euler_deg` + showcase-style mesh/axes |
| 3 | **Range** side-by-side with 2D N–E (secondary) | **Pass** — `.secondary-row`: Trajectory 2D \| Range vs time (`#traj-plot`, `#range-plot`) |
| 4 | MC bands on traj (not disabled when data present) | **Pass** — `hasBands()` true on pack; `showBands = hasBands()` at boot; checkbox checked & enabled; 2D fill + 3D p5/p50/p95; toggle rebuilds both |
| 5 | Battery SOC indicator when data present | **Pass** — transport `#soc-strip` + battery card gauge; `soc` / `power_w` / `energy_wh_remaining` on both cases; metrics `soc_final` / `soc_min` / `peak_power_w` |
| 6 | Pad/GE story copy | **Pass** — value prop, story strip, About, how-to-read; `mission_notes: pad_climb_ground_effect` |

### Acceptance cross-check (UX_SPEC §8 R3)

| # | Criterion | Result |
|---|-----------|--------|
| 1 | KPIs: P(capture), n trials, r capture | **Pass** — header chips; optional SOC final chip when metrics present |
| 2 | Success \| Fail updates geometry, attitude, range, battery | **Pass** — case seg rebuilds shell; both packs present |
| 3 | Play/scrub from **TOP** sticky transport; multi-pane sync | **Pass** — `applyFrameViews`: readouts/SOC, 3D, attitude, 2D, range, battery |
| 4 | Capture criterion on page + range; capture circle on 2D | **Pass** — story strip eq; range dashed r; 2D circle at CPA target |
| 5 | min_range histogram + capture marker | **Pass** — MC panel retained |
| 6 | 3D flight path N/E/up; scrub without scene destroy | **Pass** — restyle trail/markers; `uirevision` pattern retained |
| 7 | Attitude at origin, right primary, scrub-synced | **Pass** — fixed cube ~±1.05; restyle airframe/motors/axes |
| 8 | Range(t) secondary beside 2D N–E | **Pass** — not in primary-right |
| 9 | MC bands default ON; 2D + 3D; toggle in top transport | **Pass** — `#bands-toggle` in transport |
| 10 | Pack non-null `mc.bands` schema | **Pass** — see pack check |
| 11 | Battery when series present; omit when absent | **Pass** — `hasBattery()` gates panel + strip; no empty chrome if missing |
| 12 | Story pad takeoff / climb + ground effect | **Pass** |
| 13 | Empty/missing data honest | **Pass** — error card; att-empty note; bands disabled tooltip; no-MC note |
| 14 | Dark theme + sticky chrome over plots | **Pass** — showcase tokens; blur sticky stack |
| 15 | Independent of showcase data | **Pass** — `./data/demo.json` only |
| 16 | Static host / relative fetch | **Pass** — CDN Plotly; `index.html` cache-bust `?v=3` |

### Pack check: bands + battery + attitude

Static inspection of `/home/trey/proj/quadrotor-sim/docs/demos/intercept/data/demo.json`:

| Field | Value |
|-------|--------|
| `mc.bands` | Object (not `null`) |
| `frame` | `"plot"` |
| `percentiles` | `[5, 50, 95]` |
| `method` | `axiswise_percentile` |
| `n_paths_used` | **80** (how-to documents n=80; band-max export) |
| `ownship.N/E/U` × `p5/p50/p95` | Present under `bands.ownship` |
| Cases | `success` + `fail` |
| `timeseries.euler_deg` | Present on both |
| `timeseries.soc` | Present on both (fraction; UI maps ≤1.01 → %) |
| `timeseries.power_w` | Present on both |
| `timeseries.energy_wh_remaining` | Present on both |
| Metrics battery | `soc_final`, `soc_min`, `peak_power_w`, `battery_enabled: true` |
| MC KPIs | `n_trials: 500`, `p_capture: 1.0` |
| Story | `ui.mission_notes: "pad_climb_ground_effect"`; pad + GE in value_prop / about / how_to_read |

### Layout vs R3 wireframe

Shipped DOM (matches brief sketch):

```text
sticky-chrome: header (KPIs, Success|Fail, About) + transport (play/CPA/scrub/speed/MC bands/SOC)
story strip (pad climb + GE + capture eq)
primary-row:  3D trajectory | attitude @ origin
secondary-row: 2D N–E      | range vs time
battery-row:  SOC gauge | power_w | energy_wh_remaining
MC: histogram + how-to
footer
```

CSS: `.primary-row` / `.secondary-row` `1fr 1fr`; stack ≤960px; `.sticky-chrome` for header+transport stack.

### Frame sync (smoke-level code review)

| Event | Behavior |
|-------|----------|
| scrub / play / ←→ / CPA | single `frameIndex` → 3D restyle, attitude restyle, 2D rebuild, range, battery + SOC strip |
| case toggle | pause; rebuild shell; redraw all |
| bands toggle | rebuild 2D+3D band layers (`traj3dReady` invalidation) |
| projection NE/NU | 2D only |

---

## Non-blocking nits

1. **Sticky model** — header and transport share one sticky block (`top: 0`) rather than separate sticky layers with `transport { top: var(--header-h) }`. Meets “sticky at top”; opening About grows sticky height and can crowd the first plot row on short viewports.
2. **Band path count** — pack uses `n_paths_used: 80` (exporter `--band-max-trials 80`). R2 preferred ≥100 for envelope quality; still non-null and visible; document honesty is fine.
3. **Battery scrub cost** — `drawBattery()` runs full Plotly paths each frame (vs restyle-only on 3D/attitude). Acceptable for demo pack size; optional later optimization.
4. **Fail + SOC** — both nominals carry battery series; no issue observed in pack. If a future fail pack omits SOC, panel correctly hides via `hasBattery()`.

---

## Summary

| Focus | Status |
|-------|--------|
| Transport sticky top | **Met** |
| Attitude primary-right | **Met** |
| Range + 2D secondary | **Met** |
| MC bands visible by default | **Met** |
| Battery SOC when data present | **Met** |
| Pad / GE story | **Met** |
| R2 3D + bands retention | **Met** |

**UX satisfied (R3).** No further hard product gates remaining for this demo’s declared R3 scope.
