# RGB Evolution Visualizer — Implementation Plan

A teaching-oriented natural-selection simulator. Each creature's "genome" is an
RGB color, so **a creature's color *is* its genetic fingerprint** — selection is
something you watch happen on screen as the population's palette shifts cycle
over cycle.

This document proposes the class design, the simulation manager, the runner
script, the configuration style, and flags the open design questions (with
recommendations) that we should settle before writing code. Organizational
choices (TOML via `tomllib`, a `SimulationRunner` with `setup()`/`run()`, a thin
`runner.py` CLI, timestamped output dirs with a copied config) follow the
conventions already established in `evolution_simulator`.

---

## 1. Core concepts and conventions

| Concept | Decision |
|---|---|
| **Genome** | An RGB triple, each channel a float in `[0.0, 1.0]`. Stored internally as a length-3 `numpy` array. |
| **World space** | A 2-D box `[0, width] × [0, height]`, floats. Origin bottom-left. "Black screen" = background; creatures/food are colored dots. |
| **Color = genome** | A creature is rendered with the literal RGB of its genome. Food likewise. This is the whole point — no separate phenotype. |
| **Time** | The sim advances in **cycles**. Each cycle has three phases (food → walk → mate). Within the walk phase, time advances in **ticks**; every alive creature moves once per tick. |
| **Generations** | Non-overlapping by default (see §6.2): the survivors of a cycle mate to produce the next cycle's population, then the parents are retired. |
| **Randomness** | A single seeded `numpy.random.Generator` threaded through every stochastic call (seeding, food placement, walking, mating), exactly as in `evolution_simulator`. Guarantees reproducibility from `seed`. |

---

## 2. Domain classes

### 2.1 `RGBGenome` (`genome.py`)
A small value type wrapping a 3-vector. Keeps color math in one place.

| Attribute | Type | Meaning |
|---|---|---|
| `rgb` | `np.ndarray` shape `(3,)`, float | Channels in `[0,1]`. |

Key methods:
- `as_array() -> np.ndarray`
- `to_hex() / to_mpl()` — render helpers for the visualizer.
- `distance(other) -> float` — Euclidean distance in color space.
- `blend(other) -> RGBGenome` — channel-wise average (used by mating).
- `clamped()` / validation — keep channels in `[0,1]` after noise/mutation.
- `classmethod random(rng)`, `classmethod from_channels(r,g,b)`.

### 2.2 `Creature` (`creature.py`)

| Attribute | Type | Meaning |
|---|---|---|
| `id` | `int` | Stable identifier. |
| `genome` | `RGBGenome` | Its color/genes. |
| `position` | `np.ndarray (2,)` | Location in the box. |
| `energy` | `float` | Depletes 1 (configurable) per tick; replenished by food. |
| `alive` | `bool` | Set `False` when energy ≤ 0. |
| `generation` | `int` | Cycle in which it was born. |
| `walker` | `Walker` | Locomotion strategy + per-creature state (e.g. current heading). |
| `food_eaten`, `energy_gained` | stats | For logging/inspection. |

Key methods:
- `step(world, rng)` — ask `walker` for a displacement, apply it with the world's boundary rule, pay the move cost.
- `consume(food) -> float` — gain `food.energy_value × overlap(self.genome, food.genome)` (see §5); returns energy gained.
- `is_alive`.

### 2.3 `FoodResource` (`food.py`)
Static — never moves once placed.

| Attribute | Type | Meaning |
|---|---|---|
| `id` | `int` | |
| `genome` | `RGBGenome` | The food's color; determines who can use it. |
| `position` | `np.ndarray (2,)` | Fixed for the cycle. |
| `energy_value` | `float` | Max energy a *perfectly aligned* creature gains. |
| `consumed` | `bool` | Removed from play once eaten. |

### 2.4 `World` (`world.py`)
The box plus everything in it; owns spatial queries and boundary handling.

