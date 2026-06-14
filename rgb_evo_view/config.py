"""Run configuration: TOML on disk, frozen dataclasses in memory.

A run is fully described by one TOML file (see ``simulation_configs/default.toml``).
``load_config`` parses it with the standard-library ``tomllib`` and maps each
section onto a small frozen dataclass.  Unknown keys raise a ``TypeError`` so
typos in a config surface immediately rather than being silently ignored.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class WorldConfig:
    width: float = 100.0
    height: float = 100.0
    boundary_mode: str = "reflect"  # reflect | clamp | wrap
    contact_radius: float = 2.0


@dataclass(frozen=True)
class SeedConfig:
    """The founding population placed in cycle 0."""

    count: int = 200
    init_mode: str = "random"  # random | all_r | all_g | all_b | fixed | uniform_split | directed
    fixed_rgb: list[float] | None = None  # for init_mode = "fixed"
    base_rgb: list[float] | None = None  # for init_mode = "directed"
    noise: float = 0.1  # directed: per-channel gaussian std
    starting_energy: float = 60.0  # energy a creature is created with; also the per-cycle
    # reset value unless energy.carryover_energy is set (then it is only the initial budget)


@dataclass(frozen=True)
class LocomotionConfig:
    walk_mode: str = "brownian"  # brownian | inertial
    step_size: float = 1.5
    inertia: float = 0.8  # inertial only: 0 = brownian, ->1 = straight lines


@dataclass(frozen=True)
class FoodConfig:
    count: int = 150
    genome_mode: str = "random"  # fixed | random | directed
    fixed_rgb: list[float] | None = None  # for genome_mode = "fixed"
    base_rgb: list[float] | None = None  # for genome_mode = "directed"
    noise: float = 0.15  # directed: per-channel gaussian std
    energy_value: float | list[float] = 25.0  # scalar, or [min, max] to draw per food
    placement: str = "uniform"  # uniform


@dataclass(frozen=True)
class EnergyConfig:
    overlap_model: str = "projection"  # projection | penalized_projection | cosine | histogram_min
    gamma: float = 1.0  # >1 sharpens selection
    move_cost: float = 1.0  # energy spent per tick
    min_overlap: float = 0.0  # floor on the overlap fraction in [0,1]; baseline nutrition any food yields
    # When True, surviving parents carry their leftover energy into the next cycle
    # instead of being reset to starting_energy. Fitness then compounds across
    # cycles -- a marginally-fed survivor starts the next cycle near empty -- which
    # sharpens selection without touching the food economy. Only meaningful with
    # mating.parents_survive = True (otherwise parents do not persist).
    carryover_energy: bool = False


@dataclass(frozen=True)
class MatingConfig:
    distance_space: str = "position"  # position | genome
    offspring_per_pair: int = 2  # 2 = stable population
    parents_survive: bool = False  # False = non-overlapping generations
    mutation_sigma: float = 0.02  # per-channel gaussian noise on offspring; 0 = pure average
    offspring_placement: str = "midpoint"  # midpoint | random


@dataclass(frozen=True)
class SimulationConfig:
    num_cycles: int = 50
    steps_per_cycle: int = 100
    seed: int | None = 42
    output_dir: str = "runs"
    world: WorldConfig = field(default_factory=WorldConfig)
    seeding: SeedConfig = field(default_factory=SeedConfig)
    locomotion: LocomotionConfig = field(default_factory=LocomotionConfig)
    food: FoodConfig = field(default_factory=FoodConfig)
    energy: EnergyConfig = field(default_factory=EnergyConfig)
    mating: MatingConfig = field(default_factory=MatingConfig)


def load_config(path: str | Path) -> SimulationConfig:
    """Parse a TOML config file into a ``SimulationConfig``.

    The ``[simulation]`` table supplies the top-level fields; every other table
    maps to its matching nested dataclass.  Missing tables fall back to the
    dataclass defaults, so a minimal config need only override what it cares about.
    """
    path = Path(path)
    with path.open("rb") as fh:
        data = tomllib.load(fh)

    sim = data.get("simulation", {})
    return SimulationConfig(
        num_cycles=sim.get("num_cycles", 50),
        steps_per_cycle=sim.get("steps_per_cycle", 100),
        seed=sim.get("seed"),
        output_dir=sim.get("output_dir", "runs"),
        world=WorldConfig(**data.get("world", {})),
        seeding=SeedConfig(**data.get("seed", {})),
        locomotion=LocomotionConfig(**data.get("locomotion", {})),
        food=FoodConfig(**data.get("food", {})),
        energy=EnergyConfig(**data.get("energy", {})),
        mating=MatingConfig(**data.get("mating", {})),
    )
