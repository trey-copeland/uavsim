"""Visualization and reports — consumers of run artifacts only."""

from uavsim.viz.compare import CompareResult, compare_runs
from uavsim.viz.gallery import generate_base_case_gallery, write_gallery
from uavsim.viz.loaders import RunArtifacts, load_run
from uavsim.viz.report import ReportResult, generate_report

__all__ = [
    "CompareResult",
    "ReportResult",
    "RunArtifacts",
    "compare_runs",
    "generate_base_case_gallery",
    "generate_report",
    "load_run",
    "write_gallery",
]
