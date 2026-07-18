"""Controller protocol and implementations (LQR + PID cascade)."""

from uavsim.control.base import Controller, saturate
from uavsim.control.export import (
    controller_from_artifact,
    export_from_run_dir,
    load_controller_artifact,
    write_controller_artifact,
)
from uavsim.control.factory import build_controller_from_mapping, controller_artifact_for
from uavsim.control.lqr import DEFAULT_Q_DIAG, DEFAULT_R_DIAG, LqrHoverController, design_lqr_hover
from uavsim.control.pid import DEFAULT_PID_GAINS, PidCascadeController, PidGains, design_pid_cascade

__all__ = [
    "DEFAULT_PID_GAINS",
    "DEFAULT_Q_DIAG",
    "DEFAULT_R_DIAG",
    "Controller",
    "LqrHoverController",
    "PidCascadeController",
    "PidGains",
    "build_controller_from_mapping",
    "controller_artifact_for",
    "controller_from_artifact",
    "design_lqr_hover",
    "design_pid_cascade",
    "export_from_run_dir",
    "load_controller_artifact",
    "saturate",
    "write_controller_artifact",
]
