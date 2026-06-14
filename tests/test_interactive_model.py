"""Pure helpers behind the interactive viewer: index, color, palette, flowers."""

import numpy as np
import pytest

from rgb_evo_view.simulation import Frame
from visualizer.interactive_model import (
    ascii_flowers,
    build_frame_index,
    colors_to_hex,
    sample_palette,
)


def _frame(cycle, tick, phase="walk", n_creatures=4):
    rng = np.random.default_rng(cycle * 100 + tick)
    return Frame(
        cycle=cycle,
        tick=tick,
        phase=phase,
        creature_positions=rng.random((n_creatures, 2)),
        creature_colors=rng.random((n_creatures, 3)),
        food_positions=rng.random((2, 2)),
        food_colors=rng.random((2, 3)),
    )


def _stream(num_cycles=3, steps=5):
    """Walk frames 0..steps-1 plus a mate frame at tick == steps, per cycle."""
    frames = []
    for c in range(num_cycles):
        for t in range(steps):
            frames.append(_frame(c, t, "walk"))
        frames.append(_frame(c, steps, "mate"))
    return frames


# ── frame index ──────────────────────────────────────────────────────────────


def test_index_maps_cycle_tick_to_position():
    frames = _stream(num_cycles=3, steps=5)
    idx = build_frame_index(frames)

    assert idx.cycles == (0, 1, 2)
    assert idx.frame_count == len(frames)
    # First frame of cycle 1 sits after cycle 0's 5 walk + 1 mate = 6 frames.
    assert idx.index_of(1, 0) == 6
    # The mate frame is the last selectable tick (tick == steps).
    assert idx.ticks_for(0)[-1] == 5
    assert frames[idx.index_of(0, 5)].phase == "mate"


def test_index_snaps_to_nearest_tick_when_absent():
    frames = _stream(num_cycles=2, steps=5)
    idx = build_frame_index(frames)
    # tick 99 doesn't exist; snaps to the cycle's max available tick (the mate).
    assert idx.index_of(0, 99) == idx.index_of(0, 5)


def test_index_unknown_cycle_raises():
    idx = build_frame_index(_stream(num_cycles=1, steps=3))
    with pytest.raises(KeyError):
        idx.index_of(7, 0)


# ── colors_to_hex ─────────────────────────────────────────────────────────────


def test_colors_to_hex_matches_genome_convention():
    colors = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.5, 0.25, 0.75]])
    assert colors_to_hex(colors) == ["#000000", "#ffffff", "#8040bf"]


def test_colors_to_hex_empty():
    assert colors_to_hex(np.zeros((0, 3))) == []


# ── sample_palette ────────────────────────────────────────────────────────────


def test_sample_palette_caps_at_population_and_is_deterministic():
    frame = _frame(0, 0, n_creatures=4)
    rng = np.random.default_rng(0)
    pal = sample_palette(frame, n=10, rng=rng)
    assert len(pal) == 4  # capped at the 4 living creatures
    assert all(c.startswith("#") and len(c) == 7 for c in pal)
    # Same seed -> same sample.
    again = sample_palette(frame, n=10, rng=np.random.default_rng(0))
    assert pal == again


def test_sample_palette_empty_population():
    empty = Frame(0, 0, "walk", np.zeros((0, 2)), np.zeros((0, 3)), np.zeros((0, 2)), np.zeros((0, 3)))
    assert sample_palette(empty, rng=np.random.default_rng(0)) == []


def test_sample_palette_rejects_unknown_method():
    frame = _frame(0, 0)
    with pytest.raises(NotImplementedError):
        sample_palette(frame, rng=np.random.default_rng(0), method="kmeans")


# ── ascii_flowers ─────────────────────────────────────────────────────────────


def test_ascii_flowers_headed_by_generation_and_tints_petals():
    html = ascii_flowers(["#ff0000", "#00ff00"], generation=7)
    assert "generation 7" in html
    assert "<pre>" in html
    # Petal color appears in spans.
    assert "color:#ff0000" in html
    # A muted stem green (not the petal color) also appears.
    assert "#2f5d2f" in html or "#3a7a3a" in html or "#4a8a4a" in html


def test_ascii_flowers_empty_palette():
    html = ascii_flowers([], generation=0)
    assert "generation 0" in html
    assert "no living creatures" in html
