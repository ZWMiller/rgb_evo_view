"""Persist and replay the :class:`Frame` stream so an animation can be rebuilt
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
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import numpy as np

from .simulation import Frame

# Geometry is downcast to half precision on save: the rendered GIF cannot resolve
# more than this (fp16 steps ~0.0005 over a [0,1] color, ~0.06 over a 100-wide
# world), and it halves the frame log on disk.
_STORE_DTYPE = np.float16


def save_frames(path: str | Path, frames: Iterable[Frame]) -> int:
    """Write a ``Frame`` stream to ``path`` as one compressed ``.npz``.

    Returns the number of frames written.  ``frames`` may be any iterable,
    including the live ``SimulationManager.frames()`` generator.
    """
    cycles: list[int] = []
    ticks: list[int] = []
    phases: list[str] = []
    creature_counts: list[int] = []
    food_counts: list[int] = []
    c_pos: list[np.ndarray] = []
    c_col: list[np.ndarray] = []
    f_pos: list[np.ndarray] = []
    f_col: list[np.ndarray] = []

    for frame in frames:
        cycles.append(frame.cycle)
        ticks.append(frame.tick)
        phases.append(frame.phase)
        creature_counts.append(len(frame.creature_positions))
        food_counts.append(len(frame.food_positions))
        c_pos.append(np.asarray(frame.creature_positions, dtype=_STORE_DTYPE).reshape(-1, 2))
        c_col.append(np.asarray(frame.creature_colors, dtype=_STORE_DTYPE).reshape(-1, 3))
        f_pos.append(np.asarray(frame.food_positions, dtype=_STORE_DTYPE).reshape(-1, 2))
        f_col.append(np.asarray(frame.food_colors, dtype=_STORE_DTYPE).reshape(-1, 3))

    def _stack(parts: list[np.ndarray], width: int) -> np.ndarray:
        return np.concatenate(parts) if parts else np.empty((0, width), dtype=_STORE_DTYPE)

    np.savez_compressed(
        path,
        cycle=np.asarray(cycles, dtype=np.int64),
        tick=np.asarray(ticks, dtype=np.int64),
        phase=np.asarray(phases, dtype="U8"),
        creature_counts=np.asarray(creature_counts, dtype=np.int64),
        food_counts=np.asarray(food_counts, dtype=np.int64),
        creature_positions=_stack(c_pos, 2),
        creature_colors=_stack(c_col, 3),
        food_positions=_stack(f_pos, 2),
        food_colors=_stack(f_col, 3),
    )
    return len(cycles)


def load_frames(path: str | Path) -> list[Frame]:
    """Replay frames previously written by :func:`save_frames`.

    Geometry comes back as float32 (widened from the stored float16) so consumers
    get a conventional float dtype; the values are unchanged from what was saved.
    """
    with np.load(path) as data:
        cycles = data["cycle"]
        ticks = data["tick"]
        phases = data["phase"]
        c_offsets = np.concatenate([[0], np.cumsum(data["creature_counts"])])
        f_offsets = np.concatenate([[0], np.cumsum(data["food_counts"])])
        c_pos = data["creature_positions"].astype(np.float32)
        c_col = data["creature_colors"].astype(np.float32)
        f_pos = data["food_positions"].astype(np.float32)
        f_col = data["food_colors"].astype(np.float32)

        frames: list[Frame] = []
        for i in range(len(cycles)):
            cs, ce = int(c_offsets[i]), int(c_offsets[i + 1])
            fs, fe = int(f_offsets[i]), int(f_offsets[i + 1])
            frames.append(
                Frame(
                    cycle=int(cycles[i]),
                    tick=int(ticks[i]),
                    phase=str(phases[i]),
                    creature_positions=c_pos[cs:ce],
                    creature_colors=c_col[cs:ce],
                    food_positions=f_pos[fs:fe],
                    food_colors=f_col[fs:fe],
                )
            )
    return frames
