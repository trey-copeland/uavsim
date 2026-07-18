"""Visualization and reports — consumers of run artifacts only."""

from uavsim.viz.compare import CompareResult, compare_runs
from uavsim.viz.report import ReportResult, generate_report

__all__ = ["CompareResult", "ReportResult", "compare_runs", "generate_report"]
