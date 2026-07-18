"""Command-line interface for uavsim."""

from __future__ import annotations

import argparse
import sys

from uavsim import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uavsim",
        description=("Quadrotor simulation and GNC analysis (SIL-first; HIL-ready architecture)."),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # Phase 1+: wired to library. Stubs document the intended surface.
    p_sim = sub.add_parser("simulate", help="Run a nominal closed-loop SIL study")
    p_sim.add_argument("study", nargs="?", help="Path to study YAML (Phase 1+)")

    p_study = sub.add_parser("study", help="Run a full study (e.g. Monte Carlo)")
    p_study.add_argument("study", nargs="?", help="Path to study YAML (Phase 3+)")

    p_report = sub.add_parser("report", help="Generate report/figures from a run directory")
    p_report.add_argument("run_dir", nargs="?", help="Path to run directory (Phase 3+)")

    p_export = sub.add_parser(
        "export-controller",
        help="Export a versioned controller artifact from a run or design",
    )
    p_export.add_argument("source", nargs="?", help="Run dir or design path (Phase 5+)")

    p_compare = sub.add_parser(
        "compare",
        help="Compare two run directories (metrics + overlays)",
    )
    p_compare.add_argument("run_a", nargs="?", help="First run directory (Phase 5+)")
    p_compare.add_argument("run_b", nargs="?", help="Second run directory (Phase 5+)")

    p_hil = sub.add_parser("hil", help="Hardware-in-the-loop session (post-core)")
    p_hil.add_argument("study", nargs="?", help="Path to study YAML (Phase 7+)")

    return parser


def _not_implemented(command: str, phase_hint: str) -> int:
    print(
        f"uavsim {command}: not implemented yet ({phase_hint}).\n"
        "See ROADMAP.md for sequencing and docs/ARCHITECTURE.md for design.",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    phase = {
        "simulate": "Phase 1+",
        "study": "Phase 3+",
        "report": "Phase 3+",
        "export-controller": "Phase 5+",
        "compare": "Phase 5+",
        "hil": "Phase 7+",
    }.get(args.command, "future phase")

    return _not_implemented(args.command, phase)


if __name__ == "__main__":
    raise SystemExit(main())
