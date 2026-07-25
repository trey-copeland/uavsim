# Shared static demo assets

| File | Role |
|------|------|
| [`flight_viz.js`](flight_viz.js) | **Canonical** Plotly flight helpers (`window.UavFlightViz`): body↔plot frames, X-quad mesh, inverse mixer, thrust/torque arrows, attitude trace builders |

## Consumers

Apps load a **copy** under their own `lib/` so local `python -m http.server --directory <app>` keeps working:

| App | Load path |
|-----|-----------|
| Showcase | `docs/showcase/lib/flight_viz.js` ← `./lib/flight_viz.js` |
| Intercept | `docs/demos/intercept/lib/flight_viz.js` ← `./lib/flight_viz.js` |

## Sync after edits

```bash
# from repo root
cp docs/shared/flight_viz.js docs/showcase/lib/flight_viz.js
cp docs/shared/flight_viz.js docs/demos/intercept/lib/flight_viz.js
```

GitHub Pages (`pages-site.yml`) deploys each app’s tree (including `lib/`).

## API (summary)

```js
UavFlightViz.vehicleGeom(eulerDeg, u, limits, mixParams)
UavFlightViz.buildAttitudeTraces(g0, bounds)
UavFlightViz.attitudeRestyleXYZ(g)
UavFlightViz.ATTITUDE_RESTYLE_IDS
UavFlightViz.defaultAttitudeLayout({ uirevision, height, … })
UavFlightViz.vehicleTriadAt(pos, eulerDeg, scale)  // path 3D triad
```
