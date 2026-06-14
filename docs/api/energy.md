<a id="rgb_evo_view.energy"></a>

# rgb\_evo\_view.energy

Energy-overlap models: how much of a food's energy a creature can extract.

When a creature eats a food it gains ``food.energy_value * fraction`` where
``fraction in [0, 1]`` measures how well the creature's color matches the food's.
Two anchors pin every model down: against pure-red food ``(1,0,0)`` a creature
with ``R=0`` gains nothing, and a creature with ``R=1`` gains the maximum.

Each model is a function ``(creature_rgb, food_rgb) -> fraction`` registered by
name; the config selects one, and an optional ``gamma`` exponent sharpens how
steeply a mismatch is punished.

<a id="rgb_evo_view.energy.projection"></a>

#### projection

```python
def projection(creature: np.ndarray, food: np.ndarray) -> float
```

Score by how much of the food's *own* color the creature actually carries.

Geometrically this projects the creature's color onto the food's color
direction and measures the projection as a fraction of the food vector's own
length: ``(c . f) / (f . f)``.  Only the channels the food contains can earn
energy, each weighted by how strongly the food expresses it, and brightness
matters -- a half-strength match in the right channel yields half the energy.
Crucially it never looks at pigment the creature spends on channels the food
lacks, so those channels are *neutral*: neither rewarded nor punished.  For
pure-red food a creature scores exactly its own red value; a grey
``(0.5,0.5,0.5)`` creature scores 0.5.  Colorless food (all zeros) yields 0.

<a id="rgb_evo_view.energy.penalized_projection"></a>

#### penalized\_projection

```python
def penalized_projection(creature: np.ndarray, food: np.ndarray) -> float
```

Like ``projection``, but also charges the creature for off-axis pigment.

The creature's color is split relative to the food's color axis into a part
*along* the axis (useful) and a part *perpendicular* to it (wasted).  The
aligned part is rewarded exactly as in ``projection``; the perpendicular
part -- the euclidean distance from the creature's color to the food's axis,
``sqrt(|c|^2 - proj_len^2)`` -- is subtracted, weighted by ``WASTE_PENALTY``
and scaled by the food's length.  So unlike plain projection no channel is
neutral: any pigment the food does not want drags the score down.  The
anchors still hold (a color on the food's axis is unpenalized; ``R=0`` clamps
to 0), but a creature must match the food's *whole* color, absences included.

<a id="rgb_evo_view.energy.cosine"></a>

#### cosine

```python
def cosine(creature: np.ndarray, food: np.ndarray) -> float
```

Score by the *angle* between the two colors as vectors in RGB space.

This is the cosine of the angle between the creature's color vector and the
food's: ``(c . f) / (|c| |f|)``.  It rewards pointing the same direction (the
same hue) and is blind to length, so a faint red and a bright red both score
a perfect match against red food.  Because it compares whole directions, any
channel the creature spends on colors the food lacks tilts the vector away
and lowers the score -- so this model actively punishes "wasted" pigment.
Returns 0 if either color is black (zero length, no defined direction).

<a id="rgb_evo_view.energy.histogram_min"></a>

#### histogram\_min

```python
def histogram_min(creature: np.ndarray, food: np.ndarray) -> float
```

Score by the pigment the two colors literally share, channel by channel.

For each channel it takes the smaller of the creature's and the food's value
-- the amount they overlap -- sums those overlaps, and normalizes by the
food's total pigment: ``sum(min(c, f)) / sum(f)``.  Intuitively, the creature
can only "drink" pigment it has in common with the food, and surplus in any
channel beyond what the food offers is ignored rather than rewarded.

<a id="rgb_evo_view.energy.get_overlap_model"></a>

#### get\_overlap\_model

```python
def get_overlap_model(name: str) -> OverlapModel
```

Look up an overlap model by config name.

<a id="rgb_evo_view.energy.energy_fraction"></a>

#### energy\_fraction

```python
def energy_fraction(creature: RGBGenome,
                    food: RGBGenome,
                    model: OverlapModel,
                    gamma: float = 1.0,
                    min_overlap: float = 0.0) -> float
```

Fraction of a food's energy a creature extracts, in ``[0, 1]``.

Clamps the model's raw score into ``[0, 1]``, then (if ``gamma != 1``) raises
it to ``gamma`` to sharpen selection -- ``gamma > 1`` means only well-matched
creatures profit, while ``gamma == 1`` leaves the score untouched.

Finally, if ``min_overlap > 0`` the score is lifted off the floor with an
affine remap ``min_overlap + (1 - min_overlap) * frac``: a perfect match still
scores 1, a total mismatch scores ``min_overlap`` instead of 0, and every
creature in between keeps its ordering.  This is a baseline-nutrition knob --
any food becomes minimally edible -- that softens the cycle-0 die-off so
selection drifts the palette over many cycles instead of in one step.  It
overrides the "colorless food yields 0" anchor: with a floor, all food feeds.
