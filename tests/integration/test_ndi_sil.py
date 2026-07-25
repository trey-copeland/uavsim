"""SIL: ideal cascade NDI on figure-eight tracks within portfolio bounds."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from uavsim.studies import run_nominal_study
from uavsim.viz.stack import build_stack_from_study_mapping

ROOT = Path(__file__).resolve().parents[2]


def test_figure_eight_ndi_tracks(tmp_path: Path) -> None:
    """
    Full-state NDI on baseline figure-eight should track in the same
    honesty band as other ideal laws (position_bound_m = 0.75).
    Soft RMSE band is looser than LQR heritage until gains are finalized.
    """
    result = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_ndi.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    m = result.metrics
    assert m["success"] is True
    rmse = float(m["rmse_position_m"])
    assert np.isfinite(rmse) and rmse >= 0.0
    assert rmse < 0.5, f"position RMSE {rmse} m outside soft NDI band"
    max_e = float(m["max_position_error_m"])
    assert max_e < 1.0, f"max position error {max_e} m too large"
    # Artifact present for System / gallery handoff
    art = result.run_dir / "nominal" / "controller_artifact.yaml"
    assert art.is_file()


def test_edge_figure_eight_ndi_finite(tmp_path: Path) -> None:
    """Edge mission: NDI must not NaN/explode; soft RMSE band (stress case)."""
    result = run_nominal_study(
        ROOT / "configs" / "studies" / "edge_figure_eight_ndi.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    m = result.metrics
    rmse = float(m["rmse_position_m"])
    assert np.isfinite(rmse)
    assert rmse < 2.0, f"edge NDI RMSE {rmse} m exploded"
    max_e = float(m["max_position_error_m"])
    assert np.isfinite(max_e) and max_e < 5.0


def test_law_compare_hifi_three_laws(tmp_path: Path) -> None:
    """Aggressive aero+quat path: NDI should clearly beat hover LQR on RMSE."""
    results = {}
    for name in ("lqr", "pid", "ndi"):
        r = run_nominal_study(
            ROOT / "configs" / "studies" / f"law_compare_hifi_{name}.yaml",
            output_root=tmp_path / "runs",
            run_mc=False,
        )
        results[name] = r.metrics
        assert np.isfinite(float(r.metrics["rmse_position_m"]))

    ndi_rmse = float(results["ndi"]["rmse_position_m"])
    lqr_rmse = float(results["lqr"]["rmse_position_m"])
    pid_rmse = float(results["pid"]["rmse_position_m"])
    # Relative ordering on this stress path (not coupled to LQR pass/fail)
    assert ndi_rmse < lqr_rmse, f"NDI {ndi_rmse} should beat LQR {lqr_rmse} on law-compare path"
    assert ndi_rmse < pid_rmse
    assert results["ndi"]["success"] is True


def test_ndi_study_catalog_loads() -> None:
    """All portfolio NDI YAMLs validate as ndi_cascade studies."""
    from uavsim.studies.config import load_study

    studies = sorted((ROOT / "configs" / "studies").glob("*ndi*.yaml"))
    assert len(studies) >= 16
    for path in studies:
        cfg, *_ = load_study(path)
        assert cfg.controller.type == "ndi_cascade", path.name


def test_ndi_all_studies_smoke_finite(tmp_path: Path) -> None:
    """
    Execute every *ndi* study once; assert finite metrics (no crash / NaN).

    Soft bounds only — naive / IMU-only / motor-lag cells may drift far
    (teaching failures). Does not expand the showcase.
    """
    studies = sorted((ROOT / "configs" / "studies").glob("*ndi*.yaml"))
    assert len(studies) >= 16
    # Core cells that should stay in honesty success under ideal/full KF
    expect_success = {
        "figure_eight_ndi",
        "plant_nominal_ndi",
        "plant_aero_ndi",
        "plant_ge_ndi",
        "plant_quat_ndi",
        "law_compare_hifi_ndi",
        "figure_eight_gps_imu_kf_ndi",
        "figure_eight_flow_alt_kf_ndi",
    }
    # Teaching / incomplete-bus / harsh plant: finite only (may wander far)
    teaching_fail = {
        "figure_eight_gps_imu_naive_ndi",
        "edge_gps_imu_naive_ndi",
        "figure_eight_imu_only_kf_ndi",
        "edge_imu_only_kf_ndi",
        "figure_eight_ahrs_kf_ndi",
        "edge_ahrs_kf_ndi",
        "plant_motors_ndi",
    }
    for path in studies:
        result = run_nominal_study(path, output_root=tmp_path / "runs", run_mc=False)
        m = result.metrics
        rmse = float(m["rmse_position_m"])
        max_e = float(m["max_position_error_m"])
        assert np.isfinite(rmse), f"{path.name}: non-finite RMSE"
        assert np.isfinite(max_e), f"{path.name}: non-finite max error"
        if path.stem in teaching_fail or "naive" in path.stem or "imu_only" in path.stem:
            # Completeness: sim finished with numbers (may be multi-hundred m drift)
            assert rmse < 1.0e6, f"{path.name}: RMSE {rmse} non-physical"
            continue
        assert rmse < 50.0, f"{path.name}: RMSE {rmse} m exploded"
        assert max_e < 200.0, f"{path.name}: max |e| {max_e} m exploded"
        if path.stem in expect_success:
            assert m["success"] is True, f"{path.name}: expected success, metrics={m}"


def test_ndi_stack_equations_from_study() -> None:
    from uavsim.studies.config import load_study

    study = load_study(ROOT / "configs" / "studies" / "figure_eight_ndi.yaml")
    # build_stack_from_study_mapping expects a plain mapping
    import yaml

    with (ROOT / "configs" / "studies" / "figure_eight_ndi.yaml").open(encoding="utf-8") as f:
        mapping = yaml.safe_load(f)
    stack = build_stack_from_study_mapping(mapping, repo_root=ROOT)
    ctrl = stack["details"]["controller"]
    assert ctrl["type"] == "ndi_cascade"
    eqs = ctrl.get("equations") or {}
    lines = "\n".join(eqs.get("lines") or [])
    assert "τ = ω × (I ω) + I α_des" in lines or "tau" in lines.lower() or "α_des" in lines
    assert "vacuum" in lines.lower() or "invert" in lines.lower()
    _ = study  # config loads without error
