<a id="rgb_evo_view.recording"></a>

# rgb\_evo\_view.recording

Persist and replay the :class:`Frame` stream so an animation can be rebuilt
from a run log without re-running the simulation.

A run's GIF needs the full per-tick geometry -- every creature and food position
and color, every tick -- which the per-cycle ``history.json`` does not carry.
:func:`save_frames` writes that stream to a single compressed ``frames.npz``
beside the history; :func:`load_frames` replays it back into the same ``Frame``
snapshots that the live :meth:`SimulationManager.frames` generator yields, so
``visualizer.animate`` cannot tell a replay from a live run.

The per-frame creature/food arrays are ragged (populations rise and fall), so
they are stored flat -- every frame's creatures concatenated into one array --
alongside per-frame counts.  Loading is then a cumulative-sum split, which needs
no pickling (unlike object arrays).  Positions and colors are saved as float16:
colors live in [0,1] and positions in world coordinates (~0..100), both far
coarser than fp16 resolves, and the GIF needs no more precision than that.

<a id="rgb_evo_view.recording.save_frames"></a>

#### save\_frames

```python
def save_frames(path: str | Path, frames: Iterable[Frame]) -> int
```

Write a ``Frame`` stream to ``path`` as one compressed ``.npz``.

Returns the number of frames written.  ``frames`` may be any iterable,
including the live ``SimulationManager.frames()`` generator.

<a id="rgb_evo_view.recording.load_frames"></a>

#### load\_frames

```python
def load_frames(path: str | Path) -> list[Frame]
```

Replay frames previously written by :func:`save_frames`.

Geometry comes back as float32 (widened from the stored float16) so consumers
get a conventional float dtype; the values are unchanged from what was saved.
