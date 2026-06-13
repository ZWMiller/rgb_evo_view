# Decision Log

A dated record of design decisions and methodology changes. Updated as part of feature
development and maintenance. Does not track file moves, dependency bumps, or tooling changes —
only decisions about the system itself.

---

## 2026-06-13

- **Genome is an RGB triple; color *is* the genome.** Each creature (and each food
  resource) carries a single RGB color in `[0,1]³`. The dot's rendered color is its
  entire heritable identity — selection is visible directly as the population's palette
  shifts. No separate phenotype layer.

- **Energy from food is `energy_value × overlap(creature, food)`, with four pluggable
  overlap models.** Two anchors pin every model: against pure-red food, a creature with
  `R=0` gains nothing and one with `R=1` gains the max. Models: `projection` (creature's
  shadow along the food's color axis — leaves off-axis channels *neutral*),
  `penalized_projection` (projection minus the euclidean off-axis residual — punishes
  wasted pigment), `cosine` (angle between color vectors, brightness-blind), and
  `histogram_min` (shared pigment per channel). A `gamma` exponent sharpens selection.

- **Default overlap model is `penalized_projection` (with `gamma = 1.5`).** Under plain
  `projection`, a channel the food lacks (green, for purple food) is neither rewarded nor
  punished, so it drifts and the population converges only to a *light* purple ≈ `(1, 0.5, 1)`.
  `penalized_projection` charges creatures for off-axis pigment, so green is actively
  selected down toward true purple. This was added specifically to make the "everything
  drifts to purple" demo reach real purple rather than orchid.

- **Offspring color is the parents' channel average; mating pairs by physical position.**
  Survivors are shuffled, then each is paired with its nearest *positional* neighbor (a
  `genome` distance space is available as a toggle). A small `mutation_sigma` (default 0.02)
  jitters offspring so the palette can explore beyond the parents' span.

- **`parents_survive = true` (overlapping generations) is the default, because 2
  offspring/pair cannot otherwise sustain a population.** With non-overlapping generations,
  next-cycle population ≈ this cycle's *survivors*, so any mortality below 100% ratchets the
  population to extinction (confirmed empirically: the baseline went extinct by ~cycle 38).
  Keeping survivors in the pool lets the population find a food-limited equilibrium while
  selection still acts each cycle. The alternative — non-overlapping generations — requires
  `offspring_per_pair ≥ 3`.

- **Selection requires `starting_energy < steps_per_cycle`.** Energy is reset to
  `starting_energy` at the start of every cycle and one unit is spent per tick. If the
  starting budget covers the whole walk, no creature ever starves, selection switches off,
  and (with `parents_survive`) the population grows without bound. The default keeps
  `starting_energy = 55 < steps_per_cycle = 100`.

- **Default run length set to 100 cycles.** Long enough for the palette to converge and
  stabilize under the tuned defaults (`count = 300` founders, `food = 700 @ 34` energy),
  which hold a healthy population (~100–175) across seeds without near-extinction
  bottlenecks.

- **No live windowed viewer for now; GIF export and headless are the only run modes.**
  The matplotlib `plt.show()` path needs a GUI backend that isn't available in the dev
  environment, and a richer real-time viewer is planned in pygame instead. Until then a
  bare `python runner.py` exits with a pointer to `--gif` / `--headless`, and `animate()`
  only renders GIFs.
