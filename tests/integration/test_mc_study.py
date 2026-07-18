"""Integration: Monte Carlo study + report consumer."""

from __future__ import annotations

from pathlib import Path

import pytest

from uavsim.cli.main import main
from uavsim.monte_carlo import read_trials_csv
from uavsim.studies import run_study
from uavsim.viz import generate_report

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def runs_tmp(tmp_path: Path) -> Path:
    return tmp_path / "runs"


def test_hover_mc_smoke_seed_stable(runs_tmp: Path) -> None:
    study = ROOT / "configs" / "studies" / "hover_mc_smoke.yaml"
    r1 = run_study(study, output_root=runs_tmp / "a")
    r2 = run_study(study, output_root=runs_tmp / "b")
    assert r1.success
    assert r2.success
    assert r1.n_trials == 4
    assert r1.mc_summary is not None
    assert r2.mc_summary is not None

    t1 = read_trials_csv(r1.run_dir / "monte_carlo" / "trials.csv")
    t2 = read_trials_csv(r2.run_dir / "monte_carlo" / "trials.csv")
    assert len(t1) == 4
    for a, b in zip(t1, t2, strict=True):
        assert a["trial_id"] == b["trial_id"]
        assert a["mass_kg"] == b["mass_kg"]
        assert a["rmse_position_m"] == pytest.approx(b["rmse_position_m"], rel=0, abs=1e-9)

    assert (r1.run_dir / "monte_carlo" / "summary.json").is_file()
    assert r1.mc_summary["schema_version"] == 1
    assert "rmse_position_m" in r1.mc_summary["metrics"]


def test_study_cli_mc_and_report(runs_tmp: Path) -> None:
    study = ROOT / "configs" / "studies" / "hover_mc_smoke.yaml"
    code = main(["study", str(study), "--output", str(runs_tmp), "--n-trials", "3"])
    assert code == 0
    runs = list(runs_tmp.glob("hover_mc_smoke_*"))
    assert len(runs) == 1
    run_dir = runs[0]
    assert (run_dir / "monte_carlo" / "trials.csv").is_file()

    code = main(["report", str(run_dir), "--no-figures"])
    assert code == 0
    assert (run_dir / "reports" / "summary.md").is_file()
    text = (run_dir / "reports" / "summary.md").read_text(encoding="utf-8")
    assert "Monte Carlo" in text


def test_report_consumer_reads_run_dir(runs_tmp: Path) -> None:
    study = ROOT / "configs" / "studies" / "hover_mc_smoke.yaml"
    result = run_study(study, output_root=runs_tmp, n_trials_override=2)
    rep = generate_report(result.run_dir, figures=False)
    assert rep.summary_md.is_file()
    assert "Nominal metrics" in rep.summary_md.read_text(encoding="utf-8")


def test_simulate_skips_mc_even_if_enabled(runs_tmp: Path) -> None:
    """``simulate`` is nominal-only."""
    study = ROOT / "configs" / "studies" / "hover_mc_smoke.yaml"
    code = main(["simulate", str(study), "--output", str(runs_tmp)])
    assert code == 0
    runs = list(runs_tmp.glob("hover_mc_smoke_*"))
    assert len(runs) == 1
    assert not (runs[0] / "monte_carlo").exists()
