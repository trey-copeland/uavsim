# Tutorials

Story-driven guides for **using and extending** `uavsim`. Contract details stay in [developer guides](../developer/README.md).

| ID | Guide | Status |
|----|--------|--------|
| **T0** | [First run — install → simulate → report](00_first_run.md) | Ready |
| **T-GUIDE-ONLINE** | [Online intercept (G-6)](01_online_intercept.md) | Ready |
| **T-ENERGY** | [Battery / energy feasibility](02_battery_energy.md) | Ready |
| **T-GUIDE-PLUGIN** | Guidance extension / registry (from intercept) | Planned — this branch |
| **D-INTERCEPT** | [Interactive demo SPA](../demos/intercept/) | Ready |

### Live demos

| Surface | URL |
|---------|-----|
| Portfolio showcase | [trey-copeland.github.io/uavsim](https://trey-copeland.github.io/uavsim/) |
| Intercept dashboard | […/uavsim/intercept/](https://trey-copeland.github.io/uavsim/intercept/) |

Local static servers (from **repo root**):

```bash
python3 -m http.server 8766 --directory docs/showcase
python3 -m http.server 8765 --directory docs/demos/intercept
```

### Suggested path

1. **T0** — green install and one LQR hover study  
2. **Showcase** — browse the controller × sensor matrix in the browser  
3. **T-GUIDE-ONLINE** + **live intercept** — online replan and capture metrics  
4. **T-ENERGY** — opt-in battery and energy-fail recipe  
5. Developer guides — vehicles, control, guidance, estimation  

**Plans:** [TUTORIALS.md](../../plan/TUTORIALS.md) · [ONLINE_INTERCEPT_AND_BATTERY.md](../../plan/ONLINE_INTERCEPT_AND_BATTERY.md)
