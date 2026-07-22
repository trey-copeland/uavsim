# Airframe families

**Goal:** Support comparative GNC research across vehicle configurations while keeping the **quadrotor core** lightweight and the default demos honest.

**Backlog:** [`EXTENSIBILITY_TODO.md`](EXTENSIBILITY_TODO.md) (V-8, D-3, D-7/D-8, D-11/D-12, S-7, COMM/INSTR).  
**Architecture:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) §8.6 Multi-airframe extensibility · §7A HIL seams.

---

## Current (core)

| Family | Model | Actuation | Status |
|--------|--------|-----------|--------|
| Quadrotor | Rigid **6-DoF** NED / FRD-like; Euler default or optional **quat** plant | Body wrench \([F, \tau]\); optional **mixer + motors** (`sim.plant: motors`) | **Shipped** — default vehicle + studies + aero opt-in |

See [vehicles.md](vehicles.md) and [dynamics.md](dynamics.md) for today’s contracts.

---

## SIL foundation (Phase 5c/5d + plant fidelity — landed)

Shipped while the HIL rig is ordered/built:

1. ~~**D-10**~~ — quaternion / SO(3) attitude + error-state control/metrics.  
2. ~~**D-3**~~ — `DynamicsModel` protocol.  
3. ~~**5d observers**~~ — `linear_kf` / `mekf` / `partial_raw` (default full-state unchanged); EST-6 flow+alt.  
4. ~~**D-7 / D-8**~~ — first-order motors + X-quad mixer.  
5. ~~**D-4 / D-5**~~ — body drag, prop H-force, ground effect (`vehicle.aero`).  

**Next before multi-airframe:** **D-13 / V-7** — flexible/elastic lumped states.

---

## Planned (additive, after flex / as research needs)

| Family | Sketch | Design notes |
|--------|--------|--------------|
| Tilt-rotor / hybrid VTOL | Extended states (tilt angles), hover / transition / cruise, hybrid aero | New `DynamicsModel` + params; mode-aware guidance/control; not a rewrite of quad `f` |
| Fixed-wing / other | As research needs | Same protocol + study selector (S-7) |

**Rules**

1. **Additive** states and parameters only — do not break the core 12-state quad path.  
2. Shared **MC, export/compare, viz** stay backend-agnostic where possible.  
3. Prefer **pluggable dynamics** (D-3) over `if airframe == …` in the closed-loop core.  
4. Airframe-specific hardware (myDAQ, ESC RPM, lab bus) stays in a **HIL companion**; this repo owns SIL contracts and fixed-step plant seams.

---

## HIL rig tie-in (companion)

Intended lab path (not implemented in this package):

- Airframe kit motors (e.g. F450-class) for motor/mixer validation.  
- myDAQ + high-bandwidth accelerometers (**>1 kHz**) and ESC RPM (INSTR-1).  
- Lightweight pub/sub on the rig (NATS/MQTT, COMM-1); flight-oriented DDS/CAN later (COMM-2).

SIL remains the default design loop; HIL reuses plant I/O and metrics (ARCH §7A).

---

## Comparative studies (vision)

Once S-7 lands, studies should be able to select an airframe family and run the same mission / MC recipe for robustness compare (e.g. quad vs tilt-rotor under mass/inertia scatter) without forking the pipeline.

Until then: one airframe (quadrotor), multiple controllers and missions — as in the [live showcase](https://trey-copeland.github.io/uavsim/).
