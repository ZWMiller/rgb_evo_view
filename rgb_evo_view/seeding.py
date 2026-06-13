"""Seeding the founding population that starts a run.

The very first cycle needs creatures from nothing.  ``seed_population`` builds
them according to the ``[seed]`` config: how many, what starting colors, and --
via the locomotion config -- how each one will move.  Every founder is dropped
at a random spot in the world and given the configured starting energy.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .config import LocomotionConfig, SeedConfig
from .creature import Creature
from .genome import RGBGenome
from .locomotion import build_walker
from .world import World

_PRIMARIES = {
    "all_r": (1.0, 0.0, 0.0),
    "all_g": (0.0, 1.0, 0.0),
    "all_b": (0.0, 0.0, 1.0),
}


def _founder_genome(cfg: SeedConfig, index: int, rng: np.random.Generator) -> RGBGenome:
    """The starting color for founder number ``index`` under the configured mode."""
    mode = cfg.init_mode
    if mode == "random":
        return RGBGenome.random(rng)
    if mode in _PRIMARIES:
        return RGBGenome.from_channels(*_PRIMARIES[mode])
    if mode == "fixed":
        if cfg.fixed_rgb is None:
            raise ValueError("seed init_mode 'fixed' requires fixed_rgb")
        return RGBGenome.from_array(cfg.fixed_rgb)
    if mode == "uniform_split":
        # Split the population into equal R / G / B thirds by index.
        primary = (_PRIMARIES["all_r"], _PRIMARIES["all_g"], _PRIMARIES["all_b"])[index % 3]
        return RGBGenome.from_channels(*primary)
    if mode == "directed":
        if cfg.base_rgb is None:
            raise ValueError("seed init_mode 'directed' requires base_rgb")
        base = np.asarray(cfg.base_rgb, dtype=float)
        return RGBGenome.from_array(base + rng.normal(0.0, cfg.noise, size=3))
    raise ValueError(f"Unknown seed init_mode {mode!r}")


def seed_population(
    cfg: SeedConfig,
    loco: LocomotionConfig,
    world: World,
    rng: np.random.Generator,
    next_id: Callable[[], int],
) -> list[Creature]:
    """Build the founding population (generation 0)."""
    return [
        Creature(
            creature_id=next_id(),
            genome=_founder_genome(cfg, i, rng),
            position=world.random_position(rng),
            energy=cfg.starting_energy,
            walker=build_walker(loco),
            generation=0,
        )
        for i in range(cfg.count)
    ]
