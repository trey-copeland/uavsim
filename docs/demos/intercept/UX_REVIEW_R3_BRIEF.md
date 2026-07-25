# Intercept demo — UX R3 implementer brief

| Field | Value |
|-------|--------|
| **Iteration** | 3 (layout + attitude + battery + story) |
| **Audience** | Implementer |
| **Normative design** | [`UX_SPEC.md`](UX_SPEC.md) (R3) · tasks: [`IMPLEMENT_CHECKLIST.md`](IMPLEMENT_CHECKLIST.md) |
| **Do not** | Rebuild showcase matrix; add npm build; ship `bands: null` on primary pack; implement only partial layout (all hard items below) |

---

## Why R3

R2 closed 3D path + non-null `mc.bands`. Product still requires a **portfolio-grade review surface**:

1. **Scrub/play at the TOP** (sticky near header) — not buried under plots.  
2. **Attitude plot** (Flight dual-pane style, vehicle at origin) **where range-vs-time currently is** (right of 3D).  
3. **Range-vs-time** moves **down**, **side-by-side with top-down (N–E)**.  
4. **MC confidence bands** remain **visible by default** on **2D and 3D** when data present (exporter already produces `mc.bands`).  
5. **Battery**: SOC gauge/bar scrub-synced + power/energy series when pack has fields.  
6. Mission story: **pad climb + ground effect** (takeoff from pad / GE).

These are **acceptance gates** in UX_SPEC §2 / §3 / §8 — not polish.

---

## Layout wireframe (normative)

**Current (R2 SPA):**

```text
Header (KPIs, Success|Fail)
Story strip
┌─────────────────────┬─────────────────────┐
│  Trajectory 3D      │  Range vs time      │
│  + MC fan           │                     │
├─────────────────────┴─────────────────────┤
│  Trajectory 2D N–E + bands (full width)   │
├───────────────────────────────────────────┤
│  Transport (play/scrub)  ← too low        │
├───────────────────────────────────────────┤
│  MC histogram                             │
└───────────────────────────────────────────┘
```

**Target (R3):**

```text
┌───────────────────────────────────────────────────────────┐
│ HEADER (sticky)                                           │
│  title · value prop · About · meta                        │
│  [ Success | Fail ]   P(cap) · n · r_cap  [Capture badge] │
├───────────────────────────────────────────────────────────┤
│ TRANSPORT (sticky)  ★ HARD                                │
│  [Play] [CPA]  ════ scrub ════  t=…s  range=…m  [0.5 1 2×]│
│  [✓ MC bands]  [SOC ████░░ 62%]  ← SOC optional strip     │
├───────────────────────────────────────────────────────────┤
│ STORY: pad takeoff → climb (ground effect) → intercept…   │
├─────────────────────────────┬─────────────────────────────┤
│ PRIMARY LEFT ★              │ PRIMARY RIGHT ★ HARD        │
│ Trajectory 3D (N/E/up)      │ Vehicle attitude @ origin   │
│ ownship + target + trail    │ X-quad mesh + body axes     │
│ MC p5/p50/p95 (toggle)      │ euler scrub-synced          │
│ markers at t_i              │ (wrench optional)           │
├─────────────────────────────┼─────────────────────────────┤
│ SECONDARY LEFT ★            │ SECONDARY RIGHT ★ HARD      │
│ Top-down 2D N–E             │ Range vs time               │
│ paths + capture circle      │ range_m(t) + r_cap line     │
│ MC band fill (default ON)   │ playhead                    │
├─────────────────────────────┴─────────────────────────────┤
│ BATTERY ★ HARD when data present                          │
│  SOC gauge/bar (live)  │  power_w(t)  │  energy_wh_rem(t) │
├───────────────────────────────────────────────────────────┤
│ MC: min_range histogram + how-to-read                     │
├───────────────────────────────────────────────────────────┤
│ Footer                                                    │
└───────────────────────────────────────────────────────────┘
```

### CSS / DOM sketch

