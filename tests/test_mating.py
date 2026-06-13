import itertools

import numpy as np

from rgb_evo_view.config import LocomotionConfig, MatingConfig, WorldConfig
from rgb_evo_view.creature import Creature
from rgb_evo_view.genome import RGBGenome
from rgb_evo_view.locomotion import BrownianWalker
from rgb_evo_view.mating import reproduce
from rgb_evo_view.world import World

LOCO = LocomotionConfig()


def _creature(ids, rgb, x, y):
    return Creature(next(ids), RGBGenome.from_channels(*rgb), [x, y], 10.0, BrownianWalker(1.0))


def _world():
    return World(WorldConfig(width=100.0, height=100.0))


def _mating(**overrides):
    base = dict(distance_space="position", offspring_per_pair=2, mutation_sigma=0.0)
    base.update(overrides)
    return MatingConfig(**base)


def test_offspring_color_is_parent_average_without_mutation(rng):
    ids = itertools.count()
    a = _creature(ids, (1.0, 0.0, 1.0), 0.0, 0.0)
    b = _creature(ids, (0.0, 0.0, 1.0), 1.0, 0.0)
    kids = reproduce(
        [a, b],
        _mating(offspring_per_pair=1),
        LOCO,
        _world(),
        50.0,
        generation=1,
        rng=rng,
        next_id=lambda: next(ids),
    )
    assert len(kids) == 1
    assert np.allclose(kids[0].genome.rgb, [0.5, 0.0, 1.0])


def test_offspring_per_pair_controls_population(rng):
    ids = itertools.count()
    creatures = [_creature(ids, (0.5, 0.5, 0.5), i, 0.0) for i in range(4)]
    kids = reproduce(
        creatures,
        _mating(offspring_per_pair=2),
        LOCO,
        _world(),
        50.0,
        generation=1,
        rng=rng,
        next_id=lambda: next(ids),
    )
    assert len(kids) == 4  # 2 pairs x 2 offspring


def test_odd_creature_left_without_mate_is_dropped(rng):
    ids = itertools.count()
    creatures = [_creature(ids, (0.5, 0.5, 0.5), i, 0.0) for i in range(3)]
    kids = reproduce(
        creatures,
        _mating(offspring_per_pair=1),
        LOCO,
        _world(),
        50.0,
        generation=1,
        rng=rng,
        next_id=lambda: next(ids),
    )
    assert len(kids) == 1  # one pair mates, the leftover does not


def test_position_pairing_picks_nearest(rng):
    ids = itertools.count()
    # Shuffle is seeded; assert the produced offspring positions come from
    # midpoints of genuinely adjacent pairs rather than distant ones.
    a = _creature(ids, (1.0, 0.0, 0.0), 0.0, 0.0)
    b = _creature(ids, (1.0, 0.0, 0.0), 0.5, 0.0)  # very close to a
    c = _creature(ids, (1.0, 0.0, 0.0), 50.0, 0.0)
    d = _creature(ids, (1.0, 0.0, 0.0), 50.5, 0.0)  # very close to c
    kids = reproduce(
        [a, b, c, d],
        _mating(offspring_per_pair=1),
        LOCO,
        _world(),
        50.0,
        generation=1,
        rng=rng,
        next_id=lambda: next(ids),
    )
    xs = sorted(float(k.position[0]) for k in kids)
    # Midpoints should be ~0.25 (a-b) and ~50.25 (c-d), never a cross-pair midpoint.
    assert xs[0] < 1.0 and xs[1] > 49.0


def test_parents_survive_keeps_parents(rng):
    ids = itertools.count()
    creatures = [_creature(ids, (0.5, 0.5, 0.5), i, 0.0) for i in range(2)]
    kids = reproduce(
        creatures,
        _mating(offspring_per_pair=2, parents_survive=True),
        LOCO,
        _world(),
        50.0,
        generation=1,
        rng=rng,
        next_id=lambda: next(ids),
    )
    assert len(kids) == 4  # 2 parents + 2 offspring


def test_empty_survivors_yield_no_offspring(rng):
    ids = itertools.count()
    assert (
        reproduce([], _mating(), LOCO, _world(), 50.0, generation=1, rng=rng, next_id=lambda: next(ids)) == []
    )
