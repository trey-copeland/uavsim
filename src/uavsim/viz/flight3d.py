"""Interactive Plotly 3D flight view (V1, V2, V7) — optional dependency."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from uavsim.viz.loaders import (
    RunArtifacts,
    body_axes_ned,
    interpolate_ref_at,
    ned_to_plot,
)


def plotly_available() -> bool:
    try:
        import plotly  # noqa: F401

        return True
    except ImportError:
        return False


def write_flight_html(
    art: RunArtifacts,
    out_path: Path | None = None,
    *,
    max_frames: int = 80,
) -> Path:
    """V1/V7: interactive HTML with playback, trail, vectors, HUD annotations."""
    if not plotly_available():
        msg = "plotly is required for --interactive (uv sync --extra viz)"
        raise ImportError(msg)
    if art.t is None or art.x is None or art.u is None:
        msg = "Run has no nominal timeseries; cannot build flight_3d.html"
        raise FileNotFoundError(msg)

    import plotly.graph_objects as go

    out_path = out_path or (art.run_dir / "figures" / "flight_3d.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    t, x, u = art.t, art.x, art.u
    n = t.size
    step = max(1, n // max_frames)
    idx = np.arange(0, n, step)
    if idx[-1] != n - 1:
        idx = np.append(idx, n - 1)

    path = ned_to_plot(x[:, 0:3])
    ref_path = None
    if art.x_ref is not None:
        ref_path = ned_to_plot(art.x_ref[:, 0:3])

    # Scale arrows from path extent
    extent = float(np.max(np.ptp(path, axis=0))) if path.size else 1.0
    extent = max(extent, 0.5)
    v_scale = 0.25 * extent / max(float(np.max(np.linalg.norm(x[:, 6:9], axis=1))), 0.1)
    if art.t_ref is not None and art.x_ref is not None:
        e_stack = np.vstack(
            [x[i, 0:3] - interpolate_ref_at(art.t_ref, art.x_ref, float(t[i]))[0:3] for i in idx]
        )
        e_peak = float(np.max(np.linalg.norm(e_stack, axis=1)))
    else:
        e_peak = float(np.max(np.linalg.norm(x[:, 0:3] - x[0:1, 0:3], axis=1)))
    e_scale = 0.4 * extent / max(e_peak, 0.05)
    thrust_scale = 0.3 * extent

    def frame_traces(i: int) -> list:
        p = path[i]
        vel = x[i, 6:9]
        vel_plot = np.array([vel[0], vel[1], -vel[2]]) * v_scale
        traces = [
            go.Scatter3d(
                x=path[: i + 1, 0],
                y=path[: i + 1, 1],
                z=path[: i + 1, 2],
                mode="lines",
                line={"width": 4, "color": "royalblue"},
                name="trail",
            ),
            go.Scatter3d(
                x=[p[0]],
                y=[p[1]],
                z=[p[2]],
                mode="markers",
                marker={"size": 5, "color": "black"},
                name="vehicle",
            ),
        ]
        if ref_path is not None:
            traces.insert(
                0,
                go.Scatter3d(
                    x=ref_path[:, 0],
                    y=ref_path[:, 1],
                    z=ref_path[:, 2],
                    mode="lines",
                    line={"width": 2, "color": "orange", "dash": "dash"},
                    name="reference",
                    opacity=0.7,
                ),
            )
        # velocity
        traces.append(
            go.Cone(
                x=[p[0]],
                y=[p[1]],
                z=[p[2]],
                u=[vel_plot[0]],
                v=[vel_plot[1]],
                w=[vel_plot[2]],
                colorscale=[[0, "green"], [1, "green"]],
                showscale=False,
                sizemode="absolute",
                sizeref=max(float(np.linalg.norm(vel_plot)), 1e-3),
                name="velocity",
                anchor="tail",
            )
        )
        # position error
        if art.t_ref is not None and art.x_ref is not None:
            xref = interpolate_ref_at(art.t_ref, art.x_ref, float(t[i]))
            e = x[i, 0:3] - xref[0:3]
            e_plot = np.array([e[0], e[1], -e[2]]) * e_scale
            traces.append(
                go.Scatter3d(
                    x=[p[0], p[0] + e_plot[0]],
                    y=[p[1], p[1] + e_plot[1]],
                    z=[p[2], p[2] + e_plot[2]],
                    mode="lines+markers",
                    line={"width": 6, "color": "crimson"},
                    marker={"size": 2},
                    name="pos error",
                )
            )
        # thrust along -body z in NED → plot frame
        r = body_axes_ned(x[i, 3:6])
        thrust_ned = -r[:, 2] * float(u[i, 0])  # direction * F
        thr_plot = np.array([thrust_ned[0], thrust_ned[1], -thrust_ned[2]])
        thr_n = np.linalg.norm(thr_plot)
        if thr_n > 1e-9:
            f_scale = float(u[i, 0]) / max(float(np.max(u[:, 0])), 1e-6)
            thr_plot = thr_plot / thr_n * thrust_scale * f_scale
        traces.append(
            go.Scatter3d(
                x=[p[0], p[0] + thr_plot[0]],
                y=[p[1], p[1] + thr_plot[1]],
                z=[p[2], p[2] + thr_plot[2]],
                mode="lines",
                line={"width": 5, "color": "purple"},
                name="thrust",
            )
        )
        # body triad
        ax_scale = 0.2 * extent
        for col, color, name in (
            (0, "red", "body-x"),
            (1, "lime", "body-y"),
            (2, "cyan", "body-z"),
        ):
            v = r[:, col]
            vp = np.array([v[0], v[1], -v[2]]) * ax_scale
            traces.append(
                go.Scatter3d(
                    x=[p[0], p[0] + vp[0]],
                    y=[p[1], p[1] + vp[1]],
                    z=[p[2], p[2] + vp[2]],
                    mode="lines",
                    line={"width": 3, "color": color},
                    name=name,
                    showlegend=bool(i == int(idx[0])),
                )
            )
        return traces

    # HUD via title updates
    def title_for(i: int) -> str:
        vel = float(np.linalg.norm(x[i, 6:9]))
        f = float(u[i, 0])
        tau = float(np.linalg.norm(u[i, 1:4]))
        e_norm = 0.0
        if art.t_ref is not None and art.x_ref is not None:
            xref = interpolate_ref_at(art.t_ref, art.x_ref, float(t[i]))
            e_norm = float(np.linalg.norm(x[i, 0:3] - xref[0:3]))
        elif art.metrics:
            e_norm = float(np.linalg.norm(x[i, 0:3]))
        att = np.rad2deg(x[i, 3:6])
        return (
            f"{art.study_id} | t={t[i]:.2f}s | "
            f"|e_p|={e_norm:.3f} m | |v|={vel:.3f} m/s | "
            f"F={f:.2f} N | |τ|={tau:.3f} N·m | "
            f"φθψ=({att[0]:.1f},{att[1]:.1f},{att[2]:.1f})°"
        )

    # Full path baseline figure
    frames = []
    for k, i in enumerate(idx):
        frames.append(
            go.Frame(
                data=frame_traces(int(i)),
                name=str(k),
                layout=go.Layout(title=title_for(int(i))),
            )
        )

    fig = go.Figure(
        data=frame_traces(int(idx[0])),
        frames=frames,
        layout=go.Layout(
            title=title_for(int(idx[0])),
            scene={
                "xaxis_title": "N [m]",
                "yaxis_title": "E [m]",
                "zaxis_title": "up [m]",
                "aspectmode": "data",
            },
            margin={"l": 0, "r": 0, "t": 60, "b": 0},
            updatemenus=[
                {
                    "type": "buttons",
                    "showactive": False,
                    "y": 0,
                    "x": 0.1,
                    "xanchor": "right",
                    "yanchor": "top",
                    "buttons": [
                        {
                            "label": "Play",
                            "method": "animate",
                            "args": [
                                None,
                                {
                                    "frame": {"duration": 50, "redraw": True},
                                    "fromcurrent": True,
                                    "transition": {"duration": 0},
                                },
                            ],
                        },
                        {
                            "label": "Pause",
                            "method": "animate",
                            "args": [
                                [None],
                                {
                                    "frame": {"duration": 0, "redraw": False},
                                    "mode": "immediate",
                                    "transition": {"duration": 0},
                                },
                            ],
                        },
                    ],
                }
            ],
            sliders=[
                {
                    "steps": [
                        {
                            "args": [
                                [str(k)],
                                {
                                    "frame": {"duration": 0, "redraw": True},
                                    "mode": "immediate",
                                },
                            ],
                            "label": f"{t[int(i)]:.2f}",
                            "method": "animate",
                        }
                        for k, i in enumerate(idx)
                    ],
                    "x": 0.1,
                    "len": 0.85,
                    "currentvalue": {"prefix": "t = ", "suffix": " s"},
                }
            ],
        ),
    )
    fig.write_html(str(out_path), include_plotlyjs="cdn", full_html=True)
    return out_path


def write_compare_flight_html(
    art_a: RunArtifacts,
    art_b: RunArtifacts,
    out_path: Path,
    *,
    max_frames: int = 60,
) -> Path:
    """V2: dual trails + two vehicle markers."""
    if not plotly_available():
        msg = "plotly is required for interactive compare (uv sync --extra viz)"
        raise ImportError(msg)
    if art_a.t is None or art_a.x is None or art_b.t is None or art_b.x is None:
        msg = "Both runs need nominal timeseries for compare_3d.html"
        raise FileNotFoundError(msg)

    import plotly.graph_objects as go

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pa = ned_to_plot(art_a.x[:, 0:3])
    pb = ned_to_plot(art_b.x[:, 0:3])
    ta, tb = art_a.t, art_b.t
    # Common time samples from A
    n = ta.size
    step = max(1, n // max_frames)
    idx = np.arange(0, n, step)
    if idx[-1] != n - 1:
        idx = np.append(idx, n - 1)

    def xb_at(t: float) -> np.ndarray:
        j = int(np.argmin(np.abs(tb - t)))
        return pb[j]

    def frame_data(i: int) -> list:
        ti = float(ta[i])
        pbi = xb_at(ti)
        return [
            go.Scatter3d(
                x=pa[: i + 1, 0],
                y=pa[: i + 1, 1],
                z=pa[: i + 1, 2],
                mode="lines",
                line={"width": 4, "color": "royalblue"},
                name=art_a.study_id,
            ),
            go.Scatter3d(
                x=pb[:, 0],
                y=pb[:, 1],
                z=pb[:, 2],
                mode="lines",
                line={"width": 3, "color": "darkorange", "dash": "dash"},
                name=art_b.study_id,
                opacity=0.7,
            ),
            go.Scatter3d(
                x=[pa[i, 0]],
                y=[pa[i, 1]],
                z=[pa[i, 2]],
                mode="markers",
                marker={"size": 5, "color": "blue"},
                name="A",
            ),
            go.Scatter3d(
                x=[pbi[0]],
                y=[pbi[1]],
                z=[pbi[2]],
                mode="markers",
                marker={"size": 5, "color": "orange"},
                name="B",
            ),
        ]

    frames = [
        go.Frame(
            data=frame_data(int(i)),
            name=str(k),
            layout=go.Layout(
                title=f"Compare {art_a.study_id} vs {art_b.study_id} | t={ta[int(i)]:.2f}s"
            ),
        )
        for k, i in enumerate(idx)
    ]

    fig = go.Figure(
        data=frame_data(int(idx[0])),
        frames=frames,
        layout=go.Layout(
            title=f"Compare {art_a.study_id} vs {art_b.study_id}",
            scene={
                "xaxis_title": "N [m]",
                "yaxis_title": "E [m]",
                "zaxis_title": "up [m]",
                "aspectmode": "data",
            },
            updatemenus=[
                {
                    "type": "buttons",
                    "buttons": [
                        {
                            "label": "Play",
                            "method": "animate",
                            "args": [
                                None,
                                {"frame": {"duration": 50, "redraw": True}, "fromcurrent": True},
                            ],
                        },
                        {
                            "label": "Pause",
                            "method": "animate",
                            "args": [[None], {"mode": "immediate"}],
                        },
                    ],
                }
            ],
            sliders=[
                {
                    "steps": [
                        {
                            "args": [[str(k)], {"frame": {"duration": 0}, "mode": "immediate"}],
                            "label": f"{ta[int(i)]:.2f}",
                            "method": "animate",
                        }
                        for k, i in enumerate(idx)
                    ]
                }
            ],
        ),
    )
    fig.write_html(str(out_path), include_plotlyjs="cdn", full_html=True)
    return out_path
