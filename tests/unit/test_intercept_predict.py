"""Intercept lead-point helpers."""

from __future__ import annotations

import numpy as np

from uavsim.guidance.intercept.predict import predict_constant_velocity


def test_predict_constant_velocity() -> None:
    p = np.array([1.0, 2.0, 3.0])
    v = np.array([0.0, 5.0, 0.0])
    p_star = predict_constant_velocity(p, v, 1.5)
    np.testing.assert_allclose(p_star, [1.0, 9.5, 3.0])
