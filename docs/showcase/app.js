/* uavsim results showcase — React 18 (no JSX build). Data: ./data/showcase.json */
(function () {
  const e = React.createElement;
  const { useState, useEffect, useMemo, useRef } = React;

  function roleBadge(role) {
    if (role && role.includes("pid")) return e("span", { className: "badge pid" }, "PID");
    if (role && role.includes("mc")) return e("span", { className: "badge mc" }, "MC");
    if (role && role.includes("lqr")) return e("span", { className: "badge lqr" }, "LQR");
    return e("span", { className: "badge" }, role || "run");
  }

  function fmt(x, digits) {
    if (x === true) return "true";
    if (x === false) return "false";
    if (x === null || x === undefined) return "—";
    if (typeof x === "number" && Number.isFinite(x)) return x.toFixed(digits ?? 4);
    return String(x);
  }

  /**
   * Fit a viewing box to path geometry (meters, plot frame N/E/up).
   *
   * Horizontal extents drive the frame; vertical gets enough thickness to
   * avoid a paper-thin slab without turning a 2 m square into a huge empty cube.
   */
  function fitSceneBounds(plotArrays) {
    const xs = [];
    const ys = [];
    const zs = [];
    (plotArrays || []).forEach(function (arr) {
      if (!arr) return;
      for (let k = 0; k < arr.length; k++) {
        xs.push(+arr[k][0]);
        ys.push(+arr[k][1]);
        zs.push(+arr[k][2]);
      }
    });
    function lohi(a, minSpan) {
      if (!a.length) return { lo: -minSpan / 2, hi: minSpan / 2, mid: 0, span: minSpan };
      let lo = Math.min.apply(null, a);
      let hi = Math.max.apply(null, a);
      if (!Number.isFinite(lo) || !Number.isFinite(hi)) {
        return { lo: -minSpan / 2, hi: minSpan / 2, mid: 0, span: minSpan };
      }
      let span = hi - lo;
      if (span < minSpan) {
        const mid = 0.5 * (lo + hi);
        lo = mid - minSpan / 2;
        hi = mid + minSpan / 2;
        span = minSpan;
      }
      return { lo: lo, hi: hi, mid: 0.5 * (lo + hi), span: span };
    }

    const px = lohi(xs, 1.0);
    const py = lohi(ys, 1.0);
    const pz = lohi(zs, 0.25);
    const hSpan = Math.max(px.span, py.span, 1.0);
    // Vertical window: real thickness, but at least ~40% of horizontal so the path is readable
    const vSpan = Math.max(pz.span, 0.4 * hSpan, 0.8);
    const padH = 0.22 * hSpan;
    const padV = 0.15 * vSpan;

    const xMid = px.mid;
    const yMid = py.mid;
    const zMid = pz.mid;
    // Square the horizontal FOV so N/E aren't stretched
    const halfH = 0.5 * hSpan + padH;
    const halfV = 0.5 * vSpan + padV;

    return {
      x: [xMid - halfH, xMid + halfH],
      y: [yMid - halfH, yMid + halfH],
      z: [zMid - halfV, zMid + halfV],
      halfH: halfH,
      halfV: halfV,
      // For aspectratio (relative display sizes)
      ar: {
        x: 1,
        y: 1,
        z: Math.max(0.35, Math.min(1.0, halfV / halfH)),
      },
    };
  }

  function sceneBoundsFromPlots(plotArrays) {
    return fitSceneBounds(plotArrays);
  }

  /** Invisible corners so Plotly's data-driven camera always "sees" the full FOV. */
  function cornerTrace(bounds) {
    const xr = bounds.x;
    const yr = bounds.y;
    const zr = bounds.z;
    const xs = [];
    const ys = [];
    const zs = [];
    for (let ix = 0; ix < 2; ix++) {
      for (let iy = 0; iy < 2; iy++) {
        for (let iz = 0; iz < 2; iz++) {
          xs.push(xr[ix]);
          ys.push(yr[iy]);
          zs.push(zr[iz]);
        }
      }
    }
    return {
      type: "scatter3d",
      mode: "markers",
      x: xs,
      y: ys,
      z: zs,
      marker: { size: 1, opacity: 0, color: "#000" },
      name: "_bounds",
      showlegend: false,
      hoverinfo: "skip",
    };
  }

  function PlotDiv({ id, data, layout, config }) {
    const ref = useRef(null);
    useEffect(() => {
      if (!ref.current || !window.Plotly) return;
      Plotly.react(
        ref.current,
        data,
        layout,
        config || { responsive: true, displayModeBar: true }
      );
    }, [id, data, layout]);
    useEffect(() => {
      return () => {
        if (ref.current && window.Plotly) Plotly.purge(ref.current);
      };
    }, [id]);
    return e("div", { className: "plot", ref, id });
  }

  /**
   * Flight 3D: newPlot once per run (fixed FOV), restyle-only on scrub.
   */
  function Flight3DView({ runId, ts, frame }) {
    const ref = useRef(null);
    const ready = useRef(false);
    const boundsRef = useRef(null);
    const idxRef = useRef({ trail: 1, veh: 2, vel: 3 });

    function applyFrame(i) {
      if (!ref.current || !window.Plotly || !ready.current || !ts || !ts.pos_plot) return;
      const pos = ts.pos_plot;
      const n = pos.length;
      const ii = Math.max(0, Math.min(i, n - 1));
      const trail = pos.slice(0, ii + 1);
      const bounds = boundsRef.current;
      const halfH = bounds ? bounds.halfH : 1;
      const v = ts.vel_ned[ii];
      const vNorm = Math.hypot(v[0], v[1], v[2]) || 1;
      const vLen = 0.12 * 2 * halfH;
      const px = pos[ii][0];
      const py = pos[ii][1];
      const pz = pos[ii][2];
      const ix = idxRef.current;

      Plotly.restyle(
        ref.current,
        {
          x: [
            trail.map(function (p) {
              return p[0];
            }),
            [px],
            [px, px + (v[0] / vNorm) * vLen],
          ],
          y: [
            trail.map(function (p) {
              return p[1];
            }),
            [py],
            [py, py + (v[1] / vNorm) * vLen],
          ],
          z: [
            trail.map(function (p) {
              return p[2];
            }),
            [pz],
            [pz, pz - (v[2] / vNorm) * vLen],
          ],
        },
        [ix.trail, ix.veh, ix.vel]
      );
    }

    // Full (re)build when run changes
    useEffect(() => {
      if (!ref.current || !window.Plotly || !ts || !ts.pos_plot) return;
      const pos = ts.pos_plot;
      const bounds = fitSceneBounds([pos, ts.ref_plot]);
      boundsRef.current = bounds;
      ready.current = false;

      const axis = function (title, range) {
        return {
          title: title,
          range: range.slice(),
          autorange: false,
          gridcolor: "#2d3a4d",
          zerolinecolor: "#3a4a60",
          showbackground: true,
          backgroundcolor: "rgba(12,16,24,0.9)",
        };
      };

      const traces = [];
      // 0: invisible FOV corners (forces initial camera to the full box)
      traces.push(cornerTrace(bounds));
      // 1: full path
      traces.push({
        type: "scatter3d",
        mode: "lines",
        x: pos.map(function (p) {
          return p[0];
        }),
        y: pos.map(function (p) {
          return p[1];
        }),
        z: pos.map(function (p) {
          return p[2];
        }),
        line: { color: "rgba(100,140,200,0.45)", width: 4 },
        name: "path",
        hoverinfo: "skip",
      });
      let next = 2;
      if (ts.ref_plot) {
        traces.push({
          type: "scatter3d",
          mode: "lines",
          x: ts.ref_plot.map(function (p) {
            return p[0];
          }),
          y: ts.ref_plot.map(function (p) {
            return p[1];
          }),
          z: ts.ref_plot.map(function (p) {
            return p[2];
          }),
          line: { color: "orange", width: 2, dash: "dash" },
          name: "reference",
          opacity: 0.75,
          hoverinfo: "skip",
        });
        next = 3;
      }
      idxRef.current = { trail: next, veh: next + 1, vel: next + 2 };
      traces.push({
        type: "scatter3d",
        mode: "lines",
        x: [pos[0][0]],
        y: [pos[0][1]],
        z: [pos[0][2]],
        line: { color: "#3d9cf0", width: 6 },
        name: "trail",
      });
      traces.push({
        type: "scatter3d",
        mode: "markers",
        x: [pos[0][0]],
        y: [pos[0][1]],
        z: [pos[0][2]],
        marker: { size: 5, color: "#e7ecf3" },
        name: "vehicle",
      });
      traces.push({
        type: "scatter3d",
        mode: "lines",
        x: [pos[0][0], pos[0][0]],
        y: [pos[0][1], pos[0][1]],
        z: [pos[0][2], pos[0][2]],
        line: { color: "#3ecf8e", width: 6 },
        name: "velocity",
      });

      const layout = {
        paper_bgcolor: "#0c1018",
        plot_bgcolor: "#0c1018",
        font: { color: "#e7ecf3", size: 11 },
        margin: { l: 0, r: 0, t: 10, b: 0 },
        uirevision: "flight-static-" + runId,
        scene: {
          xaxis: axis("N [m]", bounds.x),
          yaxis: axis("E [m]", bounds.y),
          zaxis: axis("up [m]", bounds.z),
          aspectmode: "manual",
          aspectratio: bounds.ar,
          bgcolor: "#0c1018",
          // Farther isometric-ish eye so the whole FOV fits on first paint
          camera: {
            eye: { x: 2.4, y: 2.4, z: 1.55 },
            center: { x: 0, y: 0, z: 0 },
            up: { x: 0, y: 0, z: 1 },
          },
        },
        showlegend: true,
        legend: { orientation: "h", y: 1.08 },
        height: 520,
      };

      Plotly.newPlot(ref.current, traces, layout, {
        responsive: true,
        displayModeBar: true,
      }).then(function () {
        ready.current = true;
        applyFrame(0);
      });

      return function () {
        ready.current = false;
        if (ref.current && window.Plotly) Plotly.purge(ref.current);
      };
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [runId, ts]);

    // Scrub: restyle only
    useEffect(() => {
      applyFrame(frame);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [frame, runId]);

    return e("div", { className: "plot", ref: ref, id: "flight3d-" + runId });
  }

  function Overview({ doc, onSelect }) {
    const runs = doc.runs || [];
    return e(
      "div",
      { className: "grid cols-3" },
      runs.map((r) => {
        const m = r.metrics || {};
        return e(
          "div",
          { key: r.id, className: "card", style: { cursor: "pointer" }, onClick: () => onSelect(r.id) },
          e("h3", null, r.label, " ", roleBadge(r.role)),
          e("div", { className: "stat" }, fmt(m.rmse_position_m), e("span", null, "RMSE position [m]")),
          e(
            "p",
            { style: { margin: "0.5rem 0 0", fontSize: "0.85rem", color: "var(--muted)" } },
            "max |e| ",
            fmt(m.max_position_error_m),
            " m · success ",
            e("span", { className: m.success ? "ok" : "fail" }, String(m.success))
          ),
          r.mc
            ? e(
                "p",
                { style: { margin: "0.35rem 0 0", fontSize: "0.8rem", color: "var(--muted)" } },
                "MC N=",
                r.mc.n_trials,
                " · fail rate ",
                fmt((r.mc.summary || {}).failure_rate, 3)
              )
            : null
        );
      }),
      e(
        "div",
        { className: "card", style: { gridColumn: "1 / -1" } },
        e("h2", null, "About these runs"),
        e(
          "p",
          { style: { margin: 0, color: "var(--muted)", fontSize: "0.9rem" } },
          doc.description ||
            "LQR and PID on a gentle square, plus hover Monte Carlo under mass and inertia uncertainty."
        )
      )
    );
  }

  function FlightTab({ run }) {
    const ts = run.timeseries;
    const [frame, setFrame] = useState(0);
    // Reset scrub when switching runs (new id).
    useEffect(() => {
      setFrame(0);
    }, [run && run.id]);

    if (!ts) return e("div", { className: "card" }, "No timeseries for this run.");

    const n = ts.t.length;
    const i = Math.min(frame, n - 1);
    const v = ts.vel_ned[i];
    const u = ts.u[i];
    const hud =
      "t=" +
      fmt(ts.t[i], 2) +
      "s | |v|=" +
      fmt(Math.hypot(v[0], v[1], v[2]), 3) +
      " m/s | F=" +
      fmt(u[0], 2) +
      " N | |τ|=" +
      fmt(Math.hypot(u[1], u[2], u[3]), 3) +
      " · φθψ=(" +
      fmt(ts.euler_deg[i][0], 1) +
      "," +
      fmt(ts.euler_deg[i][1], 1) +
      "," +
      fmt(ts.euler_deg[i][2], 1) +
      ")°";

    return e(
      "div",
      null,
      e(
        "div",
        { className: "row" },
        e("strong", null, run.label),
        roleBadge(run.role),
        e("label", null, "scrub "),
        e("input", {
          type: "range",
          min: 0,
          max: n - 1,
          value: i,
          onChange: (ev) => setFrame(Number(ev.target.value)),
          style: { width: "240px" },
        }),
        e("span", { style: { color: "var(--muted)", fontSize: "0.85rem" } }, hud)
      ),
      e("div", { className: "card" }, e(Flight3DView, { runId: run.id, ts: ts, frame: i })),
      e(
        "div",
        { className: "grid cols-1", style: { marginTop: "1rem" } },
        e("div", { className: "card" }, e(PlotDiv, {
          id: "pos_ts",
          data: [
            { x: ts.t, y: ts.pos_ned.map((p) => p[0]), name: "N", type: "scatter", mode: "lines" },
            { x: ts.t, y: ts.pos_ned.map((p) => p[1]), name: "E", type: "scatter", mode: "lines" },
            { x: ts.t, y: ts.pos_ned.map((p) => p[2]), name: "D", type: "scatter", mode: "lines" },
            {
              x: [ts.t[i], ts.t[i]],
              y: [
                Math.min.apply(
                  null,
                  ts.pos_ned.map(function (p) {
                    return Math.min(p[0], p[1], p[2]);
                  })
                ),
                Math.max.apply(
                  null,
                  ts.pos_ned.map(function (p) {
                    return Math.max(p[0], p[1], p[2]);
                  })
                ),
              ],
              mode: "lines",
              line: { color: "white", dash: "dot", width: 1 },
              showlegend: false,
              hoverinfo: "skip",
            },
          ],
          layout: {
            title: "Position NED",
            paper_bgcolor: "#0c1018",
            plot_bgcolor: "#0c1018",
            font: { color: "#e7ecf3", size: 11 },
            margin: { t: 40, r: 10, b: 40, l: 50 },
            height: 260,
            legend: { orientation: "h" },
            xaxis: { title: "t [s]", gridcolor: "#2d3a4d", zeroline: false },
            yaxis: { title: "m", gridcolor: "#2d3a4d", zeroline: false },
          },
        })),
        // Stacked force / torque — magnitudes differ by ~10³
        e("div", { className: "card" }, e(PlotDiv, {
          id: "u_ts_stacked",
          data: [
            {
              x: ts.t,
              y: ts.u.map(function (uu) {
                return uu[0];
              }),
              name: "F",
              type: "scatter",
              mode: "lines",
              line: { color: "#3d9cf0" },
              yaxis: "y",
            },
            {
              x: [ts.t[i], ts.t[i]],
              y: [
                Math.min.apply(
                  null,
                  ts.u.map(function (uu) {
                    return uu[0];
                  })
                ),
                Math.max.apply(
                  null,
                  ts.u.map(function (uu) {
                    return uu[0];
                  })
                ),
              ],
              mode: "lines",
              line: { color: "rgba(255,255,255,0.5)", dash: "dot", width: 1 },
              showlegend: false,
              hoverinfo: "skip",
              yaxis: "y",
            },
            {
              x: ts.t,
              y: ts.u.map(function (uu) {
                return uu[1];
              }),
              name: "τφ",
              type: "scatter",
              mode: "lines",
              line: { color: "#e6b450" },
              yaxis: "y2",
            },
            {
              x: ts.t,
              y: ts.u.map(function (uu) {
                return uu[2];
              }),
              name: "τθ",
              type: "scatter",
              mode: "lines",
              line: { color: "#3ecf8e" },
              yaxis: "y2",
            },
            {
              x: ts.t,
              y: ts.u.map(function (uu) {
                return uu[3];
              }),
              name: "τψ",
              type: "scatter",
              mode: "lines",
              line: { color: "#f07178" },
              yaxis: "y2",
            },
            {
              x: [ts.t[i], ts.t[i]],
              y: (function () {
                const tqs = ts.u.map(function (uu) {
                  return [uu[1], uu[2], uu[3]];
                });
                let lo = Infinity;
                let hi = -Infinity;
                for (let k = 0; k < tqs.length; k++) {
                  for (let j = 0; j < 3; j++) {
                    lo = Math.min(lo, tqs[k][j]);
                    hi = Math.max(hi, tqs[k][j]);
                  }
                }
                if (!Number.isFinite(lo) || lo === hi) {
                  lo = -0.01;
                  hi = 0.01;
                }
                return [lo, hi];
              })(),
              mode: "lines",
              line: { color: "rgba(255,255,255,0.5)", dash: "dot", width: 1 },
              showlegend: false,
              hoverinfo: "skip",
              yaxis: "y2",
            },
          ],
          layout: {
            title: "Control u(t) — force & torques stacked",
            paper_bgcolor: "#0c1018",
            plot_bgcolor: "#0c1018",
            font: { color: "#e7ecf3", size: 11 },
            margin: { t: 40, r: 20, b: 40, l: 55 },
            height: 380,
            legend: { orientation: "h", y: 1.12 },
            // Top: thrust [N]
            yaxis: {
              title: "F [N]",
              domain: [0.58, 1.0],
              gridcolor: "#2d3a4d",
              zeroline: false,
              titlefont: { size: 11 },
            },
            // Bottom: body torques [N·m]
            yaxis2: {
              title: "τ [N·m]",
              domain: [0.0, 0.48],
              gridcolor: "#2d3a4d",
              zeroline: true,
              zerolinecolor: "#3a4a60",
              titlefont: { size: 11 },
            },
            xaxis: {
              title: "t [s]",
              gridcolor: "#2d3a4d",
              zeroline: false,
              anchor: "y2",
            },
          },
        }))
      )
    );
  }

  function MetricsTab({ run }) {
    const m = run.metrics || {};
    const keys = Object.keys(m);
    return e(
      "div",
      { className: "grid cols-2" },
      e(
        "div",
        { className: "card" },
        e("h2", null, "Metrics — ", run.label),
        e(
          "table",
          { className: "metrics" },
          e("thead", null, e("tr", null, e("th", null, "metric"), e("th", null, "value"))),
          e(
            "tbody",
            null,
            keys.map((k) =>
              e("tr", { key: k }, e("td", null, k), e("td", null, fmt(m[k], 6)))
            )
          )
        )
      ),
      run.feasibility
        ? e(
            "div",
            { className: "card" },
            e("h2", null, "Feasibility"),
            e(
              "p",
              null,
              "ok: ",
              e("span", { className: run.feasibility.ok ? "ok" : "fail" }, String(run.feasibility.ok))
            ),
            (run.feasibility.issues || []).length
              ? e(
                  "ul",
                  { style: { fontSize: "0.85rem", color: "var(--muted)" } },
                  run.feasibility.issues.map((iss, idx) =>
                    e(
                      "li",
                      { key: idx },
                      "[",
                      iss.severity || "?",
                      "] ",
                      iss.code || "",
                      ": ",
                      iss.message || ""
                    )
                  )
                )
              : e("p", { style: { color: "var(--muted)" } }, "No issues reported.")
          )
        : null
    );
  }

  function McTab({ run }) {
    const mc = run.mc;
    if (!mc || !mc.trials || !mc.trials.length) {
      return e(
        "div",
        { className: "card" },
        "No Monte Carlo trials in this run. Open the Monte Carlo card from Overview."
      );
    }
    const trials = mc.trials;
    const col = (key) => trials.map((t) => t[key]).filter((x) => x != null && Number.isFinite(+x)).map(Number);
    const rmse = col("rmse_position_m");
    const att = col("rmse_attitude_rad").map((r) => (r * 180) / Math.PI);
    const s = [...rmse].sort((a, b) => a - b);
    const cdfY = s.map((_, i) => (i + 1) / s.length);
    const nShow = trials.length;
    const nAll = mc.n_trials || nShow;
    const sum = mc.summary || {};
    const nOk =
      sum.n_success != null
        ? sum.n_success
        : trials.filter((t) => t.success === true).length;
    const mPos = (sum.metrics || {}).rmse_position_m || {};
    const plotTheme = {
      paper_bgcolor: "#0c1018",
      plot_bgcolor: "#0c1018",
      font: { color: "#e7ecf3", size: 11 },
      margin: { t: 36, r: 12, b: 40, l: 48 },
    };
    const nbins = Math.max(12, Math.min(40, Math.floor(Math.sqrt(Math.max(rmse.length, 1)))));

    // Multi-metric distribution grid (heritage-style pack)
    const distSpecs = [
      { key: "rmse_position_m", title: "Position RMSE [m]", scale: 1 },
      { key: "rmse_attitude_rad", title: "Attitude RMSE [deg]", scale: 180 / Math.PI },
      { key: "max_position_error_m", title: "Max |e| [m]", scale: 1 },
      { key: "rmse_velocity_m_s", title: "Velocity RMSE [m/s]", scale: 1 },
      { key: "peak_thrust_n", title: "Peak thrust [N]", scale: 1 },
      { key: "control_effort_proxy", title: "Control effort", scale: 1 },
    ];
    const distGrid = {
      data: distSpecs.map((spec, i) => ({
        x: col(spec.key).map((v) => v * spec.scale),
        type: "histogram",
        nbinsx: nbins,
        marker: { color: "#5b9fd4", line: { color: "#111315", width: 0.35 } },
        xaxis: "x" + (i + 1),
        yaxis: "y" + (i + 1),
        name: spec.title,
        showlegend: false,
      })),
      layout: (function () {
        const L = {
          ...plotTheme,
          height: 440,
          title: { text: "Metric distributions (all trials in payload)", font: { size: 13 } },
          margin: { t: 48, r: 16, b: 36, l: 40 },
        };
        for (let i = 0; i < 6; i++) {
          const colI = i % 3;
          const rowI = Math.floor(i / 3);
          const x0 = 0.06 + colI * 0.32;
          const x1 = x0 + 0.26;
          const y0 = rowI === 0 ? 0.58 : 0.08;
          const y1 = rowI === 0 ? 0.95 : 0.45;
          L["xaxis" + (i + 1)] = {
            domain: [x0, x1],
            anchor: "y" + (i + 1),
            title: { text: distSpecs[i].title, font: { size: 10 } },
            gridcolor: "#2a2f36",
            zeroline: false,
            tickfont: { size: 9 },
          };
          L["yaxis" + (i + 1)] = {
            domain: [y0, y1],
            anchor: "x" + (i + 1),
            title: colI === 0 ? { text: "count", font: { size: 10 } } : undefined,
            gridcolor: "#2a2f36",
            tickfont: { size: 9 },
          };
        }
        return L;
      })(),
    };

    // Parameter sensitivity grid: params vs position RMSE + Ixx/Iyy vs attitude
    const sensPairs = [
      { x: "mass_kg", y: "rmse_position_m", xt: "mass [kg]", yt: "pos RMSE [m]", yScale: 1 },
      { x: "ixx_kg_m2", y: "rmse_position_m", xt: "Ixx [kg·m²]", yt: "pos RMSE [m]", yScale: 1 },
      { x: "iyy_kg_m2", y: "rmse_position_m", xt: "Iyy [kg·m²]", yt: "pos RMSE [m]", yScale: 1 },
      { x: "izz_kg_m2", y: "rmse_position_m", xt: "Izz [kg·m²]", yt: "pos RMSE [m]", yScale: 1 },
      { x: "arm_length_m", y: "rmse_position_m", xt: "arm [m]", yt: "pos RMSE [m]", yScale: 1 },
      {
        x: "iyy_kg_m2",
        y: "rmse_attitude_rad",
        xt: "Iyy [kg·m²]",
        yt: "att RMSE [deg]",
        yScale: 180 / Math.PI,
      },
    ];
    const sensGrid = {
      data: sensPairs.map((p, i) => {
        const xs = [];
        const ys = [];
        trials.forEach((t) => {
          const xv = t[p.x];
          const yv = t[p.y];
          if (xv == null || yv == null) return;
          if (!Number.isFinite(+xv) || !Number.isFinite(+yv)) return;
          xs.push(+xv);
          ys.push(+yv * p.yScale);
        });
        return {
          x: xs,
          y: ys,
          mode: "markers",
          type: "scatter",
          marker: { size: 5, color: "#e6b450", opacity: 0.65, line: { width: 0 } },
          xaxis: "x" + (i + 1),
          yaxis: "y" + (i + 1),
          showlegend: false,
        };
      }),
      layout: (function () {
        const L = {
          ...plotTheme,
          height: 440,
          title: { text: "Parameter sensitivity", font: { size: 13 } },
          margin: { t: 48, r: 16, b: 36, l: 48 },
        };
        for (let i = 0; i < sensPairs.length; i++) {
          const colI = i % 3;
          const rowI = Math.floor(i / 3);
          const x0 = 0.07 + colI * 0.32;
          const x1 = x0 + 0.26;
          const y0 = rowI === 0 ? 0.58 : 0.08;
          const y1 = rowI === 0 ? 0.95 : 0.45;
          L["xaxis" + (i + 1)] = {
            domain: [x0, x1],
            anchor: "y" + (i + 1),
            title: { text: sensPairs[i].xt, font: { size: 10 } },
            gridcolor: "#2a2f36",
            zeroline: false,
            tickfont: { size: 9 },
          };
          L["yaxis" + (i + 1)] = {
            domain: [y0, y1],
            anchor: "x" + (i + 1),
            title: { text: sensPairs[i].yt, font: { size: 10 } },
            gridcolor: "#2a2f36",
            tickfont: { size: 9 },
          };
        }
        return L;
      })(),
    };

    // Correlation bars (position RMSE vs params) from summary when present
    const corr =
      sum.correlations_vs_rmse_position ||
      (sum.correlations && sum.correlations.rmse_position_m) ||
      {};
    const corrKeys = ["mass_kg", "ixx_kg_m2", "iyy_kg_m2", "izz_kg_m2", "arm_length_m"].filter(
      (k) => corr[k] != null && Number.isFinite(+corr[k])
    );
    const corrVals = corrKeys.map((k) => +corr[k]);

    return e(
      "div",
      { className: "grid cols-2" },
      e(
        "div",
        { className: "card" },
        e("h2", null, "MC summary — ", run.label),
        e("div", { className: "stat" }, String(nAll), e("span", null, "trials")),
        e(
          "p",
          { style: { color: "var(--muted)", fontSize: "0.85rem" } },
          "success ",
          nOk,
          "/",
          nAll,
          nShow !== nAll ? " · plots use " + nShow + " trials" : "",
          " · fail rate ",
          fmt(sum.failure_rate, 3)
        ),
        mPos.mean != null
          ? e(
              "p",
              { style: { color: "var(--muted)", fontSize: "0.85rem", marginTop: "0.35rem" } },
              "pos RMSE mean ",
              fmt(mPos.mean, 4),
              " ± ",
              fmt(mPos.std, 4),
              " m · p95 ",
              fmt(mPos.p95, 4),
              " m"
            )
          : null,
        att.length
          ? e(
              "p",
              { style: { color: "var(--muted)", fontSize: "0.85rem" } },
              "att RMSE (payload) mean ",
              fmt(att.reduce((a, b) => a + b, 0) / att.length, 2),
              "°"
            )
          : null
      ),
      e("div", { className: "card" }, e(PlotDiv, {
        id: "mc_hist",
        data: [
          {
            x: rmse,
            type: "histogram",
            nbinsx: nbins,
            marker: { color: "#5b9fd4", line: { color: "#111315", width: 0.4 } },
          },
        ],
        layout: {
          ...plotTheme,
          title: "Position RMSE",
          height: 280,
          xaxis: { title: "RMSE [m]", gridcolor: "#2a2f36" },
          yaxis: { title: "count", gridcolor: "#2a2f36" },
        },
      })),
      e("div", { className: "card" }, e(PlotDiv, {
        id: "mc_cdf",
        data: [
          {
            x: s,
            y: cdfY,
            type: "scatter",
            mode: "lines",
            line: { shape: "hv", color: "#3ecf8e", width: 2 },
          },
        ],
        layout: {
          ...plotTheme,
          title: "Position RMSE CDF",
          height: 280,
          xaxis: { title: "RMSE [m]", gridcolor: "#2a2f36" },
          yaxis: { title: "CDF", gridcolor: "#2a2f36", range: [0, 1.02] },
        },
      })),
      corrKeys.length
        ? e("div", { className: "card" }, e(PlotDiv, {
            id: "mc_corr",
            data: [
              {
                y: corrKeys,
                x: corrVals,
                type: "bar",
                orientation: "h",
                marker: {
                  color: corrVals.map((v) => (v >= 0 ? "#f07178" : "#5b9fd4")),
                  line: { color: "#111315", width: 0.4 },
                },
              },
            ],
            layout: {
              ...plotTheme,
              title: "Pearson r vs position RMSE",
              height: 280,
              xaxis: { title: "r", range: [-1.05, 1.05], gridcolor: "#2a2f36", zeroline: true },
              yaxis: { automargin: true, tickfont: { size: 10 } },
              margin: { t: 40, r: 16, b: 40, l: 100 },
            },
          }))
        : e(
            "div",
            { className: "card" },
            e("h2", null, "Correlations"),
            e("p", { style: { color: "var(--muted)" } }, "No correlation summary in this run.")
          ),
      e(
        "div",
        { className: "card", style: { gridColumn: "1 / -1" } },
        e(PlotDiv, { id: "mc_dist_grid", data: distGrid.data, layout: distGrid.layout })
      ),
      e(
        "div",
        { className: "card", style: { gridColumn: "1 / -1" } },
        e(PlotDiv, { id: "mc_sens_grid", data: sensGrid.data, layout: sensGrid.layout })
      )
    );
  }

  function CompareTab({ doc }) {
    const cmp = doc.compare;
    if (!cmp) return e("div", { className: "card" }, "No compare pair in this gallery.");
    const a = (doc.runs || []).find((r) => r.id === cmp.a);
    const b = (doc.runs || []).find((r) => r.id === cmp.b);
    if (!a || !b || !a.timeseries || !b.timeseries) {
      return e("div", { className: "card" }, "Compare runs missing timeseries.");
    }
    const pa = a.timeseries.pos_plot;
    const pb = b.timeseries.pos_plot;
    const rows = (cmp.deltas && cmp.deltas.rows) || [];

    return e(
      "div",
      { className: "grid cols-2" },
      e(
        "div",
        { className: "card", style: { gridColumn: "1 / -1" } },
        e("h2", null, "Controller compare: ", cmp.label_a, " vs ", cmp.label_b),
        e(
          "table",
          { className: "metrics" },
          e(
            "thead",
            null,
            e("tr", null, e("th", null, "metric"), e("th", null, "A"), e("th", null, "B"), e("th", null, "Δ (B−A)"))
          ),
          e(
            "tbody",
            null,
            rows
              .filter((r) => ["rmse_position_m", "max_position_error_m", "success", "control_effort_proxy"].includes(r.metric))
              .map((r) =>
                e(
                  "tr",
                  { key: r.metric },
                  e("td", null, r.metric),
                  e("td", null, fmt(r.a, 5)),
                  e("td", null, fmt(r.b, 5)),
                  e("td", null, fmt(r.delta, 5))
                )
              )
          )
        )
      ),
      e("div", { className: "card", style: { gridColumn: "1 / -1" } }, e(PlotDiv, {
        id: "cmp3d",
        data: (function () {
          const b = fitSceneBounds([pa, pb]);
          return [
            cornerTrace(b),
            {
              type: "scatter3d",
              mode: "lines",
              x: pa.map(function (p) {
                return p[0];
              }),
              y: pa.map(function (p) {
                return p[1];
              }),
              z: pa.map(function (p) {
                return p[2];
              }),
              line: { color: "#3d9cf0", width: 5 },
              name: cmp.label_a,
            },
            {
              type: "scatter3d",
              mode: "lines",
              x: pb.map(function (p) {
                return p[0];
              }),
              y: pb.map(function (p) {
                return p[1];
              }),
              z: pb.map(function (p) {
                return p[2];
              }),
              line: { color: "#e6b450", width: 4, dash: "dash" },
              name: cmp.label_b,
            },
          ];
        })(),
        layout: (function () {
          const b = fitSceneBounds([pa, pb]);
          return {
            title: "Path overlay (N, E, up=−D)",
            paper_bgcolor: "#0c1018",
            plot_bgcolor: "#0c1018",
            font: { color: "#e7ecf3", size: 11 },
            height: 480,
            margin: { t: 40, r: 0, b: 0, l: 0 },
            uirevision: "compare-paths",
            scene: {
              xaxis: { title: "N", gridcolor: "#2d3a4d", range: b.x, autorange: false },
              yaxis: { title: "E", gridcolor: "#2d3a4d", range: b.y, autorange: false },
              zaxis: { title: "up", gridcolor: "#2d3a4d", range: b.z, autorange: false },
              aspectmode: "manual",
              aspectratio: b.ar,
              bgcolor: "#0c1018",
              camera: { eye: { x: 2.4, y: 2.4, z: 1.55 } },
            },
            legend: { orientation: "h" },
          };
        })(),
      }))
    );
  }

  function App() {
    const [doc, setDoc] = useState(null);
    const [err, setErr] = useState(null);
    const [tab, setTab] = useState("overview");
    const [runId, setRunId] = useState(null);

    useEffect(() => {
      fetch("./data/showcase.json")
        .then((r) => {
          if (!r.ok) throw new Error("Failed to load data/showcase.json (" + r.status + ")");
          return r.json();
        })
        .then((j) => {
          setDoc(j);
          setRunId((j.ui && j.ui.default_run) || (j.runs && j.runs[0] && j.runs[0].id));
        })
        .catch((ex) => setErr(String(ex)));
    }, []);

    const run = useMemo(() => {
      if (!doc || !runId) return null;
      return (doc.runs || []).find((r) => r.id === runId) || doc.runs[0];
    }, [doc, runId]);

    if (err) {
      return e(
        "div",
        { className: "card", style: { margin: "2rem" } },
        e("h2", null, "Showcase data missing"),
        e("p", null, err),
        e(
          "p",
          { style: { color: "var(--muted)" } },
          "Generate with: ",
          e("code", null, "uv run uavsim gallery --base-case")
        )
      );
    }
    if (!doc || !run) return e("p", { className: "loading" }, "Loading showcase…");

    const tabs = [
      ["overview", "Overview"],
      ["flight", "Flight 3D"],
      ["metrics", "Metrics"],
      ["monte_carlo", "Monte Carlo"],
      ["compare", "Compare"],
    ];

    let body;
    if (tab === "overview") body = e(Overview, { doc, onSelect: (id) => { setRunId(id); setTab("flight"); } });
    else if (tab === "flight")
      body = e(
        "div",
        null,
        e(
          "div",
          { className: "row" },
          e("label", null, "Run "),
          e(
            "select",
            { value: run.id, onChange: (ev) => setRunId(ev.target.value) },
            doc.runs.map((r) => e("option", { key: r.id, value: r.id }, r.label))
          )
        ),
        e(FlightTab, { run })
      );
    else if (tab === "metrics")
      body = e(
        "div",
        null,
        e(
          "div",
          { className: "row" },
          e(
            "select",
            { value: run.id, onChange: (ev) => setRunId(ev.target.value) },
            doc.runs.map((r) => e("option", { key: r.id, value: r.id }, r.label))
          )
        ),
        e(MetricsTab, { run })
      );
    else if (tab === "monte_carlo") {
      const mcRun = doc.runs.find((r) => r.mc) || run;
      body = e(McTab, { run: mcRun });
    } else if (tab === "compare") body = e(CompareTab, { doc });

    return e(
      "div",
      null,
      e(
        "header",
        { className: "app-header" },
        e("h1", null, doc.title || "uavsim · flight results"),
        e("p", { className: "tagline" }, doc.description || ""),
        e(
          "div",
          { className: "meta" },
          "v",
          doc.uavsim_version || "?",
          doc.generated_at
            ? " · " + String(doc.generated_at).slice(0, 10)
            : ""
        )
      ),
      e(
        "nav",
        { className: "tabs" },
        tabs.map(([id, label]) =>
          e(
            "button",
            {
              key: id,
              className: tab === id ? "active" : "",
              onClick: () => setTab(id),
            },
            label
          )
        )
      ),
      e("main", null, body),
      e(
        "footer",
        { className: "footer" },
        "Simulation only — not flight software. Source: ",
        e("a", { href: "https://github.com/trey-copeland/uavsim" }, "github.com/trey-copeland/uavsim")
      )
    );
  }

  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(e(App));
})();
