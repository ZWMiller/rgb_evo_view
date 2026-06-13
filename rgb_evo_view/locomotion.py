"""How creatures wander during the walk phase.

A ``Walker`` carries one creature's locomotion state and, each tick, returns the
displacement to add to that creature's position.  The simulation pays one move
cost per tick regardless of how the displacement was chosen, so locomotion only
decides *direction and distance*, never energy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from .config import LocomotionConfig


def _unit_from_angle(rng: np.random.Generator) -> np.ndarray:
    """A random unit vector drawn uniformly over directions."""
    theta = rng.uniform(0.0, 2.0 * np.pi)
    return np.array([np.cos(theta), np.sin(theta)])


class Walker(ABC):
    """Base class: turns the shared RNG into a per-tick displacement."""

    def __init__(self, step_size: float) -> None:
        self.step_size = step_size

    @abstractmethod
    def next_delta(self, rng: np.random.Generator) -> np.ndarray:
        """Return the ``(dx, dy)`` displacement for this tick."""


class BrownianWalker(Walker):
    """A pure random walk: every tick heads off in a fresh random direction.

    There is no memory between ticks, so the path is a jittery cloud -- the
    simplest possible locomotion and a good baseline.
    """

    def next_delta(self, rng: np.random.Generator) -> np.ndarray:
        return self.step_size * _unit_from_angle(rng)


class InertialWalker(Walker):
    """A random walk with momentum: each tick nudges the previous heading.

    The new heading is a blend of the old heading and a fresh random direction,
    weighted by ``inertia``.  At ``inertia = 0`` it degenerates to a Brownian
    walk; as ``inertia`` approaches 1 the creature keeps turning only slightly
    and travels in long, smooth arcs.
    """

    def __init__(self, step_size: float, inertia: float) -> None:
        super().__init__(step_size)
        if not 0.0 <= inertia <= 1.0:
            raise ValueError(f"inertia must be in [0, 1], got {inertia}")
        self.inertia = inertia
        self.heading: np.ndarray | None = None  # set lazily on the first step

    def next_delta(self, rng: np.random.Generator) -> np.ndarray:
        rand_dir = _unit_from_angle(rng)
        if self.heading is None:
            direction = rand_dir
        else:
            direction = self.inertia * self.heading + (1.0 - self.inertia) * rand_dir
            norm = np.linalg.norm(direction)
            direction = rand_dir if norm == 0.0 else direction / norm
        self.heading = direction
        return self.step_size * direction


def build_walker(cfg: LocomotionConfig) -> Walker:
    """Construct a fresh walker (with its own state) for a single creature."""
    if cfg.walk_mode == "brownian":
        return BrownianWalker(cfg.step_size)
    if cfg.walk_mode == "inertial":
        return InertialWalker(cfg.step_size, cfg.inertia)
    raise ValueError(f"Unknown walk_mode {cfg.walk_mode!r}; choose 'brownian' or 'inertial'")
