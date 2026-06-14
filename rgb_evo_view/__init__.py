"""rgb_evo_view: a teaching visualizer where a creature's color *is* its genome.

Each creature is an RGB triple in ``[0, 1]^3``; natural selection is something you
watch directly as the population's palette shifts toward whatever color the
environment rewards. This package exposes the pieces needed to build and drive a
run -- :class:`SimulationConfig` / :func:`load_config` for configuration,
:class:`SimulationManager` for orchestration, and the :class:`Creature`,
:class:`FoodResource`, :class:`RGBGenome`, :class:`World`, and :class:`Frame`
value/domain types.
"""

from .config import SimulationConfig as SimulationConfig
from .config import load_config as load_config
from .creature import Creature as Creature
from .food import FoodResource as FoodResource
from .genome import RGBGenome as RGBGenome
from .simulation import Frame as Frame
from .simulation import SimulationManager as SimulationManager
from .world import World as World
