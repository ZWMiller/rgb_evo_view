"""The RGB genome value type.

A creature's (and a food resource's) genetics are a single RGB color with each
channel a float in ``[0, 1]``.  In the visualizer the color *is* the genome, so
selection is something you watch as the population's palette shifts.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RGBGenome:
    """An immutable RGB triple with the color math used across the sim.

    Channels are floats in ``[0, 1]``.  Construct via the channel constructor or
    the ``random`` / ``from_array`` factories so values are always clamped.
    """

    rgb: np.ndarray

    def __post_init__(self) -> None:
        arr = np.asarray(self.rgb, dtype=float).reshape(3)
        # ``frozen=True`` blocks normal assignment; go through object.__setattr__.
        object.__setattr__(self, "rgb", np.clip(arr, 0.0, 1.0))

    # ── constructors ──────────────────────────────────────────────────────────
    @classmethod
    def from_channels(cls, r: float, g: float, b: float) -> RGBGenome:
        return cls(np.array([r, g, b], dtype=float))

    @classmethod
    def from_array(cls, arr) -> RGBGenome:
        return cls(np.asarray(arr, dtype=float))

    @classmethod
    def random(cls, rng: np.random.Generator) -> RGBGenome:
        """A uniformly random color."""
        return cls(rng.random(3))

    # ── color math ────────────────────────────────────────────────────────────
    def as_array(self) -> np.ndarray:
        """A copy of the channel array (callers must not mutate the genome)."""
        return self.rgb.copy()

    def distance(self, other: RGBGenome) -> float:
        """Euclidean distance to another genome in color space."""
        return float(np.linalg.norm(self.rgb - other.rgb))

    def blend(self, other: RGBGenome) -> RGBGenome:
        """Channel-wise average of two genomes (used to make offspring)."""
        return RGBGenome((self.rgb + other.rgb) / 2.0)

    # ── render helpers ────────────────────────────────────────────────────────
    def to_mpl(self) -> tuple[float, float, float]:
        """An ``(r, g, b)`` tuple for matplotlib facecolors."""
        return tuple(self.rgb)

    def to_hex(self) -> str:
        r, g, b = (int(round(c * 255)) for c in self.rgb)
        return f"#{r:02x}{g:02x}{b:02x}"
