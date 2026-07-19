"""Report / figure generation as a pure consumer of run directories."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from uavsim.results import write_text_report
from uavsim.viz.loaders import load_run
from uavsim.viz.static_plots import write_static_figures


@dataclass
class ReportResult:
    run_dir: Path
    summary_md: Path
    figures: list[Path] = field(default_factory=list)
    interactive: Path | None = None
    message: str = ""


def generate_report(
    run_dir: str | Path,
    *,
    figures: bool = True,
    interactive: bool = False,
) -> ReportResult:
    """
    Rebuild ``reports/summary.md`` from artifacts; optionally static + interactive figures.

    Does not re-run simulation. Static figures need matplotlib; interactive needs plotly.
    """
    run_dir = Path(run_dir)
    art = load_run(run_dir)

    (run_dir / "reports").mkdir(exist_ok=True)
    summary_md = write_text_report(
        run_dir,
        art.metrics,
        art.study_id,
        mc_summary=art.mc_summary,
        feasibility=art.feasibility,
    )

    fig_paths: list[Path] = []
    interactive_path: Path | None = None
    parts: list[str] = ["report written"]

    if figures:
        try:
            fig_paths = write_static_figures(art)
            if fig_paths:
                parts.append(f"{len(fig_paths)} static figure(s)")
            else:
                parts.append("no static figure data")
        except ImportError:
            parts.append("matplotlib missing (skip static figures)")

    if interactive:
        try:
            from uavsim.viz.flight3d import write_flight_html

            interactive_path = write_flight_html(art)
            fig_paths.append(interactive_path)
            parts.append(f"interactive={interactive_path}")
        except ImportError as exc:
            parts.append(str(exc))
        except FileNotFoundError as exc:
            parts.append(str(exc))

        if art.trials:
            try:
                from uavsim.viz.mc_plots import write_mc_dashboard_html

                dash = write_mc_dashboard_html(art)
                fig_paths.append(dash)
                sens = art.run_dir / "figures" / "mc_sensitivity.html"
                if sens.is_file():
                    fig_paths.append(sens)
                parts.append(f"mc_dashboard={dash}")
            except (ImportError, FileNotFoundError) as exc:
                parts.append(f"mc_dashboard skipped: {exc}")

    return ReportResult(
        run_dir=run_dir,
        summary_md=summary_md,
        figures=fig_paths,
        interactive=interactive_path,
        message="; ".join(parts),
    )
