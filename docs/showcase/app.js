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
   * Equal-span 3D box around path points (meters).
   * Flat trajectories (tiny Z span) still get a cubic world box so Plotly
   * does not zoom into a paper-thin slab.
   */
  function equalSceneBounds(plotArrays, padFrac, minHalf) {
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
    function midHalf(a) {
      if (!a.length) return { mid: 0, half: minHalf || 1 };
      let lo = Math.min.apply(null, a);
      let hi = Math.max.apply(null, a);
      if (!Number.isFinite(lo) || !Number.isFinite(hi)) return { mid: 0, half: minHalf || 1 };
      const mid = 0.5 * (lo + hi);
      let half = 0.5 * (hi - lo);
      const pad = padFrac == null ? 0.2 : padFrac;
      half = Math.max(half * (1 + pad), minHalf == null ? 0.75 : minHalf);
      return { mid: mid, half: half };
    }
    const mx = midHalf(xs);
    const my = midHalf(ys);
    const mz = midHalf(zs);
    const half = Math.max(mx.half, my.half, mz.half);
    return {
      x: [mx.mid - half, mx.mid + half],
      y: [my.mid - half, my.mid + half],
      z: [mz.mid - half, mz.mid + half],
      half: half,
    };
  }

  function sceneBoundsFromPlots(plotArrays, padFrac) {
    // Used by compare tab — equal box for stability.
    return equalSceneBounds(plotArrays, padFrac, 0.75);
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
   * Flight 3D: newPlot once per run (fixed equal bounds + camera), then
   * restyle-only on scrub so zoom/orbit never resets.
   */
  function Flight3DView({ runId, ts, frame }) {
    const ref = useRef(null);
    const ready = useRef(false);
    const boundsRef = useRef(null);

    // Full (re)build when run changes
    useEffect(() => {
      if (!ref.current || !window.Plotly || !ts || !ts.pos_plot) return;
      const pos = ts.pos_plot;
      const bounds = equalSceneBounds([pos, ts.ref_plot], 0.25, 1.0);
      boundsRef.current = bounds;
      ready.current = false;

      const axis = function (title, range) {
        return {
          title: title,
          range: range,
          autorange: false,
          gridcolor: "#2d3a4d",
          zerolinecolor: "#3a4a60",
          showbackground: true,
          backgroundcolor: "#0c1018",
        };
      };

      const traces = [
        {
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
          line: { color: "rgba(100,140,200,0.4)", width: 4 },
          name: "path",
          hoverinfo: "skip",
        },
      ];
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
      }
      // placeholders for trail / vehicle / velocity — updated via restyle
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
          // Equal meters on all axes (matches equal ranges)
          aspectmode: "cube",
          bgcolor: "#0c1018",
          // Pull back so the full box is visible on first paint
          camera: {
            eye: { x: 1.85, y: 1.85, z: 1.35 },
            center: { x: 0, y: 0, z: 0 },
            up: { x: 0, y: 0, z: 1 },
          },
        },
        showlegend: true,
        legend: { orientation: "h", y: 1.08 },
        height: 500,
      };

      Plotly.newPlot(ref.current, traces, layout, {
        responsive: true,
        displayModeBar: true,
      }).then(function () {
        ready.current = true;
      });

      return function () {
        ready.current = false;
        if (ref.current && window.Plotly) Plotly.purge(ref.current);
      };
    }, [runId, ts]);

    // Scrub: restyle only — never relayout scene (preserves zoom/orbit)
    useEffect(() => {
      if (!ref.current || !window.Plotly || !ready.current || !ts || !ts.pos_plot) return;
      const pos = ts.pos_plot;
      const n = pos.length;
      const i = Math.max(0, Math.min(frame, n - 1));
      const trail = pos.slice(0, i + 1);
      const bounds = boundsRef.current;
      const half = bounds ? bounds.half : 1;
      const v = ts.vel_ned[i];
      const vNorm = Math.hypot(v[0], v[1], v[2]) || 1;
      const vLen = 0.1 * 2 * half; // ~10% of box edge
      const px = pos[i][0];
      const py = pos[i][1];
      const pz = pos[i][2];

      // Trace index: 0 path, [1 ref?], trail, vehicle, velocity
      const hasRef = !!ts.ref_plot;
      const iTrail = hasRef ? 2 : 1;
      const iVeh = iTrail + 1;
      const iVel = iTrail + 2;

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
        [iTrail, iVeh, iVel]
      );
    }, [frame, ts, runId]);

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
        e("h2", null, "Base case narrative"),
        e(
          "p",
          { style: { margin: 0, color: "var(--muted)", fontSize: "0.9rem" } },
          doc.description ||
            "Portfolio SIL demo: nonlinear quadrotor tracking, two controllers, Monte Carlo robustness."
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
        { className: "grid cols-2", style: { marginTop: "1rem" } },
        e("div", { className: "card" }, e(PlotDiv, {
          id: "pos_ts",
          data: [
            { x: ts.t, y: ts.pos_ned.map((p) => p[0]), name: "N", type: "scatter", mode: "lines" },
            { x: ts.t, y: ts.pos_ned.map((p) => p[1]), name: "E", type: "scatter", mode: "lines" },
            { x: ts.t, y: ts.pos_ned.map((p) => p[2]), name: "D", type: "scatter", mode: "lines" },
            {
              x: [ts.t[i], ts.t[i]],
              y: [
                Math.min(...ts.pos_ned.map((p) => Math.min(p[0], p[1], p[2]))),
                Math.max(...ts.pos_ned.map((p) => Math.max(p[0], p[1], p[2]))),
              ],
              mode: "lines",
              line: { color: "white", dash: "dot", width: 1 },
              showlegend: false,
            },
          ],
          layout: {
            title: "Position NED",
            paper_bgcolor: "#0c1018",
            plot_bgcolor: "#0c1018",
            font: { color: "#e7ecf3", size: 11 },
            margin: { t: 40, r: 10, b: 40, l: 50 },
            height: 280,
            legend: { orientation: "h" },
          },
        })),
        e("div", { className: "card" }, e(PlotDiv, {
          id: "u_ts",
          data: [
            { x: ts.t, y: ts.u.map((u) => u[0]), name: "F", type: "scatter", mode: "lines" },
            { x: ts.t, y: ts.u.map((u) => u[1]), name: "τφ", type: "scatter", mode: "lines" },
            { x: ts.t, y: ts.u.map((u) => u[2]), name: "τθ", type: "scatter", mode: "lines" },
            { x: ts.t, y: ts.u.map((u) => u[3]), name: "τψ", type: "scatter", mode: "lines" },
          ],
          layout: {
            title: "Control u(t)",
            paper_bgcolor: "#0c1018",
            plot_bgcolor: "#0c1018",
            font: { color: "#e7ecf3", size: 11 },
            margin: { t: 40, r: 10, b: 40, l: 50 },
            height: 280,
            legend: { orientation: "h" },
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
      return e("div", { className: "card" }, "No Monte Carlo trials in this run. Select the hover MC card.");
    }
    const trials = mc.trials;
    const rmse = trials.map((t) => t.rmse_position_m).filter((x) => x != null);
    const mass = trials.map((t) => t.mass_kg);
    const s = [...rmse].sort((a, b) => a - b);
    const cdfY = s.map((_, i) => (i + 1) / s.length);
    const nOk = trials.filter((t) => t.success === true).length;

    return e(
      "div",
      { className: "grid cols-2" },
      e(
        "div",
        { className: "card" },
        e("h2", null, "MC summary"),
        e("div", { className: "stat" }, String(mc.n_trials), e("span", null, "trials")),
        e(
          "p",
          { style: { color: "var(--muted)", fontSize: "0.85rem" } },
          "success ",
          nOk,
          "/",
          trials.length,
          " · fail rate ",
          fmt((mc.summary || {}).failure_rate, 3)
        )
      ),
      e("div", { className: "card" }, e(PlotDiv, {
        id: "mc_hist",
        data: [{ x: rmse, type: "histogram", nbinsx: 12, marker: { color: "#3d9cf0" } }],
        layout: {
          title: "RMSE histogram",
          paper_bgcolor: "#0c1018",
          plot_bgcolor: "#0c1018",
          font: { color: "#e7ecf3", size: 11 },
          height: 300,
          margin: { t: 40, r: 10, b: 40, l: 50 },
        },
      })),
      e("div", { className: "card" }, e(PlotDiv, {
        id: "mc_cdf",
        data: [{ x: s, y: cdfY, type: "scatter", mode: "lines", line: { shape: "hv", color: "#3ecf8e" } }],
        layout: {
          title: "RMSE CDF",
          paper_bgcolor: "#0c1018",
          plot_bgcolor: "#0c1018",
          font: { color: "#e7ecf3", size: 11 },
          height: 300,
          margin: { t: 40, r: 10, b: 40, l: 50 },
          xaxis: { title: "RMSE [m]" },
          yaxis: { title: "CDF" },
        },
      })),
      e("div", { className: "card" }, e(PlotDiv, {
        id: "mc_scatter",
        data: [
          {
            x: mass,
            y: rmse,
            mode: "markers",
            type: "scatter",
            marker: { size: 9, color: "#e6b450" },
          },
        ],
        layout: {
          title: "mass vs RMSE",
          paper_bgcolor: "#0c1018",
          plot_bgcolor: "#0c1018",
          font: { color: "#e7ecf3", size: 11 },
          height: 300,
          margin: { t: 40, r: 10, b: 40, l: 50 },
          xaxis: { title: "mass [kg]" },
          yaxis: { title: "RMSE [m]" },
        },
      }))
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
        preserveCamera: true,
        data: [
          {
            type: "scatter3d",
            mode: "lines",
            x: pa.map((p) => p[0]),
            y: pa.map((p) => p[1]),
            z: pa.map((p) => p[2]),
            line: { color: "#3d9cf0", width: 5 },
            name: cmp.label_a,
          },
          {
            type: "scatter3d",
            mode: "lines",
            x: pb.map((p) => p[0]),
            y: pb.map((p) => p[1]),
            z: pb.map((p) => p[2]),
            line: { color: "#e6b450", width: 4, dash: "dash" },
            name: cmp.label_b,
          },
        ],
        layout: (function () {
          const b = sceneBoundsFromPlots([pa, pb], 0.18);
          return {
            title: "Path overlay (N, E, up=−D)",
            paper_bgcolor: "#0c1018",
            plot_bgcolor: "#0c1018",
            font: { color: "#e7ecf3", size: 11 },
            height: 460,
            margin: { t: 40, r: 0, b: 0, l: 0 },
            uirevision: "compare-paths",
            scene: {
              xaxis: { title: "N", gridcolor: "#2d3a4d", range: b.x, autorange: false },
              yaxis: { title: "E", gridcolor: "#2d3a4d", range: b.y, autorange: false },
              zaxis: { title: "up", gridcolor: "#2d3a4d", range: b.z, autorange: false },
              aspectmode: "cube",
              bgcolor: "#0c1018",
              camera: { eye: { x: 1.55, y: 1.55, z: 1.15 } },
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
        e("h1", null, doc.title || "uavsim showcase"),
        e("p", null, doc.description || ""),
        e(
          "div",
          { className: "meta" },
          "uavsim ",
          doc.uavsim_version || "?",
          " · generated ",
          doc.generated_at || "?",
          " · schema ",
          doc.schema_version
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
        "Simulation only — not flight-critical. ",
        e("a", { href: "https://github.com/trey-copeland/uavsim" }, "github.com/trey-copeland/uavsim"),
        " · regenerate: ",
        e("code", null, "uv run uavsim gallery --base-case")
      )
    );
  }

  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(e(App));
})();
