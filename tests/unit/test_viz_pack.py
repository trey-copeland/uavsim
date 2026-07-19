"""Visualization pack unit tests (loaders, static, interactive if plotly)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from uavsim.studies import run_nominal_study
from uavsim.viz.flight3d import plotly_available, write_flight_html
from uavsim.viz.loaders import load_run, saturation_mask
from uavsim.viz.report import generate_report
from uavsim.viz.static_plots import write_static_figures

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def hover_run(tmp_path: Path) -> Path:
    result = run_nominal_study(
        ROOT / "configs" / "studies" / "hover_nominal.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    return result.run_dir


@pytest.fixture
def square_run(tmp_path: Path) -> Path:
    result = run_nominal_study(
        ROOT / "configs" / "studies" / "gentle_square.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    return result.run_dir


def test_load_run_and_static_pack(hover_run: Path) -> None:
    art = load_run(hover_run)
    assert art.t is not None and art.x is not None
    figs = write_static_figures(art)
    names = {p.name for p in figs}
    assert "nominal_timeseries.png" in names
    assert "flight_still.png" in names
    assert "error_control_strips.png" in names


def test_feasibility_in_report(square_run: Path) -> None:
    rep = generate_report(square_run, figures=True, interactive=False)
    text = rep.summary_md.read_text(encoding="utf-8")
    assert "Feasibility" in text
    assert len(rep.figures) >= 3


def test_saturation_mask_detects_high_thrust() -> None:
    from uavsim.viz.loaders import ActuatorLimitView

    u = np.array([[9.5, 0, 0, 0], [1.0, 0, 0, 0]], dtype=float)
    lim = ActuatorLimitView(thrust_max_n=9.81, torque_max_nm=1.0)
    sat = saturation_mask(u, lim, margin=0.95)
    assert sat[0]
    assert not sat[1]


def test_mc_static_pack(tmp_path: Path) -> None:
    result = run_nominal_study(
        ROOT / "configs" / "studies" / "hover_mc_smoke.yaml",
        output_root=tmp_path / "runs",
        run_mc=True,
        n_trials_override=4,
    )
    art = load_run(result.run_dir)
    figs = write_static_figures(art)
    names = {p.name for p in figs}
    assert "mc_rmse_hist.png" in names
    assert "mc_rmse_cdf.png" in names
    assert "mc_mass_vs_rmse.png" in names


@pytest.mark.skipif(not plotly_available(), reason="plotly not installed")
def test_interactive_html(square_run: Path) -> None:
    art = load_run(square_run)
    out = write_flight_html(art, square_run / "figures" / "flight_3d.html", max_frames=20)
    assert out.is_file()
    html = out.read_text(encoding="utf-8")
    assert "plotly" in html.lower() or "Plotly" in html


@pytest.mark.skipif(not plotly_available(), reason="plotly not installed")
def test_report_interactive_cli(square_run: Path) -> None:
    from uavsim.cli.main import main

    code = main(["report", str(square_run), "--interactive", "--no-figures"])
    assert code == 0
    assert (square_run / "figures" / "flight_3d.html").is_file()
