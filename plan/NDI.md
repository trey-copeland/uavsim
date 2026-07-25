# Plan: Nonlinear Dynamic Inversion (NDI) in the portfolio

| Field | Value |
|-------|--------|
| **Status** | Planned — implement on branch `ndi` |
| **Goal** | Third control-law family alongside hover LQR/LQG and cascade PID, with full side-by-side story: baseline, envelope-edge, estimation matrix, τ-envelope, and Hi-fi plant variants |
| **Primary interface** | Existing `Controller` → body wrench \(u=[F,\tau_\phi,\tau_\theta,\tau_\psi]\) |
| **Audience** | Hiring GNC reviewers + technical peers (honest SIL report, not black-box demo) |

This document is the **implementation plan and product contract** for NDI. Execute in the order of §7 unless a dependency forces a skip; do not ship a half-wired matrix.

---

## 1. Product intent

### 1.1 One-sentence story

> Same missions and plants; three laws (PID, LQR/LQG, NDI); show where hover linearization dies, where cascade maps are enough, and where inverting the nonlinear rigid-body model recovers tracking — including under richer plants.

### 1.2 What “all of it” means (acceptance)

| Surface | Requirement |
|---------|-------------|
| **Controller** | `ndi_cascade` (or equivalent id) implements full-state NDI cascade → saturated body wrench |
| **Studies** | Ideal NDI on baseline + envelope-edge; NDI × same sensor suites as LQR/PID where applicable; NDI on Hi-fi plant cells |
| **Showcase matrix** | Side-by-side **three law rows** (or equivalent IA) for estimation missions; Hi-fi includes NDI column or row |
| **Envelope** | τ-sweep includes ideal NDI (+ optional partial-sensor NDI schemes if cost allows; **minimum: ideal NDI**) |
| **System tab** | Controller block shows **full inversion equations**; plant/observer unchanged in contract |
| **Export** | `controller_artifact` + gallery `stack.details.controller` for NDI gains + inversion assumptions |
| **Tests** | Unit + integration: baseline track, edge stress vs LQR, saturation safety, sign conventions (NED) |
| **Docs** | `docs/developer/control.md`, LIMITATIONS honesty, showcase README / UI_SPEC / STACK_SPEC |

### 1.3 Explicit non-goals (v1)

- Full differential-flatness \(y^{(4)}\) I/O linearization as the default law (optional appendix later)
- Adaptive / learning inversion
- Motor-level NDI as the primary command interface (wrench stays primary; motors plant remains outer lag)
- Claiming robustness to large aero mismatch without INDI (document; optional Phase E)

---

## 2. Control design (MVP law)

### 2.1 Architecture: cascade NDI (recommended ship)

Structure parallels `pid_cascade` but replaces small-angle tilt maps and rate PD with **model inversion**.

```text
x̂, x_r
   │
   ▼
┌──────────────────┐
│ Position / vel   │  virtual accel a_v in NED
│ PD (or PID) on e │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Thrust + attitude│  f_des from a_v and gravity (NED z+ down)
│ direction map    │  F = ‖·‖, R_des / b3_des from thrust direction + yaw
└────────┬─────────┘
         ▼
┌──────────────────┐
│ SO(3) + rate NDI │  invert Euler: τ = ω×Iω + I α_des
│ α_des from e_R,e_ω│
└────────┬─────────┘
         ▼
    u = sat([F, τ])
```

### 2.2 Equations (System tab source of truth)

**Frames:** NED inertial, FRD body (match plant). Gravity \(+mg\) along NED \(+z\).

**Position loop (virtual control):**

\[
e_p = p_r - p,\quad e_v = v_r - v
\]
\[
a_v = a_r + K_d e_v + K_p e_p
\]

where \(a_r = \dot v_r\) from reference (numerical derivative of \(v_r\) if not in `ReferenceSample`; prefer smooth minsnap missions).

**Collective thrust and desired body-z (level of detail to lock in implementation review):**

With NED \(z+\) down, hover needs \(F \approx mg\) along **−body \(z\)** so that inertial thrust counters gravity. Desired specific force / acceleration command must use the **same sign convention as `state_derivative`** (already fixed for PID/LQR). Implementation must unit-test against hover hold and known \(\pm\theta \Rightarrow \mp \ddot N\) behavior.

