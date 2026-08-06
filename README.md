# uavsim flight results (React)

Single-page React app for the portfolio **base case**: a guided technical report with a **controller × sensor** matrix (**LQR/LQG**, **PID**, **NDI**) on **baseline** and **near-envelope** missions, **higher-fidelity plant** variants, a **law-compare** mission (aggressive path + aero + quat), Flight 3D, System block diagram, Monte Carlo, and a **tracking envelope**.

**UI product spec:** [UI_SPEC.md](UI_SPEC.md)  
**Closed-loop stack provenance:** [STACK_SPEC.md](STACK_SPEC.md)

**Walkthrough (header strip):** Matrix → Flight → Laws → Envelope.  
**Mission** is a segmented control in the sticky header (rebinds all tabs).  
**System** tab shows the active run’s block diagram and equations when gallery includes `stack`.

## Missions

| Mission | Path / stress | Matrix |
|---------|----------------|--------|
| **Baseline** | `figure_eight.yaml`, constant yaw | Estimation (3 laws × sensors) |
| **Envelope edge** | `figure_eight_envelope_edge.yaml` (τ★≈0.28), scheduled yaw | Same estimation matrix, edge twins |
| **Hi-fi** | Plant variants, ideal state | LQR + NDI × vacuum / motors / aero / GE / quat |
| **Laws (hi-fi)** | `law_compare_hifi.yaml`, aggressive + scheduled yaw | LQR vs PID vs NDI on aero + quat plant |

## Estimation matrix (baseline / edge)

| Row | Ideal | GPS+IMU naive | GPS+IMU KF | AHRS | Flow+alt | IMU-only |
|-----|-------|---------------|------------|------|----------|----------|
| **LQR / LQG** | `figure_eight` | `…_gps_imu_naive` | `…_gps_imu_lqg` | `…_ahrs_lqg` | `…_flow_alt_lqg` | `…_imu_only_lqg` |
| **PID** | `figure_eight_pid` | `…_naive_pid` | `…_kf_pid` | `…_ahrs_kf_pid` | `…_flow_alt_kf_pid` | `…_imu_only_kf_pid` |
| **NDI** | `figure_eight_ndi` | `…_naive_ndi` | `…_kf_ndi` | `…_ahrs_kf_ndi` | `…_flow_alt_kf_ndi` | `…_imu_only_kf_ndi` |

Edge twins use `edge_*` study ids (same roles). MC: `figure_eight_gps_imu_lqg_mc` (+ edge twin).

**Naming:** LQG = linear KF + hover LQR. **KF → PID/NDI** is not classical LQG.  
**Honesty:** [docs/LIMITATIONS.md](../LIMITATIONS.md).

## Higher-fidelity plant mission

| Plant | LQR run id | NDI run id |
|-------|------------|------------|
| Vacuum wrench | `plant_nominal_lqr` | `plant_nominal_ndi` |
| Mixer + motors | `plant_motors_lqr` | `plant_motors_ndi` |
| Body drag + prop H | `plant_aero_lqr` | `plant_aero_ndi` |
| Ground effect | `plant_ge_lqr` | `plant_ge_ndi` |
| Quaternion plant | `plant_quat_lqr` | `plant_quat_ndi` |

## Law-compare mission

| Law | Study |
|-----|--------|
| Hover LQR | `law_compare_hifi_lqr` |
| Cascade PID | `law_compare_hifi_pid` |
| Cascade NDI | `law_compare_hifi_ndi` |

Shared aggressive mission + aero vehicle + quat plant; metrics only (no ranking copy in the SPA).

## Envelope tab (τ sweep)

Time-scale sweep over matrix schemes (LQR family, PID family, **ideal NDI**). Shared position bound for comparable success. Solid = LQR family, dashed = PID, NDI as its own scheme id `ideal_ndi`.

## Flight tab

Dual-pane scrubber: trajectory + vehicle attitude / per-rotor thrust (inverse mix of \(u\)).

## Rebuild gallery

```bash
uv run uavsim gallery --base-case
# writes docs/showcase/data/showcase.json (+ SPA files)
```

Smoke:

```bash
uv run uavsim gallery --base-case --n-mc-trials 8 --skip-envelope
uv run uavsim gallery --base-case --n-mc-trials 2 --skip-envelope --skip-edge-mission
```

Local preview:

```bash
python -m http.server 8765 --directory docs/showcase
```

Data: `data/showcase.json` (browser-safe, downsampled). React + Plotly from CDN.  
**Stale-data risk:** rebuild before external demos.
