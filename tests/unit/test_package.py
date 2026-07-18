"""Phase 0: package import and version smoke tests."""

from __future__ import annotations

import uavsim


def test_version_is_semver_like() -> None:
    parts = uavsim.__version__.split(".")
    assert len(parts) >= 2
    assert all(p.isdigit() for p in parts[:2])


def test_core_subpackages_importable() -> None:
    import uavsim.cli
    import uavsim.control
    import uavsim.dynamics
    import uavsim.guidance
    import uavsim.guidance.waypoints
    import uavsim.hil
    import uavsim.interfaces
    import uavsim.metrics
    import uavsim.monte_carlo
    import uavsim.reference
    import uavsim.results
    import uavsim.sim
    import uavsim.studies
    import uavsim.vehicles
    import uavsim.viz

    assert uavsim.vehicles.__doc__
    assert uavsim.dynamics.__doc__
    assert uavsim.reference.__doc__
    assert uavsim.guidance.__doc__