Sketch (to be finalized against plant, not invented ad hoc):

\[
f_{\text{cmd}}^{\text{NED}} = m\, a_v \quad\text{(with gravity accounting matching plant)}
\]
\[
F = \mathrm{clip}(\|f_{\text{thrust}}\|,\, F_{\min}, F_{\max}),\quad
b_{3,\text{des}} \parallel \text{thrust direction in NED}
\]

Yaw reference \(\psi_r\) (or \(\psi\) from \(x_r\)) completes \(R_{\text{des}}\) (or desired quaternion).

**Attitude / rate NDI (Euler equation inverse):**

\[
e_R = \mathrm{vee}\big(\log(R_{\text{des}}^\top R)\big)\quad\text{(existing SO(3) helpers)}
\]
\[
e_\omega = \omega - \omega_{\text{des}}
\]
\[
\alpha_{\text{des}} = \dot\omega_{\text{des}} - K_R e_R - K_\omega e_\omega
\]
\[
\tau = \omega \times (I\omega) + I\,\alpha_{\text{des}}
\]
\[
u = \mathrm{saturate}([F,\tau^\top]^\top)
\]

**Inversion model (document on artifact):**

| Field | v1 default |
|-------|------------|
| Rigid body | Diagonal \(I\), mass \(m\), gravity \(g\) from vehicle |
| Aero in inverse | **Off** (vacuum inverse) unless `invert_aero: true` later |
| Motors in inverse | **None** — command wrench; plant may lag |
| Attitude plant | Control bus Euler 12-state; SO(3) error (same as LQR/PID) |

### 2.3 Gains (YAML)

```yaml
controller:
  type: ndi_cascade
  kp_pos: [..]   # 3
  kd_pos: [..]   # 3
  k_R: [..]      # 3 attitude (SO(3)) gains
  k_omega: [..]  # 3 rate gains
  max_tilt_rad: 0.7   # safety on F direction / attitude ref
  # optional:
  # use_ref_accel: true
  # invert_model: vacuum_rigid_body
```

Tune so that on **baseline figure-eight + ideal state**, NDI RMSE is in the same ballpark as ideal LQR (not required to beat it). On **envelope-edge**, NDI should **not collapse** the way hover LQR can when tilt leaves the linear regime (success criterion: competitive tracking or clear improvement vs LQR on the same bound — document actual numbers after tune).

### 2.4 Singularities and safety (must implement)

| Hazard | Mitigation |
|--------|------------|
| \(F \to 0\) | Floor \(F \ge F_{\min}\) or \(F \ge \epsilon mg\); degrade attitude cmd |
| Thrust direction / tilt limit | Clamp commanded accel horizontal component; `max_tilt_rad` |
| Reference accel noise | Low-pass or use guidance backend derivatives when available |
| Post-inversion saturation | Saturate \(u\); optional log `ndi_saturated` in metrics later |
| Euler wrap | SO(3) error only — no component-wise Euler subtraction |

---

## 3. Code map

| Path | Work |
|------|------|
| `src/uavsim/control/ndi.py` | **New** — gains, controller, `design_ndi_cascade` |
| `src/uavsim/control/factory.py` | Wire `type: ndi_cascade` |
| `src/uavsim/control/export.py` | Artifact schema for NDI |
| `src/uavsim/control/__init__.py` | Exports |
| `src/uavsim/viz/stack.py` | `_controller_equations("ndi_cascade")` + gains dump |
| `docs/developer/control.md` | NDI section |
| `docs/LIMITATIONS.md` | Model match / saturation / not INDI |
| `configs/studies/*ndi*.yaml` | Study set (§4) |
| `src/uavsim/studies/envelope.py` | NDI schemes in matrix / showcase scales |
| `src/uavsim/viz/gallery.py` | Matrix rows, labels, plant×NDI, BASE/EDGE/PLANT lists |
| `docs/showcase/app.js` | Three-law matrix UX if needed; badges; System already generic |
| `docs/showcase/UI_SPEC.md`, `README.md`, `STACK_SPEC.md` | Sync |
| `tests/unit/test_ndi_*.py` | Signs, hover, inversion identity at equilibrium |
| `tests/integration/...` | Study smoke baseline + edge |

