"""The mating phase: surviving creatures pair up and produce the next generation.

The algorithm follows the brief: shuffle the survivors, then repeatedly take the
first one, find its nearest partner, pair them off (removing both from the pool),
and emit offspring whose color is the parents' average (optionally jittered by a
small mutation).  An odd creature left with no partner simply does not breed.

"Nearest" is measured either in the world (physical position) or in color space,
per ``MatingConfig.distance_space``.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .config import LocomotionConfig, MatingConfig
from .creature import Creature
from .genome import RGBGenome
from .locomotion import build_walker
from .world import World


def _coord(creature: Creature, space: str) -> np.ndarray:
    """The vector used to measure 'closeness' for pairing."""
    if space == "position":
        return creature.position
    if space == "genome":
        return creature.genome.rgb
    raise ValueError(f"Unknown distance_space {space!r}; choose 'position' or 'genome'")


def _nearest_index(target: Creature, pool: list[Creature], space: str) -> int:
    """Index in ``pool`` of the creature closest to ``target``."""
    tc = _coord(target, space)
    dists = [float(np.sum((_coord(other, space) - tc) ** 2)) for other in pool]
    return int(np.argmin(dists))


def _make_offspring(
    parent_a: Creature,
    parent_b: Creature,
    cfg: MatingConfig,
    loco: LocomotionConfig,
    starting_energy: float,
    generation: int,
    rng: np.random.Generator,
    next_id: Callable[[], int],
) -> Creature:
    """One child of two parents: averaged color (plus mutation) and a placement."""
    blended = parent_a.genome.blend(parent_b.genome).rgb
    if cfg.mutation_sigma > 0.0:
        blended = blended + rng.normal(0.0, cfg.mutation_sigma, size=3)
    genome = RGBGenome.from_array(blended)  # clamps back into [0, 1]

    if cfg.offspring_placement == "midpoint":
        position = (parent_a.position + parent_b.position) / 2.0
    elif cfg.offspring_placement == "random":
        position = None  # filled in by the caller, which knows the world
    else:
        raise ValueError(f"Unknown offspring_placement {cfg.offspring_placement!r}")

    return Creature(
        creature_id=next_id(),
        genome=genome,
        position=position if position is not None else parent_a.position,
        energy=starting_energy,
        walker=build_walker(loco),
        generation=generation,
    )


def reproduce(
    survivors: list[Creature],
    cfg: MatingConfig,
    loco: LocomotionConfig,
    world: World,
    starting_energy: float,
    generation: int,
    rng: np.random.Generator,
    next_id: Callable[[], int],
) -> list[Creature]:
    """Pair the survivors and return the next generation.

    With ``parents_survive`` the survivors carry over alongside their offspring;
    otherwise the generation fully turns over (offspring only).
    """
    # Shuffle by drawing a permutation of indices (keeps the shared RNG as the
    # single source of randomness, and works on a plain list of objects).
    order = rng.permutation(len(survivors))
    pool = [survivors[i] for i in order]

    offspring: list[Creature] = []
    while len(pool) >= 2:
        first = pool.pop(0)
        partner = pool.pop(_nearest_index(first, pool, cfg.distance_space))
        for _ in range(cfg.offspring_per_pair):
            child = _make_offspring(first, partner, cfg, loco, starting_energy, generation, rng, next_id)
            if cfg.offspring_placement == "random":
                child.position = world.random_position(rng)
            offspring.append(child)
    # A single leftover creature (odd population) finds no mate and is dropped.

    if cfg.parents_survive:
        return survivors + offspring
    return offspring
