/* uavsim intercept L0 demo — vanilla JS + Plotly.
 * R3: sticky top transport · 3D|attitude · 2D|range · MC bands · battery.
 */
(function () {
  "use strict";

  const COLORS = {
    accent: "#5b9fd4",
    good: "#3ecf8e",
    bad: "#f07178",
    warn: "#e6b450",
    muted: "#9aa0a6",
    grid: "#2a2f36",
    paper: "#0c1018",
    plot: "#111315",
    text: "#e8eaed",
    scene: "#0a0e16",
  };

  const PLOTLY_CFG = {
    displaylogo: false,
    responsive: true,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
  };

  /** @type {any} */
  let demo = null;
  /** @type {'success'|'fail'} */
  let caseId = "success";
  let frameIndex = 0;
  let playing = false;
  let speed = 1;
  let showBands = true;
  /** @type {'NE'|'NU'} */
  let projection = "NE";
  let aboutOpen = false;
  /** @type {number|null} */
  let rafId = null;
  let lastWall = 0;

  let traj3dReady = false;
  /** @type {{trail:number, own:number, tgt:number}|null} */
  let traj3dIdx = null;
  let traj3dKey = "";

  let attReady = false;
  /** @type {{frame:number, motors:number, ax:number, ay:number, az:number}|null} */
  let attIdx = null;
  let attKey = "";

  const el = {
    app: document.getElementById("app"),
  };

  function fmt(x, digits) {
    if (x === true) return "true";
    if (x === false) return "false";
    if (x === null || x === undefined || Number.isNaN(x)) return "—";
    if (typeof x === "number" && Number.isFinite(x)) return x.toFixed(digits ?? 3);
    return String(x);
  }

  function fmtPct(p) {
    if (p === null || p === undefined || !Number.isFinite(p)) return "—";
    return (100 * p).toFixed(1) + "%";
  }

  function activeCase() {
    if (!demo || !demo.cases) return null;
    return demo.cases[caseId] || demo.cases.success || null;
  }

  function captureRadius() {
    const c = activeCase();
    if (c && c.metrics && c.metrics.capture_radius_m != null) return Number(c.metrics.capture_radius_m);
    if (demo && demo.ui && demo.ui.capture_radius_m != null) return Number(demo.ui.capture_radius_m);
    if (demo && demo.mc && demo.mc.summary && demo.mc.summary.capture_radius_m != null)
      return Number(demo.mc.summary.capture_radius_m);
    return 1;
  }

  function hasMc() {
    return !!(demo && demo.mc && demo.mc.trials && demo.mc.trials.length);
  }

  function hasBands() {
    const b = demo && demo.mc && demo.mc.bands;
    if (!b || !b.ownship) return false;
    if (b.ownship.median && b.ownship.radius_horiz_m && b.ownship.radius_horiz_m.p95) {
      return b.ownship.median.N && b.ownship.median.N.length > 0;
    }
    return !!(b.ownship.N && b.ownship.E && b.ownship.N.p5 && b.ownship.N.p5.length);
  }

  function hasFail() {
    return !!(demo && demo.cases && demo.cases.fail);
  }

  function nFrames() {
    const c = activeCase();
    const t = c && c.timeseries && c.timeseries.t;
    return t ? t.length : 0;
  }

  function hasEuler() {
    const c = activeCase();
    const e = c && c.timeseries && c.timeseries.euler_deg;
    return !!(e && e.length);
  }

  function hasBattery() {
    const c = activeCase();
    const ts = c && c.timeseries;
    if (!ts) return false;
    return !!(
      (ts.soc && ts.soc.length) ||
      (ts.power_w && ts.power_w.length) ||
      (ts.energy_wh_remaining && ts.energy_wh_remaining.length)
    );
  }

  /** SOC as 0–100 percent from fraction or already-percent values. */
  function socPercent(v) {
    if (v == null || !Number.isFinite(v)) return null;
    if (v <= 1.01) return 100 * v;
    return v;
  }

  function plotLayoutBase(overrides) {
    return Object.assign(
      {
        paper_bgcolor: COLORS.paper,
        plot_bgcolor: COLORS.plot,
        font: { color: COLORS.text, size: 11 },
        margin: { l: 48, r: 16, t: 28, b: 44 },
        showlegend: true,
        legend: {
          orientation: "h",
          y: 1.12,
          x: 0,
          font: { size: 10, color: COLORS.muted },
          bgcolor: "rgba(0,0,0,0)",
        },
        xaxis: {
          gridcolor: COLORS.grid,
          zerolinecolor: COLORS.grid,
          color: COLORS.muted,
        },
        yaxis: {
          gridcolor: COLORS.grid,
          zerolinecolor: COLORS.grid,
          color: COLORS.muted,
        },
      },
      overrides || {}
    );
  }

  /* ── Attitude helpers via shared UavFlightViz ── */

  // Shared geometry (docs/shared/flight_viz.js → ./lib/)
  const FV = window.UavFlightViz;
  if (!FV) {
    throw new Error("UavFlightViz missing — load ./lib/flight_viz.js before app.js");
  }
  const deg2rad = FV.deg2rad;
  const rotationBodyToNed = FV.rotationBodyToNed;
  const bodyToPlot = FV.bodyToPlot;

  /** Actuator limits for thrust scaling (from pack ui or defaults). */
  function attitudeLimits() {
    const ui = (demo && demo.ui) || {};
    const lim = ui.limits || {};
    return {
      thrust_max_n: +(lim.thrust_max_n || ui.thrust_max_n || 66.2),
      torque_max_nm: +(lim.torque_max_nm || ui.torque_max_nm || 4.0),
    };
  }

  function mixParams() {
    const ui = (demo && demo.ui) || {};
    const veh = ui.vehicle || {};
    return {
      arm_length_m: +(veh.arm_length_m || ui.arm_length_m || 0.32),
      ct_n_s2: +(veh.ct_n_s2 || ui.ct_n_s2 || 1.02e-5),
      cq_nm_s2: +(veh.cq_nm_s2 || ui.cq_nm_s2 || 1.6e-7),
      mass_kg: +(veh.mass_kg || ui.mass_kg || 1.5),
    };
  }

  function vehicleGeom(eulerDeg, u) {
    return FV.vehicleGeom(eulerDeg, u || [0, 0, 0, 0], attitudeLimits(), mixParams());
  }

  /* ── Scene bounds ──────────────────────────────────── */

  function fitSceneBounds(plotArrays) {
    const xs = [];
    const ys = [];
    const zs = [];
    (plotArrays || []).forEach(function (arr) {
      if (!arr) return;
      for (let k = 0; k < arr.length; k++) {
        if (!arr[k] || arr[k].length < 3) continue;
        const a = +arr[k][0];
        const b = +arr[k][1];
        const c = +arr[k][2];
        if (Number.isFinite(a)) xs.push(a);
        if (Number.isFinite(b)) ys.push(b);
        if (Number.isFinite(c)) zs.push(c);
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
    const vSpan = Math.max(pz.span, 0.4 * hSpan, 0.8);
    const padH = 0.22 * hSpan;
    const padV = 0.15 * vSpan;
    const halfH = 0.5 * hSpan + padH;
    const halfV = 0.5 * vSpan + padV;
    return {
      x: [px.mid - halfH, px.mid + halfH],
      y: [py.mid - halfH, py.mid + halfH],
      z: [pz.mid - halfV, pz.mid + halfV],
      halfH: halfH,
      halfV: halfV,
      ar: {
        x: 1,
        y: 1,
        z: Math.max(0.35, Math.min(1.0, halfV / halfH)),
      },
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
      hoverinfo: "skip",
      showlegend: false,
    };
  }

  function bandPathsAsPlotArrays(bands) {
    if (!bands || !bands.ownship) return [];
    const o = bands.ownship;
    const out = [];
    ["p5", "p50", "p95"].forEach(function (k) {
      if (!o.N || !o.E || !o.U || !o.N[k] || !o.E[k] || !o.U[k]) return;
      const arr = [];
      for (let i = 0; i < o.N[k].length; i++) {
        arr.push([o.N[k][i], o.E[k][i], o.U[k][i]]);
      }
      out.push(arr);
    });
    return out;
  }

  /* ── Render shell ──────────────────────────────────── */

  function renderShell() {
    const ui = (demo && demo.ui) || {};
    const title = (demo && demo.title) || "uavsim · intercept L0";
    const valueProp = ui.value_prop || "";
    const mc = demo && demo.mc;
    const summary = (mc && mc.summary) || {};
    const nTrials = summary.n_trials != null ? summary.n_trials : mc && mc.n_trials;
    const pCap = summary.p_capture;
    const rCap = captureRadius();
    const c = activeCase();
    const interceptOk = c && c.metrics && c.metrics.intercept_success;
    const pClass = !hasMc() ? "" : pCap >= 0.5 ? "good" : "bad";
    const failMcNote = caseId === "fail" && hasMc();
    const batt = hasBattery();
    const m = (c && c.metrics) || {};
    const socFinal = m.soc_final != null ? socPercent(m.soc_final) : null;
    const socMin = m.soc_min != null ? socPercent(m.soc_min) : null;

    traj3dReady = false;
    traj3dIdx = null;
    traj3dKey = "";
    attReady = false;
    attIdx = null;
    attKey = "";

    const storyDefault =
      "Pad climb intercept — ownship takes off from a pad, climbs through ground effect, " +
      "then tracks an open-loop path toward a scripted target with fixed NDI.";

    el.app.innerHTML = `
      <div class="sticky-chrome">
        <header class="app-header">
          <h1>${escapeHtml(title)}</h1>
          <p class="tagline">${escapeHtml(valueProp)}</p>
          <div class="meta">
            generated ${escapeHtml(demo.generated_at || "—")}
            · uavsim ${escapeHtml(demo.uavsim_version || "—")}
            ${mc && mc.source_study ? " · MC " + escapeHtml(mc.source_study) : ""}
          </div>
          <div class="header-row">
            <div class="seg" id="case-seg" role="group" aria-label="Nominal case">
              <button type="button" data-case="success" class="${caseId === "success" ? "active" : ""}">Success</button>
              <button type="button" data-case="fail" class="${caseId === "fail" ? "active" : ""}" ${hasFail() ? "" : "disabled"}>Fail</button>
            </div>
            <span class="badge ${interceptOk ? "ok" : "miss"}" id="capture-badge">${interceptOk ? "Capture" : "Miss"}</span>
            <div class="kpi-row" id="kpi-row">
              <div class="kpi ${pClass}">
                <span class="kpi-label">P(capture)</span>
                <span class="kpi-value">${hasMc() ? fmtPct(pCap) : "no MC"}</span>
              </div>
              <div class="kpi">
                <span class="kpi-label">n trials</span>
                <span class="kpi-value">${hasMc() ? String(nTrials) : "—"}</span>
              </div>
              <div class="kpi">
                <span class="kpi-label">r capture</span>
                <span class="kpi-value">${fmt(rCap, 2)} m</span>
              </div>
              ${
                socFinal != null
                  ? `<div class="kpi">
                <span class="kpi-label">SOC final</span>
                <span class="kpi-value">${fmt(socFinal, 1)}%</span>
              </div>`
                  : socMin != null
                    ? `<div class="kpi">
                <span class="kpi-label">SOC min</span>
                <span class="kpi-value">${fmt(socMin, 1)}%</span>
              </div>`
                    : ""
              }
            </div>
            <button type="button" class="about-toggle" id="about-btn">About</button>
          </div>
          <div class="about-panel ${aboutOpen ? "" : "hidden"}" id="about-panel">
            ${(ui.about_paragraphs || []).map((p) => `<p>${escapeHtml(p)}</p>`).join("")}
          </div>
        </header>

        <div class="transport" id="transport">
          <button type="button" class="btn primary" id="play-btn">${playing ? "Pause" : "Play"}</button>
          <button type="button" class="btn" id="cpa-btn">Jump to CPA</button>
          <div class="scrub-wrap">
            <input type="range" id="scrub" min="0" max="${Math.max(0, nFrames() - 1)}" value="${frameIndex}" step="1" />
            <div class="scrub-labels"><span>t₀</span><span>t<sub>f</sub></span></div>
          </div>
          <div class="readouts" id="readouts"></div>
          <div class="seg speed-seg" id="speed-seg" role="group" aria-label="Playback speed">
            <button type="button" data-speed="0.5" class="${speed === 0.5 ? "active" : ""}">0.5×</button>
            <button type="button" data-speed="1" class="${speed === 1 ? "active" : ""}">1×</button>
            <button type="button" data-speed="2" class="${speed === 2 ? "active" : ""}">2×</button>
          </div>
          <label class="tool-label transport-bands" id="bands-label" title="${hasBands() ? "Show soft MC plant-scatter cloud on 2D + 3D" : "Bands not in data pack"}">
            <input type="checkbox" id="bands-toggle" ${showBands && hasBands() ? "checked" : ""} ${hasBands() ? "" : "disabled"} />
            MC cloud
          </label>
          <div class="soc-strip ${batt ? "" : "hidden"}" id="soc-strip" title="State of charge @ scrub">
            <span class="soc-label">SOC</span>
            <div class="soc-bar-track"><div class="soc-bar-fill" id="soc-bar-fill" style="width:0%"></div></div>
            <span class="soc-pct" id="soc-pct">—</span>
          </div>
        </div>
      </div>

      <div class="story-strip">
        <strong>Pad climb intercept</strong> — ${escapeHtml(
          ui.mission_notes === "pad_climb_ground_effect"
            ? "ownship takes off from a pad, climbs through ground effect, then tracks an open-loop path toward a scripted target with fixed NDI."
            : storyDefault.replace(/^Pad climb intercept — /, "")
        )}
        Capture when
        <span class="capture-eq">min ‖p<sub>own</sub> − p<sub>tgt</sub>‖ ≤ ${fmt(rCap, 2)} m</span>.
        Plant MC on the success recipe; battery SOC/power when logged.
        ${
          failMcNote
            ? '<span class="fail-mc-note"> MC / bands: success plant study</span>'
            : ""
        }
      </div>

      <main>
        <div class="primary-row">
          <section class="card">
            <h2>Trajectory 3D</h2>
            <div class="plot-host tall" id="traj3d-plot"></div>
          </section>
          <section class="card">
            <h2>Attitude @ origin</h2>
            <div class="plot-host tall" id="attitude-plot"></div>
            <p class="muted-note ${hasEuler() ? "hidden" : ""}" id="att-empty">
              Attitude not in pack (missing <code>euler_deg</code>). Rebuild exporter from state <code>x[:,3:6]</code>.
            </p>
          </section>
        </div>

        <div class="secondary-row">
          <section class="card">
            <h2>
              Trajectory 2D
              <span class="card-tools">
                <div class="seg" id="proj-seg" role="group" aria-label="Projection">
                  <button type="button" data-proj="NE" class="${projection === "NE" ? "active" : ""}">N–E</button>
                  <button type="button" data-proj="NU" class="${projection === "NU" ? "active" : ""}">N–Up</button>
                </div>
              </span>
            </h2>
            <div class="plot-host mid" id="traj-plot"></div>
          </section>
          <section class="card">
            <h2>Range vs time</h2>
            <div class="plot-host mid" id="range-plot"></div>
          </section>
        </div>

        <section class="card battery-row ${batt ? "" : "hidden"}" id="battery-panel">
          <h2>Battery</h2>
          <div class="battery-grid">
            <div class="soc-gauge-wrap">
              <div class="soc-gauge-label">SOC @ t</div>
              <div class="soc-gauge-value" id="soc-gauge-value">—</div>
              <div class="soc-bar-track large"><div class="soc-bar-fill" id="soc-gauge-fill" style="width:0%"></div></div>
            </div>
            <div class="plot-host mid" id="power-plot"></div>
            <div class="plot-host mid" id="energy-plot"></div>
          </div>
        </section>

        <section class="card mc-panel ${hasMc() ? "" : "hidden"}" id="mc-panel">
          <h2>Monte Carlo — min range</h2>
          <div class="mc-grid">
            <div>
              <div class="plot-host hist" id="hist-plot"></div>
            </div>
            <div>
              <ul class="stat-list" id="mc-stats"></ul>
              <ul class="how-to" id="how-to"></ul>
            </div>
          </div>
        </section>
        <p class="muted-note ${hasMc() ? "hidden" : ""}" id="no-mc-note">
          Monte Carlo not in this data pack — KPIs show nominal only. Rebuild with a success run that includes
          <code>monte_carlo/trials.csv</code> or shard CSVs.
        </p>
      </main>

      <footer>
        Simulation only — not flight software.
        · <a href="../../../README.md">uavsim README</a>
        · data: <code>data/demo.json</code>
        · rebuild: see <a href="./README.md">demo README</a>
      </footer>
    `;

    wireControls();
    updateReadouts();
    drawAll();
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* ── Controls ──────────────────────────────────────── */

  function applyFrameViews() {
    updateReadouts();
    [
      [() => drawTraj3d(false), "traj3d"],
      [() => drawAttitude(false), "attitude"],
      [drawTraj2d, "traj2d"],
      [drawRange, "range"],
      [drawBattery, "battery"],
    ].forEach(function (pair) {
      try {
        pair[0]();
      } catch (err) {
        console.error("[intercept demo] frame " + pair[1] + " failed:", err);
      }
    });
  }

  function wireControls() {
    const caseSeg = document.getElementById("case-seg");
    if (caseSeg) {
      caseSeg.querySelectorAll("button[data-case]").forEach((btn) => {
        btn.addEventListener("click", () => {
          if (btn.disabled) return;
          const next = btn.getAttribute("data-case");
          if (next === caseId) return;
          caseId = next;
          frameIndex = 0;
          stopPlay();
          renderShell();
        });
      });
    }

    const aboutBtn = document.getElementById("about-btn");
    if (aboutBtn) {
      aboutBtn.addEventListener("click", () => {
        aboutOpen = !aboutOpen;
        const panel = document.getElementById("about-panel");
        if (panel) panel.classList.toggle("hidden", !aboutOpen);
      });
    }

    const projSeg = document.getElementById("proj-seg");
    if (projSeg) {
      projSeg.querySelectorAll("button[data-proj]").forEach((btn) => {
        btn.addEventListener("click", () => {
          projection = btn.getAttribute("data-proj");
          projSeg.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b === btn));
          drawTraj2d();
        });
      });
    }

    const bands = document.getElementById("bands-toggle");
    if (bands) {
      bands.addEventListener("change", () => {
        showBands = bands.checked;
        traj3dReady = false;
        traj3dKey = "";
        drawTraj3d(true);
        drawTraj2d();
      });
    }

    const playBtn = document.getElementById("play-btn");
    if (playBtn) {
      playBtn.addEventListener("click", () => {
        if (playing) stopPlay();
        else startPlay();
      });
    }

    const cpaBtn = document.getElementById("cpa-btn");
    if (cpaBtn) {
      cpaBtn.addEventListener("click", () => {
        jumpToCpa();
      });
    }

    const scrub = document.getElementById("scrub");
    if (scrub) {
      scrub.addEventListener("input", () => {
        frameIndex = parseInt(scrub.value, 10) || 0;
        if (playing) stopPlay();
        applyFrameViews();
      });
    }

    const speedSeg = document.getElementById("speed-seg");
    if (speedSeg) {
      speedSeg.querySelectorAll("button[data-speed]").forEach((btn) => {
        btn.addEventListener("click", () => {
          speed = parseFloat(btn.getAttribute("data-speed")) || 1;
          speedSeg.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b === btn));
        });
      });
    }
  }

  function onKey(ev) {
    const tag = (ev.target && ev.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
      ev.preventDefault();
      const step = ev.shiftKey ? 10 : 1;
      const n = nFrames();
      if (!n) return;
      if (ev.key === "ArrowLeft") frameIndex = Math.max(0, frameIndex - step);
      else frameIndex = Math.min(n - 1, frameIndex + step);
      stopPlay();
      syncScrub();
      applyFrameViews();
    } else if (ev.key === " " || ev.code === "Space") {
      ev.preventDefault();
      if (playing) stopPlay();
      else startPlay();
    }
  }

  function syncScrub() {
    const scrub = document.getElementById("scrub");
    if (scrub) {
      scrub.max = String(Math.max(0, nFrames() - 1));
      scrub.value = String(frameIndex);
    }
    const playBtn = document.getElementById("play-btn");
    if (playBtn) playBtn.textContent = playing ? "Pause" : "Play";
  }

  function updateSocUi(pct) {
    const fill = document.getElementById("soc-bar-fill");
    const pctEl = document.getElementById("soc-pct");
    const gFill = document.getElementById("soc-gauge-fill");
    const gVal = document.getElementById("soc-gauge-value");
    const w = pct == null ? 0 : Math.max(0, Math.min(100, pct));
    const color =
      pct == null ? COLORS.muted : pct > 50 ? COLORS.good : pct > 20 ? COLORS.warn : COLORS.bad;
    if (fill) {
      fill.style.width = w + "%";
      fill.style.background = color;
    }
    if (pctEl) pctEl.textContent = pct == null ? "—" : fmt(pct, 1) + "%";
    if (gFill) {
      gFill.style.width = w + "%";
      gFill.style.background = color;
    }
    if (gVal) gVal.textContent = pct == null ? "—" : fmt(pct, 1) + "%";
  }

  function updateReadouts() {
    const c = activeCase();
    const ts = c && c.timeseries;
    const host = document.getElementById("readouts");
    if (!host || !ts) return;
    const i = Math.min(frameIndex, ts.t.length - 1);
    const t = ts.t[i];
    const r = ts.range_m ? ts.range_m[i] : null;
    host.innerHTML = `
      <div><span>t = </span><strong>${fmt(t, 2)} s</strong></div>
      <div><span>range = </span><strong>${fmt(r, 3)} m</strong></div>
      <div><span>frame </span><strong>${i + 1}/${ts.t.length}</strong></div>
    `;
    if (ts.soc && ts.soc.length) {
      updateSocUi(socPercent(ts.soc[i]));
    } else {
      updateSocUi(null);
    }
  }

  function jumpToCpa() {
    const c = activeCase();
    if (!c || !c.timeseries) return;
    const tCpa = c.metrics && c.metrics.time_of_min_range_s;
    const t = c.timeseries.t;
    let i = 0;
    if (tCpa != null && Number.isFinite(tCpa)) {
      let best = Infinity;
      for (let k = 0; k < t.length; k++) {
        const d = Math.abs(t[k] - tCpa);
        if (d < best) {
          best = d;
          i = k;
        }
      }
    } else if (c.timeseries.range_m) {
      let best = Infinity;
      for (let k = 0; k < c.timeseries.range_m.length; k++) {
        if (c.timeseries.range_m[k] < best) {
          best = c.timeseries.range_m[k];
          i = k;
        }
      }
    }
    frameIndex = i;
    stopPlay();
    syncScrub();
    applyFrameViews();
  }

  /* ── Playback ──────────────────────────────────────── */

  function startPlay() {
    if (nFrames() < 2) return;
    if (frameIndex >= nFrames() - 1) frameIndex = 0;
    playing = true;
    lastWall = performance.now();
    syncScrub();
    rafId = requestAnimationFrame(tick);
  }

  function stopPlay() {
    playing = false;
    if (rafId != null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    syncScrub();
  }

  function tick(now) {
    if (!playing) return;
    const c = activeCase();
    const t = c && c.timeseries && c.timeseries.t;
    if (!t || t.length < 2) {
      stopPlay();
      return;
    }
    const dtWall = (now - lastWall) / 1000;
    lastWall = now;
    const simSpan = t[t.length - 1] - t[0];
    if (simSpan <= 0) {
      stopPlay();
      return;
    }
    const tNow = t[frameIndex] + dtWall * speed;
    if (tNow >= t[t.length - 1]) {
      frameIndex = t.length - 1;
      syncScrub();
      applyFrameViews();
      stopPlay();
      return;
    }
    let i = frameIndex;
    while (i < t.length - 1 && t[i + 1] < tNow) i++;
    if (t[i] < tNow && i < t.length - 1) {
      if (Math.abs(t[i + 1] - tNow) < Math.abs(t[i] - tNow)) i++;
    }
    if (i !== frameIndex) {
      frameIndex = i;
      syncScrub();
      applyFrameViews();
    }
    rafId = requestAnimationFrame(tick);
  }

  /* ── Plots ─────────────────────────────────────────── */

  function extractXY(plotPts) {
    if (!plotPts || !plotPts.length) return { x: [], y: [] };
    if (projection === "NU") {
      return {
        x: plotPts.map((p) => p[0]),
        y: plotPts.map((p) => p[2]),
        xlabel: "North (m)",
        ylabel: "Up (m)",
      };
    }
    return {
      x: plotPts.map((p) => p[1]),
      y: plotPts.map((p) => p[0]),
      xlabel: "East (m)",
      ylabel: "North (m)",
    };
  }

  function circleTrace(cx, cy, r, name) {
    const n = 64;
    const xs = [];
    const ys = [];
    for (let i = 0; i <= n; i++) {
      const a = (2 * Math.PI * i) / n;
      xs.push(cx + r * Math.cos(a));
      ys.push(cy + r * Math.sin(a));
    }
    return {
      x: xs,
      y: ys,
      mode: "lines",
      name: name || "capture r",
      line: { color: COLORS.good, width: 1.5, dash: "dash" },
      hoverinfo: "skip",
      showlegend: true,
    };
  }

  /** Linear blend of two same-length arrays. */
  function _lerpArr(a, b, t) {
    const out = [];
    for (let i = 0; i < a.length; i++) out.push((1 - t) * a[i] + t * b[i]);
    return out;
  }

  /**
   * Seaborn-style CI ribbon in 2D: solid median path + soft translucent
   * fill between ±r (horizontal radius percentiles from median).
   * Falls back to axis-wise p5/p95 fill if radius_horiz missing.
   */
  function bandCloudTraces2d(bands) {
    if (!bands || !bands.ownship) return [];
    const own = bands.ownship;
    const med = own.median;
    const rad = own.radius_horiz_m;

    // Preferred: tubular CI around median (conical when r grows along t)
    if (
      med &&
      rad &&
      med.N &&
      med.E &&
      rad.p95 &&
      rad.p68 &&
      med.N.length === rad.p95.length
    ) {
      return bandSeabornTube2d(med, rad);
    }

    // Legacy axis-wise soft fill (older packs)
    return bandAxiswiseSoftFill2d(own);
  }

  /** Unit normals along a 2D polyline (smoothed). */
  function pathNormals2d(x, y) {
    const n = x.length;
    const nx = new Array(n);
    const ny = new Array(n);
    for (let i = 0; i < n; i++) {
      const i0 = Math.max(0, i - 1);
      const i1 = Math.min(n - 1, i + 1);
      let tx = x[i1] - x[i0];
      let ty = y[i1] - y[i0];
      const len = Math.hypot(tx, ty) || 1;
      tx /= len;
      ty /= len;
      nx[i] = -ty;
      ny[i] = tx;
    }
    return { nx: nx, ny: ny };
  }

  function bandSeabornTube2d(med, rad) {
    // Projection: NE uses E vs N; NU uses N vs U with vertical radius from U axis
    let mx, my, r68, r95;
    if (projection === "NE") {
      mx = med.E;
      my = med.N;
    } else {
      // N–Up: median N vs U; still use horizontal plant scatter radius for width
      mx = med.N;
      my = med.U;
    }
    r68 = rad.p68;
    r95 = rad.p95;
    const nrm = pathNormals2d(mx, my);
    const traces = [];

    function ribbon(rArr, alpha, name, legend) {
      const xu = [];
      const yu = [];
      const xl = [];
      const yl = [];
      for (let i = 0; i < mx.length; i++) {
        const r = Math.max(0, +rArr[i] || 0);
        xu.push(mx[i] + r * nrm.nx[i]);
        yu.push(my[i] + r * nrm.ny[i]);
        xl.push(mx[i] - r * nrm.nx[i]);
        yl.push(my[i] - r * nrm.ny[i]);
      }
      // Seaborn: soft fill, no hard stroke
      return {
        x: xu.concat(xl.slice().reverse()),
        y: yu.concat(yl.slice().reverse()),
        fill: "toself",
        fillcolor: "rgba(91, 159, 212, " + alpha + ")",
        line: { width: 0, color: "rgba(0,0,0,0)" },
        mode: "lines",
        name: name,
        hoverinfo: "skip",
        showlegend: !!legend,
      };
    }

    // Outer CI then inner (seaborn multi-band look)
    traces.push(ribbon(r95, 0.22, "MC 95% CI", true));
    traces.push(ribbon(r68, 0.28, "MC ~68% CI", false));
    // Solid median (seaborn mean/median line)
    traces.push({
      x: mx,
      y: my,
      mode: "lines",
      name: "MC median",
      line: { color: "rgba(70, 130, 180, 0.95)", width: 2.5 },
      hoverinfo: "skip",
      showlegend: true,
    });
    return traces;
  }

  function bandAxiswiseSoftFill2d(own) {
    let x5, x50, x95, y5, y50, y95;
    if (projection === "NE") {
      if (!own.E || !own.N) return [];
      x5 = own.E.p5;
      x50 = own.E.p50;
      x95 = own.E.p95;
      y5 = own.N.p5;
      y50 = own.N.p50;
      y95 = own.N.p95;
    } else {
      if (!own.N || !own.U) return [];
      x5 = own.N.p5;
      x50 = own.N.p50;
      x95 = own.N.p95;
      y5 = own.U.p5;
      y50 = own.U.p50;
      y95 = own.U.p95;
    }
    if (!x5 || !x95) return [];
    return [
      {
        x: x5.concat(x95.slice().reverse()),
        y: y5.concat(y95.slice().reverse()),
        fill: "toself",
        fillcolor: "rgba(91, 159, 212, 0.22)",
        line: { width: 0, color: "rgba(0,0,0,0)" },
        mode: "lines",
        name: "MC 95% (axis-wise)",
        hoverinfo: "skip",
        showlegend: true,
      },
      {
        x: x50,
        y: y50,
        mode: "lines",
        name: "MC median",
        line: { color: "rgba(70, 130, 180, 0.95)", width: 2.5 },
        hoverinfo: "skip",
        showlegend: true,
      },
    ];
  }

  /**
   * 3D: soft tubular CI about median (horizontal radius) + solid median path.
   * Looks conical when r_horiz grows after takeoff / during chase.
   */
  function bandCloudTraces3d(bands) {
    if (!bands || !bands.ownship) return [];
    const o = bands.ownship;
    const med = o.median;
    const rad = o.radius_horiz_m;
    if (med && rad && med.N && med.E && med.U && rad.p95) {
      return bandSeabornTube3d(med, rad);
    }
    // Legacy axis-wise soft strands
    if (!o.N || !o.E || !o.U || !o.N.p50) return [];
    return [
      {
        type: "scatter3d",
        mode: "lines",
        x: o.N.p50,
        y: o.E.p50,
        z: o.U.p50,
        line: { color: "rgba(70, 130, 180, 0.95)", width: 5 },
        name: "MC median",
        hoverinfo: "skip",
      },
    ];
  }

  function bandSeabornTube3d(med, rad) {
    const mn = med.N;
    const me = med.E;
    const mu = med.U;
    const r68 = rad.p68;
    const r95 = rad.p95;
    const n = mn.length;
    const traces = [];

    // Soft "sausage" surface: several angular generators at r68 / r95
    const nAng = 12;
    function ringStrand(rArr, alpha, width, name, legend) {
      for (let a = 0; a < nAng; a++) {
        const th = (2 * Math.PI * a) / nAng;
        const c = Math.cos(th);
        const s = Math.sin(th);
        const xs = [];
        const ys = [];
        const zs = [];
        for (let i = 0; i < n; i++) {
          const r = Math.max(0, +rArr[i] || 0);
          xs.push(mn[i] + r * c);
          ys.push(me[i] + r * s);
          zs.push(mu[i]);
        }
        traces.push({
          type: "scatter3d",
          mode: "lines",
          x: xs,
          y: ys,
          z: zs,
          line: { color: "rgba(91, 159, 212," + alpha + ")", width: width },
          name: name,
          showlegend: legend && a === 0,
          hoverinfo: "skip",
        });
      }
    }
    ringStrand(r95, 0.18, 3, "MC 95% tube", true);
    ringStrand(r68, 0.28, 2, "MC ~68% tube", false);

    // Solid median (seaborn line)
    traces.push({
      type: "scatter3d",
      mode: "lines",
      x: mn,
      y: me,
      z: mu,
      line: { color: "rgba(70, 130, 180, 0.95)", width: 6 },
      name: "MC median",
      hoverinfo: "skip",
      showlegend: true,
    });
    return traces;
  }

  function cpaIndex(c, ts) {
    let cpaIdx = 0;
    if (c.metrics && c.metrics.time_of_min_range_s != null) {
      const tCpa = c.metrics.time_of_min_range_s;
      let best = Infinity;
      for (let k = 0; k < ts.t.length; k++) {
        const d = Math.abs(ts.t[k] - tCpa);
        if (d < best) {
          best = d;
          cpaIdx = k;
        }
      }
    } else if (ts.range_m) {
      let best = Infinity;
      for (let k = 0; k < ts.range_m.length; k++) {
        if (ts.range_m[k] < best) {
          best = ts.range_m[k];
          cpaIdx = k;
        }
      }
    }
    return cpaIdx;
  }

  /* ── 3D trajectory ─────────────────────────────────── */

  function applyTraj3dFrame(host, ts, i) {
    if (!traj3dReady || !traj3dIdx || !host || !ts || !ts.pos_plot) return;
    const own = ts.pos_plot;
    const tgt = ts.target_plot || [];
    const ii = Math.max(0, Math.min(i, own.length - 1));
    const trail = own.slice(0, ii + 1);
    const px = own[ii][0];
    const py = own[ii][1];
    const pz = own[ii][2];
    const tx = tgt[ii] ? tgt[ii][0] : px;
    const ty = tgt[ii] ? tgt[ii][1] : py;
    const tz = tgt[ii] ? tgt[ii][2] : pz;
    Plotly.restyle(
      host,
      {
        x: [trail.map((p) => p[0]), [px], [tx]],
        y: [trail.map((p) => p[1]), [py], [ty]],
        z: [trail.map((p) => p[2]), [pz], [tz]],
      },
      [traj3dIdx.trail, traj3dIdx.own, traj3dIdx.tgt]
    );
  }

  function drawTraj3d(forceFull) {
    const host = document.getElementById("traj3d-plot");
    const c = activeCase();
    if (!host || !c || !c.timeseries || typeof Plotly === "undefined") return;
    const ts = c.timeseries;
    const own = ts.pos_plot || [];
    const tgt = ts.target_plot || [];
    const i = Math.min(frameIndex, Math.max(0, own.length - 1));
    const key = caseId + "|" + (showBands && hasBands() ? "b1" : "b0");

    if (!forceFull && traj3dReady && traj3dKey === key) {
      applyTraj3dFrame(host, ts, i);
      return;
    }

    traj3dReady = false;
    traj3dKey = key;

    const bandArrs = showBands && hasBands() ? bandPathsAsPlotArrays(demo.mc.bands) : [];
    const bounds = fitSceneBounds([own, tgt, ts.ref_plot].concat(bandArrs));

    function axis(title, range) {
      return {
        title: title,
        range: range.slice(),
        autorange: false,
        gridcolor: "#243044",
        zerolinecolor: "#3a4a60",
        showbackground: true,
        backgroundcolor: "rgba(10,14,22,0.95)",
      };
    }

    const traces = [];
    traces.push(cornerTrace(bounds));

    if (showBands && hasBands()) {
      bandCloudTraces3d(demo.mc.bands).forEach(function (tr) {
        traces.push(tr);
      });
    }

    if (tgt.length) {
      traces.push({
        type: "scatter3d",
        mode: "lines",
        x: tgt.map((p) => p[0]),
        y: tgt.map((p) => p[1]),
        z: tgt.map((p) => p[2]),
        line: { color: COLORS.warn, width: 5 },
        name: "target",
        hoverinfo: "skip",
      });
    }
    if (own.length) {
      traces.push({
        type: "scatter3d",
        mode: "lines",
        x: own.map((p) => p[0]),
        y: own.map((p) => p[1]),
        z: own.map((p) => p[2]),
        line: { color: "rgba(91, 159, 212, 0.4)", width: 4 },
        name: "ownship",
        hoverinfo: "skip",
      });
    }

    const trailIdx = traces.length;
    traces.push({
      type: "scatter3d",
      mode: "lines",
      x: own.length ? [own[0][0]] : [0],
      y: own.length ? [own[0][1]] : [0],
      z: own.length ? [own[0][2]] : [0],
      line: { color: COLORS.accent, width: 8 },
      name: "trail",
    });
    const ownIdx = traces.length;
    traces.push({
      type: "scatter3d",
      mode: "markers",
      x: own.length ? [own[0][0]] : [0],
      y: own.length ? [own[0][1]] : [0],
      z: own.length ? [own[0][2]] : [0],
      marker: {
        size: 6,
        color: "#e8f4ff",
        line: { color: COLORS.accent, width: 2 },
        symbol: "circle",
      },
      name: "ownship @ t",
    });
    const tgtIdx = traces.length;
    traces.push({
      type: "scatter3d",
      mode: "markers",
      x: tgt.length ? [tgt[0][0]] : [0],
      y: tgt.length ? [tgt[0][1]] : [0],
      z: tgt.length ? [tgt[0][2]] : [0],
      marker: {
        size: 6,
        color: COLORS.warn,
        symbol: "diamond",
      },
      name: "target @ t",
    });

    traj3dIdx = { trail: trailIdx, own: ownIdx, tgt: tgtIdx };

    const layout = {
      paper_bgcolor: COLORS.scene,
      plot_bgcolor: COLORS.scene,
      font: { color: COLORS.text, size: 11 },
      margin: { l: 0, r: 0, t: 8, b: 0 },
      uirevision: "intercept3d-" + caseId,
      scene: {
        xaxis: axis("N [m]", bounds.x),
        yaxis: axis("E [m]", bounds.y),
        zaxis: axis("up [m]", bounds.z),
        aspectmode: "manual",
        aspectratio: bounds.ar,
        bgcolor: COLORS.scene,
        camera: {
          eye: { x: 1.9, y: 1.9, z: 1.25 },
          center: { x: 0, y: 0, z: 0 },
          up: { x: 0, y: 0, z: 1 },
        },
      },
      showlegend: true,
      legend: {
        orientation: "h",
        y: 1.08,
        x: 0,
        font: { size: 10, color: COLORS.muted },
        bgcolor: "rgba(0,0,0,0)",
      },
    };

    Plotly.react(host, traces, layout, PLOTLY_CFG).then(function () {
      traj3dReady = true;
      applyTraj3dFrame(host, ts, i);
    });
  }

  /* ── Attitude ──────────────────────────────────────── */

  function frameControl(ts, i) {
    if (!ts || !ts.u || !ts.u.length) return [0, 0, 0, 0];
    const ii = Math.max(0, Math.min(i, ts.u.length - 1));
    const row = ts.u[ii];
    if (!row || !row.length) return [0, 0, 0, 0];
    return [+row[0] || 0, +row[1] || 0, +row[2] || 0, +row[3] || 0];
  }

  function applyAttitudeFrame(host, ts, i) {
    if (!attReady || !host || !ts || !ts.euler_deg) return;
    const ii = Math.max(0, Math.min(i, ts.euler_deg.length - 1));
    const g = vehicleGeom(ts.euler_deg[ii], frameControl(ts, ii));
    const xyz = FV.attitudeRestyleXYZ(g);
    Plotly.restyle(host, xyz, FV.ATTITUDE_RESTYLE_IDS);
  }

  function drawAttitude(forceFull) {
    const host = document.getElementById("attitude-plot");
    const c = activeCase();
    if (!host || !c || !c.timeseries || typeof Plotly === "undefined") return;
    const ts = c.timeseries;
    if (!ts.euler_deg || !ts.euler_deg.length) {
      host.innerHTML = "";
      attReady = false;
      return;
    }
    const i = Math.min(frameIndex, ts.euler_deg.length - 1);
    const key = caseId;

    if (!forceFull && attReady && attKey === key) {
      applyAttitudeFrame(host, ts, i);
      return;
    }

    attReady = false;
    attKey = key;
    const g0 = vehicleGeom(ts.euler_deg[0], frameControl(ts, 0));
    const span = 1.05;
    const bounds = { x: [-span, span], y: [-span, span], z: [-span, span] };
    const traces = FV.buildAttitudeTraces(g0, bounds);
    const layout = FV.defaultAttitudeLayout({
      span: span,
      uirevision: "att-" + caseId,
      sceneBg: COLORS.scene,
      fontColor: COLORS.text,
      mutedColor: COLORS.muted,
      legendY: 1.08,
    });

    Plotly.react(host, traces, layout, PLOTLY_CFG).then(function () {
      attReady = true;
      applyAttitudeFrame(host, ts, i);
    });
  }

  /* ── 2D trajectory ─────────────────────────────────── */

  function drawTraj2d() {
    const host = document.getElementById("traj-plot");
    const c = activeCase();
    if (!host || !c || !c.timeseries || typeof Plotly === "undefined") return;
    const ts = c.timeseries;
    const own = ts.pos_plot || [];
    const tgt = ts.target_plot || [];
    const i = Math.min(frameIndex, Math.max(0, own.length - 1));
    const rCap = captureRadius();

    const ownXY = extractXY(own);
    const tgtXY = extractXY(tgt);
    const trailOwn = extractXY(own.slice(0, i + 1));
    const ownNow = own[i] || [0, 0, 0];
    const tgtNow = tgt[i] || [0, 0, 0];
    const nowOwn = extractXY([ownNow]);
    const nowTgt = extractXY([tgtNow]);

    const cpaIdx = cpaIndex(c, ts);
    const cpaTgt = tgt[cpaIdx] || tgtNow;
    const cpaXY = extractXY([cpaTgt]);

    const traces = [];

    if (showBands && hasBands()) {
      bandCloudTraces2d(demo.mc.bands).forEach(function (tr) {
        traces.push(tr);
      });
    }

    if (tgt.length) {
      traces.push({
        x: tgtXY.x,
        y: tgtXY.y,
        mode: "lines",
        name: "target",
        line: { color: COLORS.warn, width: 2 },
      });
    }
    if (own.length) {
      traces.push({
        x: ownXY.x,
        y: ownXY.y,
        mode: "lines",
        name: "ownship",
        line: { color: COLORS.accent, width: 1.5, dash: "dot" },
        opacity: 0.55,
      });
      traces.push({
        x: trailOwn.x,
        y: trailOwn.y,
        mode: "lines",
        name: "ownship trail",
        line: { color: COLORS.accent, width: 2.5 },
        showlegend: false,
      });
    }
    if (ts.ref_plot && ts.ref_plot.length) {
      const refXY = extractXY(ts.ref_plot);
      traces.push({
        x: refXY.x,
        y: refXY.y,
        mode: "lines",
        name: "reference",
        line: { color: COLORS.muted, width: 1, dash: "dash" },
        opacity: 0.7,
      });
    }

    traces.push(circleTrace(cpaXY.x[0], cpaXY.y[0], rCap, `capture ${fmt(rCap, 1)} m`));

    traces.push({
      x: nowTgt.x,
      y: nowTgt.y,
      mode: "markers",
      name: "target @ t",
      marker: { color: COLORS.warn, size: 11, symbol: "diamond" },
    });
    traces.push({
      x: nowOwn.x,
      y: nowOwn.y,
      mode: "markers",
      name: "ownship @ t",
      marker: { color: COLORS.accent, size: 12, symbol: "circle" },
    });

    const layout = plotLayoutBase({
      title: {
        text: projection === "NE" ? "North–East (top-down)" : "North–Up",
        font: { size: 12, color: COLORS.muted },
      },
      xaxis: {
        title: ownXY.xlabel,
        gridcolor: COLORS.grid,
        zerolinecolor: COLORS.grid,
        color: COLORS.muted,
        scaleanchor: "y",
        scaleratio: 1,
      },
      yaxis: {
        title: ownXY.ylabel,
        gridcolor: COLORS.grid,
        zerolinecolor: COLORS.grid,
        color: COLORS.muted,
      },
      margin: { l: 52, r: 12, t: 36, b: 44 },
      uirevision: "traj2d-" + caseId + "-" + projection,
    });

    Plotly.react(host, traces, layout, PLOTLY_CFG);
  }

  function drawRange() {
    const host = document.getElementById("range-plot");
    const c = activeCase();
    if (!host || !c || !c.timeseries || typeof Plotly === "undefined") return;
    const ts = c.timeseries;
    const rCap = captureRadius();
    const i = Math.min(frameIndex, ts.t.length - 1);
    const tPlay = ts.t[i];

    const traces = [
      {
        x: ts.t,
        y: ts.range_m,
        mode: "lines",
        name: "range",
        line: { color: COLORS.accent, width: 2 },
      },
      {
        x: [ts.t[0], ts.t[ts.t.length - 1]],
        y: [rCap, rCap],
        mode: "lines",
        name: `r = ${fmt(rCap, 1)} m`,
        line: { color: COLORS.good, width: 1.5, dash: "dash" },
      },
      {
        x: [tPlay, tPlay],
        y: [
          Math.min(0, Math.min.apply(null, ts.range_m)),
          Math.max(rCap * 1.2, Math.max.apply(null, ts.range_m)),
        ],
        mode: "lines",
        name: "playhead",
        line: { color: COLORS.warn, width: 1.5 },
        showlegend: false,
      },
      {
        x: [tPlay],
        y: [ts.range_m[i]],
        mode: "markers",
        name: "now",
        marker: { color: COLORS.warn, size: 9 },
        showlegend: false,
      },
    ];

    const layout = plotLayoutBase({
      xaxis: {
        title: "t (s)",
        gridcolor: COLORS.grid,
        zerolinecolor: COLORS.grid,
        color: COLORS.muted,
      },
      yaxis: {
        title: "range (m)",
        gridcolor: COLORS.grid,
        zerolinecolor: COLORS.grid,
        color: COLORS.muted,
        rangemode: "tozero",
      },
      margin: { l: 52, r: 12, t: 20, b: 44 },
      uirevision: "range-" + caseId,
    });

    Plotly.react(host, traces, layout, PLOTLY_CFG);
  }

  /* ── Battery ───────────────────────────────────────── */

  function seriesPlayheadTraces(t, y, tPlay, color, name) {
    const yMin = Math.min.apply(null, y);
    const yMax = Math.max.apply(null, y);
    const pad = 0.05 * Math.max(1e-6, yMax - yMin);
    return [
      {
        x: t,
        y: y,
        mode: "lines",
        name: name,
        line: { color: color, width: 2 },
      },
      {
        x: [tPlay, tPlay],
        y: [yMin - pad, yMax + pad],
        mode: "lines",
        name: "playhead",
        line: { color: COLORS.warn, width: 1.5 },
        showlegend: false,
      },
    ];
  }

  function drawBattery() {
    if (!hasBattery()) return;
    const c = activeCase();
    const ts = c.timeseries;
    const i = Math.min(frameIndex, ts.t.length - 1);
    const tPlay = ts.t[i];

    const powerHost = document.getElementById("power-plot");
    const energyHost = document.getElementById("energy-plot");

    if (powerHost && ts.power_w && ts.power_w.length && typeof Plotly !== "undefined") {
      const traces = seriesPlayheadTraces(ts.t, ts.power_w, tPlay, COLORS.accent, "power");
      Plotly.react(
        powerHost,
        traces,
        plotLayoutBase({
          title: { text: "Power (W)", font: { size: 12, color: COLORS.muted } },
          xaxis: { title: "t (s)", gridcolor: COLORS.grid, color: COLORS.muted },
          yaxis: { title: "W", gridcolor: COLORS.grid, color: COLORS.muted },
          margin: { l: 48, r: 10, t: 32, b: 40 },
          showlegend: false,
          uirevision: "power-" + caseId,
        }),
        PLOTLY_CFG
      );
    } else if (powerHost) {
      powerHost.innerHTML = '<p class="muted-note" style="padding:1rem">power_w not in pack</p>';
    }

    if (
      energyHost &&
      ts.energy_wh_remaining &&
      ts.energy_wh_remaining.length &&
      typeof Plotly !== "undefined"
    ) {
      const traces = seriesPlayheadTraces(
        ts.t,
        ts.energy_wh_remaining,
        tPlay,
        COLORS.good,
        "energy"
      );
      Plotly.react(
        energyHost,
        traces,
        plotLayoutBase({
          title: { text: "Energy remaining (Wh)", font: { size: 12, color: COLORS.muted } },
          xaxis: { title: "t (s)", gridcolor: COLORS.grid, color: COLORS.muted },
          yaxis: { title: "Wh", gridcolor: COLORS.grid, color: COLORS.muted },
          margin: { l: 48, r: 10, t: 32, b: 40 },
          showlegend: false,
          uirevision: "energy-" + caseId,
        }),
        PLOTLY_CFG
      );
    } else if (energyHost) {
      energyHost.innerHTML =
        '<p class="muted-note" style="padding:1rem">energy_wh_remaining not in pack</p>';
    }
  }

  function drawHist() {
    const host = document.getElementById("hist-plot");
    if (!host || !hasMc() || typeof Plotly === "undefined") return;
    const trials = demo.mc.trials;
    const rCap = captureRadius();
    const vals = trials.map((t) => t.min_range_m).filter((v) => v != null && Number.isFinite(v));
    const success = trials
      .filter((t) => t.intercept_success)
      .map((t) => t.min_range_m)
      .filter((v) => v != null && Number.isFinite(v));
    const fail = trials
      .filter((t) => !t.intercept_success)
      .map((t) => t.min_range_m)
      .filter((v) => v != null && Number.isFinite(v));

    const traces = [];
    if (success.length) {
      traces.push({
        x: success,
        type: "histogram",
        name: "capture",
        marker: { color: "rgba(62, 207, 142, 0.65)" },
        opacity: 0.85,
        nbinsx: 30,
      });
    }
    if (fail.length) {
      traces.push({
        x: fail,
        type: "histogram",
        name: "miss",
        marker: { color: "rgba(240, 113, 120, 0.65)" },
        opacity: 0.85,
        nbinsx: 30,
      });
    }
    if (!traces.length && vals.length) {
      traces.push({
        x: vals,
        type: "histogram",
        name: "min_range",
        marker: { color: "rgba(91, 159, 212, 0.7)" },
        nbinsx: 30,
      });
    }

    const layout = plotLayoutBase({
      barmode: "overlay",
      xaxis: {
        title: "min range (m)",
        gridcolor: COLORS.grid,
        zerolinecolor: COLORS.grid,
        color: COLORS.muted,
      },
      yaxis: {
        title: "count",
        gridcolor: COLORS.grid,
        zerolinecolor: COLORS.grid,
        color: COLORS.muted,
      },
      shapes: [
        {
          type: "line",
          x0: rCap,
          x1: rCap,
          y0: 0,
          y1: 1,
          yref: "paper",
          line: { color: COLORS.good, width: 2, dash: "dash" },
        },
      ],
      annotations: [
        {
          x: rCap,
          y: 1,
          yref: "paper",
          text: `r=${fmt(rCap, 1)} m`,
          showarrow: false,
          xanchor: "left",
          yanchor: "bottom",
          font: { size: 10, color: COLORS.good },
          xshift: 4,
        },
      ],
      margin: { l: 48, r: 12, t: 16, b: 44 },
    });

    Plotly.react(host, traces, layout, PLOTLY_CFG);

    const statsHost = document.getElementById("mc-stats");
    const s = demo.mc.summary || {};
    const mr = s.min_range_m || {};
    const tilt = s.peak_tilt_rad || {};
    const nBand = hasBands() ? demo.mc.bands.n_paths_used : null;
    if (statsHost) {
      statsHost.innerHTML = `
        <li><span>P(capture)</span><strong class="${s.p_capture >= 0.5 ? "ok" : "fail"}">${fmtPct(s.p_capture)}</strong></li>
        <li><span>n intercept / n trials</span><strong>${s.n_intercept_success ?? "—"} / ${s.n_trials ?? "—"}</strong></li>
        <li><span>min range mean</span><strong>${fmt(mr.mean, 3)} m</strong></li>
        <li><span>min range p50</span><strong>${fmt(mr.p50, 3)} m</strong></li>
        <li><span>min range p95</span><strong>${fmt(mr.p95, 3)} m</strong></li>
        <li><span>min range [min, max]</span><strong>${fmt(mr.min, 3)} … ${fmt(mr.max, 3)} m</strong></li>
        ${
          tilt.mean != null
            ? `<li><span>peak tilt mean</span><strong>${fmt((tilt.mean * 180) / Math.PI, 1)}°</strong></li>`
            : ""
        }
        ${nBand != null ? `<li><span>band paths used</span><strong>${nBand}</strong></li>` : ""}
      `;
    }

    const how = document.getElementById("how-to");
    const bullets =
      (demo.ui && demo.ui.how_to_read) || [
        "Pad takeoff → climb through ground effect → open-loop intercept path.",
        "Plant parameter scatter only — controller gains are fixed.",
        "Capture = min range ≤ capture radius (not tracking success).",
        "MC is on the success recipe; Fail toggle is geometry contrast only.",
        "Bands = ownship spatial percentiles under plant re-sim (not sensor noise).",
      ];
    if (how) {
      how.innerHTML = bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("");
    }
  }

  function drawAll() {
    // Isolate pane failures so one bad plot cannot blank the rest.
    const panes = [
      ["traj3d", drawTraj3d],
      ["attitude", drawAttitude],
      ["traj2d", drawTraj2d],
      ["range", drawRange],
      ["battery", drawBattery],
      ["hist", drawHist],
    ];
    panes.forEach(function (pair) {
      try {
        pair[1](true);
      } catch (err) {
        console.error("[intercept demo] draw " + pair[0] + " failed:", err);
      }
    });
  }

  /* ── Load ──────────────────────────────────────────── */

  function showError(msg, detail) {
    el.app.innerHTML = `
      <div class="error-card">
        <h2>Could not load demo pack</h2>
        <p>${escapeHtml(msg)}</p>
        ${detail ? `<p><code>${escapeHtml(detail)}</code></p>` : ""}
        <p class="muted-note">
          From repo root, regenerate with
          <code>uv run python docs/demos/intercept/scripts/export_demo_data.py --success-run &lt;run&gt; --with-bands</code>
          then open this page via <code>python -m http.server</code> from
          <code>docs/demos/intercept</code> (or any ancestor with the relative path intact).
        </p>
      </div>
    `;
  }

  function applyQueryCase() {
    try {
      const q = new URLSearchParams(window.location.search);
      const c = q.get("case");
      if (c === "fail" && hasFail()) caseId = "fail";
      if (c === "success") caseId = "success";
    } catch (_) {
      /* ignore */
    }
  }

  async function boot() {
    const url = "./data/demo.json";
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
      demo = await res.json();
    } catch (err) {
      showError(
        "Failed to fetch data/demo.json. Prefer a local static server if opening via file://.",
        String(err && err.message ? err.message : err)
      );
      return;
    }

    if (!demo || !demo.cases || !demo.cases.success) {
      showError("demo.json is missing cases.success", url);
      return;
    }

    caseId = (demo.ui && demo.ui.default_case) || "success";
    if (caseId === "fail" && !hasFail()) caseId = "success";
    applyQueryCase();
    showBands = hasBands();
    frameIndex = 0;
    renderShell();
  }

  document.addEventListener("keydown", onKey);
  boot();
})();
