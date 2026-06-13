"""The world: the box everything lives in, plus its spatial queries.

The world owns the population and the current food, knows how to keep a moving
creature inside its walls, and answers the two spatial questions the simulation
asks each cycle: "what food is this creature touching?" and "who is the nearest
creature to this one?".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .config import WorldConfig

if TYPE_CHECKING:
    from .creature import Creature
    from .food import FoodResource


def _reflect(value: np.ndarray, length: float) -> np.ndarray:
    """Fold a coordinate back into ``[0, length]`` as if the walls were mirrors."""
    period = 2.0 * length
    folded = np.mod(np.abs(value), period)
    return np.where(folded > length, period - folded, folded)


class World:
    """A 2-D box holding creatures and food."""

    def __init__(self, cfg: WorldConfig) -> None:
        self.width = cfg.width
        self.height = cfg.height
        self.boundary_mode = cfg.boundary_mode
        self.contact_radius = cfg.contact_radius
        self.creatures: list[Creature] = []
        # Cached (M, 2) array of the current food positions, kept aligned with
        # ``self.food`` so contact tests can be vectorized over all food at once.
        self._food: list[FoodResource] = []
        self._food_pos = np.empty((0, 2))

    @property
    def food(self) -> list[FoodResource]:
        return self._food

    @food.setter
    def food(self, food: list[FoodResource]) -> None:
        """Set the current food and refresh the cached position array in step."""
        self._food = food
        self._food_pos = np.array([f.position for f in food]) if food else np.empty((0, 2))

    def random_position(self, rng: np.random.Generator) -> np.ndarray:
        """A uniformly random point inside the box."""
        return np.array([rng.uniform(0.0, self.width), rng.uniform(0.0, self.height)])

    def apply_boundary(self, position: np.ndarray) -> np.ndarray:
        """Bring a proposed position back inside the box per the boundary mode.

        ``reflect`` bounces off the walls, ``clamp`` sticks to them, and ``wrap``
        teleports across to the opposite edge (a toroidal world).
        """
        lengths = np.array([self.width, self.height])
        if self.boundary_mode == "reflect":
            return _reflect(position, lengths)
        if self.boundary_mode == "clamp":
            return np.clip(position, 0.0, lengths)
        if self.boundary_mode == "wrap":
            return np.mod(position, lengths)
        raise ValueError(f"Unknown boundary_mode {self.boundary_mode!r}")

    def food_in_contact(self, creature: Creature) -> list[FoodResource]:
        """All uneaten food within ``contact_radius`` of the creature.

        Distances to every food are computed in one vectorized pass; only the
        handful that fall inside the radius are then touched in Python.
        """
        if len(self.food) == 0:
            return []
        d2 = np.sum((self._food_pos - creature.position) ** 2, axis=1)
        within = np.nonzero(d2 <= self.contact_radius**2)[0]
        return [self.food[i] for i in within if not self.food[i].consumed]

    def nearest_creature(self, creature: Creature, pool: list[Creature]) -> Creature | None:
        """The creature in ``pool`` closest to ``creature`` by position (excluding itself)."""
        best: Creature | None = None
        best_d2 = np.inf
        for other in pool:
            if other is creature:
                continue
            d2 = float(np.sum((other.position - creature.position) ** 2))
            if d2 < best_d2:
                best_d2 = d2
                best = other
        return best

    def clear_food(self) -> None:
        """Remove all food (called when the walk phase ends)."""
        self.food = []