```html
<header class="app-header sticky-chrome">…</header>
<div class="transport sticky-chrome" id="transport">…</div>
<div class="story-strip">…</div>
<main>
  <div class="primary-row">
    <section class="card"><!-- #traj3d-plot --></section>
    <section class="card"><!-- #attitude-plot --></section>
  </div>
  <div class="secondary-row">
    <section class="card"><!-- #traj-plot 2D --></section>
    <section class="card"><!-- #range-plot --></section>
  </div>
  <section class="card battery-row" id="battery-panel"><!-- omit if no data --></section>
  <section class="card mc-panel">…</section>
</main>
```

```css
.sticky-chrome {
  position: sticky;
  /* header top: 0; transport top: var(--header-h) or single sticky stack */
  z-index: 40;
  background: rgba(17, 19, 21, 0.94);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
}
.primary-row, .secondary-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
@media (max-width: 960px) {
  .primary-row, .secondary-row { grid-template-columns: 1fr; }
}
```

Reference: showcase sticky chrome in [`docs/showcase/styles.css`](../../showcase/styles.css) (`.sticky-header`) and Flight toolbar in [`docs/showcase/app.js`](../../showcase/app.js) `FlightTab` (~1532–1650).

**Move bands toggle into top transport** (currently on 3D card title in R2) so it is always reachable.

---

## Data fields (browser contract)

### Always (nominal geometry)

| Path | Use |
|------|-----|
| `cases.*.timeseries.t` | scrub domain |
| `cases.*.timeseries.pos_plot` | ownship N,E,up |
| `cases.*.timeseries.target_plot` | target N,E,up |
| `cases.*.timeseries.range_m` | range plot + readout |
| `cases.*.metrics.*` | capture badge, CPA jump |

### Attitude (**R3**)

| Path | Use |
|------|-----|
| `cases.*.timeseries.euler_deg[i]` | `[φ, θ, ψ]` **degrees** at frame `i` → attitude mesh |

**Source offline:** state `x[:, 3:6]` rad (ZYX Euler). Exporter already has:

```python
"euler_deg": np.rad2deg(x[:, 3:6]).tolist() if x.shape[1] >= 6 else None
```

in [`scripts/export_demo_data.py`](scripts/export_demo_data.py). Confirm both success and fail packs include it; drop-null only if truly missing.

**Rotation convention (must match showcase):** body→NED ZYX, then plot = `(N, E, −D)` via `bodyToPlot`.

### MC bands (R2 retained — **must stay visible**)

| Path | Use |
|------|-----|
| `mc.bands.t` | band time grid (static envelope) |
| `mc.bands.ownship.N/E/U.p5\|p50\|p95` | 2D fill + 3D polylines |
| `mc.bands.n_paths_used`, `method` | About / how-to |

```json
"bands": {
  "frame": "plot",
  "percentiles": [5, 50, 95],
  "t": [],
  "n_paths_used": 100,
  "method": "axiswise_percentile",
  "ownship": {
    "N": { "p5": [], "p50": [], "p95": [] },
    "E": { "p5": [], "p50": [], "p95": [] },
    "U": { "p5": [], "p50": [], "p95": [] }
  }
}
```

| View | Draw |
|------|------|
| **2D N–E** | Fill polygon (E_p5,N_p5)→… reverse (E_p95,N_p95); accent ~18% opacity; optional p50 line |
| **3D** | Three `scatter3d` lines p5/p50/p95 in (N,E,U) |
| **Toggle** | Default **checked** when `hasBands()`; applies to **both** panes |

Bands are **not** scrub-dependent geometry; scrub only moves nominal markers.

### Battery (**R3** when present)

Pipeline can write (see `uavsim.results.run_dir` / studies pipeline):

| Path | Use |
|------|-----|
| `timeseries.soc` | SOC gauge; optional transport strip; values typically **0–1 fraction** → display as % |
| `timeseries.power_w` | Power vs time + playhead |
| `timeseries.energy_wh_remaining` | Energy remaining vs time + playhead |
| `metrics.soc_final`, `soc_min`, `peak_power_w` | optional KPI chips / About |

**Exporter task:** load these arrays from nominal timeseries if keys exist; downsample with the same index as position; omit keys if absent.

**UI rules:**

- If **any** battery series present → show battery card.  
- If **none** → **omit** card (no placeholders).  
- Gauge reads `soc[frameIndex]`; series share the global playhead vertical line pattern used by range.

