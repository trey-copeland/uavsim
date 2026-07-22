"""Phase 5d: closed-loop with linear KF observer."""

from __future__ import annotations

from pathlib import Path

from uavsim.studies import run_nominal_study

ROOT = Path(__file__).resolve().parents[2]


def test_figure_eight_full_state_still_ok(tmp_path: Path) -> None:
    r = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    assert r.metrics["success"] is True
    assert r.metrics.get("observer_id", "none") in ("none", "none")
    assert float(r.metrics["rmse_position_m"]) < 0.12


def test_figure_eight_linear_kf_tracks(tmp_path: Path) -> None:
    r = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_observer.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    assert r.success is True
    assert r.metrics["success"] is True
    assert r.metrics["observer_id"] == "linear_kf"
    rmse = float(r.metrics["rmse_position_m"])
    # Degraded vs full-state (~0.037) but still bounded
    assert rmse < 0.4, f"observer SIL RMSE {rmse}"
    assert "rmse_estimate_position_m" in r.metrics
    # x_hat logged in timeseries
    ts = list((tmp_path / "runs").glob("*/nominal/timeseries.npz"))
    assert ts
    data = __import__("numpy").load(ts[0])
    assert "x_hat" in data.files
    assert data["x_hat"].shape == data["x"].shape


def test_figure_eight_mekf_partial_tracks(tmp_path: Path) -> None:
    r = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_mekf.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    assert r.success is True
    assert r.metrics["observer_id"] == "mekf"
    rmse = float(r.metrics["rmse_position_m"])
    assert rmse < 0.75, f"MEKF partial SIL RMSE {rmse}"
    assert r.metrics.get("success") is True


def test_gps_imu_lqg_beats_naive(tmp_path: Path) -> None:
    """Teaching moment: same sensors, LQG recovers; naive partial diverges."""
    out = tmp_path / "runs"
    naive = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_gps_imu_naive.yaml",
        output_root=out,
        run_mc=False,
    )
    lqg = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_gps_imu_lqg.yaml",
        output_root=out,
        run_mc=False,
    )
    assert naive.metrics["observer_id"] == "partial_raw"
    assert lqg.metrics["observer_id"] == "linear_kf"
    assert lqg.metrics["success"] is True
    assert float(lqg.metrics["rmse_position_m"]) < 0.15
    # Naive incomplete bus should be dramatically worse
    assert float(naive.metrics["rmse_position_m"]) > 10.0 * float(lqg.metrics["rmse_position_m"])


def test_ahrs_lqg_finite_imu_only_worse(tmp_path: Path) -> None:
    out = tmp_path / "runs"
    ahrs = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_ahrs_lqg.yaml",
        output_root=out,
        run_mc=False,
    )
    imu = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_imu_only_lqg.yaml",
        output_root=out,
        run_mc=False,
    )
    assert ahrs.metrics["observer_id"] == "linear_kf"
    assert imu.metrics["observer_id"] == "linear_kf"
    # AHRS-like stays much closer to the path than rate-only
    assert float(ahrs.metrics["rmse_position_m"]) < float(imu.metrics["rmse_position_m"])
    assert float(ahrs.metrics["max_position_error_m"]) < 10.0
    # Honesty: multi-meter AHRS path is not tracking success (3× bound rule)
    assert ahrs.metrics["success"] is False
    assert imu.metrics["success"] is False


def test_flow_alt_lqg_tracks_and_beats_ahrs(tmp_path: Path) -> None:
    """GPS-denied flow+alt proxy should nearly match GPS+IMU LQG and beat AHRS."""
    out = tmp_path / "runs"
    flow = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_flow_alt_lqg.yaml",
        output_root=out,
        run_mc=False,
    )
    ahrs = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_ahrs_lqg.yaml",
        output_root=out,
        run_mc=False,
    )
    assert flow.metrics["observer_id"] == "linear_kf"
    assert flow.metrics["success"] is True
    rmse = float(flow.metrics["rmse_position_m"])
    assert rmse < 0.15, f"flow+alt LQG RMSE {rmse}"
    assert rmse < float(ahrs.metrics["rmse_position_m"])


def test_flow_alt_kf_pid_tracks(tmp_path: Path) -> None:
    r = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_flow_alt_kf_pid.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    assert r.metrics["observer_id"] == "linear_kf"
    assert r.metrics["success"] is True
    assert float(r.metrics["rmse_position_m"]) < 0.4
