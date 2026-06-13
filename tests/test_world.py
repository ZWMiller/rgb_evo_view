import itertools

import numpy as np

from rgb_evo_view.config import WorldConfig
from rgb_evo_view.creature import Creature
from rgb_evo_view.food import FoodResource
from rgb_evo_view.genome import RGBGenome
from rgb_evo_view.locomotion import BrownianWalker
from rgb_evo_view.world import World

_ids = itertools.count()


def _creature(x, y):
    return Creature(next(_ids), RGBGenome.random(np.random.default_rng(0)), [x, y], 10.0, BrownianWalker(1.0))


def _world(mode="reflect"):
    return World(WorldConfig(width=10.0, height=10.0, boundary_mode=mode, contact_radius=1.0))


def test_clamp_keeps_position_inside():
    w = _world("clamp")
    assert np.allclose(w.apply_boundary(np.array([-3.0, 12.0])), [0.0, 10.0])


def test_wrap_teleports_across_edges():
    w = _world("wrap")
    assert np.allclose(w.apply_boundary(np.array([11.0, -1.0])), [1.0, 9.0])


def test_reflect_bounces_off_walls():
    w = _world("reflect")
    # 1 unit past the right wall lands 1 unit back inside.
    assert np.allclose(w.apply_boundary(np.array([11.0, 5.0])), [9.0, 5.0])


def test_food_in_contact_respects_radius():
    w = _world()
    c = _creature(5.0, 5.0)
    near = FoodResource(0, RGBGenome.random(np.random.default_rng(0)), [5.5, 5.0], 1.0)
    far = FoodResource(1, RGBGenome.random(np.random.default_rng(0)), [8.0, 8.0], 1.0)
    eaten = FoodResource(2, RGBGenome.random(np.random.default_rng(0)), [5.0, 5.0], 1.0)
    eaten.consumed = True
    w.food = [near, far, eaten]
    touching = w.food_in_contact(c)
    assert near in touching and far not in touching and eaten not in touching


def test_nearest_creature_excludes_self():
    w = _world()
    a = _creature(0.0, 0.0)
    b = _creature(1.0, 0.0)
    c = _creature(5.0, 0.0)
    assert w.nearest_creature(a, [a, b, c]) is b
