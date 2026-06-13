"""Food resources and how they are seeded each cycle.

Food is static -- once placed at the start of a cycle it never moves, and it
vanishes when eaten or when the cycle's walk phase ends.  Its ``genome`` (color)
decides which creatures can profitably eat it; its ``energy_value`` is the most
a perfectly matched creature could gain from it.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .config import FoodConfig
from .genome import RGBGenome
from .world import World


class FoodResource:
    """A single immovable morsel of food."""

    def __init__(
        self,
        food_id: int,
        genome: RGBGenome,
        position: np.ndarray,
        energy_value: float,
    ) -> None:
        self.id = food_id
        self.genome = genome
        self.position = np.asarray(position, dtype=float)
        self.energy_value = energy_value
        self.consumed = False


def _draw_genome(cfg: FoodConfig, rng: np.random.Generator) -> RGBGenome:
    """Pick a color for one food according to the configured genome mode."""
    if cfg.genome_mode == "fixed":
        if cfg.fixed_rgb is None:
            raise ValueError("food genome_mode 'fixed' requires fixed_rgb")
        return RGBGenome.from_array(cfg.fixed_rgb)
    if cfg.genome_mode == "random":
        return RGBGenome.random(rng)
    if cfg.genome_mode == "directed":
        if cfg.base_rgb is None:
            raise ValueError("food genome_mode 'directed' requires base_rgb")
        base = np.asarray(cfg.base_rgb, dtype=float)
        return RGBGenome.from_array(base + rng.normal(0.0, cfg.noise, size=3))
    raise ValueError(f"Unknown food genome_mode {cfg.genome_mode!r}")


def _draw_energy(cfg: FoodConfig, rng: np.random.Generator) -> float:
    """Energy value for one food: a constant, or a uniform draw from [min, max]."""
    value = cfg.energy_value
    if isinstance(value, (list, tuple)):
        lo, hi = value
        return float(rng.uniform(lo, hi))
    return float(value)


def spawn_food(
    cfg: FoodConfig,
    world: World,
    rng: np.random.Generator,
    next_id: Callable[[], int],
) -> list[FoodResource]:
    """Create this cycle's food, scattered uniformly across the world."""
    if cfg.placement != "uniform":
        raise ValueError(f"Unknown food placement {cfg.placement!r}; only 'uniform' is supported")
    return [
        FoodResource(
            food_id=next_id(),
            genome=_draw_genome(cfg, rng),
            position=world.random_position(rng),
            energy_value=_draw_energy(cfg, rng),
        )
        for _ in range(cfg.count)
    ]
