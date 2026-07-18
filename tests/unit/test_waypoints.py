"""Unit tests: waypoint mission I/O and trajectory generation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from uavsim.guidance.waypoints import (
    generate_interp_trajectory,
    generate_minsnap_trajectory,
    load_mission,
    select_waypoint_method,
)

ROOT = Path(__file__).resolve().parents[2]
MISSIONS = ROOT / "configs" / "missions"


def test_load_gentle_square() -> None:
    m = load_mission(MISSIONS / "gentle_square.yaml")
    assert m.name == "gentle_square"
    assert len(m.waypoints) == 5
    assert m.frame == "NED"
    assert m.time[0] == 0.0
    assert m.time[-1] == 20.0
    np.testing.assert_allclose(m.position[0], [0, 0, 1])


def test_load_rejects_non_increasing_times(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        """
name: bad
waypoints:
  - {time: 0, x: 0, y: 0, z: 1, yaw: 0}
  - {time: 0, x: 1, y: 0, z: 1, yaw: 0}
""",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_mission(p)


def test_interp_passes_near_waypoints() -> None:
    m = load_mission(MISSIONS / "gentle_square.yaml")
    ref = generate_interp_trajectory(m, dt_s=0.01, yaw_mode="constant")
    for t, pos in zip(m.time, m.position, strict=True):
        x = ref.evaluate(float(t)).x_ref
        np.testing.assert_allclose(x[0:3], pos, atol=0.05)


def test_minsnap_passes_near_waypoints() -> None:
    m = load_mission(MISSIONS / "gentle_square.yaml")
    ref, costs = generate_minsnap_trajectory(m, dt_s=0.01, yaw_mode="constant")
    assert all(c >= 0 for c in costs.values())
    for t, pos in zip(m.time, m.position, strict=True):
        x = ref.evaluate(float(t)).x_ref
        np.testing.assert_allclose(x[0:3], pos, atol=0.08)


def test_auto_selects_minsnap_for_gentle() -> None:
    m = load_mission(MISSIONS / "gentle_square.yaml")
    method, diag = select_waypoint_method(m)
    assert method == "minsnap"
    assert diag["min_segment_s"] >= 3.0


def test_auto_selects_interp_for_aggressive() -> None:
    m = load_mission(MISSIONS / "aggressive_square.yaml")
    method, diag = select_waypoint_method(m)
    assert method == "interp"
    assert diag["min_segment_s"] < 3.0


def test_hover_mission_interp_is_stationary() -> None:
    m = load_mission(MISSIONS / "hover_hold.yaml")
    ref = generate_interp_trajectory(m, dt_s=0.05)
    speeds = np.linalg.norm(ref.x_grid[:, 6:9], axis=1)
    assert float(np.max(speeds)) < 0.05
