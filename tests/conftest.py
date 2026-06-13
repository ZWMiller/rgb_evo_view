"""Shared pytest fixtures.

The simulation threads a single ``numpy.random.Generator`` through every
randomness-bearing call rather than touching the global ``np.random`` singleton,
so tests obtain a fixed-seed generator from the ``rng`` fixture below to stay
deterministic and isolated.
"""

import numpy as np
import pytest


@pytest.fixture
def rng() -> np.random.Generator:
    """A fresh, fixed-seed generator for a single test."""
    return np.random.default_rng(1234567)
