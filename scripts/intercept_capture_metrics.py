#!/usr/bin/env python3
"""Compute min range to a scripted target mission for an intercept run dir."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# Allow running without install when repo root is cwd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uavsim.guidance.waypoints.backend import WaypointsGuidance  # noqa: E402
from uavsim.vehicles.params import default_vehicle  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", type=Path)
    p.add_argument(
        "--target-mission",
        type=Path,
        default=Path("configs/missions/tutorials/intercept_l0_target.yaml"),
    )
    p.add_argument("--capture-radius-m", type=float, default=1.0)
    args = p.parse_args()

    run = args.run_dir
    npz_path = run / "nominal" / "timeseries.npz"
    if not npz_path.is_file():
        # try nested
        candidates = list(run.glob("**/timeseries.npz"))
        if not candidates:
            print(f"no timeseries.npz under {run}", file=sys.stderr)
            return 1
        npz_path = candidates[0]

    data = np.load(npz_path)
    t = np.asarray(data["t"], dtype=float)
    x = np.asarray(data["x"], dtype=float)

    vehicle = default_vehicle()
    backend = WaypointsGuidance(method="interp", yaw_mode="from_waypoints", sample_dt_s=0.01)
    plan = backend.plan({"mission_file": str(args.target_mission)}, vehicle)
    p_t = np.vstack([plan.reference.evaluate(float(ti)).x_ref[0:3] for ti in t])
    range_m = np.linalg.norm(x[:, 0:3] - p_t, axis=1)
    i_min = int(np.argmin(range_m))
    min_range = float(range_m[i_min])
    success = bool(min_range <= args.capture_radius_m)

    # peak tilt from euler
    peak_tilt = float(np.max(np.maximum(np.abs(x[:, 3]), np.abs(x[:, 4]))))

    out = {
        "min_range_m": min_range,
        "time_of_min_range_s": float(t[i_min]),
        "capture_radius_m": args.capture_radius_m,
        "intercept_success": success,
        "peak_tilt_rad": peak_tilt,
        "peak_tilt_deg": float(np.rad2deg(peak_tilt)),
        "t_final_s": float(t[-1]),
        "target_mission": str(args.target_mission),
        "timeseries": str(npz_path),
    }
    print(json.dumps(out, indent=2))
    (npz_path.parent / "intercept_capture.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
