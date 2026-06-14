<a id="rgb_evo_view.genome"></a>

# rgb\_evo\_view.genome

The RGB genome value type.

A creature's (and a food resource's) genetics are a single RGB color with each
channel a float in ``[0, 1]``.  In the visualizer the color *is* the genome, so
selection is something you watch as the population's palette shifts.

<a id="rgb_evo_view.genome.RGBGenome"></a>

## RGBGenome Objects

```python
@dataclass(frozen=True)
class RGBGenome()
```

An immutable RGB triple with the color math used across the sim.

Channels are floats in ``[0, 1]``.  Construct via the channel constructor or
the ``random`` / ``from_array`` factories so values are always clamped.

<a id="rgb_evo_view.genome.RGBGenome.from_channels"></a>

#### from\_channels

```python
@classmethod
def from_channels(cls, r: float, g: float, b: float) -> RGBGenome
```

A genome from three channel values (clamped into ``[0, 1]``).

<a id="rgb_evo_view.genome.RGBGenome.from_array"></a>

#### from\_array

```python
@classmethod
def from_array(cls, arr) -> RGBGenome
```

A genome from any 3-element array-like (clamped into ``[0, 1]``).

<a id="rgb_evo_view.genome.RGBGenome.random"></a>

#### random

```python
@classmethod
def random(cls, rng: np.random.Generator) -> RGBGenome
```

A uniformly random color.

<a id="rgb_evo_view.genome.RGBGenome.as_array"></a>

#### as\_array

```python
def as_array() -> np.ndarray
```

A copy of the channel array (callers must not mutate the genome).

<a id="rgb_evo_view.genome.RGBGenome.distance"></a>

#### distance

```python
def distance(other: RGBGenome) -> float
```

Euclidean distance to another genome in color space.

<a id="rgb_evo_view.genome.RGBGenome.blend"></a>

#### blend

```python
def blend(other: RGBGenome) -> RGBGenome
```

Channel-wise average of two genomes (used to make offspring).

<a id="rgb_evo_view.genome.RGBGenome.to_mpl"></a>

#### to\_mpl

```python
def to_mpl() -> tuple[float, float, float]
```

An ``(r, g, b)`` tuple for matplotlib facecolors.

<a id="rgb_evo_view.genome.RGBGenome.to_hex"></a>

#### to\_hex

```python
def to_hex() -> str
```

The color as a hash-prefixed ``rrggbb`` hex string.
