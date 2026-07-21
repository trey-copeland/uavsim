"""Terminal progress for Monte Carlo (no third-party deps)."""

from __future__ import annotations

import sys
from typing import Any, TextIO


def _bar(frac: float, width: int = 28) -> str:
    frac = max(0.0, min(1.0, float(frac)))
    filled = int(round(width * frac))
    return "█" * filled + "░" * (width - filled)


class McProgressBar:
    """
    Single-line progress bar with optional global offset (for sequential shards).

    When shards run **sequentially in one process**, share one bar and pass
    ``completed_offset`` so the bar reflects study-wide progress.

    Parallel shard workers (separate processes) each get their own bar labeled
    with ``shard_id``; there is no shared TTY state across processes.
    """

    def __init__(
        self,
        total: int,
        *,
        label: str = "MC",
        width: int = 28,
        stream: TextIO | None = None,
        completed_offset: int = 0,
        shard_id: int | None = None,
        n_shards: int = 1,
    ) -> None:
        self.total = max(int(total), 1)
        self.label = label
        self.width = width
        self.stream = stream or sys.stdout
        self.completed_offset = int(completed_offset)
        self.shard_id = shard_id
        self.n_shards = max(int(n_shards), 1)
        self._n_ok = 0
        self._n_fail = 0
        self._finished = False

    def __call__(self, completed: int, total: int, trial_id: int, row: dict[str, Any]) -> None:
        """progress_fn compatible: completed/total are **within this run_monte_carlo**."""
        _ = total
        if row.get("success"):
            self._n_ok += 1
        else:
            self._n_fail += 1

        global_done = self.completed_offset + int(completed)
        frac = global_done / self.total
        pct = 100.0 * frac
        rmse = row.get("rmse_position_m")
        if rmse is not None:
            try:
                rmse_s = f"{float(rmse):.3f}"
            except (TypeError, ValueError):
                rmse_s = "—"
        else:
            rmse_s = "—"
        ok = "✓" if row.get("success") else "✗"
        shard = ""
        if self.n_shards > 1 and self.shard_id is not None:
            shard = f" shard {self.shard_id + 1}/{self.n_shards}"

        body = (
            f"[{self.label}] |{_bar(frac, self.width)}| "
            f"{global_done}/{self.total} {pct:5.1f}%{shard}  "
            f"ok={self._n_ok} fail={self._n_fail}  "
            f"last id={trial_id} {ok} rmse={rmse_s} m"
        )
        # In-place on real TTYs; line-per-trial when piped/captured
        if self.stream.isatty():
            self.stream.write("\r" + body)
        else:
            self.stream.write(body + "\n")
        self.stream.flush()
        if global_done >= self.total:
            self.finish()

    def finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        if self.stream.isatty():
            self.stream.write("\n")
            self.stream.flush()