| Attribute | Type |
|---|---|
| `width`, `height` | `float` |
| `boundary_mode` | `"reflect" | "clamp" | "wrap"` |
| `contact_radius` | `float` — how close a creature must be to a food to eat it |
| `creatures` | `list[Creature]` |
| `food` | `list[FoodResource]` |

Key methods:
- `apply_boundary(position) -> position` — reflect/clamp/wrap a proposed move.
- `food_in_contact(creature) -> list[FoodResource]` — unconsumed food within `contact_radius`.
- `nearest_creature(creature, pool) -> Creature` — for mating (§6.1).
- `clear_food()` — phase-3 cleanup.

> Spatial lookups can start as brute-force O(n·m) loops (fine for hundreds of
> dots) and later swap to a grid/KD-tree behind these same methods if needed.

---

## 3. Pluggable strategies

Each "configurable rule" the brief calls for becomes a small strategy object
selected by name from config. This keeps the manager clean and makes new modes
a one-function addition.

### 3.1 Locomotion (`locomotion.py`)
`Walker.next_delta(creature, world, rng) -> np.ndarray (2,)`.

- **`BrownianWalker(step_size)`** — each tick, a random displacement (Gaussian or
  uniform-direction × step_size). The simplest starting point.
- **`InertialWalker(step_size, inertia)`** — keeps a heading; each tick perturbs
  it by a random angle and blends with the previous heading by `inertia`
  (`0` = pure Brownian, `→1` = nearly straight lines). "Random with inertia."
- *(future)* `ChemotaxisWalker` — bias steps toward nearby compatible food.

### 3.2 Founding-population seeding (`seeding.py`)
`seed_population(cfg, world, rng) -> list[Creature]`. `init_mode`:

- `"random"` — each channel uniform in `[0,1]`.
- `"all_r" / "all_g" / "all_b"` — pure primaries `(1,0,0)`, etc.
- `"fixed"` — every creature a single configured RGB.
- `"uniform_split"` — equal thirds seeded as R, G, B (nice for demos: watch which color wins).
- `"directed"` — a base RGB + per-channel Gaussian noise.

All modes place creatures at uniformly random positions and give them
`starting_energy`.

### 3.3 Food generation + placement (`food.py`, `FoodSpawner`)
`spawn(cfg, world, rng) -> list[FoodResource]`. Genome modes (the brief's
"configurable / random / directed"):

- `"fixed"` — all food a single configured RGB.
- `"random"` — each channel uniform in `[0,1]`.
- `"directed"` — base RGB + per-channel Gaussian noise (the "this RGB with noise" case).

Plus `count` per cycle, `energy_value` (fixed scalar **or** `[min,max]` range),
and `placement` (`"uniform"` random, later `"clustered"`).

### 3.4 Energy-overlap model (`energy.py`)
The function turning (creature color, food color) → energy fraction. **This is
the key open design choice — see §5.** Implemented as named functions in a
registry so the config can pick one and tests can compare them.

### 3.5 Mating (`mating.py`)
`reproduce(survivors, cfg, rng) -> list[Creature]`. Implements the brief's
algorithm (shuffle → repeatedly pair nearest → average → offspring), with the
knobs flagged in §6.

---

## 4. `SimulationManager` (`simulation.py`)

The orchestrator. Mirrors `evolution_simulator`'s `SimulationRunner` shape
(`__init__(config_path)`, `setup()`, `run()`), renamed to make its role obvious.

| Attribute | Meaning |
|---|---|
| `config` | Parsed `SimulationConfig` (see §7). |
| `rng` | The seeded generator. |
| `world` | The `World`. |
| `cycle` | Current cycle index. |
| `history` | Per-cycle stats (population, mean RGB, deaths, births…). |
| `output_dir` | `output_dir/<timestamp>/`, with a copy of the config. |

