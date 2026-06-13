"""Per-cycle summary plots from a run's ``history``."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


def draw_mean_rgb(ax, history: list[dict]) -> None:
    """Trace the population's mean R, G, and B (each in its own color) by cycle.

    Draws onto a caller-supplied axes so both the static summary plot and the
    GIF's closing end-card share one rendering of the palette drift.  The caller
    owns the title and x-label.
    """
    cycles = [h["cycle"] for h in history]
    means = list(zip(*[h["mean_rgb"] for h in history], strict=True))
    for channel, color, label in zip(means, ("red", "green", "blue"), ("R", "G", "B"), strict=True):
        ax.plot(cycles, channel, color=color, label=label)
    ax.set_ylabel("mean channel value")
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right")


def plot_history(history: list[dict], save_path: str | Path | None = None) -> None:
    """Plot mean genome color and population over the run.

    The top panel traces the population's mean R, G, and B (each in its own
    color) cycle by cycle -- this is where you watch selection drift the palette.
    The bottom panel shows population and deaths per cycle.
    """
    if not history:
        raise ValueError("history is empty; run the simulation first")

    cycles = [h["cycle"] for h in history]
    survivors = [h["survivors"] for h in history]
    deaths = [h["deaths"] for h in history]

    fig, (ax_rgb, ax_pop) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

    draw_mean_rgb(ax_rgb, history)
    ax_rgb.set_title("Population mean color over time")

    ax_pop.plot(cycles, survivors, color="black", label="survivors")
    ax_pop.plot(cycles, deaths, color="gray", linestyle="--", label="deaths")
    ax_pop.set_ylabel("creatures")
    ax_pop.set_xlabel("cycle")
    ax_pop.legend(loc="upper right")

    fig.tight_layout()
    if save_path is not None:
        fig.savefig(str(save_path), dpi=120)
        plt.close(fig)
    else:
        plt.show()
