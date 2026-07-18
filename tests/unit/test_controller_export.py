"""Controller export / round-trip load."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from uavsim.control import (
    controller_from_artifact,
    design_lqr_hover,
    design_pid_cascade,
    export_from_run_dir,
    load_controller_artifact,
    write_controller_artifact,
)
from uavsim.control.export import export_lqr_artifact, export_pid_artifact
from uavsim.interfaces import MeasurementBus
from uavsim.reference import ReferenceSample
from uavsim.vehicles.params import default_vehicle


def test_lqr_export_round_trip() -> None:
    vehicle = default_vehicle()
    ctrl = design_lqr_hover(vehicle)
    art = export_lqr_artifact(ctrl, vehicle=vehicle)
    loaded = controller_from_artifact(art)
    np.testing.assert_allclose(loaded.k, ctrl.k)
    np.testing.assert_allclose(loaded.u_hover, ctrl.u_hover)

    x = np.zeros(12)
    x[0] = 0.1
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    bus = MeasurementBus(t=0.0, x=x)
    u1 = ctrl.compute(0.0, bus, ref).u
    u2 = loaded.compute(0.0, bus, ref).u
    np.testing.assert_allclose(u1, u2)


def test_pid_export_round_trip() -> None:
    vehicle = default_vehicle()
    ctrl = design_pid_cascade(vehicle)
    art = export_pid_artifact(ctrl, vehicle=vehicle)
    loaded = controller_from_artifact(art)
    assert loaded.id == "pid_cascade"
    x = np.zeros(12)
    x[0] = 0.2
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    bus = MeasurementBus(t=0.0, x=x)
    u = loaded.compute(0.0, bus, ref).u
    assert u.shape == (4,)
    assert np.isfinite(u).all()


def test_export_from_run_dir(tmp_path: Path) -> None:
    vehicle = default_vehicle()
    ctrl = design_lqr_hover(vehicle)
    art = export_lqr_artifact(ctrl, vehicle=vehicle)
    run = tmp_path / "run"
    (run / "nominal").mkdir(parents=True)
    write_controller_artifact(run / "nominal" / "controller_artifact.yaml", art)
    out = tmp_path / "exported.yaml"
    export_from_run_dir(run, out)
    loaded = load_controller_artifact(out)
    assert loaded["controller_type"] == "lqr_hover"
    assert loaded["schema_version"] == 1
