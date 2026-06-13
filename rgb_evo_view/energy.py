"""Energy-overlap models: how much of a food's energy a creature can extract.

When a creature eats a food it gains ``food.energy_value * fraction`` where
``fraction in [0, 1]`` measures how well the creature's color matches the food's.
Two anchors pin every model down: against pure-red food ``(1,0,0)`` a creature
with ``R=0`` gains nothing, and a creature with ``R=1`` gains the maximum.

Each model is a function ``(creature_rgb, food_rgb) -> fraction`` registered by
name; the config selects one, and an optional ``gamma`` exponent sharpens how
steeply a mismatch is punished.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .genome import RGBGenome

OverlapModel = Callable[[np.ndarray, np.ndarray], float]

# Weight of the off-axis "wasted pigment" penalty in ``penalized_projection``.
# 0 reduces it to plain ``projection``; larger values punish mismatched color
# more steeply.  1.0 makes a pure-white creature earn ~0.29 from red food.
WASTE_PENALTY = 1.0


def projection(creature: np.ndarray, food: np.ndarray) -> float:
    """Score by how much of the food's *own* color the creature actually carries.

    Geometrically this projects the creature's color onto the food's color
    direction and measures the projection as a fraction of the food vector's own
    length: ``(c . f) / (f . f)``.  Only the channels the food contains can earn
    energy, each weighted by how strongly the food expresses it, and brightness
    matters -- a half-strength match in the right channel yields half the energy.
    Crucially it never looks at pigment the creature spends on channels the food
    lacks, so those channels are *neutral*: neither rewarded nor punished.  For
    pure-red food a creature scores exactly its own red value; a grey
    ``(0.5,0.5,0.5)`` creature scores 0.5.  Colorless food (all zeros) yields 0.
    """
    denom = float(food @ food)
    if denom == 0.0:
        return 0.0
    return float(creature @ food) / denom


def penalized_projection(creature: np.ndarray, food: np.ndarray) -> float:
    """Like ``projection``, but also charges the creature for off-axis pigment.

    The creature's color is split relative to the food's color axis into a part
    *along* the axis (useful) and a part *perpendicular* to it (wasted).  The
    aligned part is rewarded exactly as in ``projection``; the perpendicular
    part -- the euclidean distance from the creature's color to the food's axis,
    ``sqrt(|c|^2 - proj_len^2)`` -- is subtracted, weighted by ``WASTE_PENALTY``
    and scaled by the food's length.  So unlike plain projection no channel is
    neutral: any pigment the food does not want drags the score down.  The
    anchors still hold (a color on the food's axis is unpenalized; ``R=0`` clamps
    to 0), but a creature must match the food's *whole* color, absences included.
    """
    denom = float(food @ food)
    if denom == 0.0:
        return 0.0
    food_len = float(np.sqrt(denom))
    proj_len = float(creature @ food) / food_len  # length of c along the food axis
    perp = float(np.sqrt(max(creature @ creature - proj_len * proj_len, 0.0)))
    reward = float(creature @ food) / denom
    return reward - WASTE_PENALTY * perp / food_len


def cosine(creature: np.ndarray, food: np.ndarray) -> float:
    """Score by the *angle* between the two colors as vectors in RGB space.

    This is the cosine of the angle between the creature's color vector and the
    food's: ``(c . f) / (|c| |f|)``.  It rewards pointing the same direction (the
    same hue) and is blind to length, so a faint red and a bright red both score
    a perfect match against red food.  Because it compares whole directions, any
    channel the creature spends on colors the food lacks tilts the vector away
    and lowers the score -- so this model actively punishes "wasted" pigment.
    Returns 0 if either color is black (zero length, no defined direction).
    """
    cn = float(np.linalg.norm(creature))
    fn = float(np.linalg.norm(food))
    if cn == 0.0 or fn == 0.0:
        return 0.0
    return float(creature @ food) / (cn * fn)


def histogram_min(creature: np.ndarray, food: np.ndarray) -> float:
    """Score by the pigment the two colors literally share, channel by channel.

    For each channel it takes the smaller of the creature's and the food's value
    -- the amount they overlap -- sums those overlaps, and normalizes by the
    food's total pigment: ``sum(min(c, f)) / sum(f)``.  Intuitively, the creature
    can only "drink" pigment it has in common with the food, and surplus in any
    channel beyond what the food offers is ignored rather than rewarded.
    """
    denom = float(food.sum())
    if denom == 0.0:
        return 0.0
    return float(np.minimum(creature, food).sum()) / denom


_REGISTRY: dict[str, OverlapModel] = {
    "projection": projection,
    "penalized_projection": penalized_projection,
    "cosine": cosine,
    "histogram_min": histogram_min,
}


def get_overlap_model(name: str) -> OverlapModel:
    """Look up an overlap model by config name."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(f"Unknown overlap_model {name!r}; choose from {sorted(_REGISTRY)}") from None


def energy_fraction(
    creature: RGBGenome,
    food: RGBGenome,
    model: OverlapModel,
    gamma: float = 1.0,
) -> float:
    """Fraction of a food's energy a creature extracts, in ``[0, 1]``.

    Clamps the model's raw score into ``[0, 1]``, then (if ``gamma != 1``) raises
    it to ``gamma`` to sharpen selection -- ``gamma > 1`` means only well-matched
    creatures profit, while ``gamma == 1`` leaves the score untouched.
    """
    frac = model(creature.rgb, food.rgb)
    frac = min(max(frac, 0.0), 1.0)
    if gamma != 1.0:
        frac = frac**gamma
    return frac