### 4.1 Lifecycle
```text
setup():
    resolve output dir, copy config, seed rng
    build World from [world] config
    seed founding population (seeding strategy)

run():
    for cycle in range(num_cycles):
        run_cycle()
        record stats; optionally emit frames to the visualizer
        if population empty: stop early (extinction)

run_cycle():               # the three phases from the brief
    PHASE 1 — spawn food:  world.food = FoodSpawner.spawn(...)
    PHASE 2 — walk:        for tick in range(steps_per_cycle): step_tick()
    PHASE 3 — mate:        world.clear_food()
                           world.creatures = reproduce(survivors, ...)

step_tick():               # one animation frame
    for creature in shuffled(alive creatures):   # shuffle = fair food contention
        creature.step(world, rng)                # move + pay move_cost
        for food in world.food_in_contact(creature):
            if not food.consumed:
                creature.energy += creature.consume(food)
                food.consumed = True
        if creature.energy <= 0:
            creature.alive = False                # dies mid-walk, stops moving
    remove consumed food; yield a frame snapshot
```

**Why lockstep ticks** (all creatures move once per tick, rather than one
creature taking all N steps before the next): it makes food competition fair,
keeps the simulation state renderable frame-by-frame for the visualizer, and
matches the mental model of "a cycle is N rounds of everyone moving."

---

## 5. Open question: partial-overlap energy model

The brief fixes two anchors for food `(1,0,0)`:
creature `R=0` → **0 energy**; creature `R=1` → **max energy**. It asks how to
score the in-between, e.g. creature `(0.5,0.5,0.5)` vs food `(1,0,0)`.

Let `c` = creature RGB, `f` = food RGB, and `gain = energy_value × frac(c,f)`
with `frac ∈ [0,1]`. Worked value below is for `c=(0.5,0.5,0.5)`, `f=(1,0,0)`.

