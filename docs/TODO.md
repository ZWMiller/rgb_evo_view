# TODO

Cross-machine task tracking for active development items.

---

## Immediate / Next Session

### Slow the evolution down — selection is far too abrupt
With the current default (`penalized_projection`, `gamma = 1.5`, purple food),
essentially everything that isn't already purple-ish starves in **cycle 0**. The
exported GIF is therefore ~1 colorful frame followed by ~599 near-identical
purple frames — it shows the *result* of selection but not the *process*.

Goal: make the drift gradual so you can watch the palette shift over many cycles.
Ideas to explore (probably a combination):
- **Soften the energy penalty** so mildly-mismatched creatures survive the early
  cycles instead of dying immediately (lower `gamma`, smaller `WASTE_PENALTY`, or
  a gentler overlap model). The first cycle's die-off is the main culprit.
- **Loosen the energy budget early** (more `starting_energy` relative to
  `steps_per_cycle`, or more/closer food) so cycle-0 mortality isn't near-total,
  then let weaker but steady selection accumulate over cycles.
- **Cap how much of the population can die per cycle**, or otherwise smooth the
  selection differential so no single cycle is decisive.
- Reconsider whether mating-by-position (vs. fitness) is doing enough of the work;
  gradual drift may want a softer survival filter + many generations.

Acceptance: a default run whose GIF visibly transitions from a rainbow through
intermediate blends to purple over a meaningful fraction of the cycles, not in
one step.

### Make the GIF readable — playback is too fast / chaotic
The current GIF subsamples every ~17th tick and plays at 25 fps, so motion is
jumpy and a viewer can't follow what's happening. Slow it down: hold each frame
longer (lower fps / higher per-frame duration) and/or subsample less aggressively
so the wandering reads as continuous motion rather than noise. Likely wants a
configurable fps/frame-duration and a sensible default once the evolution itself
is slowed.

## Backlog
