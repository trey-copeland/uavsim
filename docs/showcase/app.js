/* uavsim results showcase — React 18 (no JSX build). Data: ./data/showcase.json */
(function () {
  const e = React.createElement;
  const { useState, useEffect, useMemo, useRef } = React;

  function roleBadge(role) {
    if (!role) return e("span", { className: "badge" }, "run");
    if (role.includes("monte_carlo") || role.includes("mc"))
      return e("span", { className: "badge mc" }, "MC");
    const parts = [];
    if (role.includes("naive"))
      parts.push(e("span", { key: "n", className: "badge naive" }, "naive"));
    else if (role.includes("imu_only"))
      parts.push(e("span", { key: "i", className: "badge weak" }, "IMU-only"));
    else if (role.includes("flow"))
      parts.push(e("span", { key: "f", className: "badge ahrs" }, "flow+alt"));
    else if (role.includes("ahrs"))
      parts.push(e("span", { key: "a", className: "badge ahrs" }, "AHRS"));
    else if (role.includes("lqg"))
      parts.push(e("span", { key: "g", className: "badge lqg" }, "LQG"));
    else if (role.includes("kf"))
      parts.push(e("span", { key: "k", className: "badge lqg" }, "KF"));

    if (role.includes("pid"))
      parts.push(e("span", { key: "p", className: "badge pid" }, "PID"));
    else if (!role.includes("lqg") && (role.includes("lqr") || role.includes("ideal")))
      parts.push(e("span", { key: "l", className: "badge lqr" }, "LQR"));

    if (parts.length) return e("span", { className: "badge-row" }, parts);
    return e("span", { className: "badge" }, role);
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

  /** Plotly config: modebar on hover so tools never permanently cover titles. */
  const DEFAULT_PLOT_CONFIG = {
    responsive: true,
    displayModeBar: "hover",
    displaylogo: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
  };

  function extractPlotCaption(layout) {
    if (!layout || layout.title == null) return { caption: null, layout: layout || {} };
    const t = layout.title;
    let caption = null;
    if (typeof t === "string") caption = t;
    else if (t && typeof t.text === "string") caption = t.text;
    const next = Object.assign({}, layout);
    delete next.title;
    return { caption: caption, layout: next };
  }

  function withPlotMargins(layout) {
    const base = { t: 28, r: 18, b: 44, l: 54 };
    const m = Object.assign({}, base, (layout && layout.margin) || {});
    // Never let callers clip the top under residual modebar chrome
    if (m.t < 20) m.t = 20;
    return Object.assign({}, layout, { margin: m });
  }

  function PlotDiv({ id, data, layout, config }) {
    const ref = useRef(null);
    const extracted = extractPlotCaption(layout);
    const caption = extracted.caption;
    let finalLayout = withPlotMargins(extracted.layout);
    // Title moved to HTML caption — reclaim Plotly top margin reserved for gtitle
    if (caption && finalLayout.margin && finalLayout.margin.t > 28) {
      finalLayout = Object.assign({}, finalLayout, {
        margin: Object.assign({}, finalLayout.margin, { t: 24 }),
      });
    }
    const finalConfig = Object.assign({}, DEFAULT_PLOT_CONFIG, config || {});

    useEffect(() => {
      if (!ref.current || !window.Plotly) return;
      Plotly.react(ref.current, data, finalLayout, finalConfig);
    }, [id, data, layout, config]);
    useEffect(() => {
      return () => {
        if (ref.current && window.Plotly) Plotly.purge(ref.current);
      };
    }, [id]);

    return e(
      "div",
      { className: "plot-wrap" },
      caption
        ? e("h3", { className: "plot-caption" }, caption)
        : null,
      e("div", {
        className: "plot" + (caption ? " plot-has-caption" : ""),
        ref: ref,
        id: id,
      })
    );
  }

  // --- 3D attitude helpers (ZYX Euler body→NED, plot frame N/E/up) ---
  function deg2rad(d) {
    return (d * Math.PI) / 180;
  }
  function matMulVec(R, v) {
    return [
      R[0][0] * v[0] + R[0][1] * v[1] + R[0][2] * v[2],
      R[1][0] * v[0] + R[1][1] * v[1] + R[1][2] * v[2],
      R[2][0] * v[0] + R[2][1] * v[1] + R[2][2] * v[2],
    ];
  }
  /** Body→NED rotation, ZYX (φ, θ, ψ) in radians. */
  function rotationBodyToNed(phi, theta, psi) {
    const cph = Math.cos(phi);
    const sph = Math.sin(phi);
    const cth = Math.cos(theta);
    const sth = Math.sin(theta);
    const cps = Math.cos(psi);
    const sps = Math.sin(psi);
    // Rz(psi) @ Ry(theta) @ Rx(phi)
    return [
      [cps * cth, cps * sth * sph - sps * cph, cps * sth * cph + sps * sph],
      [sps * cth, sps * sth * sph + cps * cph, sps * sth * cph - cps * sph],
      [-sth, cth * sph, cth * cph],
    ];
  }
  function bodyToPlot(R, vb) {
    const ned = matMulVec(R, vb);
    return [ned[0], ned[1], -ned[2]];
  }
  function arrowSeg(R, originBody, dirBody, length) {
    const o = bodyToPlot(R, originBody);
    const d = bodyToPlot(R, dirBody);
    const n = Math.hypot(d[0], d[1], d[2]) || 1;
    return {
      x: [o[0], o[0] + (d[0] / n) * length],
      y: [o[1], o[1] + (d[1] / n) * length],
      z: [o[2], o[2] + (d[2] / n) * length],
    };
  }
  /**
   * X-quad mesh + wrench arrows in plot frame for current Euler (deg) and u.
   */
  function vehicleGeom(eulerDeg, u, limits) {
    const phi = deg2rad(eulerDeg[0]);
    const theta = deg2rad(eulerDeg[1]);
    const psi = deg2rad(eulerDeg[2]);
    const R = rotationBodyToNed(phi, theta, psi);
    const L = 0.38; // arm (body x/y projection)
    const motorsB = [
      [L, L, 0],
      [-L, L, 0],
      [-L, -L, 0],
      [L, -L, 0],
    ];
    // Frame: cross arms + short body box outline
    const segs = [
      // diagonal arms
      [motorsB[0], motorsB[2]],
      [motorsB[1], motorsB[3]],
      // body square
      [
        [0.1, 0.1, 0],
        [-0.1, 0.1, 0],
      ],
      [
        [-0.1, 0.1, 0],
        [-0.1, -0.1, 0],
      ],
      [
        [-0.1, -0.1, 0],
        [0.1, -0.1, 0],
      ],
      [
        [0.1, -0.1, 0],
        [0.1, 0.1, 0],
      ],
    ];
    const fx = [];
    const fy = [];
    const fz = [];
    segs.forEach(function (pair) {
      const a = bodyToPlot(R, pair[0]);
      const b = bodyToPlot(R, pair[1]);
      fx.push(a[0], b[0], null);
      fy.push(a[1], b[1], null);
      fz.push(a[2], b[2], null);
    });
    const motors = motorsB.map(function (m) {
      return bodyToPlot(R, m);
    });

    // Body axes triad (unit length ~0.22)
    const axLen = 0.28;
    const axes = {
      x: arrowSeg(R, [0, 0, 0], [1, 0, 0], axLen),
      y: arrowSeg(R, [0, 0, 0], [0, 1, 0], axLen),
      z: arrowSeg(R, [0, 0, 0], [0, 0, 1], axLen),
    };

    const F = +u[0] || 0;
    const tx = +u[1] || 0;
    const ty = +u[2] || 0;
    const tz = +u[3] || 0;
    const tNorm = Math.hypot(tx, ty, tz);
    const Fmax = (limits && limits.thrust_max_n) || 10;
    const Tmax = (limits && limits.torque_max_nm) || 1;
    // Thrust along −body z (up in plot when level)
    const thrustLen = 0.2 + 0.75 * Math.min(1.2, Math.max(0, F / Fmax));
    const thrust = arrowSeg(R, [0, 0, 0], [0, 0, -1], thrustLen);
    // Resultant torque in body frame
    let torque = { x: [0, 0], y: [0, 0], z: [0, 0] };
    if (tNorm > 1e-9) {
      const tLen = 0.15 + 0.65 * Math.min(1.2, tNorm / Math.max(Tmax, 1e-6));
      torque = arrowSeg(R, [0, 0, 0], [tx, ty, tz], tLen);
    }
    // Per-axis torque ticks (body axes, signed length)
    const tScale = 0.55 / Math.max(Tmax, 1e-6);
    const tAx = arrowSeg(R, [0, 0, 0], [1, 0, 0], tx * tScale);
    const tAy = arrowSeg(R, [0, 0, 0], [0, 1, 0], ty * tScale);
    const tAz = arrowSeg(R, [0, 0, 0], [0, 0, 1], tz * tScale);

    return {
      frame: { x: fx, y: fy, z: fz },
      motors: motors,
      axes: axes,
      thrust: thrust,
      torque: torque,
      tAx: tAx,
      tAy: tAy,
      tAz: tAz,
      F: F,
      tau: [tx, ty, tz],
      tNorm: tNorm,
    };
  }

  /**
   * Flight path 3D: newPlot once per run (fixed FOV), restyle-only on scrub.
   * Also draws a small body-frame triad at the vehicle for attitude context.
   */
  function Flight3DView({ runId, ts, frame }) {
    const ref = useRef(null);
    const ready = useRef(false);
    const boundsRef = useRef(null);
    const idxRef = useRef({ trail: 1, veh: 2, vel: 3, triad: 4 });

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
      const vLen = 0.14 * 2 * halfH;
      const px = pos[ii][0];
      const py = pos[ii][1];
      const pz = pos[ii][2];
      const ix = idxRef.current;

      // Local triad at vehicle (plot frame) from current Euler
      const eu = ts.euler_deg[ii];
      const R = rotationBodyToNed(deg2rad(eu[0]), deg2rad(eu[1]), deg2rad(eu[2]));
      const s = 0.1 * 2 * halfH;
      const ax = bodyToPlot(R, [s, 0, 0]);
      const ay = bodyToPlot(R, [0, s, 0]);
      const az = bodyToPlot(R, [0, 0, -s]); // −body z ≈ up when level
      const triadX = [px, px + ax[0], null, px, px + ay[0], null, px, px + az[0]];
      const triadY = [py, py + ax[1], null, py, py + ay[1], null, py, py + az[1]];
      const triadZ = [pz, pz + ax[2], null, pz, pz + ay[2], null, pz, pz + az[2]];

      Plotly.restyle(
        ref.current,
        {
          x: [
            trail.map(function (p) {
              return p[0];
            }),
            [px],
            [px, px + (v[0] / vNorm) * vLen],
            triadX,
          ],
          y: [
            trail.map(function (p) {
              return p[1];
            }),
            [py],
            [py, py + (v[1] / vNorm) * vLen],
            triadY,
          ],
          z: [
            trail.map(function (p) {
              return p[2];
            }),
            [pz],
            [pz, pz - (v[2] / vNorm) * vLen],
            triadZ,
          ],
        },
        [ix.trail, ix.veh, ix.vel, ix.triad]
      );
    }

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
          gridcolor: "#243044",
          zerolinecolor: "#3a4a60",
          showbackground: true,
          backgroundcolor: "rgba(10,14,22,0.95)",
        };
      };

      const traces = [];
      traces.push(cornerTrace(bounds));
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
        line: { color: "rgba(80,120,180,0.35)", width: 5 },
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
          line: { color: "rgba(255,165,40,0.85)", width: 3, dash: "dash" },
          name: "reference",
          hoverinfo: "skip",
        });
        next = 3;
      }
      idxRef.current = { trail: next, veh: next + 1, vel: next + 2, triad: next + 3 };
      traces.push({
        type: "scatter3d",
        mode: "lines",
        x: [pos[0][0]],
        y: [pos[0][1]],
        z: [pos[0][2]],
        line: { color: "#5b9fd4", width: 8 },
        name: "trail",
      });
      traces.push({
        type: "scatter3d",
        mode: "markers",
        x: [pos[0][0]],
        y: [pos[0][1]],
        z: [pos[0][2]],
        marker: {
          size: 7,
          color: "#e8f4ff",
          line: { color: "#5b9fd4", width: 2 },
          symbol: "circle",
        },
        name: "vehicle",
      });
      traces.push({
        type: "scatter3d",
        mode: "lines",
        x: [pos[0][0], pos[0][0]],
        y: [pos[0][1], pos[0][1]],
        z: [pos[0][2], pos[0][2]],
        line: { color: "#3ecf8e", width: 7 },
        name: "velocity",
      });
      traces.push({
        type: "scatter3d",
        mode: "lines",
        x: [0, 0],
        y: [0, 0],
        z: [0, 0],
        line: { color: "rgba(231,236,243,0.85)", width: 4 },
        name: "body axes",
        hoverinfo: "skip",
      });

      const layout = {
        paper_bgcolor: "#0a0e16",
        plot_bgcolor: "#0a0e16",
        font: { color: "#e7ecf3", size: 11 },
        margin: { l: 0, r: 0, t: 8, b: 0 },
        uirevision: "flight-static-" + runId,
        scene: {
          xaxis: axis("N [m]", bounds.x),
          yaxis: axis("E [m]", bounds.y),
          zaxis: axis("up [m]", bounds.z),
          aspectmode: "manual",
          aspectratio: bounds.ar,
          bgcolor: "#0a0e16",
          camera: {
            eye: { x: 2.35, y: 2.35, z: 1.5 },
            center: { x: 0, y: 0, z: 0 },
            up: { x: 0, y: 0, z: 1 },
          },
        },
        showlegend: true,
        legend: { orientation: "h", y: 1.1, font: { size: 10 } },
        height: 480,
      };

      Plotly.newPlot(ref.current, traces, layout, {
        responsive: true,
        displayModeBar: "hover",
        displaylogo: false,
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

    useEffect(() => {
      applyFrame(frame);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [frame, runId]);

    return e("div", { className: "plot plot-flight", ref: ref, id: "flight3d-" + runId });
  }

  /**
   * Vehicle attitude + wrench: X-quad mesh, body axes, thrust (−body z) and torque arrows.
   * Uses same scrub index as the path plot. Fixed cube FOV at origin.
   */
  function VehicleAttitudeView({ runId, ts, frame, limits }) {
    const ref = useRef(null);
    const ready = useRef(false);
    // trace indices: 0 bounds, 1 frame, 2 motors, 3 ax, 4 ay, 5 az, 6 thrust, 7 torque, 8–10 tau axes
    const IDX = { frame: 1, motors: 2, ax: 3, ay: 4, az: 5, thrust: 6, torque: 7, tAx: 8, tAy: 9, tAz: 10 };

    function applyFrame(i) {
      if (!ref.current || !window.Plotly || !ready.current || !ts) return;
      const n = ts.t.length;
      const ii = Math.max(0, Math.min(i, n - 1));
      const g = vehicleGeom(ts.euler_deg[ii], ts.u[ii], limits);
      const m = g.motors;
      Plotly.restyle(
        ref.current,
        {
          x: [
            g.frame.x,
            m.map(function (p) {
              return p[0];
            }),
            g.axes.x.x,
            g.axes.y.x,
            g.axes.z.x,
            g.thrust.x,
            g.torque.x,
            g.tAx.x,
            g.tAy.x,
            g.tAz.x,
          ],
          y: [
            g.frame.y,
            m.map(function (p) {
              return p[1];
            }),
            g.axes.x.y,
            g.axes.y.y,
            g.axes.z.y,
            g.thrust.y,
            g.torque.y,
            g.tAx.y,
            g.tAy.y,
            g.tAz.y,
          ],
          z: [
            g.frame.z,
            m.map(function (p) {
              return p[2];
            }),
            g.axes.x.z,
            g.axes.y.z,
            g.axes.z.z,
            g.thrust.z,
            g.torque.z,
            g.tAx.z,
            g.tAy.z,
            g.tAz.z,
          ],
        },
        [IDX.frame, IDX.motors, IDX.ax, IDX.ay, IDX.az, IDX.thrust, IDX.torque, IDX.tAx, IDX.tAy, IDX.tAz]
      );
    }

    useEffect(() => {
      if (!ref.current || !window.Plotly || !ts) return;
      ready.current = false;
      const g0 = vehicleGeom(ts.euler_deg[0], ts.u[0], limits);
      const span = 1.05;
      const bounds = {
        x: [-span, span],
        y: [-span, span],
        z: [-span, span],
      };
      const ax = function (title) {
        return {
          title: title,
          range: [-span, span],
          autorange: false,
          gridcolor: "#243044",
          zerolinecolor: "#3a4a60",
          showbackground: true,
          backgroundcolor: "rgba(10,14,22,0.95)",
          showspikes: false,
        };
      };
      const line3 = function (seg, color, width, name, showleg) {
        return {
          type: "scatter3d",
          mode: "lines",
          x: seg.x,
          y: seg.y,
          z: seg.z,
          line: { color: color, width: width },
          name: name,
          showlegend: !!showleg,
          hoverinfo: "name",
        };
      };
      const m0 = g0.motors;
      const traces = [
        cornerTrace(bounds),
        {
          type: "scatter3d",
          mode: "lines",
          x: g0.frame.x,
          y: g0.frame.y,
          z: g0.frame.z,
          line: { color: "#8ab4e8", width: 8 },
          name: "airframe",
          hoverinfo: "skip",
        },
        {
          type: "scatter3d",
          mode: "markers",
          x: m0.map(function (p) {
            return p[0];
          }),
          y: m0.map(function (p) {
            return p[1];
          }),
          z: m0.map(function (p) {
            return p[2];
          }),
          marker: {
            size: 8,
            color: ["#5b9fd4", "#e6b450", "#5b9fd4", "#e6b450"],
            symbol: "circle",
            line: { width: 1, color: "#0a0e16" },
          },
          name: "motors",
          hoverinfo: "skip",
        },
        line3(g0.axes.x, "#f07178", 6, "body +x", true),
        line3(g0.axes.y, "#3ecf8e", 6, "body +y", true),
        line3(g0.axes.z, "#5b9fd4", 6, "body +z", true),
        line3(g0.thrust, "#4fd1ff", 12, "thrust −z", true),
        line3(g0.torque, "#e6b450", 10, "torque τ", true),
        line3(g0.tAx, "rgba(240,113,120,0.55)", 5, "τφ", false),
        line3(g0.tAy, "rgba(62,207,142,0.55)", 5, "τθ", false),
        line3(g0.tAz, "rgba(91,159,212,0.55)", 5, "τψ", false),
      ];
      const layout = {
        paper_bgcolor: "#0a0e16",
        plot_bgcolor: "#0a0e16",
        font: { color: "#e7ecf3", size: 11 },
        margin: { l: 0, r: 0, t: 8, b: 0 },
        uirevision: "veh-static-" + runId,
        scene: {
          xaxis: ax("N"),
          yaxis: ax("E"),
          zaxis: ax("up"),
          aspectmode: "cube",
          bgcolor: "#0a0e16",
          camera: {
            eye: { x: 1.55, y: 1.55, z: 1.15 },
            center: { x: 0, y: 0, z: 0 },
            up: { x: 0, y: 0, z: 1 },
          },
        },
        showlegend: true,
        legend: { orientation: "h", y: 1.12, font: { size: 10 } },
        height: 480,
      };
      Plotly.newPlot(ref.current, traces, layout, {
        responsive: true,
        displayModeBar: "hover",
        displaylogo: false,
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

    useEffect(() => {
      applyFrame(frame);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [frame, runId]);

    return e("div", { className: "plot plot-vehicle", ref: ref, id: "veh3d-" + runId });
  }

  function WrenchHud({ ts, frame, limits }) {
    const i = Math.max(0, Math.min(frame, ts.t.length - 1));
    const u = ts.u[i];
    const eu = ts.euler_deg[i];
    const v = ts.vel_ned[i];
    const w = ts.omega[i];
    const F = u[0];
    const tNorm = Math.hypot(u[1], u[2], u[3]);
    const vNorm = Math.hypot(v[0], v[1], v[2]);
    const Fmax = (limits && limits.thrust_max_n) || null;
    const Tmax = (limits && limits.torque_max_nm) || null;
    const fFrac = Fmax ? Math.min(1, Math.max(0, F / Fmax)) : null;
    const tFrac = Tmax ? Math.min(1, Math.max(0, tNorm / Tmax)) : null;

    function bar(frac, color) {
      if (frac === null) return null;
      return e(
        "div",
        { className: "hud-bar" },
        e("div", {
          className: "hud-bar-fill",
          style: { width: 100 * frac + "%", background: color },
        })
      );
    }

    return e(
      "div",
      { className: "wrench-hud" },
      e(
        "div",
        { className: "hud-block" },
        e("div", { className: "hud-label" }, "Thrust F"),
        e("div", { className: "hud-value accent-f" }, fmt(F, 3), e("span", { className: "hud-unit" }, " N")),
        bar(fFrac, "linear-gradient(90deg,#1a6a9a,#4fd1ff)"),
        Fmax ? e("div", { className: "hud-sub" }, fmt(100 * fFrac, 0), "% of limit ", fmt(Fmax, 1), " N") : null
      ),
      e(
        "div",
        { className: "hud-block" },
        e("div", { className: "hud-label" }, "Torque |τ|"),
        e("div", { className: "hud-value accent-t" }, fmt(tNorm, 4), e("span", { className: "hud-unit" }, " N·m")),
        bar(tFrac, "linear-gradient(90deg,#8a6a20,#e6b450)"),
        e(
          "div",
          { className: "hud-sub mono" },
          "τφ ",
          fmt(u[1], 3),
          " · τθ ",
          fmt(u[2], 3),
          " · τψ ",
          fmt(u[3], 3)
        )
      ),
      e(
        "div",
        { className: "hud-block" },
        e("div", { className: "hud-label" }, "Attitude φ θ ψ"),
        e(
          "div",
          { className: "hud-value mono" },
          fmt(eu[0], 1),
          "°  ",
          fmt(eu[1], 1),
          "°  ",
          fmt(eu[2], 1),
          "°"
        ),
        e(
          "div",
          { className: "hud-sub mono" },
          "pqr ",
          fmt(w[0], 2),
          " ",
          fmt(w[1], 2),
          " ",
          fmt(w[2], 2),
          " rad/s"
        )
      ),
      e(
        "div",
        { className: "hud-block" },
        e("div", { className: "hud-label" }, "Speed |v|"),
        e("div", { className: "hud-value" }, fmt(vNorm, 3), e("span", { className: "hud-unit" }, " m/s")),
        e(
          "div",
          { className: "hud-sub mono" },
          "NED ",
          fmt(v[0], 2),
          " ",
          fmt(v[1], 2),
          " ",
          fmt(v[2], 2)
        )
      )
    );
  }

  function Overview({ doc, onSelect }) {
    const runs = doc.runs || [];
    const byId = {};
    runs.forEach(function (r) {
      byId[r.id] = r;
    });
    const matrix = doc.estimation_matrix;
    const columns = (matrix && matrix.columns) || null;
    const rowDefs = (matrix && matrix.rows) || null;
    const scenarios = (matrix && matrix.scenarios) || [];

    function fmtRmse(v) {
      if (v === null || v === undefined || !Number.isFinite(+v)) return "—";
      const x = +v;
      // Keep digit bands similar width across the grid
      if (x >= 100) return x.toFixed(0);
      if (x >= 10) return x.toFixed(1);
      return x.toFixed(3);
    }
    function fmtMaxE(v) {
      if (v === null || v === undefined || !Number.isFinite(+v)) return "—";
      const x = +v;
      if (x >= 100) return x.toFixed(0);
      if (x >= 10) return x.toFixed(1);
      return x.toFixed(2);
    }

    function cellCard(sc) {
      if (!sc) {
        return e("div", { className: "matrix-cell empty", key: "empty" }, "—");
      }
      const run = sc.run_id ? byId[sc.run_id] : null;
      const m = (sc.metrics || (run && run.metrics)) || {};
      const ok = m.success;
      const tib = m.time_in_bounds_frac;
      const tibStr =
        tib != null && Number.isFinite(+tib) ? Math.round(100 * +tib) + "% in-bound" : null;
      return e(
        "div",
        {
          key: sc.id || sc.run_id,
          className: "matrix-cell card" + (ok === false ? " cell-fail" : ""),
          style: { cursor: sc.run_id ? "pointer" : "default" },
          onClick: function () {
            if (sc.run_id && onSelect) onSelect(sc.run_id);
          },
          title: sc.lesson || sc.label || "",
        },
        e(
          "div",
          { className: "matrix-cell-head" },
          e("span", { className: "matrix-method" }, sc.method || sc.label || ""),
          run ? roleBadge(run.role) : null
        ),
        e(
          "div",
          { className: "stat matrix-rmse" },
          fmtRmse(m.rmse_position_m),
          e("span", null, "RMSE [m]")
        ),
        e(
          "p",
          { className: "matrix-meta" },
          "max |e| ",
          fmtMaxE(m.max_position_error_m),
          " · ",
          e("span", { className: ok ? "ok" : "fail" }, ok === true ? "ok" : ok === false ? "fail" : "—"),
          tibStr ? e("span", null, " · " + tibStr) : null
        )
      );
    }

    // Extra runs not in the matrix (e.g. Monte Carlo)
    const matrixRunIds = {};
    scenarios.forEach(function (s) {
      if (s.run_id) matrixRunIds[s.run_id] = true;
    });
    const extra = runs.filter(function (r) {
      return !matrixRunIds[r.id];
    });

    const gridBlock =
      columns && rowDefs && scenarios.length
        ? e(
            "div",
            { className: "card matrix-wrap", style: { gridColumn: "1 / -1" } },
            e("h2", null, matrix.title || "Controller × sensor matrix"),
            e(
              "p",
              { style: { color: "var(--muted)", fontSize: "0.9rem", marginTop: 0 } },
              "Click a cell to open Flight 3D. Compare down a column (same sensors, different law) ",
              "or across a row (same law, harder sensors)."
            ),
            e(
              "div",
              { className: "table-wrap matrix-scroll" },
              e(
                "table",
                { className: "controller-matrix" },
                e(
                  "colgroup",
                  null,
                  e("col", { className: "row-head" }),
                  columns.map(function (c) {
                    return e("col", { key: c.id, className: "sensor" });
                  })
                ),
                e(
                  "thead",
                  null,
                  e(
                    "tr",
                    null,
                    e("th", { className: "corner" }, "Law \\ sensors"),
                    columns.map(function (c) {
                      return e(
                        "th",
                        { key: c.id },
                        e("div", { className: "col-label" }, c.label),
                        e(
                          "div",
                          { className: "col-sub", title: c.sensors || "" },
                          c.sensors || ""
                        )
                      );
                    })
                  )
                ),
                e(
                  "tbody",
                  null,
                  rowDefs.map(function (row) {
                    return e(
                      "tr",
                      { key: row.id },
                      e("th", { className: "row-label" }, row.label),
                      columns.map(function (col) {
                        const sc = scenarios.find(function (s) {
                          return s.column === col.id && s.controller === row.controller;
                        });
                        return e("td", { key: col.id }, cellCard(sc));
                      })
                    );
                  })
                )
              )
            )
          )
        : null;

    return e(
      "div",
      { className: "grid cols-3" },
      gridBlock,
      extra.map(function (r) {
        const m = r.metrics || {};
        return e(
          "div",
          {
            key: r.id,
            className: "card",
            style: { cursor: "pointer" },
            onClick: function () {
              onSelect(r.id);
            },
          },
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
            "Controller × sensor matrix on the elevated figure-eight, plus Monte Carlo and envelope."
        )
      )
    );
  }

  function FlightTab({ run }) {
    const ts = run.timeseries;
    const [frame, setFrame] = useState(0);
    useEffect(() => {
      setFrame(0);
    }, [run && run.id]);

    if (!ts) return e("div", { className: "card" }, "No timeseries for this run.");

    const n = ts.t.length;
    const i = Math.min(frame, n - 1);
    const limits = run.limits || {};

    return e(
      "div",
      { className: "flight-tab" },
      e(
        "div",
        { className: "flight-toolbar card" },
        e(
          "div",
          { className: "flight-toolbar-left" },
          e("strong", null, run.label),
          roleBadge(run.role),
          e(
            "span",
            { className: "flight-time mono" },
            "t = ",
            fmt(ts.t[i], 2),
            " s",
            e("span", { className: "muted" }, " / ", fmt(ts.t[n - 1], 1), " s")
          )
        ),
        e(
          "div",
          { className: "flight-scrub" },
          e("label", { htmlFor: "flight-scrub-" + run.id }, "scrub"),
          e("input", {
            id: "flight-scrub-" + run.id,
            type: "range",
            min: 0,
            max: n - 1,
            value: i,
            onChange: function (ev) {
              setFrame(Number(ev.target.value));
            },
          }),
          e(
            "span",
            { className: "flight-frame mono muted" },
            i + 1,
            " / ",
            n
          )
        )
      ),
      e(
        "div",
        { className: "flight-stage" },
        e(
          "div",
          { className: "card flight-panel" },
          e("h3", { className: "panel-title" }, "Trajectory"),
          e(
            "p",
            { className: "panel-sub" },
            "NED path in plot frame (N, E, up). Blue trail = history · green = velocity · axes at vehicle."
          ),
          e(Flight3DView, { runId: run.id, ts: ts, frame: i })
        ),
        e(
          "div",
          { className: "card flight-panel flight-panel-vehicle" },
          e("h3", { className: "panel-title" }, "Vehicle attitude & wrench"),
          e(
            "p",
            { className: "panel-sub" },
            "X-quad body at origin. Cyan = thrust (−body z) · gold = τ · RGB = body axes. Length ∝ magnitude."
          ),
          e(VehicleAttitudeView, {
            runId: run.id,
            ts: ts,
            frame: i,
            limits: limits,
          }),
          e(WrenchHud, { ts: ts, frame: i, limits: limits })
        )
      ),
      e(
        "div",
        { className: "grid cols-1", style: { marginTop: "1rem" } },
        e(
          "div",
          { className: "card" },
          e(PlotDiv, {
            id: "pos_ts",
            data: [
              {
                x: ts.t,
                y: ts.pos_ned.map(function (p) {
                  return p[0];
                }),
                name: "N",
                type: "scatter",
                mode: "lines",
                line: { color: "#5b9fd4" },
              },
              {
                x: ts.t,
                y: ts.pos_ned.map(function (p) {
                  return p[1];
                }),
                name: "E",
                type: "scatter",
                mode: "lines",
                line: { color: "#3ecf8e" },
              },
              {
                x: ts.t,
                y: ts.pos_ned.map(function (p) {
                  return p[2];
                }),
                name: "D",
                type: "scatter",
                mode: "lines",
                line: { color: "#e6b450" },
              },
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
                line: { color: "rgba(255,255,255,0.55)", dash: "dot", width: 1 },
                showlegend: false,
                hoverinfo: "skip",
              },
            ],
            layout: {
              title: "Position NED",
              paper_bgcolor: "#0a0e16",
              plot_bgcolor: "#0a0e16",
              font: { color: "#e7ecf3", size: 11 },
              margin: { t: 28, r: 10, b: 40, l: 50 },
              height: 260,
              legend: { orientation: "h" },
              xaxis: { title: "t [s]", gridcolor: "#2d3a4d", zeroline: false },
              yaxis: { title: "m", gridcolor: "#2d3a4d", zeroline: false },
            },
          })
        ),
        e(
          "div",
          { className: "card" },
          e(PlotDiv, {
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
                line: { color: "#4fd1ff" },
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
                line: { color: "#f07178" },
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
                line: { color: "#5b9fd4" },
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
              title: "Control u(t) — force & torques",
              paper_bgcolor: "#0a0e16",
              plot_bgcolor: "#0a0e16",
              font: { color: "#e7ecf3", size: 11 },
              margin: { t: 28, r: 20, b: 40, l: 55 },
              height: 360,
              legend: { orientation: "h", y: 1.12 },
              yaxis: {
                title: "F [N]",
                domain: [0.58, 1.0],
                gridcolor: "#2d3a4d",
                zeroline: false,
                titlefont: { size: 11 },
              },
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
          })
        )
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

  const COMPARE_METRIC_KEYS = [
    "rmse_position_m",
    "max_position_error_m",
    "final_position_error_m",
    "time_in_bounds_frac",
    "rmse_attitude_rad",
    "max_attitude_error_rad",
    "rmse_velocity_m_s",
    "control_effort_proxy",
    "peak_thrust_n",
    "peak_torque_nm",
    "success",
    "sim_success",
    "observer_id",
  ];

  function computeClientDeltas(metricsA, metricsB) {
    const ma = metricsA || {};
    const mb = metricsB || {};
    const rows = [];
    COMPARE_METRIC_KEYS.forEach(function (key) {
      if (!(key in ma) && !(key in mb)) return;
      const va = ma[key];
      const vb = mb[key];
      if (typeof va === "boolean" || typeof vb === "boolean") {
        rows.push({ metric: key, a: va, b: vb, delta: null });
        return;
      }
      if (typeof va === "string" || typeof vb === "string") {
        rows.push({ metric: key, a: va, b: vb, delta: null });
        return;
      }
      const fa = Number(va);
      const fb = Number(vb);
      if (Number.isFinite(fa) && Number.isFinite(fb)) {
        rows.push({ metric: key, a: fa, b: fb, delta: fb - fa });
      } else {
        rows.push({ metric: key, a: va, b: vb, delta: null });
      }
    });
    return rows;
  }

  function CompareTab({ doc }) {
    const runs = doc.runs || [];
    // Prefer runs with metrics; timeseries optional for path overlay
    const candidates = runs.filter(function (r) {
      return r && r.metrics;
    });
    const defaults = doc.compare || {};
    const defaultA =
      (defaults.a && candidates.some(function (r) {
        return r.id === defaults.a;
      })
        ? defaults.a
        : null) ||
      (candidates[0] && candidates[0].id) ||
      "";
    const defaultB =
      (defaults.b && candidates.some(function (r) {
        return r.id === defaults.b;
      })
        ? defaults.b
        : null) ||
      (candidates[1] && candidates[1].id) ||
      (candidates[0] && candidates[0].id) ||
      "";

    const [idA, setIdA] = useState(defaultA);
    const [idB, setIdB] = useState(defaultB);

    // If gallery data reloads with new defaults and state is empty
    useEffect(
      function () {
        if (!idA && defaultA) setIdA(defaultA);
        if (!idB && defaultB) setIdB(defaultB);
      },
      [defaultA, defaultB]
    );

    if (!candidates.length) {
      return e("div", { className: "card" }, "No runs with metrics to compare.");
    }

    const a = candidates.find(function (r) {
      return r.id === idA;
    }) || candidates[0];
    const b = candidates.find(function (r) {
      return r.id === idB;
    }) || candidates[Math.min(1, candidates.length - 1)];

    const labelA = a.label || a.id;
    const labelB = b.label || b.id;
    const rows = computeClientDeltas(a.metrics, b.metrics);
    const highlight = [
      "rmse_position_m",
      "max_position_error_m",
      "success",
      "control_effort_proxy",
      "rmse_attitude_rad",
      "observer_id",
    ];
    const primaryRows = rows.filter(function (r) {
      return highlight.indexOf(r.metric) >= 0;
    });
    const otherRows = rows.filter(function (r) {
      return highlight.indexOf(r.metric) < 0;
    });

    const hasPath =
      a.timeseries &&
      a.timeseries.pos_plot &&
      b.timeseries &&
      b.timeseries.pos_plot;

    function runSelect(which, value, onChange) {
      return e(
        "label",
        { className: "compare-pick" },
        e("span", { className: "compare-pick-label" }, which),
        e(
          "select",
          {
            value: value,
            onChange: function (ev) {
              onChange(ev.target.value);
            },
            "aria-label": "Compare " + which,
          },
          candidates.map(function (r) {
            return e(
              "option",
              { key: r.id, value: r.id },
              r.label || r.id
            );
          })
        )
      );
    }

    function swapAB() {
      const prevA = idA;
      setIdA(idB);
      setIdB(prevA);
    }

    function metricTable(tableRows, caption) {
      if (!tableRows.length) return null;
      return e(
        "div",
        { className: "table-wrap", style: { marginTop: caption ? "0.75rem" : 0 } },
        caption
          ? e(
              "h3",
              { style: { margin: "0 0 0.5rem", fontSize: "0.9rem", color: "var(--muted)" } },
              caption
            )
          : null,
        e(
          "table",
          { className: "metrics" },
          e(
            "thead",
            null,
            e(
              "tr",
              null,
              e("th", null, "metric"),
              e("th", null, "A · " + labelA),
              e("th", null, "B · " + labelB),
              e("th", null, "Δ (B−A)")
            )
          ),
          e(
            "tbody",
            null,
            tableRows.map(function (r) {
              return e(
                "tr",
                { key: r.metric },
                e("td", null, r.metric),
                e("td", null, fmt(r.a, 5)),
                e("td", null, fmt(r.b, 5)),
                e("td", null, r.delta == null ? "—" : fmt(r.delta, 5))
              );
            })
          )
        )
      );
    }

    return e(
      "div",
      { className: "grid cols-2" },
      e(
        "div",
        { className: "card", style: { gridColumn: "1 / -1" } },
        e("h2", null, "Compare runs"),
        e(
          "p",
          { style: { color: "var(--muted)", fontSize: "0.9rem", marginTop: 0 } },
          "Pick any two gallery runs. Metrics are B − A. Path overlay needs timeseries on both."
        ),
        e(
          "div",
          { className: "row compare-controls" },
          runSelect("A", a.id, setIdA),
          e(
            "button",
            {
              type: "button",
              className: "btn-swap",
              onClick: swapAB,
              title: "Swap A and B",
            },
            "⇄ Swap"
          ),
          runSelect("B", b.id, setIdB)
        ),
        a.id === b.id
          ? e(
              "p",
              { style: { color: "var(--warn)", fontSize: "0.85rem" } },
              "A and B are the same run — choose a different pair to see deltas."
            )
          : null,
        metricTable(primaryRows, null),
        metricTable(otherRows, "More metrics")
      ),
      hasPath
        ? e(
            "div",
            { className: "card", style: { gridColumn: "1 / -1" } },
            e(PlotDiv, {
              id: "cmp3d-" + a.id + "-" + b.id,
              data: (function () {
                const pa = a.timeseries.pos_plot;
                const pb = b.timeseries.pos_plot;
                const bounds = fitSceneBounds([pa, pb]);
                return [
                  cornerTrace(bounds),
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
                    name: labelA,
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
                    name: labelB,
                  },
                ];
              })(),
              layout: (function () {
                const pa = a.timeseries.pos_plot;
                const pb = b.timeseries.pos_plot;
                const bounds = fitSceneBounds([pa, pb]);
                return {
                  title: "Path overlay (N, E, up=−D)",
                  paper_bgcolor: "#0c1018",
                  plot_bgcolor: "#0c1018",
                  font: { color: "#e7ecf3", size: 11 },
                  height: 480,
                  margin: { t: 40, r: 0, b: 0, l: 0 },
                  uirevision: "compare-paths-" + a.id + "-" + b.id,
                  scene: {
                    xaxis: {
                      title: "N",
                      gridcolor: "#2d3a4d",
                      range: bounds.x,
                      autorange: false,
                    },
                    yaxis: {
                      title: "E",
                      gridcolor: "#2d3a4d",
                      range: bounds.y,
                      autorange: false,
                    },
                    zaxis: {
                      title: "up",
                      gridcolor: "#2d3a4d",
                      range: bounds.z,
                      autorange: false,
                    },
                    aspectmode: "manual",
                    aspectratio: bounds.ar,
                    bgcolor: "#0c1018",
                    camera: { eye: { x: 2.4, y: 2.4, z: 1.55 } },
                  },
                  legend: { orientation: "h" },
                };
              })(),
            })
          )
        : e(
            "div",
            { className: "card", style: { gridColumn: "1 / -1" } },
            e("h3", null, "Path overlay"),
            e(
              "p",
              { style: { color: "var(--muted)", margin: 0 } },
              "One or both selected runs have no timeseries in the gallery payload ",
              "(e.g. Monte Carlo-only cards). Metrics above still compare."
            )
          )
    );
  }

  function EstimationTab({ doc, onSelectRun }) {
    const matrix = doc.estimation_matrix;
    if (!matrix || !matrix.scenarios || !matrix.scenarios.length) {
      return e(
        "div",
        { className: "card" },
        e("h2", null, "Estimation / LQG"),
        e("p", { style: { color: "var(--muted)" } }, "No estimation matrix in this gallery.")
      );
    }
    const scenarios = matrix.scenarios;
    const columns = matrix.columns || [];
    // Grouped bar chart: x = sensor column, series = controller family
    const ctrlOrder = ["lqr", "pid"];
    const ctrlColors = { lqr: "#5b9fd4", pid: "#e6a05c" };
    const colIds = columns.length
      ? columns.map(function (c) {
          return c.id;
        })
      : scenarios.map(function (s) {
          return s.id;
        });
    const colLabels = columns.length
      ? columns.map(function (c) {
          return c.label;
        })
      : scenarios.map(function (s) {
          return s.label;
        });

    function rmseFor(colId, controller) {
      const s = scenarios.find(function (sc) {
        if (sc.column && sc.controller)
          return sc.column === colId && sc.controller === controller;
        // legacy single-row matrix
        return sc.id === colId;
      });
      if (!s || !s.metrics) return null;
      const v = s.metrics.rmse_position_m;
      return v != null && Number.isFinite(+v) ? +v : null;
    }

    const barTraces = ctrlOrder.map(function (ctrl) {
      const raw = colIds.map(function (cid) {
        return rmseFor(cid, ctrl);
      });
      const display = raw.map(function (v) {
        return v == null ? null : Math.min(v, 5);
      });
      return {
        x: colLabels,
        y: display,
        name: ctrl === "lqr" ? "LQR / LQG" : "PID",
        type: "bar",
        marker: { color: ctrlColors[ctrl] },
        text: raw.map(function (v) {
          return v == null ? "—" : v > 5 ? ">5 (" + fmt(v, 1) + ")" : fmt(v, 3);
        }),
        textposition: "outside",
        hovertemplate: "%{x}<br>" + (ctrl === "lqr" ? "LQR/LQG" : "PID") + " RMSE %{text}<extra></extra>",
      };
    });

    const plotTheme = {
      paper_bgcolor: "#0c1018",
      plot_bgcolor: "#0c1018",
      font: { color: "#e7ecf3", size: 11 },
      margin: { t: 48, r: 20, b: 80, l: 56 },
    };

    return e(
      "div",
      null,
      e(
        "div",
        { className: "card" },
        e("h2", null, matrix.title || "Controller × sensor matrix"),
        e("p", null, matrix.description || ""),
        e(
          "p",
          { style: { color: "var(--muted)", fontSize: "0.9rem" } },
          "Grouped bars: LQR/LQG vs PID per sensor column. Display capped at 5 m RMSE. ",
          "Click a table row to open Flight 3D."
        )
      ),
      e(
        "div",
        { className: "card" },
        e(PlotDiv, {
          id: "est-rmse-bars",
          data: barTraces,
          layout: {
            ...plotTheme,
            barmode: "group",
            height: 360,
            title: {
              text: "Position RMSE: LQR/LQG vs PID by sensors",
              font: { size: 13 },
            },
            yaxis: { title: "RMSE position [m] (display cap 5)", gridcolor: "#2a2f36" },
            xaxis: { tickangle: -18 },
            legend: { orientation: "h", y: 1.12 },
          },
        })
      ),
      e(
        "div",
        { className: "card" },
        e("h3", null, "Scenario table"),
        e(
          "div",
          { className: "table-wrap" },
          e(
            "table",
            { className: "metrics" },
            e(
              "thead",
              null,
              e(
                "tr",
                null,
                ["Scenario", "Law", "Sensors", "Method", "RMSE [m]", "max |e| [m]", "ok", "Lesson"].map(
                  function (h) {
                    return e("th", { key: h }, h);
                  }
                )
              )
            ),
            e(
              "tbody",
              null,
              scenarios.map(function (s, i) {
                const m = s.metrics || {};
                const ok = m.success;
                return e(
                  "tr",
                  {
                    key: s.id || i,
                    style: {
                      cursor: s.run_id ? "pointer" : "default",
                      color: ok === false ? "#e07070" : undefined,
                    },
                    onClick: function () {
                      if (s.run_id && onSelectRun) onSelectRun(s.run_id);
                    },
                  },
                  e("td", null, s.label),
                  e("td", null, s.controller === "pid" ? "PID" : s.controller === "lqr" ? "LQR" : "—"),
                  e("td", null, s.sensors),
                  e("td", null, s.method),
                  e("td", null, fmt(m.rmse_position_m, 4)),
                  e("td", null, fmt(m.max_position_error_m, 3)),
                  e(
                    "td",
                    null,
                    ok === true
                      ? "yes"
                      : ok === false
                        ? "no"
                        : "—",
                    m.time_in_bounds_frac != null
                      ? e(
                          "span",
                          { style: { color: "var(--muted)", fontSize: "0.8rem" } },
                          " (",
                          fmt(100 * m.time_in_bounds_frac, 0),
                          "% tib)"
                        )
                      : null
                  ),
                  e("td", { style: { maxWidth: "22rem", fontSize: "0.85rem" } }, s.lesson || "")
                );
              })
            )
          )
        )
      ),
      e(
        "div",
        { className: "card" },
        e("h3", null, "How to read this"),
        e(
          "ul",
          { style: { color: "var(--muted)", lineHeight: 1.5 } },
          e(
            "li",
            null,
            e("strong", null, "Filter benefit (either law): "),
            "GPS+IMU + KF ≪ naive partial on the same sensors."
          ),
          e(
            "li",
            null,
            e("strong", null, "Law comparison: "),
            "Ideal / filtered columns show whether PID or hover LQR tracks better under the same information."
          ),
          e(
            "li",
            null,
            e("strong", null, "GPS-denied: "),
            "Flow+alt (body velocity + height + gyro) is the practical win; ",
            "AHRS (att+ω) stays finite but weaker; IMU-only (ω) cannot observe position."
          ),
          e(
            "li",
            null,
            e("strong", null, "Naming: "),
            "LQG = linear KF + LQR. PID+KF is the cascade law on x_hat, not classical LQG."
          ),
          e(
            "li",
            null,
            e("strong", null, "Envelope tab: "),
            "limits of idealized full-state LQR when the path leaves the hover linearization — different question."
          )
        )
      )
    );
  }

  function EnvelopeTab({ doc }) {
    const env = doc.envelope;
    if (!env || !env.points || !env.points.length) {
      return e(
        "div",
        { className: "card" },
        e("h2", null, "Linearization envelope"),
        e(
          "p",
          { style: { color: "var(--muted)" } },
          "No envelope series in this gallery. Rebuild with ",
          e("code", null, "uv run uavsim gallery --base-case"),
          " (omit ",
          e("code", null, "--skip-envelope"),
          ")."
        )
      );
    }

    const laws = ["lqr", "lqg"];
    const colors = { lqr: "#5b9fd4", lqg: "#c9a227" };
    const points = env.points;
    const plotTheme = {
      paper_bgcolor: "#0c1018",
      plot_bgcolor: "#0c1018",
      font: { color: "#e7ecf3", size: 11 },
      margin: { t: 36, r: 12, b: 40, l: 48 },
    };

    function seriesFor(law, xKey, yKey, yScale) {
      const xs = [];
      const ys = [];
      const texts = [];
      const symbols = [];
      points
        .filter(function (p) {
          return p.law === law;
        })
        .sort(function (a, b) {
          return (a.time_scale || 0) - (b.time_scale || 0);
        })
        .forEach(function (p) {
          const x = p[xKey];
          const y = p[yKey];
          if (x == null || y == null) return;
          if (!Number.isFinite(+x) || !Number.isFinite(+y)) return;
          xs.push(+x);
          ys.push(+y * (yScale || 1));
          texts.push(
            law.toUpperCase() +
              " τ=" +
              p.time_scale +
              "<br>peak tilt " +
              fmt(p.peak_tilt_deg, 1) +
              "°" +
              "<br>rmse " +
              fmt(p.rmse_position_m, 3) +
              " m" +
              "<br>" +
              (p.success ? "success" : "FAIL")
          );
          symbols.push(p.success ? "circle" : "x");
        });
      return {
        x: xs,
        y: ys,
        text: texts,
        mode: "lines+markers",
        name: law.toUpperCase(),
        line: { color: colors[law] || "#aaa", width: 2 },
        marker: {
          size: 10,
          color: colors[law] || "#aaa",
          symbol: symbols,
          line: { width: 1, color: "#111" },
        },
        hovertemplate: "%{text}<extra></extra>",
      };
    }

    const plotRmseVsTau = {
      data: laws.map(function (law) {
        return seriesFor(law, "time_scale", "rmse_position_m", 1);
      }),
      layout: {
        ...plotTheme,
        height: 360,
        title: { text: "Position RMSE vs time scale τ (1 = portfolio path)", font: { size: 13 } },
        xaxis: {
          title: "τ (smaller = faster / more aggressive)",
          gridcolor: "#2a2f36",
          autorange: "reversed",
        },
        yaxis: { title: "RMSE position [m]", gridcolor: "#2a2f36", type: "log" },
        legend: { orientation: "h" },
        margin: { t: 48, r: 20, b: 48, l: 56 },
      },
    };

    const plotRmseVsTilt = {
      data: laws.map(function (law) {
        return seriesFor(law, "peak_tilt_deg", "rmse_position_m", 1);
      }),
      layout: {
        ...plotTheme,
        height: 360,
        title: {
          text: "Position RMSE vs peak plant tilt (linearization distance)",
          font: { size: 13 },
        },
        xaxis: { title: "Peak |φ| or |θ| [deg]", gridcolor: "#2a2f36" },
        yaxis: { title: "RMSE position [m]", gridcolor: "#2a2f36", type: "log" },
        legend: { orientation: "h" },
        margin: { t: 48, r: 20, b: 48, l: 56 },
        shapes: [
          {
            type: "line",
            x0: 15,
            x1: 15,
            y0: 0,
            y1: 1,
            yref: "paper",
            line: { color: "rgba(200,120,80,0.7)", width: 1, dash: "dot" },
          },
        ],
        annotations: [
          {
            x: 15,
            y: 1,
            yref: "paper",
            text: "~15° small-angle ref",
            showarrow: false,
            xanchor: "left",
            font: { size: 10, color: "#c87850" },
          },
        ],
      },
    };

    const b = env.boundary || {};
    const rows = points
      .slice()
      .sort(function (a, c) {
        if (a.time_scale !== c.time_scale) return c.time_scale - a.time_scale;
        return String(a.law).localeCompare(String(c.law));
      });

    return e(
      "div",
      null,
      e(
        "div",
        { className: "card" },
        e("h2", null, env.title || "Linearization envelope"),
        e("p", null, env.description || ""),
        e(
          "div",
          { className: "metric-grid" },
          laws.map(function (law) {
            const bb = b[law] || {};
            return e(
              "div",
              { key: law, className: "metric" },
              e("div", { className: "k" }, law.toUpperCase() + " last success τ"),
              e("div", { className: "v" }, fmt(bb.last_success_time_scale, 2)),
              e(
                "div",
                { className: "k", style: { marginTop: "0.35rem" } },
                "first fail τ / peak tilt"
              ),
              e(
                "div",
                { className: "v" },
                (bb.first_fail_time_scale != null ? fmt(bb.first_fail_time_scale, 2) : "—") +
                  " / " +
                  (bb.first_fail_peak_tilt_deg != null
                    ? fmt(bb.first_fail_peak_tilt_deg, 1) + "°"
                    : "—")
              )
            );
          })
        ),
        (env.notes || []).map(function (n, i) {
          return e("p", { key: i, style: { color: "var(--muted)", fontSize: "0.9rem" } }, "• " + n);
        })
      ),
      e("div", { className: "card" }, e(PlotDiv, { id: "env-rmse-tau", ...plotRmseVsTau })),
      e("div", { className: "card" }, e(PlotDiv, { id: "env-rmse-tilt", ...plotRmseVsTilt })),
      e(
        "div",
        { className: "card" },
        e("h3", null, "Sweep table"),
        e(
          "div",
          { className: "table-wrap" },
          e(
            "table",
            { className: "metrics" },
            e(
              "thead",
              null,
              e(
                "tr",
                null,
                ["τ", "law", "success", "RMSE pos [m]", "max pos [m]", "peak tilt [°]", "peak v [m/s]"].map(
                  function (h) {
                    return e("th", { key: h }, h);
                  }
                )
              )
            ),
            e(
              "tbody",
              null,
              rows.map(function (p, i) {
                return e(
                  "tr",
                  {
                    key: i,
                    style: p.success ? undefined : { color: "#e07070" },
                  },
                  e("td", null, fmt(p.time_scale, 2)),
                  e("td", null, String(p.law).toUpperCase()),
                  e("td", null, p.success ? "yes" : "no"),
                  e("td", null, fmt(p.rmse_position_m, 4)),
                  e("td", null, fmt(p.max_position_error_m, 3)),
                  e("td", null, fmt(p.peak_tilt_deg, 1)),
                  e("td", null, fmt(p.peak_speed_m_s, 2))
                );
              })
            )
          )
        )
      )
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
      ["estimation", "Estimation"],
      ["flight", "Flight 3D"],
      ["metrics", "Metrics"],
      ["monte_carlo", "Monte Carlo"],
      ["envelope", "Envelope"],
      ["compare", "Compare"],
    ];

    let body;
    if (tab === "overview") body = e(Overview, { doc, onSelect: (id) => { setRunId(id); setTab("flight"); } });
    else if (tab === "estimation")
      body = e(EstimationTab, {
        doc,
        onSelectRun: (id) => {
          setRunId(id);
          setTab("flight");
        },
      });
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
    } else if (tab === "envelope") body = e(EnvelopeTab, { doc });
    else if (tab === "compare") body = e(CompareTab, { doc });

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