**Factory contract:** no new plant APIs required for v1.

---

## 4. Study matrix (build all)

### 4.1 Naming

| Gallery role / id pattern | Meaning |
|---------------------------|---------|
| `ideal_ndi` | Full state → NDI |
| `est_*_ndi` | Same sensors as LQR/PID siblings → NDI (naive / KF / AHRS / flow / IMU) |
| `edge_*_ndi` | Envelope-edge mission twins |
| `plant_*_ndi` | Hi-fi plant × ideal NDI |

Study files live under `configs/studies/` with clear `study_id`s.

### 4.2 Ideal full-state (law triangle)

| Study | Mission | Compare to |
|-------|---------|------------|
| `figure_eight_ndi.yaml` | baseline figure-eight | `figure_eight.yaml` (LQR), `figure_eight_pid.yaml` |
| `edge_figure_eight_ndi.yaml` | envelope edge | `edge_figure_eight.yaml`, `edge_figure_eight_pid.yaml` |

### 4.3 Estimation × NDI (parity with LQR/PID rows)

Mirror existing channels and observer configs from LQR/PID studies (same noise, seeds, channels):

| Sensors | Baseline study | Edge study |
|---------|----------------|------------|
| GPS+IMU naive | `figure_eight_gps_imu_naive_ndi.yaml` | `edge_gps_imu_naive_ndi.yaml` |
| GPS+IMU + linear KF | `figure_eight_gps_imu_kf_ndi.yaml` | `edge_gps_imu_kf_ndi.yaml` |
| AHRS | `figure_eight_ahrs_kf_ndi.yaml` | `edge_ahrs_kf_ndi.yaml` |
| Flow+alt | `figure_eight_flow_alt_kf_ndi.yaml` | `edge_flow_alt_kf_ndi.yaml` |
| IMU-only | `figure_eight_imu_only_kf_ndi.yaml` | `edge_imu_only_kf_ndi.yaml` |

**Note:** “LQG” remains **KF + LQR** only. NDI + KF is **not** called LQG in UI copy (method string: `linear_kf → NDI`).

Naive partial bus → NDI is an **intentional stress** (same teaching fail mode as naive → LQR).

### 4.4 Hi-fi plant × ideal NDI

| Plant | Study | Twin LQR study |
|-------|--------|----------------|
| Vacuum wrench | `plant_nominal` already ideal LQR; add NDI as `plant_nominal_ndi` **or** share nominal path with law switch | `figure_eight_ndi` may double as nominal |
| Motors | `figure_eight_ndi_motors.yaml` | `figure_eight_motors.yaml` |
| Aero | `figure_eight_ndi_aero.yaml` | `figure_eight_aero.yaml` |
| GE (low path) | `figure_eight_ndi_ge.yaml` | `figure_eight_ge.yaml` |
| Quat plant | `figure_eight_ndi_quat.yaml` | `figure_eight_quat.yaml` |

Hi-fi showcase matrix becomes **laws × plant variants** or **plants × laws**:

**Preferred IA (clear side-by-side):**

| | Vacuum | Motors | Aero | GE | Quat |
|--|--------|--------|------|-----|------|
| Ideal LQR | ✓ | ✓ | ✓ | ✓ | ✓ |
| Ideal PID | optional v1.1 if cost | | | | |
| **Ideal NDI** | ✓ | ✓ | ✓ | ✓ | ✓ |

Minimum for “all of it”: **LQR + NDI** on all five plants; PID on vacuum (+ optional others).

### 4.5 Monte Carlo (optional but valuable)

- `figure_eight_gps_imu_kf_ndi_mc.yaml` — mass/I scatter, NDI gains fixed (same philosophy as LQR MC)
- Edge MC twin if baseline MC stays in gallery

Ship if schedule allows after nominal matrix is green; do not block NDI merge on MC.

---

## 5. Showcase / envelope integration

### 5.1 Estimation missions (`baseline`, `envelope_edge`)

**Rows:** LQR/LQG · PID · **NDI**  
**Columns:** unchanged sensor suite (ideal, GPS+IMU naive, GPS+IMU KF, AHRS, flow+alt, IMU-only)

