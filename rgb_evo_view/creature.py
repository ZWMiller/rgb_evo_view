"""The Creature: a colored dot that wanders, eats, starves, and breeds."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .energy import OverlapModel, energy_fraction
from .genome import RGBGenome
from .locomotion import Walker

if TYPE_CHECKING:
    from .food import FoodResource
    from .world import World


class Creature:
    """One organism in the simulation.

    Its ``genome`` is its color and its entire heritable identity.  During the
    walk phase it moves each tick (paying a move cost charged by the simulation)
    and tops its energy up by eating food it bumps into; if energy hits zero it
    dies and stops moving for the rest of the cycle.
    """

    def __init__(
        self,
        creature_id: int,
        genome: RGBGenome,
        position: np.ndarray,
        energy: float,
        walker: Walker,
        generation: int = 0,
    ) -> None:
        self.id = creature_id
        self.genome = genome
        self.position = np.asarray(position, dtype=float)
        self.energy = energy
        self.walker = walker
        self.generation = generation
        self.alive = True
        # Per-cycle bookkeeping for logging.
        self.food_eaten = 0
        self.energy_gained = 0.0

    def move(self, world: World, rng: np.random.Generator) -> None:
        """Take one step, keeping the creature inside the world's bounds."""
        delta = self.walker.next_delta(rng)
        self.position = world.apply_boundary(self.position + delta)

    def consume(
        self, food: FoodResource, model: OverlapModel, gamma: float, min_overlap: float = 0.0
    ) -> float:
        """Eat a food: gain energy proportional to how well our colors match.

        Marks the food consumed and returns the energy gained (also added to this
        creature's running totals).
        """
        gained = food.energy_value * energy_fraction(self.genome, food.genome, model, gamma, min_overlap)
        self.energy += gained
        self.energy_gained += gained
        self.food_eaten += 1
        food.consumed = True
        return gained
