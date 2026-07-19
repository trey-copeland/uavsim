"""Command-line interface for uavsim."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

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

    p_sim = sub.add_parser("simulate", help="Run a nominal closed-loop SIL study")
    p_sim.add_argument("study", type=Path, help="Path to study YAML")
    p_sim.add_argument(
        "--output",
        type=Path,
        default=Path("runs"),
        help="Root directory for run artifacts (default: runs/)",
    )

    p_study = sub.add_parser("study", help="Run a full study (nominal + optional Monte Carlo)")
    p_study.add_argument("study", type=Path, help="Path to study YAML")
    p_study.add_argument(
        "--output",
        type=Path,
        default=Path("runs"),
        help="Root directory for run artifacts (default: runs/)",
    )
    p_study.add_argument(
        "--mc",
        action="store_true",
        help="Force Monte Carlo even if study YAML has monte_carlo.enabled=false",
    )
    p_study.add_argument(
        "--no-mc",
        action="store_true",
        help="Skip Monte Carlo even if enabled in study YAML",
    )
    p_study.add_argument(
        "--n-trials",
        type=int,
        default=None,
        help="Override monte_carlo.n_trials for this run",
    )
    p_study.add_argument(
        "--backend",
        choices=["local", "docker"],
        default=None,
        help="MC execution backend (default: study config)",
    )
    p_study.add_argument(
        "--shards",
        type=int,
        default=None,
        help="Partition MC trials across N shards (default: study config)",
    )
    p_study.add_argument(
        "--image",
        type=str,
        default=None,
        help="Docker image for --backend docker (default: uavsim:local or UAVSIM_DOCKER_IMAGE)",
    )

    p_shard = sub.add_parser(
        "mc-shard",
        help="Run one MC shard worker (writes trials under --output)",
    )
    p_shard.add_argument("study", type=Path, help="Path to study YAML")
    p_shard.add_argument("--shard-id", type=int, required=True, help="Shard index [0, shards)")
    p_shard.add_argument("--shards", type=int, required=True, help="Total number of shards")
    p_shard.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory for this shard's trials.csv / shard_meta.json",
    )
    p_shard.add_argument("--n-trials", type=int, default=None, help="Override n_trials")

    p_merge = sub.add_parser(
        "mc-merge",
        help="Merge shard directories into trials table + summary",
    )
    p_merge.add_argument(
        "shard_dirs",
        nargs="+",
        type=Path,
        help="Shard directories each containing trials.csv",
    )
    p_merge.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for merged trials.csv + summary.json",
    )
    p_merge.add_argument(
        "--n-trials",
        type=int,
        default=None,
        help="Expected total trial count (fail if mismatch)",
    )
    p_merge.add_argument("--seed", type=int, default=None, help="base_seed for summary metadata")

    p_gallery = sub.add_parser(
        "gallery",
        help="Build React showcase (JSON + SPA) from runs or portfolio base case",
    )
    p_gallery.add_argument(
        "--base-case",
        action="store_true",
        help="Run portfolio base-case studies and write docs/showcase",
    )
    p_gallery.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: docs/showcase for --base-case)",
    )
    p_gallery.add_argument(
        "runs",
        nargs="*",
        type=Path,
        help="Run directories to include (ignored with --base-case)",
    )
    p_gallery.add_argument(
        "--n-mc-trials",
        type=int,
        default=12,
        help="MC trial count for base-case hover study (default 12)",
    )

    p_report = sub.add_parser(
        "report",
        help="Generate report/figures from a run directory (artifact consumer)",
    )
    p_report.add_argument("run_dir", type=Path, help="Path to run directory")
    p_report.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip static figure generation (markdown report only)",
    )
    p_report.add_argument(
        "--interactive",
        action="store_true",
        help="Write interactive Plotly flight_3d.html (requires plotly / --extra viz)",
    )

    p_export = sub.add_parser(
        "export-controller",
        help="Export a versioned controller artifact from a run directory",
    )
    p_export.add_argument(
        "source", type=Path, help="Run directory containing nominal/controller_artifact.yaml"
    )
    p_export.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output path for controller artifact YAML",
    )

    p_compare = sub.add_parser(
        "compare",
        help="Compare two run directories (metrics + overlays)",
    )
    p_compare.add_argument("run_a", type=Path, help="First run directory")
    p_compare.add_argument("run_b", type=Path, help="Second run directory")
    p_compare.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for compare artifacts (default: runs/compare_<a>_vs_<b>)",
    )
    p_compare.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip overlay figures",
    )
    p_compare.add_argument(
        "--interactive",
        action="store_true",
        help="Write dual-run Plotly compare_3d.html (requires plotly)",
    )

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


def _print_study_result(result: Any) -> None:
    status = "OK" if result.success else "FAILED"
    print(f"[{status}] run_dir={result.run_dir}")
    m = result.metrics
    if m:
        print(
            f"  rmse_pos={m.get('rmse_position_m', float('nan')):.4f} m  "
            f"max_pos={m.get('max_position_error_m', float('nan')):.4f} m  "
            f"success={m.get('success')}"
        )
    if result.mc_summary is not None:
        s = result.mc_summary
        print(
            f"  MC n={s.get('n_trials')}  "
            f"success={s.get('n_success')}/{s.get('n_trials')}  "
            f"fail_rate={s.get('failure_rate')}  "
            f"backend={result.backend}  shards={result.n_shards}"
        )
        rmse = (s.get("metrics") or {}).get("rmse_position_m") or {}
        if rmse:
            print(f"  MC rmse_pos mean={rmse.get('mean'):.4f}  p95={rmse.get('p95'):.4f} m")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "simulate":
        from uavsim.studies import run_nominal_study

        study_path = Path(args.study)
        if not study_path.is_file():
            print(f"Study file not found: {study_path}", file=sys.stderr)
            return 1
        result = run_nominal_study(study_path, output_root=args.output, run_mc=False)
        _print_study_result(result)
        return 0 if result.success else 1

    if args.command == "study":
        from uavsim.studies import run_study

        study_path = Path(args.study)
        if not study_path.is_file():
            print(f"Study file not found: {study_path}", file=sys.stderr)
            return 1
        if args.mc and args.no_mc:
            print("Cannot combine --mc and --no-mc", file=sys.stderr)
            return 1
        if args.n_trials is not None and args.n_trials < 1:
            print("--n-trials must be >= 1", file=sys.stderr)
            return 1
        if args.shards is not None and args.shards < 1:
            print("--shards must be >= 1", file=sys.stderr)
            return 1

        force_mc: bool | None = None
        if args.mc:
            force_mc = True
        elif args.no_mc:
            force_mc = False

        try:
            result = run_study(
                study_path,
                output_root=args.output,
                force_mc=force_mc,
                n_trials_override=args.n_trials,
                backend=args.backend,
                n_shards=args.shards,
                docker_image=args.image,
                repo_root=Path.cwd(),
            )
        except (NotImplementedError, ValueError, RuntimeError, FileNotFoundError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

        _print_study_result(result)
        return 0 if result.success else 1

    if args.command == "mc-shard":
        from uavsim.studies.pipeline import run_mc_shard_only

        study_path = Path(args.study)
        if not study_path.is_file():
            print(f"Study file not found: {study_path}", file=sys.stderr)
            return 1
        if args.shards < 1 or args.shard_id < 0 or args.shard_id >= args.shards:
            print("Invalid --shard-id / --shards", file=sys.stderr)
            return 1
        try:
            out = run_mc_shard_only(
                study_path,
                shard_id=args.shard_id,
                n_shards=args.shards,
                output_dir=args.output,
                n_trials_override=args.n_trials,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"[OK] shard_dir={out}")
        return 0

    if args.command == "mc-merge":
        from uavsim.monte_carlo import merge_shard_directories, write_merged_mc_artifacts

        try:
            trials, summary = merge_shard_directories(
                list(args.shard_dirs),
                expected_n_trials=args.n_trials,
                base_seed=args.seed,
            )
            write_merged_mc_artifacts(args.output, trials, summary)
        except (ValueError, FileNotFoundError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"[OK] merged n_trials={summary.get('n_trials')} → {args.output}")
        return 0

    if args.command == "gallery":
        from uavsim.viz.gallery import (
            build_gallery_document,
            generate_base_case_gallery,
            run_to_gallery_entry,
            write_gallery,
        )

        try:
            if args.base_case:
                path = generate_base_case_gallery(
                    repo_root=Path.cwd(),
                    out_dir=args.out,
                    n_mc_trials=args.n_mc_trials,
                )
                print(f"[OK] base-case gallery → {path}")
                print(f"  open {(args.out or Path('docs/showcase')) / 'index.html'}")
                return 0
            if not args.runs:
                print("Provide run dirs or --base-case", file=sys.stderr)
                return 1
            entries = []
            for rd in args.runs:
                if not Path(rd).is_dir():
                    print(f"Not a run directory: {rd}", file=sys.stderr)
                    return 1
                entries.append(run_to_gallery_entry(rd))
            doc = build_gallery_document(entries)
            out = Path(args.out or "docs/showcase")
            write_gallery(doc, out, copy_app=True)
            print(f"[OK] gallery → {out / 'data' / 'showcase.json'}")
            return 0
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if args.command == "report":
        from uavsim.viz import generate_report

        run_dir = Path(args.run_dir)
        if not run_dir.is_dir():
            print(f"Run directory not found: {run_dir}", file=sys.stderr)
            return 1
        try:
            rep = generate_report(
                run_dir,
                figures=not args.no_figures,
                interactive=args.interactive,
            )
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"[OK] {rep.message}")
        print(f"  summary={rep.summary_md}")
        for fig in rep.figures:
            print(f"  figure={fig}")
        if rep.interactive is not None:
            print(f"  interactive={rep.interactive}")
        return 0

    if args.command == "export-controller":
        from uavsim.control import export_from_run_dir

        source = Path(args.source)
        if not source.is_dir():
            print(f"Run directory not found: {source}", file=sys.stderr)
            return 1
        try:
            out = export_from_run_dir(source, args.out)
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"[OK] controller artifact → {out}")
        return 0

    if args.command == "compare":
        from uavsim.viz import compare_runs

        if not Path(args.run_a).is_dir() or not Path(args.run_b).is_dir():
            print("Both run directories must exist", file=sys.stderr)
            return 1
        try:
            cmp = compare_runs(
                args.run_a,
                args.run_b,
                output_dir=args.output,
                figures=not args.no_figures,
                interactive=args.interactive,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"[OK] compare → {cmp.output_dir}")
        print(f"  summary={cmp.summary_md}")
        print(f"  deltas={cmp.delta_json}")
        for fig in cmp.figures:
            print(f"  figure={fig}")
        if cmp.interactive is not None:
            print(f"  interactive={cmp.interactive}")
        return 0

    phase = {
        "hil": "Phase 7+",
    }.get(args.command, "future phase")
    return _not_implemented(args.command, phase)


if __name__ == "__main__":
    raise SystemExit(main())
