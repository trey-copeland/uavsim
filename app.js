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

  /** Resolve mission catalog entry (dual-mission showcase). */
  function getMission(doc, missionId) {
    const missions = (doc && doc.missions) || [];
    if (!missions.length) return null;
    return (
      missions.find(function (m) {
        return m.id === missionId;
      }) || missions[0]
    );
  }

  /** Runs belonging to the selected mission (legacy docs: all runs). */
  function runsForMission(doc, missionId) {
    const runs = (doc && doc.runs) || [];
    const mission = getMission(doc, missionId);
    if (!mission) return runs;
    if (mission.run_ids && mission.run_ids.length) {
      const allow = {};
      mission.run_ids.forEach(function (id) {
        allow[id] = true;
      });
      const filtered = runs.filter(function (r) {
        return allow[r.id];
      });
      if (filtered.length) return filtered;
    }
    const mid = mission.id;
    const byMid = runs.filter(function (r) {
      return r.mission_id === mid;
    });
    return byMid.length ? byMid : runs;
  }

  /** Scenario run_id for the active mission. */
  function scenarioRunId(sc, missionId) {
    if (!sc) return null;
    const map = sc.run_id_by_mission;
    if (map && missionId && map[missionId]) return map[missionId];
    return sc.run_id || null;
  }

  /** Scenario metrics for the active mission. */
  function scenarioMetrics(sc, missionId, byId) {
    if (!sc) return {};
    const map = sc.metrics_by_mission;
    if (map && missionId && map[missionId]) return map[missionId];
    const rid = scenarioRunId(sc, missionId);
    if (rid && byId && byId[rid] && byId[rid].metrics) return byId[rid].metrics;
    return sc.metrics || {};
  }

  /** Segmented mission control (2 options → chips, not a dropdown). */
  function MissionSelector({ doc, missionId, onChange, className, showHint }) {
    const missions = (doc && doc.missions) || [];
    if (!missions.length) return null;
    const activeId = missionId || missions[0].id;
    const active = getMission(doc, activeId);
    return e(
      "div",
      { className: "mission-selector " + (className || "") },
      e("span", { className: "mission-label", id: "mission-label" }, "Mission"),
      e(
        "div",
        {
          className: "mission-seg",
          role: "group",
          "aria-labelledby": "mission-label",
        },
        missions.map(function (m) {
          const on = m.id === activeId;
          return e(
            "button",
            {
              key: m.id,
              type: "button",
              className: "mission-seg-btn" + (on ? " active" : ""),
              "aria-pressed": on ? "true" : "false",
              onClick: function () {
                if (!on) onChange(m.id);
              },
            },
            m.short_label || m.label || m.id
          );
        })
      ),
      showHint && active && active.description
        ? e("span", { className: "mission-hint", title: active.description }, active.description)
        : null
    );
  }

  /** Compact in-tab reminder — primary control stays in the sticky header. */
  function ActiveMissionChip({ doc, missionId }) {
    const m = getMission(doc, missionId);
    if (!m) return null;
    return e(
      "span",
      { className: "active-mission-chip", title: m.description || "" },
      "Active mission · ",
      e("strong", null, m.short_label || m.label || m.id)
    );
  }

  /** 4-step walkthrough for first-time readers. */
  function StoryStrip({ activeTab, onNavigate }) {
    const steps = [
      { id: "overview", n: "1", label: "Matrix", blurb: "12 stacks" },
      { id: "flight", n: "2", label: "Flight", blurb: "scrub trajectory" },
      { id: "estimation", n: "3", label: "Laws", blurb: "LQR vs PID" },
      { id: "envelope", n: "4", label: "Envelope", blurb: "vs time scale τ" },
    ];
    return e(
      "nav",
      { className: "story-strip", "aria-label": "Suggested walkthrough" },
      e("span", { className: "story-strip-label" }, "Walkthrough"),
      steps.map(function (s, i) {
        const on = activeTab === s.id;
        return e(
          React.Fragment,
          { key: s.id },
          i > 0 ? e("span", { className: "story-arrow", "aria-hidden": "true" }, "→") : null,
          e(
            "button",
            {
              type: "button",
              className: "story-step" + (on ? " active" : ""),
              onClick: function () {
                onNavigate(s.id);
              },
              "aria-current": on ? "step" : undefined,
            },
            e("span", { className: "story-n" }, s.n),
            e("span", { className: "story-text" },
              e("span", { className: "story-title" }, s.label),
              e("span", { className: "story-blurb" }, s.blurb)
            )
          )
        );
      })
    );
  }

  const VALUE_PROP =
    "SIL comparison of hover LQR and cascade PID under the same sensor suites.";
  const DEFAULT_TITLE = "uavsim · controller × sensor flight study";
  /** Fallback About panel when gallery JSON has no ui.about_paragraphs */
  const ABOUT_PARAGRAPHS = [
    "Offline SIL results for a quadrotor figure-eight: the same path flown by hover LQR and cascade PID under several sensor suites (ideal full state, GPS+IMU naive, GPS+IMU + linear KF, AHRS, optical-flow proxy + altitude, IMU-only).",
    "Two missions share that geometry. Baseline uses constant yaw and the portfolio timing. Near-envelope compresses time (τ★≈0.28) and adds scheduled yaw so tilt and heading demand are visible under ideal LQR.",
    "Ideal full-state is the tracking upper bound. Stacks that do not observe position (or feed an incomplete state bus) are expected to exceed the position bound; those cases are included on purpose.",
    "Also included: Monte Carlo on GPS+IMU LQG, and a time-scale envelope over every matrix stack. Simulation only — not flight software.",
  ];

  /** GPS+IMU naive vs KF columns (same bus; shows value of a state estimate). */
  const TEACHING_PAIR_COLUMNS = { gps_imu_naive: true, gps_imu_filter: true };

  function sortToggle(cur, key) {
    if (cur.key === key) return { key: key, dir: cur.dir === "asc" ? "desc" : "asc" };
    return { key: key, dir: key === "scheme" || key === "family" || key === "label" || key === "sensors" || key === "method" || key === "lesson" || key === "law" ? "asc" : "desc" };
  }

  function thSortable(label, key, sortState, setSort) {
    const active = sortState.key === key;
    const arrow = active ? (sortState.dir === "asc" ? " ▲" : " ▼") : "";
    return e(
      "th",
      {
        key: key,
        className: "sortable" + (active ? " sorted" : ""),
        onClick: function () {
          setSort(sortToggle(sortState, key));
        },
        title: "Sort by " + label,
      },
      label + arrow
    );
  }

  function fmtMaybe(v, digits) {
    if (v == null || !Number.isFinite(+v)) return "—";
    const x = +v;
    if (Math.abs(x) >= 1000) return x.toExponential(1);
    if (Math.abs(x) >= 100) return x.toFixed(0);
    return fmt(x, digits);
  }

  function cmpTableVal(a, c, key) {
    let va = a[key];
    let vc = c[key];
    if (key === "success") {
      va = a.success ? 1 : 0;
      vc = c.success ? 1 : 0;
    }
    if (va == null && vc == null) return 0;
    if (va == null) return 1;
    if (vc == null) return -1;
    if (typeof va === "string") return String(va).localeCompare(String(vc));
    return va - vc;
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

  function Overview({
    doc,
    onSelect,
    missionId,
    onOpenHeroFlight,
    onGoEstimation,
    onGoEnvelope,
  }) {
    const mission = getMission(doc, missionId);
    const runs = runsForMission(doc, missionId);
    const byId = {};
    (doc.runs || []).forEach(function (r) {
      byId[r.id] = r;
    });
    const matrix = doc.estimation_matrix;
    const columns = (matrix && matrix.columns) || null;
    const rowDefs = (matrix && matrix.rows) || null;
    const scenarios = (matrix && matrix.scenarios) || [];
    const [highlightPair, setHighlightPair] = useState(true);

    function fmtRmse(v) {
      if (v === null || v === undefined || !Number.isFinite(+v)) return "—";
      const x = +v;
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
      const rid = scenarioRunId(sc, missionId);
      const run = rid ? byId[rid] : null;
      const m = scenarioMetrics(sc, missionId, byId);
      const ok = m.success;
      const tib = m.time_in_bounds_frac;
      const tibStr =
        tib != null && Number.isFinite(+tib) ? Math.round(100 * +tib) + "% in-bound" : null;
      const teach =
        highlightPair && sc.column && TEACHING_PAIR_COLUMNS[sc.column];
      return e(
        "div",
        {
          key: (sc.id || rid) + ":" + (missionId || ""),
          className:
            "matrix-cell card" +
            (ok === false ? " cell-fail" : "") +
            (teach ? " cell-teach" : ""),
          style: { cursor: rid ? "pointer" : "default" },
          onClick: function () {
            if (rid && onSelect) onSelect(rid);
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
          e("span", { className: ok ? "ok" : "fail" }, ok === true ? "pass" : ok === false ? "fail" : "—"),
          e("span", { className: "matrix-meta-sec" }, " · max |e| ", fmtMaxE(m.max_position_error_m), " m"),
          tibStr ? e("span", { className: "matrix-meta-sec" }, " · ", tibStr) : null
        )
      );
    }

    const matrixRunIds = {};
    scenarios.forEach(function (s) {
      const rid = scenarioRunId(s, missionId);
      if (rid) matrixRunIds[rid] = true;
    });
    const extra = runs.filter(function (r) {
      return !matrixRunIds[r.id];
    });

    const gridBlock =
      columns && rowDefs && scenarios.length
        ? e(
            "div",
            { className: "card matrix-wrap", style: { gridColumn: "1 / -1" } },
            e(
              "div",
              { className: "row matrix-mission-row" },
              e("h2", { style: { margin: 0, flex: "1 1 auto" } }, matrix.title || "Controller × sensor matrix"),
              e(ActiveMissionChip, { doc: doc, missionId: missionId })
            ),
            e(
              "p",
              { className: "matrix-lead" },
              "Position RMSE for each controller×sensor cell. Click a cell to open Flight 3D. ",
              "Read ",
              e("strong", null, "down a column"),
              " (same sensors, different law) or ",
              e("strong", null, "across a row"),
              " (same law, fewer measurements)."
            ),
            e(
              "div",
              { className: "matrix-legend" },
              e("span", { className: "legend-item" }, e("span", { className: "lg pass" }), " within bound"),
              e("span", { className: "legend-item" }, e("span", { className: "lg fail" }), " exceeds bound"),
              e("span", { className: "legend-item" }, e("span", { className: "lg teach" }), " GPS+IMU naive vs KF"),
              e("span", { className: "legend-item muted" }, "click → Flight"),
              e(
                "label",
                { className: "legend-toggle" },
                e("input", {
                  type: "checkbox",
                  checked: highlightPair,
                  onChange: function (ev) {
                    setHighlightPair(ev.target.checked);
                  },
                }),
                " Highlight GPS+IMU naive vs KF"
              )
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
                    return e("col", {
                      key: c.id,
                      className:
                        "sensor" +
                        (highlightPair && TEACHING_PAIR_COLUMNS[c.id] ? " col-teach" : ""),
                    });
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
                        {
                          key: c.id,
                          className:
                            highlightPair && TEACHING_PAIR_COLUMNS[c.id] ? "th-teach" : "",
                        },
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
      { className: "grid cols-3 overview-grid" },
      e(
        "div",
        { className: "card hero-cta", style: { gridColumn: "1 / -1" } },
        e("div", { className: "hero-cta-body" },
          e("div", { className: "hero-cta-kicker" }, "Suggested first look"),
          e("h2", { className: "hero-cta-title" }, "Flight 3D on the near-envelope mission"),
          e(
            "p",
            { className: "hero-cta-copy" },
            "Start on the near-envelope mission in Flight 3D (τ★≈0.28 + scheduled yaw) so tilt and heading change under ideal LQR are easy to see. The matrix and envelope tabs use the same stacks for cross-comparison."
          ),
          e(
            "div",
            { className: "hero-cta-actions" },
            e(
              "button",
              {
                type: "button",
                className: "btn-primary",
                onClick: function () {
                  if (onOpenHeroFlight) onOpenHeroFlight();
                },
              },
              "Open Flight · envelope edge"
            ),
            e(
              "button",
              {
                type: "button",
                className: "btn-ghost",
                onClick: function () {
                  if (onGoEstimation) onGoEstimation();
                },
              },
              "LQR vs PID by sensors"
            ),
            e(
              "button",
              {
                type: "button",
                className: "btn-ghost",
                onClick: function () {
                  if (onGoEnvelope) onGoEnvelope();
                },
              },
              "Tracking vs time scale τ"
            )
          )
        )
      ),
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
            " m · ",
            e("span", { className: m.success ? "ok" : "fail" }, m.success ? "pass" : "fail")
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
      })
    );
  }

  function FlightTab({ run }) {
    const ts = run.timeseries;
    const [frame, setFrame] = useState(0);
    useEffect(() => {
      setFrame(0);
    }, [run && run.id]);

    // ← / → step scrubber (Shift = ±10 frames). Ignore when typing in form fields.
    useEffect(() => {
      if (!ts) return;
      const nFrames = ts.t.length;
      function onKey(ev) {
        if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
        const tag = (ev.target && ev.target.tagName) || "";
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
          // Still allow arrows on the range slider itself
          if (!(ev.target.type === "range")) return;
        }
        if (ev.target && ev.target.isContentEditable) return;
        const step = ev.shiftKey ? 10 : 1;
        const delta = ev.key === "ArrowRight" ? step : -step;
        ev.preventDefault();
        setFrame(function (prev) {
          const next = prev + delta;
          if (next < 0) return 0;
          if (next > nFrames - 1) return nFrames - 1;
          return next;
        });
      }
      window.addEventListener("keydown", onKey);
      return function () {
        window.removeEventListener("keydown", onKey);
      };
    }, [ts, run && run.id]);

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
            title: "Drag or use ← → keys (Shift for ±10)",
          }),
          e(
            "span",
            { className: "flight-frame mono muted" },
            i + 1,
            " / ",
            n
          ),
          e(
            "span",
            { className: "flight-keys muted", title: "Keyboard" },
            "← →"
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

  function CompareTab({ doc, missionId }) {
    const mission = getMission(doc, missionId);
    const runs = runsForMission(doc, missionId);
    // Prefer runs with metrics; timeseries optional for path overlay
    const candidates = runs.filter(function (r) {
      return r && r.metrics;
    });
    const defaults = doc.compare || {};
    const missionCompare = (mission && mission.compare_ids) || null;
    const preferredA = (missionCompare && missionCompare[0]) || defaults.a;
    const preferredB = (missionCompare && missionCompare[1]) || defaults.b;
    const defaultA =
      (preferredA && candidates.some(function (r) {
        return r.id === preferredA;
      })
        ? preferredA
        : null) ||
      (candidates[0] && candidates[0].id) ||
      "";
    const defaultB =
      (preferredB && candidates.some(function (r) {
        return r.id === preferredB;
      })
        ? preferredB
        : null) ||
      (candidates[1] && candidates[1].id) ||
      (candidates[0] && candidates[0].id) ||
      "";

    const [idA, setIdA] = useState(defaultA);
    const [idB, setIdB] = useState(defaultB);

    // Mission change rebinds A/B to that mission's teaching pair
    useEffect(
      function () {
        if (defaultA) setIdA(defaultA);
        if (defaultB) setIdB(defaultB);
      },
      [missionId, defaultA, defaultB]
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
        e(
          "div",
          { className: "row matrix-mission-row" },
          e("h2", { style: { margin: 0, flex: "1 1 auto" } }, "Compare runs"),
          e(ActiveMissionChip, { doc: doc, missionId: missionId })
        ),
        e(
          "p",
          { className: "compare-caption" },
          e("strong", null, "Default pair: "),
          "GPS+IMU naive → LQR vs GPS+IMU LQG (same measurements; KF reconstructs state). ",
          "Table values are B − A. Path overlay requires timeseries on both runs."
        ),
        e(
          "p",
          { style: { color: "var(--muted)", fontSize: "0.85rem", marginTop: 0 } },
          "Select any two runs for the active mission."
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

  function EstimationTab({ doc, onSelectRun, missionId }) {
    const matrix = doc.estimation_matrix;
    if (!matrix || !matrix.scenarios || !matrix.scenarios.length) {
      return e(
        "div",
        { className: "card" },
        e("h2", null, "LQR vs PID by sensors"),
        e("p", { style: { color: "var(--muted)" } }, "No estimation matrix in this gallery.")
      );
    }
    const scenarios = matrix.scenarios;
    const columns = matrix.columns || [];
    const byId = {};
    (doc.runs || []).forEach(function (r) {
      byId[r.id] = r;
    });
    const mission = getMission(doc, missionId);
    const [rowSuccess, setRowSuccess] = useState("all");
    const [rowQuery, setRowQuery] = useState("");
    const [rowSort, setRowSort] = useState({ key: "rmse_position_m", dir: "asc" });

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
        return sc.id === colId;
      });
      if (!s) return null;
      const m = scenarioMetrics(s, missionId, byId);
      const v = m.rmse_position_m;
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

    const tableRows = scenarios
      .map(function (s) {
        const rid = scenarioRunId(s, missionId);
        const m = scenarioMetrics(s, missionId, byId);
        return {
          id: s.id,
          run_id: rid,
          label: s.label || s.id,
          law: s.controller === "pid" ? "PID" : s.controller === "lqr" ? "LQR" : "—",
          family: s.controller || "—",
          sensors: s.sensors || "—",
          method: s.method || "—",
          rmse_position_m: m.rmse_position_m,
          max_position_error_m: m.max_position_error_m,
          success: m.success,
          time_in_bounds_frac: m.time_in_bounds_frac,
          lesson: s.lesson || "",
        };
      })
      .filter(function (r) {
        if (rowSuccess === "ok" && !r.success) return false;
        if (rowSuccess === "fail" && r.success) return false;
        if (rowQuery) {
          const q = rowQuery.toLowerCase();
          const blob = [r.label, r.law, r.sensors, r.method, r.lesson].join(" ").toLowerCase();
          if (blob.indexOf(q) < 0) return false;
        }
        return true;
      })
      .sort(function (a, c) {
        const dir = rowSort.dir === "asc" ? 1 : -1;
        return dir * cmpTableVal(a, c, rowSort.key);
      });

    return e(
      "div",
      null,
      e(
        "div",
        { className: "card" },
        e(
          "div",
          { className: "row matrix-mission-row" },
          e("h2", { style: { margin: 0, flex: "1 1 auto" } }, "LQR vs PID by sensor suite"),
          e(ActiveMissionChip, { doc: doc, missionId: missionId })
        ),
        e(
          "p",
          { className: "matrix-lead" },
          "Same cells as Overview, plotted as grouped bars. ",
          "Compare laws under identical measurements; compare ",
          e("strong", null, "GPS+IMU naive"),
          " (partial bus) to ",
          e("strong", null, "GPS+IMU + linear KF"),
          " on that bus. Bar display is capped at 5 m RMSE."
        )
      ),
      e(
        "div",
        { className: "card" },
        e(PlotDiv, {
          id: "est-rmse-bars-" + (missionId || "default"),
          data: barTraces,
          layout: {
            ...plotTheme,
            barmode: "group",
            height: 360,
            title: {
              text:
                "Position RMSE by sensor column" +
                (mission ? " · " + (mission.short_label || mission.label) : ""),
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
          "p",
          { style: { color: "var(--muted)", fontSize: "0.85rem", marginTop: 0 } },
          "Click a row to open Flight 3D. Sort headers · filter by pass/fail · search."
        ),
        e(
          "div",
          { className: "row data-table-toolbar" },
          e(
            "label",
            { className: "toolbar-field" },
            e("span", null, "Bound"),
            e(
              "select",
              {
                value: rowSuccess,
                onChange: function (ev) {
                  setRowSuccess(ev.target.value);
                },
              },
              e("option", { value: "all" }, "All"),
              e("option", { value: "ok" }, "Within bound"),
              e("option", { value: "fail" }, "Exceeds bound")
            )
          ),
          e(
            "label",
            { className: "toolbar-field grow" },
            e("span", null, "Search"),
            e("input", {
              type: "search",
              placeholder: "scenario, sensors, method…",
              value: rowQuery,
              onChange: function (ev) {
                setRowQuery(ev.target.value);
              },
            })
          ),
          e(
            "span",
            { className: "toolbar-count" },
            tableRows.length,
            " / ",
            scenarios.length,
            " rows"
          )
        ),
        e(
          "div",
          { className: "table-wrap data-table-wrap scroll-y" },
          e(
            "table",
            { className: "metrics data-table sticky-head" },
            e(
              "thead",
              null,
              e(
                "tr",
                null,
                thSortable("Scenario", "label", rowSort, setRowSort),
                thSortable("Law", "law", rowSort, setRowSort),
                thSortable("Sensors", "sensors", rowSort, setRowSort),
                thSortable("Method", "method", rowSort, setRowSort),
                thSortable("RMSE [m]", "rmse_position_m", rowSort, setRowSort),
                thSortable("max |e| [m]", "max_position_error_m", rowSort, setRowSort),
                thSortable("OK", "success", rowSort, setRowSort),
                thSortable("Notes", "lesson", rowSort, setRowSort)
              )
            ),
            e(
              "tbody",
              null,
              tableRows.length
                ? tableRows.map(function (r) {
                    return e(
                      "tr",
                      {
                        key: r.id + ":" + (missionId || ""),
                        className: (r.success === false ? "row-fail" : "") + (r.run_id ? " row-click" : ""),
                        style: { cursor: r.run_id ? "pointer" : "default" },
                        onClick: function () {
                          if (r.run_id && onSelectRun) onSelectRun(r.run_id);
                        },
                        title: r.run_id ? "Open Flight 3D" : "",
                      },
                      e("td", null, r.label),
                      e("td", null, r.law),
                      e("td", null, r.sensors),
                      e("td", null, r.method),
                      e("td", { className: "num" }, fmtMaybe(r.rmse_position_m, 4)),
                      e("td", { className: "num" }, fmtMaybe(r.max_position_error_m, 3)),
                      e(
                        "td",
                        null,
                        e(
                          "span",
                          { className: r.success ? "pill ok" : "pill fail" },
                          r.success === true ? "pass" : r.success === false ? "fail" : "—"
                        ),
                        r.time_in_bounds_frac != null
                          ? e(
                              "span",
                              { className: "table-sub" },
                              " ",
                              fmt(100 * r.time_in_bounds_frac, 0),
                              "% tib"
                            )
                          : null
                      ),
                      e(
                        "td",
                        { className: "td-notes", title: r.lesson },
                        r.lesson || "—"
                      )
                    );
                  })
                : e(
                    "tr",
                    null,
                    e("td", { colSpan: 8, style: { color: "var(--muted)" } }, "No rows match filters.")
                  )
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
          { className: "readout-list" },
          e(
            "li",
            null,
            e("strong", null, "Naive vs KF (same GPS+IMU bus): "),
            "partial_raw leaves zeros for unmeasured states; linear KF reconstructs a full x̂ for the law."
          ),
          e(
            "li",
            null,
            e("strong", null, "LQR vs PID: "),
            "same sensors and (when used) the same KF — only the control law changes."
          ),
          e(
            "li",
            null,
            e("strong", null, "GPS-denied columns: "),
            "flow+alt (body_vel + alt + ω) is navigable; AHRS (att+ω) stays finite but drifts in position; IMU-only (ω) does not observe position."
          ),
          e(
            "li",
            null,
            e("strong", null, "Naming: "),
            "LQG here means linear KF + hover LQR. PID+KF is cascade PID on x̂, not classical LQG design."
          ),
          e(
            "li",
            null,
            e("strong", null, "Envelope tab: "),
            "same stacks swept over mission time scale τ (plant aggression), not a new sensor set."
          )
        )
      )
    );
  }

  /** Stable colors for envelope scheme series (matrix cells). */
  const ENVELOPE_SCHEME_COLORS = {
    ideal_lqr: "#5b9fd4",
    gps_imu_naive_lqr: "#e07070",
    gps_imu_lqg: "#3ecf8e",
    ahrs_lqg: "#c9a227",
    flow_alt_lqg: "#7c6cf0",
    imu_only_lqg: "#9aa0a6",
    ideal_pid: "#5bc0de",
    gps_imu_naive_pid: "#f0a0a0",
    gps_imu_kf_pid: "#6edc9a",
    ahrs_kf_pid: "#e6b450",
    flow_alt_kf_pid: "#a89cf5",
    imu_only_kf_pid: "#b0b5ba",
    lqr: "#5b9fd4",
    lqg: "#c9a227",
    pid: "#5bc0de",
  };

  // Plot windows: fly-away schemes (naive/IMU) otherwise stretch axes to 10⁴° / km RMSE
  const ENV_PLOT_TILT_MAX_DEG = 75;
  const ENV_PLOT_RMSE_MAX_M = 5;
  const ENV_PLOT_RMSE_MIN_M = 1e-4;

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

    const points = env.points;
    const schemeMeta = env.schemes || env.laws || [];
    const lawIds = [];
    const seen = {};
    (schemeMeta.length ? schemeMeta : points).forEach(function (s) {
      const id = s.id || s.law;
      if (!id || seen[id]) return;
      seen[id] = true;
      lawIds.push(id);
    });
    points.forEach(function (p) {
      if (p.law && !seen[p.law]) {
        seen[p.law] = true;
        lawIds.push(p.law);
      }
    });

    const labelOf = {};
    const familyOf = {};
    schemeMeta.forEach(function (s) {
      const id = s.id || s.law;
      if (!id) return;
      labelOf[id] = s.label || id;
      familyOf[id] = s.family || (String(id).indexOf("pid") >= 0 ? "pid" : "lqr");
    });
    points.forEach(function (p) {
      if (p.law && p.label) labelOf[p.law] = p.label;
      if (p.law && p.family) familyOf[p.law] = p.family;
    });

    const ENV_DEFAULT_ON = {
      ideal_lqr: true,
      ideal_pid: true,
      gps_imu_lqg: true,
      flow_alt_lqg: true,
      gps_imu_naive_lqr: true,
    };
    const [familyFilter, setFamilyFilter] = useState("all");
    const [visible, setVisible] = useState(function () {
      const init = {};
      lawIds.forEach(function (id) {
        // Recommended teaching set by default — not all 12 (reduces plot noise)
        init[id] = !!ENV_DEFAULT_ON[id];
        if (!Object.keys(ENV_DEFAULT_ON).length) init[id] = true;
      });
      // If none of the defaults exist (legacy data), show all
      const any = lawIds.some(function (id) {
        return init[id];
      });
      if (!any) {
        lawIds.forEach(function (id) {
          init[id] = true;
        });
      }
      return init;
    });
    const [sweepOpen, setSweepOpen] = useState(false);
    // Sweep table state
    const [sweepSuccess, setSweepSuccess] = useState("all"); // all | ok | fail
    const [sweepQuery, setSweepQuery] = useState("");
    const [sweepSort, setSweepSort] = useState({ key: "time_scale", dir: "desc" });
    // Boundary summary sort
    const [boundSort, setBoundSort] = useState({ key: "last_ok", dir: "desc" });

    const activeLaws = lawIds.filter(function (id) {
      if (!visible[id]) return false;
      if (familyFilter === "all") return true;
      return (familyOf[id] || "lqr") === familyFilter;
    });

    const activeSet = {};
    activeLaws.forEach(function (id) {
      activeSet[id] = true;
    });

    const plotTheme = {
      paper_bgcolor: "#0c1018",
      plot_bgcolor: "#0c1018",
      font: { color: "#e7ecf3", size: 11 },
    };

    function hoverText(name, p, clippedNote) {
      return (
        name +
        "<br>τ=" +
        p.time_scale +
        "<br>peak tilt " +
        fmt(p.peak_tilt_deg, 1) +
        "°" +
        "<br>rmse " +
        fmt(p.rmse_position_m, 3) +
        " m" +
        "<br>" +
        (p.success ? "success" : "FAIL") +
        (clippedNote || "")
      );
    }

    /** Series for τ plot — clamp RMSE for display so fly-aways don't dominate. */
    function seriesRmseVsTau(law) {
      const name = labelOf[law] || law;
      const xs = [];
      const ys = [];
      const texts = [];
      const symbols = [];
      const sizes = [];
      points
        .filter(function (p) {
          return p.law === law;
        })
        .sort(function (a, b) {
          return (a.time_scale || 0) - (b.time_scale || 0);
        })
        .forEach(function (p) {
          const x = p.time_scale;
          const y = p.rmse_position_m;
          if (x == null || y == null) return;
          if (!Number.isFinite(+x) || !Number.isFinite(+y) || +y <= 0) return;
          const yPlot = Math.min(Math.max(+y, ENV_PLOT_RMSE_MIN_M), ENV_PLOT_RMSE_MAX_M);
          const clipped = +y > ENV_PLOT_RMSE_MAX_M;
          xs.push(+x);
          ys.push(yPlot);
          texts.push(hoverText(name, p, clipped ? "<br>(RMSE clipped for scale)" : ""));
          symbols.push(p.success ? "circle" : "x");
          sizes.push(clipped ? 10 : 8);
        });
      const col = ENVELOPE_SCHEME_COLORS[law] || "#aaa";
      return {
        x: xs,
        y: ys,
        text: texts,
        mode: "lines+markers",
        name: name,
        line: {
          color: col,
          width: 2,
          dash: (familyOf[law] || "") === "pid" ? "dash" : "solid",
        },
        marker: {
          size: sizes,
          color: col,
          symbol: symbols,
          line: { width: 1, color: "#111" },
        },
        hovertemplate: "%{text}<extra></extra>",
      };
    }

    /**
     * Tilt plot: only plot points inside a sane attitude window.
     * Wild tumbles (naive/IMU) sit on a right-edge "off-scale" marker instead of
     * stretching the x-axis to 10⁴°.
     */
    function seriesRmseVsTilt(law) {
      const name = labelOf[law] || law;
      const xs = [];
      const ys = [];
      const texts = [];
      const symbols = [];
      const sizes = [];
      const xOff = [];
      const yOff = [];
      const tOff = [];
      points
        .filter(function (p) {
          return p.law === law;
        })
        .sort(function (a, b) {
          return (a.peak_tilt_deg || 0) - (b.peak_tilt_deg || 0);
        })
        .forEach(function (p) {
          const tilt = p.peak_tilt_deg;
          const y = p.rmse_position_m;
          if (tilt == null || y == null) return;
          if (!Number.isFinite(+tilt) || !Number.isFinite(+y) || +y <= 0) return;
          const yPlot = Math.min(Math.max(+y, ENV_PLOT_RMSE_MIN_M), ENV_PLOT_RMSE_MAX_M);
          const yClip = +y > ENV_PLOT_RMSE_MAX_M;
          if (+tilt <= ENV_PLOT_TILT_MAX_DEG) {
            xs.push(+tilt);
            ys.push(yPlot);
            texts.push(hoverText(name, p, yClip ? "<br>(RMSE clipped for scale)" : ""));
            symbols.push(p.success ? "circle" : "x");
            sizes.push(8);
          } else {
            // Park off-scale points at the right edge
            xOff.push(ENV_PLOT_TILT_MAX_DEG);
            yOff.push(yPlot);
            tOff.push(
              hoverText(name, p, "<br>(tilt off-scale: " + fmt(tilt, 0) + "° → parked at " + ENV_PLOT_TILT_MAX_DEG + "°)")
            );
          }
        });
      const col = ENVELOPE_SCHEME_COLORS[law] || "#aaa";
      const traces = [
        {
          x: xs,
          y: ys,
          text: texts,
          mode: "lines+markers",
          name: name,
          legendgroup: law,
          line: {
            color: col,
            width: 2,
            dash: (familyOf[law] || "") === "pid" ? "dash" : "solid",
          },
          marker: {
            size: sizes,
            color: col,
            symbol: symbols,
            line: { width: 1, color: "#111" },
          },
          hovertemplate: "%{text}<extra></extra>",
        },
      ];
      if (xOff.length) {
        traces.push({
          x: xOff,
          y: yOff,
          text: tOff,
          mode: "markers",
          name: name + " (off-scale tilt)",
          legendgroup: law,
          showlegend: false,
          marker: {
            size: 11,
            color: col,
            symbol: "triangle-right",
            line: { width: 1, color: "#111" },
          },
          hovertemplate: "%{text}<extra></extra>",
        });
      }
      return traces;
    }

    // Tight τ range from data (avoid empty padding)
    const tauVals = [];
    points.forEach(function (p) {
      if (activeSet[p.law] && p.time_scale != null && Number.isFinite(+p.time_scale)) {
        tauVals.push(+p.time_scale);
      }
    });
    const tauMin = tauVals.length ? Math.min.apply(null, tauVals) : 0.12;
    const tauMax = tauVals.length ? Math.max.apply(null, tauVals) : 1.0;
    const tauPad = 0.03 * (tauMax - tauMin || 1);

    const plotRmseVsTau = {
      data: activeLaws.map(seriesRmseVsTau),
      layout: {
        ...plotTheme,
        height: 380,
        title: {
          text: "Position RMSE vs τ  ·  y capped at " + ENV_PLOT_RMSE_MAX_M + " m (hover for true RMSE)",
          font: { size: 12 },
        },
        xaxis: {
          title: "τ (smaller = faster)",
          gridcolor: "#2a2f36",
          range: [tauMax + tauPad, tauMin - tauPad], // reversed: gentle left → aggressive right
          dtick: 0.1,
        },
        yaxis: {
          title: "RMSE position [m]",
          gridcolor: "#2a2f36",
          type: "log",
          range: [Math.log10(ENV_PLOT_RMSE_MIN_M), Math.log10(ENV_PLOT_RMSE_MAX_M)],
        },
        legend: {
          orientation: "v",
          x: 1.02,
          y: 1,
          font: { size: 9 },
          bgcolor: "rgba(12,16,24,0.85)",
          bordercolor: "#2a2f36",
          borderwidth: 1,
        },
        margin: { t: 48, r: 160, b: 48, l: 56 },
      },
    };

    const tiltTraces = [];
    activeLaws.forEach(function (law) {
      seriesRmseVsTilt(law).forEach(function (tr) {
        tiltTraces.push(tr);
      });
    });

    const plotRmseVsTilt = {
      data: tiltTraces,
      layout: {
        ...plotTheme,
        height: 380,
        title: {
          text:
            "RMSE vs peak tilt  ·  x ≤ " +
            ENV_PLOT_TILT_MAX_DEG +
            "° (▶ = off-scale tumble) · y capped at " +
            ENV_PLOT_RMSE_MAX_M +
            " m",
          font: { size: 12 },
        },
        xaxis: {
          title: "Peak plant tilt [deg]",
          gridcolor: "#2a2f36",
          range: [0, ENV_PLOT_TILT_MAX_DEG + 2],
          dtick: 15,
        },
        yaxis: {
          title: "RMSE position [m]",
          gridcolor: "#2a2f36",
          type: "log",
          range: [Math.log10(ENV_PLOT_RMSE_MIN_M), Math.log10(ENV_PLOT_RMSE_MAX_M)],
        },
        legend: {
          orientation: "v",
          x: 1.02,
          y: 1,
          font: { size: 9 },
          bgcolor: "rgba(12,16,24,0.85)",
          bordercolor: "#2a2f36",
          borderwidth: 1,
        },
        margin: { t: 48, r: 160, b: 48, l: 56 },
        shapes: [
          {
            type: "line",
            x0: 15,
            x1: 15,
            y0: 0,
            y1: 1,
            yref: "paper",
            line: { color: "rgba(200,120,80,0.75)", width: 1.5, dash: "dot" },
          },
        ],
        annotations: [
          {
            x: 15,
            y: 1,
            yref: "paper",
            text: "~15° small-angle",
            showarrow: false,
            xanchor: "left",
            font: { size: 10, color: "#c87850" },
          },
        ],
      },
    };

    const b = env.boundary || {};

    function setFamilyPreset(fam) {
      setFamilyFilter(fam);
      if (fam === "all") return;
      const next = {};
      lawIds.forEach(function (id) {
        next[id] = (familyOf[id] || "lqr") === fam;
      });
      setVisible(next);
    }

    function toggleLaw(id) {
      setVisible(function (prev) {
        const next = Object.assign({}, prev);
        next[id] = !prev[id];
        return next;
      });
    }

    function showAll() {
      setFamilyFilter("all");
      const next = {};
      lawIds.forEach(function (id) {
        next[id] = true;
      });
      setVisible(next);
    }

    // —— Boundary summary rows (all active schemes) ——
    const boundaryRows = lawIds
      .filter(function (id) {
        return activeSet[id] && b[id];
      })
      .map(function (id) {
        const bb = b[id] || {};
        return {
          id: id,
          scheme: bb.label || labelOf[id] || id,
          family: bb.family || familyOf[id] || "—",
          last_ok: bb.last_success_time_scale,
          first_fail: bb.first_fail_time_scale,
          fail_tilt: bb.first_fail_peak_tilt_deg,
          last_tilt: bb.last_success_peak_tilt_deg,
        };
      })
      .sort(function (a, c) {
        const dir = boundSort.dir === "asc" ? 1 : -1;
        return dir * cmpTableVal(a, c, boundSort.key);
      });

    // —— Sweep table: filter + sort ——
    const sweepRows = points
      .filter(function (p) {
        if (!activeSet[p.law]) return false;
        if (sweepSuccess === "ok" && !p.success) return false;
        if (sweepSuccess === "fail" && p.success) return false;
        if (sweepQuery) {
          const q = sweepQuery.toLowerCase();
          const lab = (p.label || labelOf[p.law] || p.law || "").toLowerCase();
          const fam = (p.family || familyOf[p.law] || "").toLowerCase();
          if (lab.indexOf(q) < 0 && fam.indexOf(q) < 0 && String(p.law).indexOf(q) < 0) {
            return false;
          }
        }
        return true;
      })
      .map(function (p) {
        return {
          time_scale: p.time_scale,
          scheme: p.label || labelOf[p.law] || String(p.law),
          law: p.law,
          family: p.family || familyOf[p.law] || "—",
          success: !!p.success,
          rmse_position_m: p.rmse_position_m,
          max_position_error_m: p.max_position_error_m,
          peak_tilt_deg: p.peak_tilt_deg,
          peak_speed_m_s: p.peak_speed_m_s,
        };
      })
      .sort(function (a, c) {
        const dir = sweepSort.dir === "asc" ? 1 : -1;
        return dir * cmpTableVal(a, c, sweepSort.key);
      });

    return e(
      "div",
      null,
      e(
        "div",
        { className: "card" },
        e("h2", null, env.title || "Tracking envelope"),
        e("p", null, env.description || ""),
        e(
          "p",
          { style: { color: "var(--muted)", fontSize: "0.9rem" } },
          "Solid lines = LQR family · dashed = PID. × markers fail the shared position bound (",
          env.position_bound_m != null ? fmt(env.position_bound_m, 2) + " m" : "see studies",
          "). Extreme fly-aways are clipped on the plot axes; hover for true values."
        ),
        e(
          "div",
          { className: "row env-filters" },
          e(
            "button",
            {
              type: "button",
              className: familyFilter === "all" ? "env-chip active" : "env-chip",
              onClick: showAll,
            },
            "All schemes"
          ),
          e(
            "button",
            {
              type: "button",
              className: familyFilter === "lqr" ? "env-chip active" : "env-chip",
              onClick: function () {
                setFamilyPreset("lqr");
              },
            },
            "LQR / LQG only"
          ),
          e(
            "button",
            {
              type: "button",
              className: familyFilter === "pid" ? "env-chip active" : "env-chip",
              onClick: function () {
                setFamilyPreset("pid");
              },
            },
            "PID only"
          ),
          e(
            "button",
            {
              type: "button",
              className: "env-chip",
              onClick: function () {
                setFamilyFilter("all");
                const next = {};
                lawIds.forEach(function (id) {
                  next[id] = !!ENV_DEFAULT_ON[id];
                });
                const any = lawIds.some(function (id) {
                  return next[id];
                });
                if (!any) {
                  lawIds.forEach(function (id) {
                    next[id] = true;
                  });
                }
                setVisible(next);
              },
            },
            "Recommended set"
          )
        ),
        e(
          "div",
          { className: "env-scheme-toggles" },
          lawIds.map(function (id) {
            return e(
              "label",
              {
                key: id,
                className: "env-scheme-toggle" + (visible[id] ? " on" : ""),
                style: { borderColor: ENVELOPE_SCHEME_COLORS[id] || "var(--border)" },
              },
              e("input", {
                type: "checkbox",
                checked: !!visible[id],
                onChange: function () {
                  toggleLaw(id);
                },
              }),
              e(
                "span",
                {
                  className: "env-swatch",
                  style: { background: ENVELOPE_SCHEME_COLORS[id] || "#aaa" },
                }
              ),
              labelOf[id] || id
            );
          })
        ),
        (env.notes || []).slice(0, 3).map(function (n, i) {
          return e("p", { key: i, style: { color: "var(--muted)", fontSize: "0.85rem", margin: "0.25rem 0" } }, "• " + n);
        })
      ),

      // Boundary summary table
      e(
        "div",
        { className: "card" },
        e("h3", null, "Breakdown by scheme"),
        e(
          "p",
          { style: { color: "var(--muted)", fontSize: "0.85rem", marginTop: 0 } },
          "Last τ that still passes the shared bound, then first failing τ. Click column headers to sort. Follows the scheme filters above."
        ),
        e(
          "div",
          { className: "table-wrap data-table-wrap" },
          e(
            "table",
            { className: "metrics data-table" },
            e(
              "thead",
              null,
              e(
                "tr",
                null,
                thSortable("Scheme", "scheme", boundSort, setBoundSort),
                thSortable("Family", "family", boundSort, setBoundSort),
                thSortable("Last ok τ", "last_ok", boundSort, setBoundSort),
                thSortable("First fail τ", "first_fail", boundSort, setBoundSort),
                thSortable("Tilt @ fail [°]", "fail_tilt", boundSort, setBoundSort),
                thSortable("Tilt @ last ok [°]", "last_tilt", boundSort, setBoundSort)
              )
            ),
            e(
              "tbody",
              null,
              boundaryRows.length
                ? boundaryRows.map(function (r) {
                    const neverOk = r.last_ok == null;
                    return e(
                      "tr",
                      {
                        key: r.id,
                        className: neverOk ? "row-fail" : "",
                      },
                      e(
                        "td",
                        null,
                        e("span", {
                          className: "env-swatch inline",
                          style: { background: ENVELOPE_SCHEME_COLORS[r.id] || "#aaa" },
                        }),
                        " ",
                        r.scheme
                      ),
                      e("td", null, r.family),
                      e("td", { className: "num" }, fmtMaybe(r.last_ok, 2)),
                      e("td", { className: "num" }, fmtMaybe(r.first_fail, 2)),
                      e("td", { className: "num" }, fmtMaybe(r.fail_tilt, 1)),
                      e("td", { className: "num" }, fmtMaybe(r.last_tilt, 1))
                    );
                  })
                : e("tr", null, e("td", { colSpan: 6 }, "No schemes selected."))
            )
          )
        )
      ),

      e(
        "div",
        { className: "card plot-card" },
        e(PlotDiv, {
          id: "env-rmse-tau-" + activeLaws.join("_").slice(0, 48),
          data: plotRmseVsTau.data,
          layout: plotRmseVsTau.layout,
        })
      ),
      e(
        "div",
        { className: "card plot-card" },
        e(PlotDiv, {
          id: "env-rmse-tilt-" + activeLaws.join("_").slice(0, 48),
          data: plotRmseVsTilt.data,
          layout: plotRmseVsTilt.layout,
        })
      ),

      // Full sweep data — collapsed by default (portfolio path stays above the fold)
      e(
        "div",
        { className: "card" },
        e(
          "button",
          {
            type: "button",
            className: "collapse-toggle",
            "aria-expanded": sweepOpen ? "true" : "false",
            onClick: function () {
              setSweepOpen(!sweepOpen);
            },
          },
          e("span", null, sweepOpen ? "▼" : "▶", " Full sweep data"),
          e(
            "span",
            { className: "collapse-meta" },
            points.filter(function (p) {
              return activeSet[p.law];
            }).length,
            " points · sort / filter inside"
          )
        ),
        sweepOpen
          ? e(
              "div",
              { className: "collapse-body" },
              e(
                "div",
                { className: "row data-table-toolbar" },
                e(
                  "label",
                  { className: "toolbar-field" },
                  e("span", null, "Success"),
                  e(
                    "select",
                    {
                      value: sweepSuccess,
                      onChange: function (ev) {
                        setSweepSuccess(ev.target.value);
                      },
                    },
                    e("option", { value: "all" }, "All"),
                    e("option", { value: "ok" }, "Pass only"),
                    e("option", { value: "fail" }, "Fail only")
                  )
                ),
                e(
                  "label",
                  { className: "toolbar-field grow" },
                  e("span", null, "Search"),
                  e("input", {
                    type: "search",
                    placeholder: "scheme or family…",
                    value: sweepQuery,
                    onChange: function (ev) {
                      setSweepQuery(ev.target.value);
                    },
                  })
                ),
                e(
                  "span",
                  { className: "toolbar-count" },
                  sweepRows.length,
                  " rows shown"
                )
              ),
              e(
                "div",
                { className: "table-wrap data-table-wrap scroll-y" },
                e(
                  "table",
                  { className: "metrics data-table sticky-head" },
                  e(
                    "thead",
                    null,
                    e(
                      "tr",
                      null,
                      thSortable("τ", "time_scale", sweepSort, setSweepSort),
                      thSortable("Scheme", "scheme", sweepSort, setSweepSort),
                      thSortable("Family", "family", sweepSort, setSweepSort),
                      thSortable("OK", "success", sweepSort, setSweepSort),
                      thSortable("RMSE [m]", "rmse_position_m", sweepSort, setSweepSort),
                      thSortable("max |e| [m]", "max_position_error_m", sweepSort, setSweepSort),
                      thSortable("Tilt [°]", "peak_tilt_deg", sweepSort, setSweepSort),
                      thSortable("v [m/s]", "peak_speed_m_s", sweepSort, setSweepSort)
                    )
                  ),
                  e(
                    "tbody",
                    null,
                    sweepRows.length
                      ? sweepRows.map(function (p, i) {
                          return e(
                            "tr",
                            {
                              key: p.law + "-" + p.time_scale + "-" + i,
                              className: p.success ? "" : "row-fail",
                            },
                            e("td", { className: "num" }, fmtMaybe(p.time_scale, 2)),
                            e("td", null, p.scheme),
                            e("td", null, p.family),
                            e(
                              "td",
                              null,
                              e(
                                "span",
                                { className: p.success ? "pill ok" : "pill fail" },
                                p.success ? "pass" : "fail"
                              )
                            ),
                            e("td", { className: "num" }, fmtMaybe(p.rmse_position_m, 4)),
                            e("td", { className: "num" }, fmtMaybe(p.max_position_error_m, 3)),
                            e("td", { className: "num" }, fmtMaybe(p.peak_tilt_deg, 1)),
                            e("td", { className: "num" }, fmtMaybe(p.peak_speed_m_s, 2))
                          );
                        })
                      : e(
                          "tr",
                          null,
                          e(
                            "td",
                            { colSpan: 8, style: { color: "var(--muted)" } },
                            "No rows match filters."
                          )
                        )
                  )
                )
              )
            )
          : null
      )
    );
  }

  function App() {
    const [doc, setDoc] = useState(null);
    const [err, setErr] = useState(null);
    const [tab, setTab] = useState("overview");
    const [runId, setRunId] = useState(null);
    const [missionId, setMissionId] = useState(null);
    const [aboutOpen, setAboutOpen] = useState(false);

    useEffect(() => {
      fetch("./data/showcase.json?v=204617b")
        .then((r) => {
          if (!r.ok) throw new Error("Failed to load data/showcase.json (" + r.status + ")");
          return r.json();
        })
        .then((j) => {
          setDoc(j);
          const mid =
            (j.ui && j.ui.default_mission) ||
            (j.missions && j.missions[0] && j.missions[0].id) ||
            null;
          setMissionId(mid);
          setRunId((j.ui && j.ui.default_run) || (j.runs && j.runs[0] && j.runs[0].id));
        })
        .catch((ex) => setErr(String(ex)));
    }, []);

    function selectMission(nextMid) {
      setMissionId(nextMid);
      if (!doc) return;
      const m = getMission(doc, nextMid);
      if (m && m.default_run) {
        setRunId(m.default_run);
        return;
      }
      const runs = runsForMission(doc, nextMid);
      if (runs.length) setRunId(runs[0].id);
    }

    function openHeroFlight() {
      if (!doc) return;
      const edge = (doc.missions || []).find(function (m) {
        return m.id === "envelope_edge";
      });
      if (edge) {
        setMissionId(edge.id);
        setRunId(edge.default_run || "edge_figure_eight_lqr");
      } else {
        const hero =
          (doc.runs || []).find(function (r) {
            return r.id === "edge_figure_eight_lqr";
          }) ||
          (doc.runs || []).find(function (r) {
            return r.id === "figure_eight_lqr";
          });
        if (hero) setRunId(hero.id);
      }
      setTab("flight");
    }

    const run = useMemo(() => {
      if (!doc || !runId) return null;
      return (doc.runs || []).find((r) => r.id === runId) || doc.runs[0];
    }, [doc, runId]);

    const missionRuns = useMemo(() => {
      if (!doc) return [];
      return runsForMission(doc, missionId);
    }, [doc, missionId]);

    if (err) {
      return e(
        "div",
        { className: "card", style: { margin: "2rem" } },
        e("h2", null, "Showcase data missing"),
        e("p", null, err),
        e(
          "p",
          { style: { color: "var(--muted)" } },
          "Rebuild the gallery data, then refresh this page."
        ),
        e("p", { style: { color: "var(--muted)", fontSize: "0.85rem" } },
          e("code", null, "uv run uavsim gallery --base-case")
        )
      );
    }
    if (!doc || !run) return e("p", { className: "loading" }, "Loading showcase…");

    // Story-first order; Metrics last (power / detail)
    const tabs = [
      ["overview", "Overview"],
      ["flight", "Flight 3D"],
      ["estimation", "Estimation"],
      ["envelope", "Envelope"],
      ["monte_carlo", "Monte Carlo"],
      ["compare", "Compare"],
      ["metrics", "Run metrics"],
    ];

    const runOptions = missionRuns.length ? missionRuns : doc.runs;
    const displayTitle =
      (doc.ui && doc.ui.display_title) || doc.title || DEFAULT_TITLE;
    const valueProp = (doc.ui && doc.ui.value_prop) || VALUE_PROP;

    let body;
    if (tab === "overview")
      body = e(Overview, {
        doc: doc,
        missionId: missionId,
        onSelect: function (id) {
          setRunId(id);
          setTab("flight");
        },
        onOpenHeroFlight: openHeroFlight,
        onGoEstimation: function () {
          setTab("estimation");
        },
        onGoEnvelope: function () {
          setTab("envelope");
        },
      });
    else if (tab === "estimation")
      body = e(EstimationTab, {
        doc: doc,
        missionId: missionId,
        onSelectRun: function (id) {
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
          { className: "row tab-toolbar" },
          e(ActiveMissionChip, { doc: doc, missionId: missionId }),
          e("label", { className: "run-pick" },
            e("span", null, "Run"),
            e(
              "select",
              {
                value: run.id,
                onChange: function (ev) {
                  setRunId(ev.target.value);
                },
                "aria-label": "Select run",
              },
              runOptions.map(function (r) {
                return e("option", { key: r.id, value: r.id }, r.label);
              })
            )
          ),
          e(
            "button",
            {
              type: "button",
              className: "btn-ghost btn-sm",
              onClick: function () {
                setTab("metrics");
              },
            },
            "Full metrics →"
          )
        ),
        e(FlightTab, { run: run })
      );
    else if (tab === "metrics")
      body = e(
        "div",
        null,
        e(
          "div",
          { className: "card", style: { marginBottom: "0.75rem" } },
          e("h2", { style: { marginTop: 0 } }, "Run metrics"),
          e(
            "p",
            { className: "matrix-lead", style: { marginBottom: "0.65rem" } },
            "Numeric summary for the selected run (also linked from Flight). Use Overview and Estimation for cross-stack comparison."
          ),
          e(
            "div",
            { className: "row tab-toolbar", style: { marginBottom: 0 } },
            e(ActiveMissionChip, { doc: doc, missionId: missionId }),
            e(
              "select",
              {
                value: run.id,
                onChange: function (ev) {
                  setRunId(ev.target.value);
                },
                "aria-label": "Select run for metrics",
              },
              runOptions.map(function (r) {
                return e("option", { key: r.id, value: r.id }, r.label);
              })
            ),
            e(
              "button",
              {
                type: "button",
                className: "btn-ghost btn-sm",
                onClick: function () {
                  setTab("flight");
                },
              },
              "← Back to Flight"
            )
          )
        ),
        e(MetricsTab, { run: run })
      );
    else if (tab === "monte_carlo") {
      const mission = getMission(doc, missionId);
      const mcPreferred =
        (mission &&
          mission.mc_run_id &&
          doc.runs.find(function (r) {
            return r.id === mission.mc_run_id && r.mc;
          })) ||
        runOptions.find(function (r) {
          return r.mc;
        }) ||
        doc.runs.find(function (r) {
          return r.mc;
        }) ||
        run;
      body = e(
        "div",
        null,
        e(
          "div",
          { className: "row tab-toolbar" },
          e(ActiveMissionChip, { doc: doc, missionId: missionId })
        ),
        e(McTab, { run: mcPreferred })
      );
    } else if (tab === "envelope") body = e(EnvelopeTab, { doc: doc });
    else if (tab === "compare")
      body = e(CompareTab, {
        doc: doc,
        missionId: missionId,
      });

    return e(
      "div",
      { className: "app-shell" },
      e(
        "header",
        { className: "app-header sticky-header" },
        e(
          "div",
          { className: "header-top" },
          e("div", { className: "header-brand" },
            e("h1", null, displayTitle),
            e("p", { className: "value-prop" }, valueProp),
            e(
              "button",
              {
                type: "button",
                className: "about-toggle",
                "aria-expanded": aboutOpen ? "true" : "false",
                onClick: function () {
                  setAboutOpen(!aboutOpen);
                },
              },
              aboutOpen ? "Hide study details" : "About this study"
            ),
            aboutOpen
              ? e(
                  "div",
                  { className: "about-panel" },
                  (
                    (doc.ui && doc.ui.about_paragraphs) ||
                    ABOUT_PARAGRAPHS
                  ).map(function (para, i) {
                    return e("p", { key: i }, para);
                  }),
                  e(
                    "p",
                    { className: "desktop-note" },
                    "Best on a wide display — the matrix and envelope tables are dense by design."
                  )
                )
              : null
          ),
          e(
            "div",
            { className: "header-controls" },
            e(MissionSelector, {
              doc: doc,
              missionId: missionId,
              onChange: selectMission,
              className: "header-mission",
              showHint: true,
            }),
            e(
              "div",
              { className: "meta" },
              "v",
              doc.uavsim_version || "?",
              doc.generated_at ? " · " + String(doc.generated_at).slice(0, 10) : "",
              " · SIL"
            )
          )
        ),
        e(StoryStrip, {
          activeTab: tab,
          onNavigate: function (id) {
            setTab(id);
          },
        })
      ),
      e(
        "nav",
        {
          className: "tabs",
          role: "tablist",
          "aria-label": "Showcase sections",
        },
        tabs.map(function (pair) {
          const id = pair[0];
          const label = pair[1];
          const selected = tab === id;
          return e(
            "button",
            {
              key: id,
              type: "button",
              role: "tab",
              id: "tab-" + id,
              "aria-selected": selected ? "true" : "false",
              "aria-controls": "panel-" + id,
              className: selected ? "active" : "",
              onClick: function () {
                setTab(id);
              },
            },
            label
          );
        })
      ),
      e(
        "main",
        {
          id: "panel-" + tab,
          role: "tabpanel",
          "aria-labelledby": "tab-" + tab,
        },
        body
      ),
      e(
        "footer",
        { className: "footer" },
        "Simulation only — not flight software. Source: ",
        e(
          "a",
          { href: "https://github.com/trey-copeland/uavsim" },
          "github.com/trey-copeland/uavsim"
        )
      )
    );
  }

  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(e(App));
})();
