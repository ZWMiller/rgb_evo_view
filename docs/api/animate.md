<a id="visualizer.animate"></a>

# visualizer.animate

GIF export of a run.

Consumes the :meth:`SimulationManager.frames` generator and draws each frame as
two scatter layers on a black field: food (square markers) and creatures (round
markers), each dot painted with its own RGB genome.  A full run is tens of
thousands of ticks, so frames are auto-subsampled to keep the GIF watchable.

Timing is per-frame rather than a single fps: most frames play at the base rate,
the last frame of every cycle is held for a couple seconds (so a viewer can see
which colors survived the walk before mating reshuffles them), and a static "mean
color drift" chart is appended as a long-held closing card.  This uses Pillow's
per-frame ``duration`` list, so the long holds are single frames and cost nothing
in file size.

<a id="visualizer.animate.animate"></a>

#### animate

```python
def animate(frames: Iterable[Frame],
            history: list[dict],
            save_path: str | Path,
            *,
            world_size: tuple[float, float],
            steps_per_cycle: int,
            num_cycles: int,
            fps: int = 10,
            max_frames: int = 400,
            cycle_end_seconds: float = 2.0,
            mate_seconds: float = 1.0,
            final_chart_seconds: float = 9.0) -> None
```

Render a ``Frame`` stream to an animated GIF at ``save_path``.

``frames`` is any iterable of :class:`Frame` -- the live
``SimulationManager.frames()`` generator during a run, or a stream replayed
from a saved ``frames.npz`` (see :mod:`rgb_evo_view.recording`).  ``history``
is the per-cycle stats that feed the closing chart, and ``world_size`` /
``steps_per_cycle`` / ``num_cycles`` describe the run's geometry and length.
There is no live windowed mode yet (a pygame viewer is planned); for now this
only exports a GIF.

Walk ticks are subsampled down to roughly ``max_frames`` rendered frames so a
long run still produces a small, watchable file, but the last walk frame of
every cycle -- the survivors, just before they mate -- is always kept and held
for ``cycle_end_seconds``, and the mate frame -- the newborns before next
cycle's food is scattered -- is held for ``mate_seconds``.  A mean-color chart
is appended and held for ``final_chart_seconds``.  ``fps`` sets the base rate
for all other frames.
