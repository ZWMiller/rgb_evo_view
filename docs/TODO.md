# TODO

Cross-machine task tracking for active development items.

---

## Immediate / Next Session

(nothing queued)

## Backlog

(nothing queued)

## Done

### 2026-06-14 — Interactive web viewer (Dash + Plotly)
Browser-based replayer of a finished run's `frames.npz` (no re-simulation), a third
consumer of the one frame stream. Split for testability: `rgb_evo_view/run_loader.py`
(`load_run`/`latest_run`, with `num_cycles`/`steps_per_cycle` derived from the frames;
`build_animation.py` now uses it too), `visualizer/interactive_model.py` (Dash-free
helpers — frame index, `colors_to_hex`, palette sampling, ASCII tulips — unit-tested),
and `visualizer/interactive.py` (the Dash app). World scatter (food squares, creature
circles, genome-colored, responsive/equal-aspect) with cycle+tick scrub sliders, Play,
a speed selector, and end-of-cycle holds mirroring the GIF. A floating Replay/Summary
switcher (both views stay mounted) where Summary is a Plotly reimplementation of
`stats.plot_history` plus a stats strip with starting/final mean-color swatches. A
slide-out flower garden: a 3×3 grid of ASCII tulips whose petals sample the living
population (Resample redraws; stems are fixed per grid position). Replaced the old
"live windowed (pygame) viewer" idea, which is dropped. Added `dash`/`plotly` deps.

### 2026-06-14 — Energy carries over between cycles (stronger selection)
Added `energy.carryover_energy` (default on): surviving parents keep their leftover
energy into the next cycle instead of everyone resetting to `starting_energy`.
Fitness compounds across cycles, so marginal survivors start near empty and the
off-target green channel is driven down harder — reaching a deeper, truer purple
without inflating/deflating the food economy or the `min_overlap` floor. One-line
change in `_begin_cycle` (skip the reset; newborns/founders already get
`starting_energy` at creation). Only bites with `parents_survive = true`. Over an
80-cycle run mean green fell ≈0.35→0.26 with the population staying healthy.

### 2026-06-14 — Rebuild animations from a run log without re-simulating
Every run now persists the full per-tick `Frame` stream to `frames.npz` (ragged
arrays stored flat + per-frame counts, geometry in float16 to halve the file).
`animate()` was refactored to consume an iterable of frames + `history` + a little
geometry instead of a live `SimulationManager`, so the live `--gif` path and a
replay feed the identical renderer. New `build_animation.py <run_dir>` reloads
`frames.npz`/`history.json`/`config.toml` and re-renders with adjustable timing and
frame budget; rebuilt GIFs go to `run_animations/<run-folder-name>.gif`. Lets the
animation builder be tweaked in seconds instead of waiting on the whole sim.

### 2026-06-13 — Slow the evolution down
Added an `energy.min_overlap` floor (soft affine remap of the overlap fraction): any
food is minimally edible, so poorly-matched creatures scavenge instead of starving in
cycle 0. The default config uses `min_overlap = 0.25` over `num_cycles = 20`, which
turns the cycle-0 snap into a gradual drift over ~10 cycles. The floor also weakens
steady-state selection, so the population settles at a lighter "orchid" purple rather
than deep purple — accepted as the honest equilibrium of the gentler environment (a
decaying floor was rejected as artificially engineering the outcome).

### 2026-06-13 — Make the GIF readable
Switched from fixed-fps `FuncAnimation` to per-frame Pillow `duration`s, so holds are
single frames and cost nothing in file size. Base walk frames at 10 fps; the last walk
frame of each cycle (survivors) is held 2 s, the mate frame (births, no food yet) 1 s,
and a closing mean-color drift chart 9 s. Bumped render to 900×900 (DPI only). All
hold lengths are `animate()` parameters.
