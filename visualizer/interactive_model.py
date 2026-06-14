"""Pure (Dash-free) helpers behind the interactive viewer.

Everything here is plain data in / plain data out so it can be unit-tested
without standing up a Dash app: the (cycle, tick) -> frame-index lookup that
drives the two scrub sliders, the vectorized [0,1] color -> ``#rrggbb``
conversion the markers need, the population color sampling for the flower
garden, and the ASCII flower rendering (as an HTML string -- the Dash layer
just drops it into the page).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from rgb_evo_view.simulation import Frame


@dataclass(frozen=True)
class FrameIndex:
    """Maps the (cycle, tick) the sliders pick to a position in the frame list.

    Frames are one per walk tick (``tick`` 0..steps-1) plus one ``mate`` frame
    per cycle (``tick == steps_per_cycle``), so a cycle's last selectable tick
    is its mate frame.
    """

    cycles: tuple[int, ...]
    _ticks: dict[int, tuple[int, ...]]
    _index: dict[tuple[int, int], int]
    frame_count: int

    def ticks_for(self, cycle: int) -> tuple[int, ...]:
        """The ticks available within ``cycle``, ascending (mate tick last)."""
        return self._ticks.get(cycle, ())

    def index_of(self, cycle: int, tick: int) -> int:
        """Frame-list position for (cycle, tick).

        If that exact tick is absent (e.g. the slider lands past a short
        cycle's range), snap to the nearest available tick in that cycle.
        """
        if (cycle, tick) in self._index:
            return self._index[(cycle, tick)]
        ticks = self.ticks_for(cycle)
        if not ticks:
            raise KeyError(f"no frames for cycle {cycle}")
        nearest = min(ticks, key=lambda t: abs(t - tick))
        return self._index[(cycle, nearest)]


def build_frame_index(frames: list[Frame]) -> FrameIndex:
    """Index a frame stream for slider lookups."""
    index: dict[tuple[int, int], int] = {}
    ticks: dict[int, list[int]] = {}
    for i, f in enumerate(frames):
        index[(f.cycle, f.tick)] = i
        ticks.setdefault(f.cycle, []).append(f.tick)
    return FrameIndex(
        cycles=tuple(sorted(ticks)),
        _ticks={c: tuple(sorted(t)) for c, t in ticks.items()},
        _index=index,
        frame_count=len(frames),
    )


def colors_to_hex(colors: np.ndarray) -> list[str]:
    """Convert an ``(N, 3)`` array of [0,1] RGB rows to ``#rrggbb`` strings.

    Batched form of :meth:`rgb_evo_view.genome.RGBGenome.to_hex` (same
    ``round(c * 255)`` convention), operating on the raw array a ``Frame``
    holds so playback doesn't build N genome objects per frame.
    """
    arr = np.asarray(colors)
    if arr.size == 0:
        return []
    rgb = np.clip(np.rint(arr * 255), 0, 255).astype(int)
    return [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in rgb]


def sample_palette(
    frame: Frame,
    n: int = 6,
    *,
    rng: np.random.Generator,
    method: str = "random",
) -> list[str]:
    """Sample up to ``n`` living-creature colors as ``#rrggbb`` strings.

    Used to tint the flower garden so it reads as "what colors are winning".
    ``method="random"`` draws a uniform sample without replacement; the
    parameter is the seam for a future ``"kmeans"`` (cluster-center) mode.
    """
    if method != "random":
        raise NotImplementedError(f"unknown palette method: {method!r}")
    colors = np.asarray(frame.creature_colors)
    count = len(colors)
    if count == 0:
        return []
    k = min(n, count)
    picks = rng.choice(count, size=k, replace=False)
    return colors_to_hex(colors[picks])


# An ASCII tulip: a bloom (the top ``_BLOOM_ROWS`` lines) on a long leafy stem.
# Every glyph in the bloom takes the sampled petal color; the stem, leaves, and
# ground take a muted green.  A raw string keeps the backslashes literal; rows
# are padded to a common width at render time so flowers tile cleanly side by
# side in a monospace <pre>.
_FLOWER_ART = r"""
        ,
     /\^/`\
    | \/   |
    | |    |
    \ \    /
     '\\//'
       ||
       ||
       ||
       ||  ,
   |\  ||  |\
   | | ||  | |
   | | || / /
    \ \||/ /
     `\\//`
    ^^^^^^^^
"""
_FLOWER = _FLOWER_ART.strip("\n").split("\n")
_FLOWER_WIDTH = max(len(line) for line in _FLOWER)
_BLOOM_ROWS = 6

# A spread of muted greens (dark -> light), nothing neon, so the stems vary a
# little from one another.  Assigned by a flower's position in the garden (not
# its petal color), so each stem holds its shade while petals resample.
_STEM_GREENS = (
    "#2f5d2f",
    "#3a7a3a",
    "#4a8a4a",
    "#5a9a55",
    "#6aa860",
    "#7bb56e",
)


def _stem_for_position(index: int) -> str:
    """The fixed stem shade for the flower at grid position ``index``."""
    return _STEM_GREENS[index % len(_STEM_GREENS)]


def _span(ch: str, color: str) -> str:
    return f'<span style="color:{color}">{ch}</span>' if ch != " " else ch


def _flower_html(color: str, stem: str) -> str:
    rows = []
    for r, row in enumerate(_FLOWER):
        tint = color if r < _BLOOM_ROWS else stem
        rows.append("".join(_span(ch, tint) for ch in row.ljust(_FLOWER_WIDTH)))
    return "\n".join(rows)


def _flower_strip(chunk: list[str], start: int) -> str:
    """One row of flowers, stitched column-wise into a single ``<pre>``.

    ``start`` is the grid index of the first flower in the row, so each stem
    keeps a fixed shade tied to its position rather than its petal color.
    """
    flowers = [_flower_html(c, _stem_for_position(start + i)).split("\n") for i, c in enumerate(chunk)]
    height = len(_FLOWER)
    rows = "\n".join("  ".join(flower[r] for flower in flowers) for r in range(height))
    return f'<pre style="margin:6px 0">{rows}</pre>'


def ascii_flowers(palette: list[str], cycle: int, per_row: int = 3) -> str:
    """Render the palette as a grid of ASCII flowers, as an HTML string.

    Headed by the cycle number; flowers are tiled ``per_row`` across, wrapping
    into stacked ``<pre>`` rows.  Per-glyph color spans keep their monospace
    alignment within a row.  Returns plain HTML (no Dash types) so it stays
    testable; the Dash layer drops it into the page.
    """
    header = f'<div style="padding:4px 0">cycle {cycle}</div>'
    if not palette:
        return header + "<pre>(no living creatures)</pre>"

    strips = [_flower_strip(palette[i : i + per_row], i) for i in range(0, len(palette), per_row)]
    return header + "".join(strips)
