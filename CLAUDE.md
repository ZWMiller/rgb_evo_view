# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A teaching-oriented visualizer for natural selection where **a creature's color *is* its
genome**. Each creature is an RGB triple in `[0,1]³`; you watch selection by watching the
population's palette shift toward whatever color the environment rewards. There is no separate
phenotype layer — the rendered dot color is the entire heritable identity.

## Commands

```bash
poetry install                                  # Python 3.13+ required
poetry run pytest                               # full test suite
poetry run pytest tests/test_energy.py          # one file
poetry run pytest tests/test_energy.py::test_name -q   # one test
poetry run ruff check . && poetry run ruff format .    # lint + format
poetry run bash scripts/generate_api_docs.sh    # regenerate docs/api from docstrings

# Running a simulation (must pick a mode — bare `runner.py` exits with a pointer):
poetry run python runner.py --gif out.gif       # render run to animated GIF
poetry run python runner.py --headless          # no window; write history + stats plot
poetry run python runner.py my_config.toml --gif out.gif --cycles 200 --seed 7

# Rebuild a GIF from a saved run (no re-simulation; tweak timing/frame budget fast):
poetry run python build_animation.py runs/<timestamp>           # -> run_animations/<timestamp>.gif
poetry run python build_animation.py runs/<timestamp> --fps 15 --max-frames 800
```

A live windowed (pygame) viewer is planned but **not implemented** — that is why a run must
choose `--gif` or `--headless`. Each run writes a timestamped folder under `runs/` containing a
copy of the config, per-cycle `history.json`, a `history.png` summary plot, and `frames.npz`
(the full per-tick geometry — see below). `build_animation.py` replays `frames.npz` to rebuild
the GIF without re-running the sim; rebuilt GIFs land in `run_animations/`.

## Architecture

The cycle is **food → walk → mate**, repeated `num_cycles` times:

1. **Food** — colored food is scattered (static for the cycle).
2. **Walk** — every creature moves once per tick, paying `move_cost` energy/tick; touching food
   yields `energy_value × overlap(creature_rgb, food_rgb)`. Energy ≤ 0 means death.
3. **Mate** — survivors pair with their nearest neighbor; offspring color is the parents' average
   (plus optional mutation).

**`SimulationManager` (`simulation.py`) is the orchestrator and single source of truth.** Its
`frames()` generator yields an immutable `Frame` snapshot after every tick and every mating.
Everything else consumes that one stream: `manager.run()` drains it headlessly,
`recording.save_frames` persists it to `frames.npz`, and `visualizer/animate.py` renders frames
to a GIF. Do not add a parallel rendering path — extend `Frame`/`frames()` instead.

**`animate()` takes an *iterable of frames* (plus `history` and a little geometry), not a live
manager** — so the live run and a replay from `frames.npz` feed the identical renderer. This is
the one-stream rule, not a second path: `runner.py` drains the sim once into a list, saves it,
and hands that same list to `animate()`; `build_animation.py` hands `animate()` a list loaded
from disk. `recording.py` stores the ragged per-frame arrays flat (concatenated + per-frame
counts, no pickling) in **float16** — the GIF can't resolve finer, and it halves the file.
Note `history.json` only holds per-cycle stats, never per-tick geometry; that's why rebuilding a
GIF needs `frames.npz`.

**`World` (`world.py`)** owns the population and current food and answers the two spatial queries
the sim asks: "what food is this creature touching?" and "who is nearest?". It caches food
positions as an `(M,2)` array (via the `food` setter) so contact tests vectorize — keep that
cache aligned if you touch food handling.

**Pluggable strategies are name-registered; the config selects one by string:**
- `energy.py` — four overlap models (`projection`, `penalized_projection`, `cosine`,
  `histogram_min`) via `get_overlap_model(name)`. A `gamma` exponent sharpens selection.
- `locomotion.py` — `Walker` subclasses (`brownian`, `inertial`) via `build_walker`.
- `seeding.py` / `food.py` — population and food color modes (`random`, `fixed`, `directed`, …).

When adding a strategy, register it by name and add the matching string option to the relevant
config dataclass — that is the established extension pattern.

**Config (`config.py`)** is the contract: one TOML file → frozen nested dataclasses. Each TOML
table maps to one dataclass (`[world]`→`WorldConfig`, `[seed]`→`SeedConfig`, etc.; top-level
fields live under `[simulation]`). `load_config` uses stdlib `tomllib`; **unknown keys raise**
(via dataclass kwargs) so config typos fail loudly. CLI `--cycles/--steps/--seed` override via
`dataclasses.replace`.

**`genome.py`** — `RGBGenome` is a frozen value type that always clamps channels to `[0,1]`;
construct via its factories (`random`, `from_array`) rather than mutating.

## Gotchas

- **Keep `starting_energy` below `steps_per_cycle`.** Otherwise no creature starves, selection
  switches off, and (with `parents_survive`) the population grows unbounded. This is the single
  most important tuning constraint.
- **`energy.carryover_energy` (default on) makes survivors keep their leftover energy across
  cycles** instead of resetting to `starting_energy` every cycle — so fitness compounds and
  off-target pigment is selected down harder. It's implemented purely by `_begin_cycle` *not*
  resetting energy (newborns/founders already get `starting_energy` at creation), and only bites
  with `parents_survive = true`. With it on, `starting_energy` is just the initial budget for new
  creatures, not a per-cycle floor.
- `mating.offspring_per_pair = 2` keeps population stable; higher grows it.
- The current default overlap model is `penalized_projection` with `gamma = 1.5` — chosen so the
  purple-food demo converges to *true* purple rather than light orchid (off-axis green must be
  actively penalized, not just left neutral). See `docs/DECISION_LOG.md` for the reasoning.

## Where to read more

- `simulation_configs/default.toml` — every knob, heavily commented.
- `docs/DECISION_LOG.md` — dated design rationale (overlap models, population dynamics).
- `implementation_plan.md` — full original design.
