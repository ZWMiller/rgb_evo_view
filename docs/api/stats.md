<a id="visualizer.stats"></a>

# visualizer.stats

Per-cycle summary plots from a run's ``history``.

<a id="visualizer.stats.draw_mean_rgb"></a>

#### draw\_mean\_rgb

```python
def draw_mean_rgb(ax, history: list[dict]) -> None
```

Trace the population's mean R, G, and B (each in its own color) by cycle.

Draws onto a caller-supplied axes so both the static summary plot and the
GIF's closing end-card share one rendering of the palette drift.  The caller
owns the title and x-label.

<a id="visualizer.stats.plot_history"></a>

#### plot\_history

```python
def plot_history(history: list[dict],
                 save_path: str | Path | None = None) -> None
```

Plot mean genome color and population over the run.

The top panel traces the population's mean R, G, and B (each in its own
color) cycle by cycle -- this is where you watch selection drift the palette.
The bottom panel shows population and deaths per cycle.
