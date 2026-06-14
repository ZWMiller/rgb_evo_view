  _____   _____ ____    ______          _       _   _         __      ___
 |  __ \ / ____|  _ \  |  ____|        | |     | | (_)        \ \    / (_)
 | |__) | |  __| |_) | | |____   _____ | |_   _| |_ _  ___  _ _\ \  / / _  _____      _____ _ __
 |  _  /| | |_ |  _ <  |  __\ \ / / _ \| | | | | __| |/ _ \| '_ \ \/ / | |/ _ \ \ /\ / / _ \ '__|
 | | \ \| |__| | |_) | | |___\ V / (_) | | |_| | |_| | (_) | | | \  /  | |  __/\ V  V /  __/ |
 |_|  \_\\_____|____/  |______\_/ \___/|_|\__,_|\__|_|\___/|_| |_|\/   |_|\___| \_/\_/ \___|_|


A teaching-oriented visualizer for natural selection, where **a creature's color
is its genome**. Each creature is a dot whose genetics are its RGB value, so you
watch evolution happen directly: a screen of randomly-colored dots is reshaped,
cycle by cycle, into whatever color the environment rewards.

Each cycle has three phases:

1. **Food** — colored food resources are scattered across the world (static).
2. **Walk** — creatures wander for a fixed number of ticks, spending one energy
   per tick. Bumping into food yields energy *proportional to how well the
   creature's color matches the food's color*. Run out of energy and you die.
3. **Mate** — the survivors pair with their nearest neighbor and produce
   offspring whose color is the average of the parents'.

The bundled demo seeds **random** creatures against **purple `(1,0,1)`** food, so
selection recolors the population toward purple over the run's cycles. By default
surviving parents *carry their leftover energy* into the next cycle, so fitness
compounds and off-target pigment (the green channel here) is driven down harder.

See [`implementation_plan.md`](implementation_plan.md) for the full design,
including the four energy-overlap models and the population-dynamics trade-offs.

---

## Installation

```bash
poetry install                 # requires Python 3.13+
poetry run pre-commit install  # optional: enable the git hooks
```

## Running

```bash
poetry run python runner.py --gif out.gif   # render the run to an animated GIF
poetry run python runner.py --headless      # no window; just write history + a stats plot
poetry run python runner.py my_config.toml --gif out.gif --cycles 200 --seed 7
```

A run must choose a mode: `--gif` or `--headless`. A live windowed viewer is
planned (in pygame) but not implemented yet, so a bare `python runner.py` exits
with a pointer to those flags.

Each run writes a timestamped folder under `runs/` containing a copy of the
config, a per-cycle `history.json`, a `history.png` summary plot, and `frames.npz`
(the full per-tick geometry).

### Rebuilding an animation without re-running

Because every run saves `frames.npz`, you can re-render its GIF with different
animation settings — timing, frame budget, hold lengths — in seconds, without
paying for the simulation again:

```bash
poetry run python build_animation.py runs/<timestamp>             # -> run_animations/<timestamp>.gif
poetry run python build_animation.py runs/<timestamp> --fps 15 --max-frames 800
```

Rebuilt GIFs are written under `run_animations/`.

## Configuration

A run is fully described by one TOML file; copy and edit
[`simulation_configs/default.toml`](simulation_configs/default.toml), which is
heavily commented. Key knobs: the energy-overlap `model` (how color match maps to
energy), the locomotion `walk_mode`, the founding population, the food color/mode,
and the mating rules.

> **Tuning note:** keep `starting_energy` *below* `steps_per_cycle` — otherwise no
> creature ever starves, selection switches off, and (with `parents_survive`) the
> population grows without bound.
>
> **Carryover:** with `energy.carryover_energy` (on by default), `starting_energy`
> is only the *initial* budget for new creatures; survivors keep their leftover
> across cycles instead of resetting. This sharpens selection over the run and
> only takes effect with `parents_survive = true`.

## Development

```bash
poetry run pytest                       # run the test suite
poetry run ruff check . && poetry run ruff format .
poetry run bash scripts/generate_api_docs.sh   # regenerate docs/api from docstrings
```
