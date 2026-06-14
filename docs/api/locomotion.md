<a id="rgb_evo_view.locomotion"></a>

# rgb\_evo\_view.locomotion

How creatures wander during the walk phase.

A ``Walker`` carries one creature's locomotion state and, each tick, returns the
displacement to add to that creature's position.  The simulation pays one move
cost per tick regardless of how the displacement was chosen, so locomotion only
decides *direction and distance*, never energy.

<a id="rgb_evo_view.locomotion.Walker"></a>

## Walker Objects

```python
class Walker(ABC)
```

Base class: turns the shared RNG into a per-tick displacement.

<a id="rgb_evo_view.locomotion.Walker.next_delta"></a>

#### next\_delta

```python
@abstractmethod
def next_delta(rng: np.random.Generator) -> np.ndarray
```

Return the ``(dx, dy)`` displacement for this tick.

<a id="rgb_evo_view.locomotion.BrownianWalker"></a>

## BrownianWalker Objects

```python
class BrownianWalker(Walker)
```

A pure random walk: every tick heads off in a fresh random direction.

There is no memory between ticks, so the path is a jittery cloud -- the
simplest possible locomotion and a good baseline.

<a id="rgb_evo_view.locomotion.InertialWalker"></a>

## InertialWalker Objects

```python
class InertialWalker(Walker)
```

A random walk with momentum: each tick nudges the previous heading.

The new heading is a blend of the old heading and a fresh random direction,
weighted by ``inertia``.  At ``inertia = 0`` it degenerates to a Brownian
walk; as ``inertia`` approaches 1 the creature keeps turning only slightly
and travels in long, smooth arcs.

<a id="rgb_evo_view.locomotion.build_walker"></a>

#### build\_walker

```python
def build_walker(cfg: LocomotionConfig) -> Walker
```

Construct a fresh walker (with its own state) for a single creature.
