"""GIF export of a run.

Consumes the :meth:`SimulationManager.frames` generator and draws each frame as
two scatter layers on a black field: food (square markers) and creatures (round
markers), each dot painted with its own RGB genome.  A full run is tens of
thousands of ticks, so frames are auto-subsampled to keep the GIF watchable.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from rgb_evo_view.simulation import Frame, SimulationManager


def _subsample(frames: Iterator[Frame], stride: int) -> Iterator[Frame]:
    """Yield every ``stride``-th frame so long runs make a reasonably sized GIF."""
    for i, frame in enumerate(frames):
        if i % stride == 0:
            yield frame


def _title(frame: Frame) -> str:
    r, g, b = frame.creature_colors.mean(axis=0) if frame.population else (0, 0, 0)
    return (
        f"cycle {frame.cycle}  |  {frame.phase}  |  pop {frame.population}  "
        f"|  mean RGB ({r:.2f}, {g:.2f}, {b:.2f})"
    )


def animate(
    manager: SimulationManager,
    save_path: str | Path,
    fps: int = 25,
    max_frames: int = 600,
) -> None:
    """Render ``manager``'s run to an animated GIF at ``save_path``.

    ``manager.setup()`` must already have been called.  There is no live windowed
    mode yet (a pygame viewer is planned); for now this only exports a GIF.  The
    run's ticks are subsampled down to at most ``max_frames`` rendered frames so
    a long run still produces a small, watchable file.
    """
    if save_path is None:
        raise ValueError("animate() requires a save_path; live windowed mode is not available yet")

    total_ticks = manager.config.num_cycles * (manager.config.steps_per_cycle + 1)
    stride = max(1, -(-total_ticks // max_frames))  # ceil division
    rendered = -(-total_ticks // stride)

    fig, ax = plt.subplots(figsize=(6, 6), dpi=80)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")
    ax.set_xlim(0, manager.world.width)
    ax.set_ylim(0, manager.world.height)
    ax.set_xticks([])
    ax.set_yticks([])

    food_scatter = ax.scatter([], [], marker="s", s=18)
    creature_scatter = ax.scatter([], [], marker="o", s=36, edgecolors="white", linewidths=0.2)
    title = ax.set_title("", color="white", fontsize=10)

    def update(frame: Frame):
        food_scatter.set_offsets(frame.food_positions if len(frame.food_positions) else _empty())
        food_scatter.set_facecolors(frame.food_colors)
        creature_scatter.set_offsets(frame.creature_positions if frame.population else _empty())
        creature_scatter.set_facecolors(frame.creature_colors)
        title.set_text(_title(frame))
        return food_scatter, creature_scatter, title

    anim = FuncAnimation(
        fig,
        update,
        frames=_subsample(manager.frames(), stride),
        blit=False,
        save_count=rendered,
        cache_frame_data=False,
    )
    anim.save(str(save_path), writer=PillowWriter(fps=fps))
    plt.close(fig)


def _empty():
    import numpy as np

    return np.empty((0, 2))
