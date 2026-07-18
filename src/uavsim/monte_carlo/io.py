"""Monte Carlo artifact I/O (trial table + summary)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_trials_csv(path: Path, trials: list[dict[str, Any]]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not trials:
        path.write_text("", encoding="utf-8")
        return path

    # Union of keys, stable preferred order first
    preferred = [
        "trial_id",
        "base_seed",
        "mass_kg",
        "ixx_kg_m2",
        "iyy_kg_m2",
        "izz_kg_m2",
        "arm_length_m",
        "thrust_max_n",
        "rmse_position_m",
        "max_position_error_m",
        "final_position_error_m",
        "time_in_bounds_frac",
        "rmse_attitude_rad",
        "max_attitude_error_rad",
        "rmse_velocity_m_s",
        "control_effort_proxy",
        "peak_thrust_n",
        "peak_torque_nm",
        "success",
        "sim_success",
        "sim_message",
    ]
    keys: list[str] = []
    seen: set[str] = set()
    for k in preferred:
        if any(k in t for t in trials):
            keys.append(k)
            seen.add(k)
    for t in trials:
        for k in t:
            if k not in seen:
                keys.append(k)
                seen.add(k)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for row in trials:
            writer.writerow({k: row.get(k, "") for k in keys})
    return path


def write_trials_json(path: Path, trials: list[dict[str, Any]]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(trials, f, indent=2, sort_keys=True)
        f.write("\n")
    return path


def read_trials_csv(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, Any]] = []
        for raw in reader:
            row: dict[str, Any] = {}
            for k, v in raw.items():
                if v is None or v == "":
                    row[k] = None
                    continue
                if v in {"True", "False", "true", "false"}:
                    row[k] = v.lower() == "true"
                    continue
                try:
                    if "." in v or "e" in v.lower():
                        row[k] = float(v)
                    else:
                        row[k] = int(v)
                except ValueError:
                    row[k] = v
            rows.append(row)
        return rows
