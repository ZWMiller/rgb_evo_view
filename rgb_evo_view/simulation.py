"""The simulation manager: orchestrates the food -> walk -> mate cycle.

A run is a sequence of cycles.  Each cycle: scatter fresh food, give every
creature a full energy budget, run the walk phase (every creature moves once per
tick, paying a move cost and eating what it touches; it dies if energy runs out),
then clear the food and let the survivors mate into the next generation.

The whole run is exposed as a generator of :class:`Frame` snapshots (one per
tick, plus one after each mating), which is the single source of truth: the
visualizer animates the frames, and :meth:`SimulationManager.run` simply drains
them headlessly.  Output (a copy of the config and per-cycle ``history.json``)
lands in a timestamped folder, mirroring the sibling ``evolution_simulator``.
"""

from __future__ import annotations

import itertools
import json
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from .config import SimulationConfig
from .energy import get_overlap_model
from .food import spawn_food
from .mating import reproduce
from .seeding import seed_population
from .world import World


@dataclass(frozen=True)
class Frame:
    """An immutable snapshot of the world at one moment, for rendering."""

    cycle: int
    tick: int
    phase: str  # "walk" | "mate"
    creature_positions: np.ndarray  # (N, 2)
    creature_colors: np.ndarray  # (N, 3)
    food_positions: np.ndarray  # (M, 2)
    food_colors: np.ndarray  # (M, 3)

    @property
    def population(self) -> int:
        return len(self.creature_positions)


class SimulationManager:
    """Owns the world, the RNG, the population, and run output."""

    def __init__(self, config: SimulationConfig, config_path: Path | None = None) -> None:
        self.config = config
        self.config_path = config_path
        self.rng = np.random.default_rng(config.seed)
        self.world = World(config.world)
        self.overlap_model = get_overlap_model(config.energy.overlap_model)
        self.cycle = 0
        self.history: list[dict] = []
        self.output_dir: Path | None = None
        self._id_counter = itertools.count()
        self._food_id_counter = itertools.count()

    def _next_id(self) -> int:
        return next(self._id_counter)

    def _next_food_id(self) -> int:
        return next(self._food_id_counter)

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def setup(self) -> Path:
        """Create the output folder, seed the RNG, and build the founding population."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.output_dir = Path(self.config.output_dir) / timestamp
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.config_path is not None:
            shutil.copy(self.config_path, self.output_dir / "config.toml")

        self.world.creatures = seed_population(
            self.config.seeding,
            self.config.locomotion,
            self.world,
            self.rng,
            self._next_id,
        )
        return self.output_dir

    def run(self) -> None:
        """Run the whole simulation headlessly, discarding the rendered frames."""
        for _ in self.frames():
            pass

    def frames(self) -> Iterator[Frame]:
        """Advance the simulation, yielding a snapshot after every tick and mating."""
        self._record_founding()
        for cycle in range(self.config.num_cycles):
            self.cycle = cycle
            self._begin_cycle()
            for tick in range(self.config.steps_per_cycle):
                self._step_tick()
                yield self._snapshot(phase="walk", tick=tick)
                if not self._alive():
                    break
            self._record_stats()
            self.world.clear_food()
            self._reproduce()
            yield self._snapshot(phase="mate", tick=self.config.steps_per_cycle)
            if not self.world.creatures:
                break
        self._write_history()

    # ── phases ────────────────────────────────────────────────────────────────
    def _begin_cycle(self) -> None:
        """Phase 1: give everyone a fresh energy budget and scatter new food."""
        for creature in self.world.creatures:
            creature.energy = self.config.seeding.starting_energy
            creature.alive = True
            creature.food_eaten = 0
            creature.energy_gained = 0.0
        self.world.food = spawn_food(self.config.food, self.world, self.rng, self._next_food_id)

    def _step_tick(self) -> None:
        """Phase 2, one tick: every living creature moves, eats, and maybe dies.

        Creatures are processed in a fresh random order so that, when two reach
        the same food on the same tick, neither side is systematically favored.
        """
        move_cost = self.config.energy.move_cost
        gamma = self.config.energy.gamma
        order = self.rng.permutation(len(self.world.creatures))
        for i in order:
            creature = self.world.creatures[i]
            if not creature.alive:
                continue
            creature.move(self.world, self.rng)
            creature.energy -= move_cost
            for food in self.world.food_in_contact(creature):
                creature.consume(food, self.overlap_model, gamma)
            if creature.energy <= 0.0:
                creature.alive = False
        self.world.food = [f for f in self.world.food if not f.consumed]

    def _reproduce(self) -> None:
        """Phase 3: survivors mate to form the next generation."""
        survivors = self._alive()
        self.world.creatures = reproduce(
            survivors,
            self.config.mating,
            self.config.locomotion,
            self.world,
            self.config.seeding.starting_energy,
            generation=self.cycle + 1,
            rng=self.rng,
            next_id=self._next_id,
        )

    # ── helpers ───────────────────────────────────────────────────────────────
    def _alive(self) -> list:
        return [c for c in self.world.creatures if c.alive]

    def _snapshot(self, phase: str, tick: int) -> Frame:
        creatures = self._alive() if phase == "walk" else self.world.creatures
        c_pos = np.array([c.position for c in creatures]) if creatures else np.empty((0, 2))
        c_col = np.array([c.genome.rgb for c in creatures]) if creatures else np.empty((0, 3))
        f_pos = np.array([f.position for f in self.world.food]) if self.world.food else np.empty((0, 2))
        f_col = np.array([f.genome.rgb for f in self.world.food]) if self.world.food else np.empty((0, 3))
        return Frame(self.cycle, tick, phase, c_pos, c_col, f_pos, f_col)

    @staticmethod
    def _color_stats(creatures: list) -> tuple[list[float], list[float]]:
        """Mean and per-channel std of a group's colors (zeros if empty)."""
        if not creatures:
            return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
        colors = np.array([c.genome.rgb for c in creatures])
        return colors.mean(axis=0).tolist(), colors.std(axis=0).tolist()

    def _record_founding(self) -> None:
        """Log the founding population (cycle -1) before any selection has acted."""
        founders = self.world.creatures
        mean_rgb, std_rgb = self._color_stats(founders)
        self.history.append(
            {
                "cycle": -1,
                "started": len(founders),
                "survivors": len(founders),
                "deaths": 0,
                "mean_rgb": mean_rgb,
                "std_rgb": std_rgb,
            }
        )

    def _record_stats(self) -> None:
        """Log per-cycle outcomes, measured on the survivors before they breed."""
        survivors = self._alive()
        started = len(self.world.creatures)
        mean_rgb, std_rgb = self._color_stats(survivors)
        self.history.append(
            {
                "cycle": self.cycle,
                "started": started,
                "survivors": len(survivors),
                "deaths": started - len(survivors),
                "mean_rgb": mean_rgb,
                "std_rgb": std_rgb,
            }
        )

    def _write_history(self) -> None:
        if self.output_dir is None:
            return
        with (self.output_dir / "history.json").open("w") as fh:
            json.dump(self.history, fh, indent=2)
