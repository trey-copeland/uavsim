/**
 * Shared flight visualization helpers for uavsim static demos (showcase + intercept).
 *
 * Frame: plot coords are N, E, up (NED z flipped). Attitude uses body→NED ZYX Euler.
 * Vehicle mesh + inverse mix match uavsim.dynamics.mixer X-quad conventions.
 *
 * Global: window.UavFlightViz
 */
(function (global) {
  "use strict";

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
   * Default-vehicle X-quad inverse mixer (matches uavsim.dynamics.mixer).
   * Optional mixParams: { arm_length_m, ct_n_s2, cq_nm_s2 }.
   */
  function wrenchToMotorForces(u, mixParams) {
    const arm = (mixParams && mixParams.arm_length_m) || 0.25;
    const ell = arm / Math.SQRT2;
    const ct = (mixParams && mixParams.ct_n_s2) || 3.405e-6;
    const cq = (mixParams && mixParams.cq_nm_s2) || 5.4e-8;
    const k = cq / Math.max(ct, 1e-18);
    const B = [
      [1, 1, 1, 1],
      [-ell, -ell, ell, ell],
      [ell, -ell, -ell, ell],
      [k, -k, k, -k],
    ];
    const a = B.map(function (row, i) {
      return row.concat([+(u[i] || 0)]);
    });
    for (let col = 0; col < 4; col++) {
      let piv = col;
      for (let r = col + 1; r < 4; r++) {
        if (Math.abs(a[r][col]) > Math.abs(a[piv][col])) piv = r;
      }
      const tmp = a[col];
      a[col] = a[piv];
      a[piv] = tmp;
      const diag = a[col][col];
      if (Math.abs(diag) < 1e-14) return [0, 0, 0, 0];
      for (let c = col; c < 5; c++) a[col][c] /= diag;
      for (let r = 0; r < 4; r++) {
        if (r === col) continue;
        const f = a[r][col];
        for (let c = col; c < 5; c++) a[r][c] -= f * a[col][c];
      }
    }
    return a.map(function (row) {
      return Math.max(0, row[4]);
    });
  }

  /**
   * X-quad mesh + body axes + optional wrench / per-rotor thrust in plot frame.
   * @param {number[]} eulerDeg [φ,θ,ψ] deg
   * @param {number[]|null} u [F, τφ, τθ, τψ] — omit / null for mesh+axes only
   * @param {{thrust_max_n?:number, torque_max_nm?:number}|null} limits
   * @param {{arm_length_m?:number, ct_n_s2?:number, cq_nm_s2?:number, mass_kg?:number}|null} mixParams
   */
  function vehicleGeom(eulerDeg, u, limits, mixParams) {
    const eu = eulerDeg || [0, 0, 0];
    const phi = deg2rad(+eu[0] || 0);
    const theta = deg2rad(+eu[1] || 0);
    const psi = deg2rad(+eu[2] || 0);
    const R = rotationBodyToNed(phi, theta, psi);
    const L = 0.38;
    const motorsB = [
      [L, L, 0],
      [-L, L, 0],
      [-L, -L, 0],
      [L, -L, 0],
    ];
    const segs = [
      [motorsB[0], motorsB[2]],
      [motorsB[1], motorsB[3]],
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

    const axLen = 0.28;
    const axes = {
      x: arrowSeg(R, [0, 0, 0], [1, 0, 0], axLen),
      y: arrowSeg(R, [0, 0, 0], [0, 1, 0], axLen),
      z: arrowSeg(R, [0, 0, 0], [0, 0, 1], axLen),
    };

    const uu = u && u.length ? u : [0, 0, 0, 0];
    const F = +uu[0] || 0;
    const tx = +uu[1] || 0;
    const ty = +uu[2] || 0;
    const tz = +uu[3] || 0;
    const tNorm = Math.hypot(tx, ty, tz);
    const Fmax = (limits && limits.thrust_max_n) || 10;
    const Tmax = (limits && limits.torque_max_nm) || 1;
    const thrustLen = 0.08 + 0.18 * Math.min(1.0, Math.max(0, F / Fmax));
    const thrust = arrowSeg(R, [0, 0, 0], [0, 0, -1], thrustLen);

    const fMotors = wrenchToMotorForces(uu, mixParams);
    const fEq = Math.max(Math.abs(F), 1e-6) / 4;
    const mass = (mixParams && mixParams.mass_kg) || 0.5;
    const fRef = (mass * 9.81) / 4;
    const rotorX = [];
    const rotorY = [];
    const rotorZ = [];
    fMotors.forEach(function (fi, i) {
      const common = Math.min(1.2, Math.max(0, fi / Math.max(fRef, 1e-9)));
      const delta = (fi - fEq) / Math.max(fRef, 1e-9);
      const len = Math.max(
        0.04,
        0.05 + 0.1 * common + 0.28 * Math.max(-0.4, Math.min(1.4, delta))
      );
      const seg = arrowSeg(R, motorsB[i], [0, 0, -1], len);
      rotorX.push(seg.x[0], seg.x[1], null);
      rotorY.push(seg.y[0], seg.y[1], null);
      rotorZ.push(seg.z[0], seg.z[1], null);
    });
    const rotorThrust = { x: rotorX, y: rotorY, z: rotorZ };

    let torque = { x: [0, 0], y: [0, 0], z: [0, 0] };
    if (tNorm > 1e-9) {
      const tLen = 0.15 + 0.65 * Math.min(1.2, tNorm / Math.max(Tmax, 1e-6));
      torque = arrowSeg(R, [0, 0, 0], [tx, ty, tz], tLen);
    }
    const tScale = 0.55 / Math.max(Tmax, 1e-6);
    const tAx = arrowSeg(R, [0, 0, 0], [1, 0, 0], tx * tScale);
    const tAy = arrowSeg(R, [0, 0, 0], [0, 1, 0], ty * tScale);
    const tAz = arrowSeg(R, [0, 0, 0], [0, 0, 1], tz * tScale);

    return {
      frame: { x: fx, y: fy, z: fz },
      motors: motors,
      axes: axes,
      thrust: thrust,
      rotorThrust: rotorThrust,
      fMotors: fMotors,
      torque: torque,
      tAx: tAx,
      tAy: tAy,
      tAz: tAz,
      F: F,
      tau: [tx, ty, tz],
      tNorm: tNorm,
    };
  }

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

  function line3(seg, color, width, name, showleg) {
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
  }

  /** Trace index map for full attitude scene (bounds=0 … tAz=11). */
  const ATTITUDE_IDX = {
    bounds: 0,
    frame: 1,
    motors: 2,
    ax: 3,
    ay: 4,
    az: 5,
    thrust: 6,
    rotors: 7,
    torque: 8,
    tAx: 9,
    tAy: 10,
    tAz: 11,
  };

  /** Indices restyled each frame (excludes invisible bounds). */
  const ATTITUDE_RESTYLE_IDS = [
    ATTITUDE_IDX.frame,
    ATTITUDE_IDX.motors,
    ATTITUDE_IDX.ax,
    ATTITUDE_IDX.ay,
    ATTITUDE_IDX.az,
    ATTITUDE_IDX.thrust,
    ATTITUDE_IDX.rotors,
    ATTITUDE_IDX.torque,
    ATTITUDE_IDX.tAx,
    ATTITUDE_IDX.tAy,
    ATTITUDE_IDX.tAz,
  ];

  function motorMarkerCoords(motors) {
    return {
      x: motors.map(function (p) {
        return p[0];
      }),
      y: motors.map(function (p) {
        return p[1];
      }),
      z: motors.map(function (p) {
        return p[2];
      }),
    };
  }

  /**
   * Build full attitude Plotly traces (with thrust / rotor / torque).
   */
  function buildAttitudeTraces(g0, bounds) {
    const m0 = motorMarkerCoords(g0.motors);
    return [
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
        x: m0.x,
        y: m0.y,
        z: m0.z,
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
      line3(g0.thrust, "rgba(232, 121, 249, 0.28)", 3, "ΣF −z", true),
      line3(g0.rotorThrust, "#e879f9", 3.5, "rotor fᵢ", true),
      line3(g0.torque, "#e6b450", 8, "torque τ", true),
      line3(g0.tAx, "rgba(240,113,120,0.55)", 5, "τφ", false),
      line3(g0.tAy, "rgba(62,207,142,0.55)", 5, "τθ", false),
      line3(g0.tAz, "rgba(91,159,212,0.55)", 5, "τψ", false),
    ];
  }

  /** xyz arrays for Plotly.restyle of attitude traces (same order as ATTITUDE_RESTYLE_IDS). */
  function attitudeRestyleXYZ(g) {
    const m = motorMarkerCoords(g.motors);
    return {
      x: [
        g.frame.x,
        m.x,
        g.axes.x.x,
        g.axes.y.x,
        g.axes.z.x,
        g.thrust.x,
        g.rotorThrust.x,
        g.torque.x,
        g.tAx.x,
        g.tAy.x,
        g.tAz.x,
      ],
      y: [
        g.frame.y,
        m.y,
        g.axes.x.y,
        g.axes.y.y,
        g.axes.z.y,
        g.thrust.y,
        g.rotorThrust.y,
        g.torque.y,
        g.tAx.y,
        g.tAy.y,
        g.tAz.y,
      ],
      z: [
        g.frame.z,
        m.z,
        g.axes.x.z,
        g.axes.y.z,
        g.axes.z.z,
        g.thrust.z,
        g.rotorThrust.z,
        g.torque.z,
        g.tAx.z,
        g.tAy.z,
        g.tAz.z,
      ],
    };
  }

  function defaultAttitudeSceneAxes(span) {
    const s = span == null ? 1.05 : span;
    return function (title) {
      return {
        title: title,
        range: [-s, s],
        autorange: false,
        gridcolor: "#243044",
        zerolinecolor: "#3a4a60",
        showbackground: true,
        backgroundcolor: "rgba(10,14,22,0.95)",
        showspikes: false,
      };
    };
  }

  function defaultAttitudeLayout(opts) {
    opts = opts || {};
    const span = opts.span != null ? opts.span : 1.05;
    const ax = defaultAttitudeSceneAxes(span);
    const sceneBg = opts.sceneBg || "#0a0e16";
    return {
      paper_bgcolor: sceneBg,
      plot_bgcolor: sceneBg,
      font: { color: opts.fontColor || "#e7ecf3", size: 11 },
      margin: { l: 0, r: 0, t: 8, b: 0 },
      uirevision: opts.uirevision || "attitude",
      scene: {
        xaxis: ax("N"),
        yaxis: ax("E"),
        zaxis: ax("up"),
        aspectmode: "cube",
        bgcolor: sceneBg,
        camera: {
          eye: { x: 1.55, y: 1.55, z: 1.15 },
          center: { x: 0, y: 0, z: 0 },
          up: { x: 0, y: 0, z: 1 },
        },
      },
      showlegend: true,
      legend: {
        orientation: "h",
        y: opts.legendY != null ? opts.legendY : 1.12,
        x: 0,
        font: { size: 10, color: opts.mutedColor || "#9aa7b8" },
        bgcolor: "rgba(0,0,0,0)",
      },
      height: opts.height,
    };
  }

  /** Body triad at vehicle position in plot frame (for path 3D). */
  function vehicleTriadAt(pos, eulerDeg, scale) {
    const s = scale != null ? scale : 0.2;
    const eu = eulerDeg || [0, 0, 0];
    const R = rotationBodyToNed(deg2rad(+eu[0] || 0), deg2rad(+eu[1] || 0), deg2rad(+eu[2] || 0));
    const px = pos[0];
    const py = pos[1];
    const pz = pos[2];
    const ax = bodyToPlot(R, [s, 0, 0]);
    const ay = bodyToPlot(R, [0, s, 0]);
    const az = bodyToPlot(R, [0, 0, -s]);
    return {
      x: [px, px + ax[0], null, px, px + ay[0], null, px, px + az[0]],
      y: [py, py + ax[1], null, py, py + ay[1], null, py, py + az[1]],
      z: [pz, pz + ax[2], null, pz, pz + ay[2], null, pz, pz + az[2]],
    };
  }

  global.UavFlightViz = {
    deg2rad: deg2rad,
    matMulVec: matMulVec,
    rotationBodyToNed: rotationBodyToNed,
    bodyToPlot: bodyToPlot,
    arrowSeg: arrowSeg,
    wrenchToMotorForces: wrenchToMotorForces,
    vehicleGeom: vehicleGeom,
    cornerTrace: cornerTrace,
    line3: line3,
    ATTITUDE_IDX: ATTITUDE_IDX,
    ATTITUDE_RESTYLE_IDS: ATTITUDE_RESTYLE_IDS,
    buildAttitudeTraces: buildAttitudeTraces,
    attitudeRestyleXYZ: attitudeRestyleXYZ,
    defaultAttitudeLayout: defaultAttitudeLayout,
    defaultAttitudeSceneAxes: defaultAttitudeSceneAxes,
    vehicleTriadAt: vehicleTriadAt,
    motorMarkerCoords: motorMarkerCoords,
  };
})(typeof window !== "undefined" ? window : globalThis);
