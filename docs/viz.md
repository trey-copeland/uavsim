# Visualization pack

Normative requirements: [`SPEC.md`](../SPEC.md) §11A (V1–V8).  
**Rule:** consumers of run directories only — never live sim state.

## Quickstart

```bash
uv sync --extra viz   # matplotlib + plotly
uv run uavsim simulate configs/studies/gentle_square.yaml
uv run uavsim report runs/<study_id>_<timestamp>/ --interactive
# open figures/flight_3d.html in a browser (rotate, play, vectors + HUD)

# Full portfolio rollup (React SPA + frozen base-case JSON)
uv run uavsim gallery --base-case
python -m http.server 8765 --directory docs/showcase
```

See also [`docs/showcase/README.md`](showcase/README.md) for GitHub Pages.

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
| `figures/mc_rmse_hist.png`, `mc_rmse_cdf.png` | V5 distributions |
| `figures/mc_*_vs_rmse.png`, `mc_param_scatters.png` | V5 param sensitivity |
| `figures/mc_metrics_box.png`, `mc_metrics_dist.png` | V5 multi-metric |
| `figures/mc_success.png`, `mc_param_corr.png` | V5 summary |
| `figures/mc_exemplar_paths.png` | V5 re-sim best/median/worst paths |
| `figures/mc_dashboard.html`, `mc_sensitivity.html` | V5 interactive (`--interactive`) |
| `figures/flight_3d.html` | V1 + V7 interactive |
| `compare_*/compare_3d.html` | V2 dual overlay |
| `reports/summary.md` | metrics + V6 feasibility section |

## Vectors (interactive)

Relative arrow lengths; absolute values in the HUD: velocity, position error (if ref grid), thrust (−body-z), body triad.
