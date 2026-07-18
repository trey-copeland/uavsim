"""Controller protocol and implementations (LQR first)."""

from uavsim.control.base import Controller, saturate
from uavsim.control.lqr import DEFAULT_Q_DIAG, DEFAULT_R_DIAG, LqrHoverController, design_lqr_hover

__all__ = [
    "DEFAULT_Q_DIAG",
    "DEFAULT_R_DIAG",
    "Controller",
    "LqrHoverController",
    "design_lqr_hover",
    "saturate",
]