---

## Showcase attitude reference (copy patterns, not React)

Canonical: [`docs/showcase/app.js`](../../showcase/app.js)

| Symbol / region | Role |
|-----------------|------|
| `rotationBodyToNed(phi, theta, psi)` ~L441 | Body→NED ZYX |
| `bodyToPlot(R, vb)` ~L455 | NED → plot (N, E, up) |
| `vehicleGeom(eulerDeg, u, limits)` ~L518 | X-quad segments, motors, axes, optional thrust from `u` |
| `VehicleAttitudeView` ~L857 | Plotly scene fixed at origin; restyle on frame |
| `FlightTab` dual-pane ~L1622–1650 | Left trajectory / right attitude layout |

**Minimum viable attitude for intercept (R3):**

1. Port `deg2rad`, `matMulVec`, `rotationBodyToNed`, `bodyToPlot`, frame segment builder (even if wrench omitted).  
2. Fixed axis ranges ~`[-1.05, 1.05]` cube; scene bg `#0a0e16`; axes titled N/E/up.  
3. `uirevision: "att-" + caseId`; on scrub, restyle airframe + motors + body axes only.  
4. Skip `wrenchToMotorForces` unless `timeseries.u` exists.

Do **not** `import` showcase modules at runtime — duplicate minimal helpers in intercept `app.js` (vanilla IIFE).

---

## Frame sync contract

```text
frameIndex ──► 3D trail + own/tgt markers
            ──► attitude mesh (euler_deg[i])
            ──► 2D trail + markers
            ──► range playhead
            ──► battery SOC + power/energy playheads
            ──► transport scrub value + readouts
```

| Event | Action |
|-------|--------|
| scrub / ←→ / play tick | restyle dynamic traces only |
| case toggle | pause; index=0; `newPlot` all case-bound views |
| bands toggle | rebuild 2D+3D band layers; keep camera via uirevision |
| projection NE/NU | rebuild 2D only |

---

## Story copy (pad + GE)

Update hard-coded story strip **and** exporter `ui` block, e.g.:

> **Pad climb intercept** — ownship takes off from a pad, climbs through ground effect, then tracks an open-loop path toward a scripted target with fixed NDI. Capture when min ‖p_own − p_tgt‖ ≤ r_cap. Plant MC on the success recipe; battery SOC/power shown when logged.

About bullets should mention: pad takeoff, ground-effect model in plant, open-loop L0 (if still L0), capture radius, plant-only MC, bands method, battery opt-in.

---

## Acceptance smoke (implementer self-check)

1. Open static server → **transport visible under header without scrolling** past plots.  
2. Scroll down → transport (and/or header stack) **stays sticky**.  
3. Primary row = **3D | attitude**; secondary = **2D N–E | range**.  
4. Play/scrub → markers, attitude, range cursor, SOC (if any) move together; 3D/attitude cameras do not reset.  
5. MC bands default ON → **2D fill visible** and **3D percentile curves visible**; toggle off clears both.  
6. Pack still has non-null `mc.bands` with N/E/U p5/p95.  
7. If pack has `soc` / `power_w` / `energy_wh_remaining` → battery card works; if not → no empty battery section.  
8. Story/About mentions **pad** and **ground effect**.  
9. Success | Fail still works; P(capture) still from `intercept_success`.  
10. No npm; CDN Plotly; dark theme.

---

## Out of scope this pass

- In-browser re-sim or plant knobs  
- Full 500-path cloud in the browser  
- Required wrench HUD without `u`  
- Changing capture math or MC study design  
- Portfolio matrix / envelope tabs  

---

## Suggested implement order

1. **CSS/DOM layout** — sticky transport to top; primary = 3D|attitude shell; secondary = 2D|range (can leave attitude empty host first).  
2. **Move range draw** into secondary host; smoke scrub.  
3. **Attitude** helpers + restyle loop.  
4. **Battery** exporter pass-through + UI card.  
5. **Copy** pad/GE.  
6. **Smoke** full §8 R3 list.

---

## Document history

| Date | Note |
|------|------|
| 2026-07-25 | R3 brief: top transport, attitude, range+2D row, battery fields, pad/GE, showcase attitude refs |
