# TODO

Cross-machine task tracking for active development items.

---

## Immediate / Next Session

(nothing queued)

## Backlog

### Interactive viewer (Dash/Plotly) — replay a run's frame stream in the browser

Build an interactive web viewer for a finished run, modeled on the one in the
sibling repo `/home/zach/evolution_simulator` (specifically
`visualizer/visualizer_advanced.py` + the `visualizer` package's `latest_run`,
`load_run`, `make_app` helpers). **Reuse that tech stack — Dash + Plotly (`dash`,
`plotly.express`, `plotly.graph_objects`), served locally via `app.run(host, port)`
— but NOT its color scheme or layout; design our own.** This likely supersedes the
old "live windowed (pygame) viewer" idea below, since it gives interactive playback
without a GUI backend; keep the gif/headless export paths regardless.

**What it shows.** A scatter of the world for the selected frame: creatures as round
markers, food as square markers, each painted with its own RGB genome, on a dark
field bounded by the world size. Plus a **summary** view: the mean-RGB drift chart
and run summary stats on one page.

**Controls (all at the bottom):**
- Two scrub timelines: a **cycle** timeline and a **tick** timeline, so you can drag
  to land on any specific frame (cycle picks the cycle, tick picks the frame within
  it — including that cycle's final `mate` frame as the last tick position).
- A **Play** button that advances through frames (use `dcc.Interval` + a frame-index
  `dcc.Store`; rebuild the figure in a callback on each tick).
- A **speed selector** that changes playback rate (vary the `dcc.Interval` period
  and/or a frame stride).
- A **Summary** button/tab that swaps to the drift-chart + stats page.

**Optional flair — a "flower garden" panel (toggleable).** A small side/bottom panel
that renders a set of flowers whose **petals are colored by sampling the currently
alive creatures' colors** for the selected frame (e.g. sample N creature colors —
random or k-means cluster centers — and paint one flower per sampled color). The
point is a glanceable, intuitive read on "what colors are winning" each cycle, for
viewers who don't parse the dot cloud. Header of the panel shows the **generation
number** (the frame's `cycle`). ASCII flowers are fine and charming: green ASCII
stems/leaves with petals tinted by the sampled colors (color the petal glyphs via
HTML/`dcc.Markdown` spans or styled `html.Span`s — Dash renders HTML, so per-glyph
color is easy). Make the whole panel switch-on/off-able. Re-sample on every frame
change so the garden recolors as you scrub or play; on the `mate` frame it'll reflect
the newborns. Keep it cheap (a handful of flowers), independent of the main scatter.

**Data sources (everything is already produced by a run; no re-simulation):**
- `frames.npz` → `rgb_evo_view.recording.load_frames(path)` returns `list[Frame]`.
  `Frame` (see `rgb_evo_view/simulation.py`) has: `cycle`, `tick`, `phase`
  (`"walk"` | `"mate"`), `creature_positions` (N,2), `creature_colors` (N,3),
  `food_positions` (M,2), `food_colors` (M,3), and a `population` property. Colors
  are floats in [0,1] — convert to Plotly `"rgb(r,g,b)"` strings (×255) for markers.
  Frames are one per walk tick (`tick` 0..steps-1) plus one `mate` frame per cycle
  (`tick == steps_per_cycle`). Precompute a `(cycle, tick) -> frame index` map for
  the two sliders.
- `history.json` → list of per-cycle dicts: `cycle` (`-1` is the founding row),
  `started`, `survivors`, `deaths`, `mean_rgb` `[r,g,b]`, `std_rgb` `[r,g,b]`. Drives
  the drift chart and summary stats.
- `config.toml` → world `width`/`height` for axis bounds (these are NOT
  CLI-overridable, so the copied config is authoritative). Derive `num_cycles` /
  `steps_per_cycle` from the frames instead of trusting the config (a CLI `--cycles`
  override is not reflected in the copied config): `num_cycles = max(f.cycle)+1`, and
  `steps_per_cycle = max(tick of mate frames)`. `build_animation.py` already does
  exactly this derivation — copy that logic.

**Integration notes / gotchas:**
- A run dir under `runs/<timestamp>/` holds `config.toml`, `history.json`,
  `frames.npz`, `history.png`. Default the viewer to the most recent run dir (mirror
  evoSim's `latest_run`), with an optional positional path arg + `--port`/`--host`.
- Put it in `visualizer/` (e.g. `visualizer/interactive.py`) with a small runner
  entry like evoSim's. The existing static renderer is `visualizer/animate.py`
  (matplotlib → GIF) and the drift chart is `visualizer/stats.py:draw_mean_rgb` /
  `plot_history` — reimplement the chart in Plotly for the summary page rather than
  embedding matplotlib.
- Add `dash` + `plotly` to `pyproject.toml` deps (currently only `numpy`,
  `matplotlib`).
- Perf: a 20-cycle default run is ~2020 frames, each up to ~300 creatures + ~700
  food; holding all `Frame`s in memory is fine. Drive playback with callbacks +
  `Interval` (don't try to push every frame as a native Plotly animation).
- Reference for "what a good frame looks like": `animate.py` draws food as `marker
  's'` and creatures as `marker 'o'` with thin white edges on black, title =
  `cycle | phase | pop | mean RGB`; it holds the last walk frame (survivors) and the
  mate frame (newborns) longer. The interactive viewer doesn't need holds (the user
  scrubs), but the per-frame title/legend idea is worth keeping.

### Live windowed (pygame) viewer — likely superseded by the Dash viewer above.

## Done

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
