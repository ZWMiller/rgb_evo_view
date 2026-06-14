"""Load a finished run from its on-disk artifacts -- no re-simulation.

A run folder (``runs/<timestamp>/``) holds ``config.toml``, ``history.json``,
``frames.npz`` and ``history.png``.  Both the GIF rebuilder
(:mod:`build_animation`) and the interactive viewer need the same thing from
it: the frame stream, the per-cycle history, the world size, and the
cycle/step counts.  This module is the single place that turns a run folder
into that bundle so the two consumers don't each re-derive it.

The world size comes from the copied ``config.toml`` (it is never
CLI-overridable, so the copy is authoritative), but ``num_cycles`` /
``steps_per_cycle`` are derived from the frames themselves -- a run-time
``--cycles`` override is not reflected in the copied config, whereas the frames
always tell the truth (the mate frame of each cycle carries
``tick == steps_per_cycle`` and cycle indices are 0-based).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rgb_evo_view.config import load_config
from rgb_evo_view.recording import load_frames
from rgb_evo_view.simulation import Frame


@dataclass(frozen=True)
class LoadedRun:
    """Everything a renderer needs from a finished run, loaded from disk."""

    run_dir: Path
    frames: list[Frame]
    history: list[dict]
    world_size: tuple[float, float]
    num_cycles: int
    steps_per_cycle: int


def latest_run(runs_root: str | Path = "runs") -> Path:
    """Return the most recent run folder under ``runs_root``.

    Run folders are named ``%Y-%m-%d_%H-%M-%S``, which sorts lexically in
    chronological order, so the newest is simply the max.  Only folders that
    actually contain a ``frames.npz`` count.
    """
    root = Path(runs_root)
    candidates = sorted(d for d in root.glob("*") if (d / "frames.npz").exists())
    if not candidates:
        raise FileNotFoundError(f"No run folders with a frames.npz under {root}/")
    return candidates[-1]


def load_run(run_dir: str | Path) -> LoadedRun:
    """Load a run folder into a :class:`LoadedRun`.

    Raises ``FileNotFoundError`` if the folder has no ``frames.npz`` (the one
    artifact that cannot be regenerated without re-running the sim).
    """
    run_dir = Path(run_dir)
    frames_path = run_dir / "frames.npz"
    if not frames_path.exists():
        raise FileNotFoundError(
            f"No frame log found: {frames_path}\nRe-run the simulation (any mode) to produce one."
        )

    frames = load_frames(frames_path)

    history_path = run_dir / "history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []

    config = load_config(run_dir / "config.toml")
    world_size = (config.world.width, config.world.height)

    num_cycles = max((f.cycle for f in frames), default=0) + 1
    mate_ticks = [f.tick for f in frames if f.phase == "mate"]
    steps_per_cycle = max(mate_ticks) if mate_ticks else max((f.tick for f in frames), default=0) + 1

    return LoadedRun(
        run_dir=run_dir,
        frames=frames,
        history=history,
        world_size=world_size,
        num_cycles=num_cycles,
        steps_per_cycle=steps_per_cycle,
    )
