/* uavsim intercept L0 demo — vanilla JS + Plotly. Data: ./data/demo.json */
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
  };

  const PLOTLY_CFG = { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["lasso2d", "select2d"] };

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
    return !!(b && b.ownship && b.ownship.N && b.ownship.E);
  }

  function hasFail() {
    return !!(demo && demo.cases && demo.cases.fail);
  }

  function nFrames() {
    const c = activeCase();
    const t = c && c.timeseries && c.timeseries.t;
    return t ? t.length : 0;
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

    el.app.innerHTML = `
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
          </div>
          <button type="button" class="about-toggle" id="about-btn">About</button>
        </div>
        <div class="about-panel ${aboutOpen ? "" : "hidden"}" id="about-panel">
          ${(ui.about_paragraphs || []).map((p) => `<p>${escapeHtml(p)}</p>`).join("")}
        </div>
      </header>

      <div class="story-strip">
        <strong>L0 intercept</strong> — open-loop ownship path + scripted target + fixed NDI.
        Capture when
        <span class="capture-eq">min ‖p<sub>own</sub> − p<sub>tgt</sub>‖ ≤ ${fmt(rCap, 2)} m</span>.
        Plant MC on the success recipe; Fail is a miss nominal for geometry contrast.
      </div>

      <main>
        <div class="primary-row">
          <section class="card">
            <h2>
              Trajectory
              <span class="card-tools">
                <div class="seg" id="proj-seg" role="group" aria-label="Projection">
                  <button type="button" data-proj="NE" class="${projection === "NE" ? "active" : ""}">N–E</button>
                  <button type="button" data-proj="NU" class="${projection === "NU" ? "active" : ""}">N–Up</button>
                </div>
                <label class="tool-label" id="bands-label" title="${hasBands() ? "Show MC percentile bands" : "Bands not in data pack"}">
                  <input type="checkbox" id="bands-toggle" ${showBands && hasBands() ? "checked" : ""} ${hasBands() ? "" : "disabled"} />
                  MC bands
                </label>
              </span>
            </h2>
            <div class="plot-host tall" id="traj-plot"></div>
          </section>
          <section class="card">
            <h2>Range vs time</h2>
            <div class="plot-host tall" id="range-plot"></div>
          </section>
        </div>

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
        </div>

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
          drawTraj();
        });
      });
    }

    const bands = document.getElementById("bands-toggle");
    if (bands) {
      bands.addEventListener("change", () => {
        showBands = bands.checked;
        drawTraj();
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
        updateReadouts();
        drawTraj();
        drawRange();
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
      updateReadouts();
      drawTraj();
      drawRange();
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
    updateReadouts();
    drawTraj();
    drawRange();
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
    // Advance by wall*speed in sim time, map to nearest index
    const tNow = t[frameIndex] + dtWall * speed;
    if (tNow >= t[t.length - 1]) {
      frameIndex = t.length - 1;
      updateReadouts();
      syncScrub();
      drawTraj();
      drawRange();
      stopPlay();
      return;
    }
    // find first index with t[i] >= tNow
    let i = frameIndex;
    while (i < t.length - 1 && t[i + 1] < tNow) i++;
    if (t[i] < tNow && i < t.length - 1) {
      // pick closer
      if (Math.abs(t[i + 1] - tNow) < Math.abs(t[i] - tNow)) i++;
    }
    if (i !== frameIndex) {
      frameIndex = i;
      updateReadouts();
      syncScrub();
      drawTraj();
      drawRange();
    }
    rafId = requestAnimationFrame(tick);
  }

  /* ── Plots ─────────────────────────────────────────── */

  function extractXY(plotPts) {
    // plotPts: array of [N,E,U]
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

  function bandTrace(bands) {
    if (!bands || !bands.ownship) return null;
    const own = bands.ownship;
    const nKey = projection === "NU" ? "U" : "E";
    const eKey = projection === "NU" ? "N" : "N";
    // For NE: x=E, y=N; for NU: x=N, y=U
    let xLo, xHi, yLo, yHi;
    if (projection === "NE") {
      if (!own.E || !own.N) return null;
      xLo = own.E.p5;
      xHi = own.E.p95;
      yLo = own.N.p5;
      yHi = own.N.p95;
    } else {
      if (!own.N || !own.U) return null;
      xLo = own.N.p5;
      xHi = own.N.p95;
      yLo = own.U.p5;
      yHi = own.U.p95;
    }
    if (!xLo || !xHi || !yLo || !yHi) return null;
    // Closed polygon along time then reverse
    const x = xLo.concat(xHi.slice().reverse());
    const y = yLo.concat(yHi.slice().reverse());
    return {
      x,
      y,
      fill: "toself",
      fillcolor: "rgba(91, 159, 212, 0.15)",
      line: { color: "rgba(91, 159, 212, 0.35)", width: 1 },
      name: "MC p5–p95",
      hoverinfo: "skip",
      mode: "lines",
    };
  }

  function drawTraj() {
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

    // Capture circle centered on target at CPA (or current target if no metric)
    let cpaIdx = i;
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
    const cpaTgt = tgt[cpaIdx] || tgtNow;
    const cpaXY = extractXY([cpaTgt]);

    const traces = [];

    if (showBands && hasBands()) {
      const bt = bandTrace(demo.mc.bands);
      if (bt) traces.push(bt);
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

    traces.push(
      circleTrace(cpaXY.x[0], cpaXY.y[0], rCap, `capture ${fmt(rCap, 1)} m`)
    );

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
      title: { text: projection === "NE" ? "North–East (top-down)" : "North–Up", font: { size: 12, color: COLORS.muted } },
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
          Math.min(0, Math.min(...ts.range_m)),
          Math.max(rCap * 1.2, Math.max(...ts.range_m)),
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
    });

    Plotly.react(host, traces, layout, PLOTLY_CFG);
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

    // Capture radius vertical line via shapes
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

    // Stats panel
    const statsHost = document.getElementById("mc-stats");
    const s = demo.mc.summary || {};
    const mr = s.min_range_m || {};
    const tilt = s.peak_tilt_rad || {};
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
      `;
    }

    const how = document.getElementById("how-to");
    const bullets =
      (demo.ui && demo.ui.how_to_read) || [
        "Plant parameter scatter only — controller gains are fixed.",
        "Capture = min range ≤ capture radius (not tracking success).",
        "MC is on the success recipe; Fail toggle is geometry contrast only.",
      ];
    if (how) {
      how.innerHTML = bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("");
    }
  }

  function drawAll() {
    drawTraj();
    drawRange();
    drawHist();
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
          <code>uv run python docs/demos/intercept/scripts/export_demo_data.py --success-run &lt;run&gt;</code>
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
    let url = "./data/demo.json";
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
      demo = await res.json();
    } catch (err) {
      // file:// often blocks fetch; try to guide user
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
