# Intercept demo — R2 implementation summary

| Field | Value |
|-------|--------|
| **Iteration** | R2 (3D + MC bands) |
| **Branch** | `feature/intercept-guidance-battery` |
| **Normative** | [`UX_REVIEW_R2_BRIEF.md`](UX_REVIEW_R2_BRIEF.md), [`UX_SPEC.md`](UX_SPEC.md) §3 / §8, [`IMPLEMENT_CHECKLIST.md`](IMPLEMENT_CHECKLIST.md) |

## Shipped

### 1. Exporter bands (`scripts/export_demo_data.py`)

- `--with-bands` / `--no-with-bands` (default **true** when MC trials present)
- `--band-max-trials` (default 100), `--band-points` (160), `--band-seed`
- Offline re-sim via `prepare_study`-equivalent stack:
  - `StudyConfig` from success run `study_config.yaml`
  - Plant from trial CSV columns (`mass_kg`, `ixx/iyy/izz_kg_m2`, `arm_length_m`, `thrust_max_n`, optional propulsion)
  - Fixed NDI controller (`redesign_controller=false` → nominal controller)
  - `run_closed_loop_trial`
- Ownship NED → `ned_to_plot` (N, E, up)
- Axis-wise p5/p50/p95 on common `t` grid → `mc.bands` schema from brief
- Progress on stderr; pack size stays browser-friendly (quantile polylines only)

### 2. Data pack

| Source | Path |
|--------|------|
| Success MC | `runs/intercept_l0_success_mc_20260725T153348Z` |
| Fail nominal | `runs/intercept_l0_fail_20260725T140842Z` |

Committed pack facts (post-export):

- `mc.n_trials` = 500, `p_capture` = 1.0
- `mc.bands.n_paths_used` = 100
- `len(bands.t)` = `len(bands.ownship.N.p5)` = 160
- `demo.json` ≈ 832 KB (well under 5 MB)

### 3. SPA layout + 3D

Preferred R2 layout:

```text
3D trajectory | range(t)
2D N–E (full width, bands + capture circle)
shared transport
MC histogram
```

- Plotly `scatter3d`: ownship + target paths, trail + markers at scrub index
- `uirevision: intercept3d-<case>` so orbit survives scrub
- Scrub/play: `Plotly.restyle` on trail + markers when static shell unchanged; full `react` on case/band toggle
- MC bands default **ON** when present; single toggle drives 2D fill + 3D p5/p50/p95 fan
- Fail case: muted note “MC / bands: success plant study”
- How-to-read includes band method bullet

### 4. Docs

- Demo `README.md` documents band CLI flags and rebuild recipe
- This summary + checklist R2 items closed

## Rebuild command

```bash
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/intercept_l0_success_mc_20260725T153348Z \
  --fail-run runs/intercept_l0_fail_20260725T140842Z \
  --with-bands --band-max-trials 100 \
  --out docs/demos/intercept/data/demo.json
```

~0.45–0.5 s/trial on the L0 intercept mission (tf≈8 s); 100 trials ≈ 45 s.

## Smoke checklist (manual)

1. `cd docs/demos/intercept && python -m http.server 8765` → open `/`
2. 3D path visible; orbit; scrub does not reset camera
3. Bands ON by default → 2D fill + 3D percentile curves; toggle OFF removes both
4. Success | Fail swap nominals; histogram/P(capture) unchanged
5. Play advances 3D markers, 2D markers, range playhead together

## Out of scope (unchanged)

- Full 500-path cloud in browser
- Attitude/wrench dual-pane
- Battery UI
- In-browser re-sim
- npm build