Update:

- `ESTIMATION_MATRIX` in `gallery.py` — third row + scenarios with `run_id_by_mission`
- `BASE_CASE_STUDIES` / `EDGE_CASE_STUDIES` tuples
- Labels, About copy, value prop
- SPA: matrix already row-driven; verify three rows render; badges for `ndi`

### 5.2 Hi-fi mission (`plant_fidelity`)

Extend `PLANT_MATRIX` / `PLANT_FIDELITY_STUDIES`:

- Add NDI runs per plant cell **or** restructure to 2D plant×law grid
- `matrix_kind: plant` UI copy: “Higher-fidelity dynamics — LQR vs NDI (ideal state)”

### 5.3 Envelope tab

In `envelope.py` / `MATRIX_SCHEMES` (or equivalent):

| Scheme id | Law | Sensors |
|-----------|-----|---------|
| `ideal_lqr` | LQR | full state |
| `ideal_pid` | PID | full state |
| **`ideal_ndi`** | NDI | full state |
| existing partial schemes | keep | keep |

**Minimum ship:** all current schemes **plus** `ideal_ndi`.  
**Full ship:** also `gps_imu_kf_ndi` (and naive NDI if informative).

Envelope description copy: three ideal laws + sensor matrix stress.

### 5.4 System tab

- `equations` for NDI (full cascade + inverse Euler)
- Gains tables
- `invert_model: vacuum_rigid_body` in details
- No fake \(A,B\) CARE for NDI; optional note: “not designed via hover linearization”

### 5.5 Compare / defaults

- Baseline compare: keep naive vs LQG; add secondary compare LQR vs NDI ideal in docs
- Edge default run: consider ideal NDI or ideal LQR (product choice at UI polish)

### 5.6 Rebuild

```bash
uv run uavsim gallery --base-case
# smoke:
uv run uavsim gallery --base-case --skip-envelope --n-mc-trials 4
```

Expect longer gallery wall time (more studies × envelope schemes). Document in showcase README.

---

## 6. Testing strategy

| Layer | Cases |
|-------|--------|
| **Unit** | Hover equilibrium \(u \approx u_h\); small \(\theta\) command → correct \(F\) / \(\tau\) signs vs plant; SO(3) path; saturation clip |
| **Unit** | At \(\omega=0\), \(e_R=0\), \(\tau = I\alpha_{\text{des}}\) structure |
| **Integration** | `figure_eight_ndi` RMSE within loose bound; success true on nominal bound |
| **Integration** | Edge: NDI vs LQR metrics logged; assert NDI does not NaN / explode |
| **Regression** | Existing LQR/PID tests unchanged |
| **Stack** | `build_stack_from_study_mapping` NDI study → equations contain inversion lines |

---

## 7. Delivery phases (still build all; ordered)

Execute on branch **`ndi`**. Merge to `main` when Phase D green; Phase E can trail if needed.

### Phase A — Core law (blocking)

1. Implement `ndi.py` + factory + export  
2. `figure_eight_ndi.yaml` + unit/integration tests  
3. Sign/convention lock vs plant (copy PID tests patterns)  
4. Stack equations for NDI  

**Exit:** ideal baseline NDI tracks; artifact + System equations OK.

### Phase B — Side-by-side ideal laws + edge

1. `edge_figure_eight_ndi.yaml`  
2. Gallery: ideal NDI on baseline + edge in matrix (third row ideal column first if incremental)  
3. Envelope scheme `ideal_ndi`  
4. Docs: control.md + LIMITATIONS  

**Exit:** Overview shows LQR vs PID vs NDI ideal; envelope curve for NDI; edge mission selectable.

### Phase C — Full estimation × NDI

1. All naive/KF sensor studies for baseline + edge  
2. Wire full third matrix row  
3. SPA badges / method strings  
4. Rebuild showcase (or offline enrich + targeted runs)  

**Exit:** 3×6 matrix populated both missions (minus MC).

### Phase D — Hi-fi × NDI

1. Motors / aero / GE / quat NDI studies  
2. Plant matrix 2-law (LQR+NDI) or 3-law if PID vacuum included  
3. System plant equations already mode-aware; confirm NDI + motors story in About  

