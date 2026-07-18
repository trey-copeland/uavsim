"""Auto method selection for waypoint guidance (heritage segment policy)."""

from __future__ import annotations

from typing import Any

import numpy as np

from uavsim.guidance.waypoints.mission import WaypointMission

# Heritage empirical threshold: min-snap on short segments → huge accel
SAFE_SEGMENT_THRESHOLD_S = 3.0


def select_waypoint_method(mission: WaypointMission) -> tuple[str, dict[str, Any]]:
    """
    Choose ``interp`` vs ``minsnap`` from segment durations.

    Policy (documented, heritage-inspired):
    - If any segment is shorter than 3 s → ``interp`` (safer accel for short legs)
    - Else → ``minsnap``
    """
    durations = np.diff(mission.time)
    min_seg = float(np.min(durations))
    avg_seg = float(np.mean(durations))
    max_seg = float(np.max(durations))

    if min_seg < SAFE_SEGMENT_THRESHOLD_S:
        method = "interp"
        reason = (
            f"min segment {min_seg:.2f}s < {SAFE_SEGMENT_THRESHOLD_S:.1f}s threshold; "
            "using interp to avoid aggressive minsnap accel"
        )
    else:
        method = "minsnap"
        reason = (
            f"min segment {min_seg:.2f}s ≥ {SAFE_SEGMENT_THRESHOLD_S:.1f}s threshold; "
            "using minsnap for smoothness"
        )

    diagnostics = {
        "method": method,
        "method_reason": reason,
        "min_segment_s": min_seg,
        "avg_segment_s": avg_seg,
        "max_segment_s": max_seg,
        "threshold_s": SAFE_SEGMENT_THRESHOLD_S,
    }
    return method, diagnostics
