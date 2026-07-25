"""Visualization and reports — consumers of run artifacts only."""

from uavsim.viz.compare import CompareResult, compare_runs
from uavsim.viz.gallery import generate_base_case_gallery, write_gallery
from uavsim.viz.loaders import RunArtifacts, load_run
from uavsim.viz.report import ReportResult, generate_report
from uavsim.viz.stack import build_stack_from_run_dir, build_stack_from_study_mapping

__all__ = [
    "CompareResult",
    "ReportResult",
    "RunArtifacts",
    "build_stack_from_run_dir",
    "build_stack_from_study_mapping",
    "compare_runs",
    "generate_base_case_gallery",
    "generate_report",
    "load_run",
    "write_gallery",
]