**Exit:** Hi-fi mission tells model-match story (vacuum inverse vs lagged/aero plant).

### Phase E — Polish / optional

1. NDI MC  
2. Extra envelope schemes (KF→NDI)  
3. INDI spike doc (not required for merge)  
4. UI_SPEC / STACK_SPEC final sync  
5. LinkedIn-ready one-pager in README “Laws” section  

---

## 8. UI / copy contracts

### 8.1 Naming

| Use | String |
|-----|--------|
| Law row | `NDI` or `NDI cascade` |
| Method (ideal) | `NDI` |
| Method (filtered) | `linear_kf → NDI` |
| Method (naive) | `partial_raw → NDI` |
| Never | “LQG” for NDI+KF |

### 8.2 About / value prop (draft)

> SIL comparison of cascade PID, hover LQR/LQG, and nonlinear dynamic inversion under shared sensor suites and plant variants. Near-envelope and Hi-fi missions stress linearization and model match; System view exposes laws and EOM per run.

### 8.3 LIMITATIONS bullets (required)

- NDI inverse is **vacuum rigid-body** unless stated; aero/GE/motors in plant are **disturbances** to the inverse  
- Not robust synthesis; gains are PD-style on error coordinates after inversion  
- Large model error → prefer future INDI / robust redesign  
- Underactuated; inversion does not magically add control authority beyond \(F,\tau\) limits  

---

## 9. Risk register

| Risk | Mitigation |
|------|------------|
| NED / thrust sign bugs | Reuse PID plant-facing tests; hover + step tilt fixtures |
| Envelope rebuild time | Add `ideal_ndi` first; gate extra schemes; CI smoke `--skip-envelope` |
| Matrix overcrowding | Three rows is OK; keep columns fixed; mobile scroll already exists |
| NDI worse than LQR on baseline | Acceptable if edge story is clear; tune gains; don’t overclaim |
| Reference accel quality | Prefer minsnap; finite-diff \(v_r\) with study `sample_dt_s` |
| Scope creep into flatness/INDI | Park in §1.3 / Phase E |

---

## 10. Definition of done (merge checklist)

- [ ] `ndi_cascade` in factory + export + unit tests  
- [ ] Baseline + edge ideal NDI studies green  
- [ ] Full estimation×NDI studies for baseline + edge (parity with PID row)  
- [ ] Gallery `ESTIMATION_MATRIX` three rows; runs wired  
- [ ] Envelope includes at least `ideal_ndi`; plots/tables OK  
- [ ] Hi-fi: NDI on vacuum + motors + aero + GE + quat  
- [ ] System tab equations for NDI  
- [ ] control.md + LIMITATIONS + showcase docs updated  
- [ ] `uavsim gallery --base-case` (or documented partial enrich) updates `showcase.json`  
- [ ] No regressions on existing LQR/PID matrix cells  

---

## 11. Suggested first PR slices on `ndi` (optional stacking)

If stacking PRs for reviewability:

1. **ndi-core** — controller + ideal baseline study + tests  
2. **ndi-edge-envelope** — edge study + envelope scheme + docs  
3. **ndi-estimation-matrix** — sensor twins + gallery row  
4. **ndi-hifi** — plant variants + Hi-fi matrix  
5. **ndi-showcase-rebuild** — full gallery data + UI polish  

Or single epic branch `ndi` if working solo (this plan’s default).

---

## 12. References (in-repo)

| Doc | Relevance |
|-----|-----------|
| `docs/developer/control.md` | Controller protocol, LQR/PID patterns |
| `docs/developer/dynamics.md` | EOM, NED, aero, motors |
| `docs/showcase/STACK_SPEC.md` | System equations payload |
| `docs/showcase/UI_SPEC.md` | Matrix / missions IA |
| `src/uavsim/control/pid.py` | Cascade + NED signs to mirror |
| `src/uavsim/dynamics/attitude_error.py` | SO(3) error for NDI attitude |
| `plan/NDI.md` | **This plan** |

---

**Branch:** `ndi`  
**Last updated:** 2026-07-24 — full portfolio NDI plan (laws × sensors × envelope × Hi-fi).
