<a id="rgb_evo_view.mating"></a>

# rgb\_evo\_view.mating

The mating phase: surviving creatures pair up and produce the next generation.

The algorithm follows the brief: shuffle the survivors, then repeatedly take the
first one, find its nearest partner, pair them off (removing both from the pool),
and emit offspring whose color is the parents' average (optionally jittered by a
small mutation).  An odd creature left with no partner simply does not breed.

"Nearest" is measured either in the world (physical position) or in color space,
per ``MatingConfig.distance_space``.

<a id="rgb_evo_view.mating.reproduce"></a>

#### reproduce

```python
def reproduce(survivors: list[Creature], cfg: MatingConfig,
              loco: LocomotionConfig, world: World, starting_energy: float,
              generation: int, rng: np.random.Generator,
              next_id: Callable[[], int]) -> list[Creature]
```

Pair the survivors and return the next generation.

With ``parents_survive`` the survivors carry over alongside their offspring;
otherwise the generation fully turns over (offspring only).
