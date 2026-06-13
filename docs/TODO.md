# TODO

Cross-machine task tracking for active development items.

---

## Immediate / Next Session

(nothing queued)

## Backlog

- Live windowed (pygame) viewer — currently a run must export `--gif` or run `--headless`.

## Done

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
