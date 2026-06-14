<a id="rgb_evo_view.seeding"></a>

# rgb\_evo\_view.seeding

Seeding the founding population that starts a run.

The very first cycle needs creatures from nothing.  ``seed_population`` builds
them according to the ``[seed]`` config: how many, what starting colors, and --
via the locomotion config -- how each one will move.  Every founder is dropped
at a random spot in the world and given the configured starting energy.

<a id="rgb_evo_view.seeding.seed_population"></a>

#### seed\_population

```python
def seed_population(cfg: SeedConfig, loco: LocomotionConfig, world: World,
                    rng: np.random.Generator,
                    next_id: Callable[[], int]) -> list[Creature]
```

Build the founding population (generation 0).
