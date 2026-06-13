"""GIF export of a run.

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
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from rgb_evo_view.simulation import Frame, SimulationManager

from .stats import draw_mean_rgb

# The scatter field and the closing chart are rendered at this size so every GIF
# frame shares one resolution (a GIF animation needs uniform frame dimensions).
_FIG_SIZE = (6, 6)
_DPI = 150


def _title(frame: Frame) -> str:
    r, g, b = frame.creature_colors.mean(axis=0) if frame.population else (0, 0, 0)
    return (
        f"cycle {frame.cycle}  |  {frame.phase}  |  pop {frame.population}  "
        f"|  mean RGB ({r:.2f}, {g:.2f}, {b:.2f})"
    )


def _fig_to_image(fig) -> Image.Image:
    """Rasterize a Matplotlib figure to a PIL image (RGB)."""
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    return Image.fromarray(buf).convert("RGB")


def _chart_image(history: list[dict]) -> Image.Image:
    """The closing end-card: mean R/G/B over cycles, on black to match the frames."""
    fig, ax = plt.subplots(figsize=_FIG_SIZE, dpi=_DPI)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")
    draw_mean_rgb(ax, history)
    ax.set_xlabel("cycle")
    ax.set_title("Mean color drift over cycles")
    # Recolor every text/axis element white so it reads on the black field.
    ax.title.set_color("white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("white")
    legend = ax.get_legend()
    if legend is not None:
        legend.get_frame().set_facecolor("black")
        legend.get_frame().set_edgecolor("white")
        for text in legend.get_texts():
            text.set_color("white")
    fig.tight_layout()
    img = _fig_to_image(fig)
    plt.close(fig)
    return img


def animate(
    manager: SimulationManager,
    save_path: str | Path,
    fps: int = 10,
    max_frames: int = 400,
    cycle_end_seconds: float = 2.0,
    mate_seconds: float = 1.0,
    final_chart_seconds: float = 9.0,
) -> None:
    """Render ``manager``'s run to an animated GIF at ``save_path``.

    ``manager.setup()`` must already have been called.  There is no live windowed
    mode yet (a pygame viewer is planned); for now this only exports a GIF.

    Walk ticks are subsampled down to roughly ``max_frames`` rendered frames so a
    long run still produces a small, watchable file, but the last walk frame of
    every cycle -- the survivors, just before they mate -- is always kept and held
    for ``cycle_end_seconds``, and the mate frame -- the newborns before next
    cycle's food is scattered -- is held for ``mate_seconds``.  A mean-color chart
    is appended and held for ``final_chart_seconds``.  ``fps`` sets the base rate
    for all other frames.
    """
    if save_path is None:
        raise ValueError("animate() requires a save_path; live windowed mode is not available yet")

    base_ms = int(round(1000 / fps))
    cycle_hold_ms = int(round(cycle_end_seconds * 1000))
    mate_hold_ms = int(round(mate_seconds * 1000))
    chart_hold_ms = int(round(final_chart_seconds * 1000))

    last_tick = manager.config.steps_per_cycle - 1
    total_ticks = manager.config.num_cycles * (manager.config.steps_per_cycle + 1)
    stride = max(1, -(-total_ticks // max_frames))  # ceil division

    fig, ax = plt.subplots(figsize=_FIG_SIZE, dpi=_DPI)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")
    ax.set_xlim(0, manager.world.width)
    ax.set_ylim(0, manager.world.height)
    ax.set_xticks([])
    ax.set_yticks([])

    food_scatter = ax.scatter([], [], marker="s", s=18)
    creature_scatter = ax.scatter([], [], marker="o", s=36, edgecolors="white", linewidths=0.2)
    title = ax.set_title("", color="white", fontsize=10)

    images: list[Image.Image] = []
    durations: list[int] = []
    for i, frame in enumerate(manager.frames()):
        # The last walk tick of a cycle is the "who survived" view; the mate frame
        # is the newborns before next cycle's food lands.  Always keep both and
        # hold them; subsample the ordinary walk frames in between.
        is_cycle_end = frame.phase == "walk" and frame.tick == last_tick
        is_mate = frame.phase == "mate"
        if not (is_cycle_end or is_mate) and i % stride != 0:
            continue

        food_scatter.set_offsets(frame.food_positions if len(frame.food_positions) else _empty())
        food_scatter.set_facecolors(frame.food_colors)
        creature_scatter.set_offsets(frame.creature_positions if frame.population else _empty())
        creature_scatter.set_facecolors(frame.creature_colors)
        title.set_text(_title(frame))

        images.append(_fig_to_image(fig))
        if is_cycle_end:
            durations.append(cycle_hold_ms)
        elif is_mate:
            durations.append(mate_hold_ms)
        else:
            durations.append(base_ms)
    plt.close(fig)

    if manager.history:
        images.append(_chart_image(manager.history))
        durations.append(chart_hold_ms)

    if not images:
        raise ValueError("no frames to render; did the run produce any cycles?")

    images[0].save(
        str(save_path),
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
    )


def _empty():
    return np.empty((0, 2))