### Option A — Projection / food-weighted average **(recommended default)**
`frac = (c · f) / (f · f)` — how much of the food's *own* color the creature
carries, normalized by the food. Equivalently, a weighted average of the
creature's channels weighted by the food's channels.
- `R=0` creature → 0 ✓ · `R=1` creature → 1 ✓ · `(0.5,0.5,0.5)` → **0.5**.
- Respects magnitude: a *dim* red `(0.3,0,0)` only gets `0.3`. Generalizes
  cleanly to multi-channel food (`(1,1,0)` → average of the creature's R and G).
- Simple to explain: "you get energy for the colors you share with the food, in
  the proportions the food offers them." Recommended.

### Option B — Cosine similarity
`frac = (c · f) / (|c| · |f|)`.
- `R=0` → 0 ✓ · `R=1` → 1 ✓ · `(0.5,0.5,0.5)` → **0.577**.
- **Ignores brightness**: a barely-red `(0.01,0,0)` scores a perfect `1.0`,
  which is probably not what we want for an energy story. Sharper selection
  toward *hue* than Option A.

### Option C — Distance-based
`frac = 1 − ‖c − f‖ / √3`.
- `(0.5,0.5,0.5)` → **0.5** (coincidentally matches A here), **but it violates
  the brief's anchor**: a black creature `(0,0,0)` vs `(1,0,0)` scores `0.42`,
  not `0`. Only the *maximally opposite* color scores 0. Listed for completeness;
  not recommended given the stated requirement.

### Option D — Histogram intersection (channel-wise min)
`frac = Σ min(cᵢ, fᵢ) / Σ fᵢ`.
- `R=0` → 0 ✓ · `R=1` → 1 ✓ · `(0.5,0.5,0.5)` → **0.5**. "Shared pigment."
  Behaves almost identically to A for typical food; A is slightly cleaner to
  reason about, so A is the default and D is an easy alternative in the registry.

### Selection-strength knob
Whichever base model, expose `gamma`: `frac ← frac ** gamma`. `gamma > 1`
sharpens selection (only well-matched creatures profit); `gamma = 1` is linear.
A cheap dial for "how harsh is nature today."

**Recommendation:** ship Option A as default, with B and D in the registry and a
`gamma` exponent. All four are ~5-line functions, so we can A/B them empirically.

---

## 6. Other design questions to settle (with recommendations)

### 6.1 "Closest creature" — in which space?
Mating pairs each creature with its nearest by Euclidean distance. That can mean
**physical position** (who's nearby in the box) or **genome/color** (who's
genetically similar). The brief reads most literally as *position* (they're
scattered around the box after walking). Recommend a config switch
`mating.distance_space = "position" | "genome"`, default `"position"`. (Genome
distance gives assortative mating — a nice toggle for experiments.)

### 6.2 Population dynamics — the important one
The brief's mating makes **1 offspring per 2 parents**. Taken literally with
parents retired, the population *halves every cycle* and dies out fast. Options:

- **(Recommended) Non-overlapping generations, `offspring_per_pair = 2`:** each
  surviving pair yields 2 offspring (channel-average of the parents); parents are
  retired; next cycle starts from the offspring with fresh `starting_energy`.
  Two survivors "replace themselves," so a generation that feeds well holds
  steady and a starving one shrinks — selection with a stable-ish population.
- **Overlapping generations:** parents survive into the next cycle alongside 1
  offspring per pair; population regulated purely by starvation deaths.
- **Literal:** 1 offspring per pair, parents retired (population collapses) —
  only useful for short demos.

Make it a config knob (`mating.offspring_per_pair`, `mating.parents_survive`),
default to the first. Worth an explicit decision before coding.

### 6.3 Energy budget vs. step count
For selection to bite, `starting_energy` should be **less than** `steps_per_cycle`
so creatures *must* eat to finish the walk (otherwise everyone survives and there's
no pressure). I'll document this relationship in the config comments and pick
defaults that make starvation real (e.g. `starting_energy = 60`,
`steps_per_cycle = 100`, `move_cost = 1`).

### 6.4 Offspring genome & placement
- Genome: channel-wise average of parents (per brief). Optional
  `mating.mutation_sigma` adds small Gaussian noise per channel (clamped to
  `[0,1]`) so the palette can explore beyond the parents' span — recommend a
  small default like `0.02`; set `0` for the pure-average behavior.
- Position: spawn at the parents' midpoint (or random) — config `offspring_placement`.

### 6.5 Same-tick food contention
If two creatures reach one food in the same tick, the shuffled iteration order
decides who eats it (first marks it `consumed`). Documenting this is enough; the
shuffle keeps it unbiased.

---

## 7. Configuration style

One TOML file per run, parsed with `tomllib`, mapped onto frozen dataclasses,
and **copied into the run's output dir** — same approach as `evolution_simulator`.
Heavily commented so the file doubles as documentation.

### 7.1 Dataclasses (`config.py`)
```python
@dataclass(frozen=True)
class WorldConfig:        width: float; height: float; boundary_mode: str; contact_radius: float
@dataclass(frozen=True)
class SeedConfig:         count: int; init_mode: str; fixed_rgb: list[float] | None
                          base_rgb: list[float] | None; noise: float; starting_energy: float
@dataclass(frozen=True)
class LocomotionConfig:   walk_mode: str; step_size: float; inertia: float
@dataclass(frozen=True)
class FoodConfig:         count: int; genome_mode: str; fixed_rgb / base_rgb / noise
                          energy_value: float | list[float]; placement: str
@dataclass(frozen=True)
class EnergyConfig:       overlap_model: str; gamma: float; move_cost: float
@dataclass(frozen=True)
class MatingConfig:       distance_space: str; offspring_per_pair: int; parents_survive: bool
                          mutation_sigma: float; offspring_placement: str
@dataclass(frozen=True)
class SimulationConfig:   num_cycles: int; steps_per_cycle: int; seed: int | None
                          output_dir: str; world/seed/locomotion/food/energy/mating: …
```
A `load_config(path) -> SimulationConfig` function reads the TOML and constructs
these, applying defaults and validating (e.g. channels in range, modes known).

### 7.2 Annotated example (`simulation_configs/default.toml`)
```toml
# RGB Evolution Visualizer — run configuration.
# Copy and edit; pass the path to runner.py.

[simulation]
num_cycles      = 50      # how many food→walk→mate cycles to run
steps_per_cycle = 100     # ticks in the walk phase; each tick costs move_cost energy
seed            = 42      # omit for a fresh random run
output_dir      = "runs"  # outputs go to runs/<timestamp>/

[world]
width         = 100.0
height        = 100.0
boundary_mode = "reflect" # reflect | clamp | wrap
contact_radius = 2.0      # how close a creature must be to eat a food

[seed]                    # founding population (cycle 0)
count          = 200
init_mode      = "random" # random | all_r | all_g | all_b | fixed | uniform_split | directed
# fixed_rgb    = [1.0, 0.0, 0.0]   # for init_mode = "fixed"
# base_rgb     = [1.0, 0.0, 0.0]   # for init_mode = "directed"
# noise        = 0.1
starting_energy = 60.0    # keep BELOW steps_per_cycle so eating is necessary

[locomotion]
walk_mode = "brownian"    # brownian | inertial
step_size = 1.5
inertia   = 0.8           # only used by inertial: 0 = brownian, →1 = straight lines

[food]
count        = 150        # food placed at the start of every cycle
genome_mode  = "random"   # fixed | random | directed
# fixed_rgb  = [1.0, 0.0, 0.0]
# base_rgb   = [1.0, 0.0, 0.0]
# noise      = 0.15        # for "directed": base color + per-channel gaussian noise
energy_value = 25.0       # scalar, or a range like [15.0, 35.0]
placement    = "uniform"  # uniform | clustered

[energy]
overlap_model = "projection"  # projection | cosine | histogram_min
gamma         = 1.0           # >1 sharpens selection
move_cost     = 1.0           # energy spent per tick

[mating]
distance_space      = "position"  # position | genome
offspring_per_pair  = 2           # 2 = stable population (see plan §6.2)
parents_survive     = false       # false = non-overlapping generations
mutation_sigma      = 0.02        # per-channel gaussian noise on offspring; 0 = pure average
offspring_placement = "midpoint"  # midpoint | random
```

---

## 8. Runner script (`runner.py`)

Thin CLI, same shape as `evolution_simulator/runner.py`: argparse, optional
config path (defaults to the bundled `simulation_configs/default.toml`), and a
few overrides. It builds the manager, runs it, and hands off to the visualizer.

```text
python runner.py                          # bundled default config
python runner.py my_config.toml           # custom config
python runner.py my_config.toml --cycles 200 --seed 7
python runner.py --gif out.gif            # export animation instead of live window
python runner.py --headless               # no rendering; just write stats
```
Responsibilities: resolve/validate the config path, apply overrides, instantiate
`SimulationManager`, call `setup()` then `run()`, and select the output mode
(live window / GIF / headless).

---

## 9. Visualization (`visualizer/`)

Decoupled from the simulation: the manager emits per-tick **frame snapshots**
(creature positions+colors, food positions+colors); the visualizer just draws
them. Proposed default: **matplotlib** `FuncAnimation` — a scatter of creatures
(facecolor = their RGB) on a black axes, food as a second scatter (e.g. square
markers), with a title showing cycle / population / mean color. It works in this
WSL environment, can render a live window *or* export GIF/MP4 (so we don't depend
on a display), and keeps the dependency footprint tiny. `pygame` is a possible
later upgrade for smoother real-time interaction; the snapshot interface stays
the same either way.

A small per-cycle stats panel (population over time, mean RGB drift) is a natural
companion view and reuses the same `history`.

---

## 10. Output & logging

Mirror `evolution_simulator`: `output_dir/<YYYY-MM-DD_HH-MM-SS>/` containing a
copy of the config, a `history.json` (per-cycle: population, births, deaths,
mean/spread of RGB, total energy gained), and optionally the exported animation.
This makes runs reproducible and comparable, and the stats file feeds the
analysis/plots without re-running.

---

## 11. Proposed file layout

```text
rgb_evo_view/
  __init__.py
  genome.py          # RGBGenome value type
  creature.py        # Creature
  food.py            # FoodResource + FoodSpawner (genome + placement strategies)
  world.py           # World: bounds, contact/nearest queries, boundary rules
  locomotion.py      # Walker strategies (brownian, inertial)
  energy.py          # overlap models + gamma, name registry
  seeding.py         # founding-population seeders
  mating.py          # pairing + offspring (reproduce)
  config.py          # dataclasses + load_config(tomllib)
  simulation.py      # SimulationManager (orchestrator, frame/stat emission)
visualizer/
  __init__.py
  animate.py         # matplotlib FuncAnimation renderer + GIF/MP4 export
  stats.py           # per-cycle stat plots
simulation_configs/
  default.toml
runner.py            # CLI entry point
tests/               # see §13
```

---

## 12. Dependencies to add

Runtime deps are currently empty by design. This project needs:
- **`numpy`** — vectors, color math, the shared RNG.
- **`matplotlib`** — the visualizer + stat plots (also already a dev tool in the sibling project).

Add via `poetry add numpy matplotlib`. No other runtime deps anticipated for v1.

---

## 13. Testing strategy

Pure, seedable logic makes this very testable (`pytest`, with the shared
fixed-seed `rng` fixture in `tests/conftest.py`):
- **`energy.py`** — assert the anchors for every model (`R=0`→0, `R=1`→max) and
  the worked `(0.5,0.5,0.5)` values; `gamma` monotonicity.
- **`mating.py`** — offspring = parent average; nearest-pairing leaves the
  correct leftover on odd counts; `offspring_per_pair`/mutation behavior.
- **`locomotion.py`** — steps stay within the box under each boundary mode;
  inertia=0 reduces to brownian statistically.
- **`world.py`** — `food_in_contact` / `nearest_creature` correctness; boundary
  reflect/clamp/wrap math.
- **`seeding.py` / `food.py`** — each mode produces the expected color/position
  distributions; `directed` noise is centered on the base.
- **reproducibility** — same seed ⇒ identical run (positions, deaths, final palette).

---

## 14. Suggested build order

1. `genome.py` + `energy.py` (+ tests) — settle §5 empirically first.
2. `creature.py`, `food.py`, `world.py` — the static world and one creature that moves and eats.
3. `locomotion.py`, `seeding.py` — populate and animate the walk phase.
4. `mating.py` — close the loop; settle §6.2.
5. `config.py` + `simulation.py` + `runner.py` — wire it all to TOML.
6. `visualizer/` — make it watchable; export a GIF.
7. Stats/logging + analysis polish.

---

## 15. Decisions (settled)

1. **Energy-overlap model** (§5) — **Option A (projection)**, default in the base
   config. Both `cosine` and `histogram_min` also live in the registry.
2. **Population dynamics** (§6.2) — non-overlapping generations,
   `offspring_per_pair = 2` (configurable), parents retired.
3. **Mating distance space** (§6.1) — **position**.
4. **Mutation on offspring** (§6.4) — small default `mutation_sigma = 0.02`,
   configurable (set `0` for pure averaging).
5. **Visualizer target** (§9) — matplotlib, live window + GIF export.

### Note on the base "drift to purple" demo
Base config: creatures start **random**, food is fixed **purple `(1,0,1)`**.
Under Option A the energy fraction for `(1,0,1)` food is `(c_R + c_B)/2` — the
**green channel is neutral** (no energy, no cost). Selection drives **R→1, B→1**,
but green merely drifts around its starting mean (~0.5), so the population
converges to ≈`(1, 0.5, 1)` — a *light* purple, not pure `(1,0,1)`. Switching
`overlap_model = "cosine"` penalizes the wasted green and drives the palette to
true purple — a nice selected-vs-neutral-trait contrast.
