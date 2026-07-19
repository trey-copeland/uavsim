# Visualization pack

Normative requirements: [`SPEC.md`](../SPEC.md) §11A (V1–V8).  
**Rule:** consumers of run directories only — never live sim state.

## Quickstart

```bash
uv sync --extra viz   # matplotlib + plotly
uv run uavsim simulate configs/studies/gentle_square.yaml
uv run uavsim report runs/<study_id>_<timestamp>/ --interactive
# open figures/flight_3d.html in a browser (rotate, play, vectors + HUD)
```

Dual-run:

```bash
uv run uavsim compare runs/<a> runs/<b> --interactive
# → compare output dir: compare_3d.html + static overlays
```

## Artifacts

| File | Source |
|------|--------|
| `figures/nominal_timeseries.png` | V3 strips + V4 saturation bands |
| `figures/nominal_path_3d.png` / `flight_still.png` | V8 stills |
| `figures/mc_rmse_hist.png`, `mc_rmse_cdf.png`, `mc_mass_vs_rmse.png` | V5 |
| `figures/flight_3d.html` | V1 + V7 interactive |
| `compare_*/compare_3d.html` | V2 dual overlay |
| `reports/summary.md` | metrics + V6 feasibility section |

## Vectors (interactive)

Relative arrow lengths; absolute values in the HUD: velocity, position error (if ref grid), thrust (−body-z), body triad.
