<a id="rgb_evo_view.config"></a>

# rgb\_evo\_view.config

Run configuration: TOML on disk, frozen dataclasses in memory.

A run is fully described by one TOML file (see ``simulation_configs/default.toml``).
``load_config`` parses it with the standard-library ``tomllib`` and maps each
section onto a small frozen dataclass.  Unknown keys raise a ``TypeError`` so
typos in a config surface immediately rather than being silently ignored.

<a id="rgb_evo_view.config.WorldConfig"></a>

## WorldConfig Objects

```python
@dataclass(frozen=True)
class WorldConfig()
```

<a id="rgb_evo_view.config.WorldConfig.boundary_mode"></a>

#### boundary\_mode

reflect | clamp | wrap

<a id="rgb_evo_view.config.SeedConfig"></a>

## SeedConfig Objects

```python
@dataclass(frozen=True)
class SeedConfig()
```

The founding population placed in cycle 0.

<a id="rgb_evo_view.config.SeedConfig.init_mode"></a>

#### init\_mode

random | all_r | all_g | all_b | fixed | uniform_split | directed

<a id="rgb_evo_view.config.SeedConfig.fixed_rgb"></a>

#### fixed\_rgb

for init_mode = "fixed"

<a id="rgb_evo_view.config.SeedConfig.base_rgb"></a>

#### base\_rgb

for init_mode = "directed"

<a id="rgb_evo_view.config.SeedConfig.noise"></a>

#### noise

directed: per-channel gaussian std

<a id="rgb_evo_view.config.SeedConfig.starting_energy"></a>

#### starting\_energy

energy a creature is created with; also the per-cycle

<a id="rgb_evo_view.config.LocomotionConfig"></a>

## LocomotionConfig Objects

```python
@dataclass(frozen=True)
class LocomotionConfig()
```

<a id="rgb_evo_view.config.LocomotionConfig.walk_mode"></a>

#### walk\_mode

brownian | inertial

<a id="rgb_evo_view.config.LocomotionConfig.inertia"></a>

#### inertia

inertial only: 0 = brownian, ->1 = straight lines

<a id="rgb_evo_view.config.FoodConfig"></a>

## FoodConfig Objects

```python
@dataclass(frozen=True)
class FoodConfig()
```

<a id="rgb_evo_view.config.FoodConfig.genome_mode"></a>

#### genome\_mode

fixed | random | directed

<a id="rgb_evo_view.config.FoodConfig.fixed_rgb"></a>

#### fixed\_rgb

for genome_mode = "fixed"

<a id="rgb_evo_view.config.FoodConfig.base_rgb"></a>

#### base\_rgb

for genome_mode = "directed"

<a id="rgb_evo_view.config.FoodConfig.noise"></a>

#### noise

directed: per-channel gaussian std

<a id="rgb_evo_view.config.FoodConfig.energy_value"></a>

#### energy\_value

scalar, or [min, max] to draw per food

<a id="rgb_evo_view.config.FoodConfig.placement"></a>

#### placement

uniform

<a id="rgb_evo_view.config.EnergyConfig"></a>

## EnergyConfig Objects

```python
@dataclass(frozen=True)
class EnergyConfig()
```

<a id="rgb_evo_view.config.EnergyConfig.overlap_model"></a>

#### overlap\_model

projection | penalized_projection | cosine | histogram_min

<a id="rgb_evo_view.config.EnergyConfig.gamma"></a>

#### gamma

>1 sharpens selection

<a id="rgb_evo_view.config.EnergyConfig.move_cost"></a>

#### move\_cost

energy spent per tick

<a id="rgb_evo_view.config.EnergyConfig.min_overlap"></a>

#### min\_overlap

floor on the overlap fraction in [0,1]; baseline nutrition any food yields

<a id="rgb_evo_view.config.MatingConfig"></a>

## MatingConfig Objects

```python
@dataclass(frozen=True)
class MatingConfig()
```

<a id="rgb_evo_view.config.MatingConfig.distance_space"></a>

#### distance\_space

position | genome

<a id="rgb_evo_view.config.MatingConfig.offspring_per_pair"></a>

#### offspring\_per\_pair

2 = stable population

<a id="rgb_evo_view.config.MatingConfig.parents_survive"></a>

#### parents\_survive

False = non-overlapping generations

<a id="rgb_evo_view.config.MatingConfig.mutation_sigma"></a>

#### mutation\_sigma

per-channel gaussian noise on offspring; 0 = pure average

<a id="rgb_evo_view.config.MatingConfig.offspring_placement"></a>

#### offspring\_placement

midpoint | random

<a id="rgb_evo_view.config.load_config"></a>

#### load\_config

```python
def load_config(path: str | Path) -> SimulationConfig
```

Parse a TOML config file into a ``SimulationConfig``.

The ``[simulation]`` table supplies the top-level fields; every other table
maps to its matching nested dataclass.  Missing tables fall back to the
dataclass defaults, so a minimal config need only override what it cares about.
