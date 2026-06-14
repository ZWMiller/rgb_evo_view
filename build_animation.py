"""build_animation.py -- rebuild a run's GIF from its saved frame log.

A run folder (``runs/<timestamp>/``) holds everything needed to re-render its
animation without re-running the simulation: ``config.toml`` (world size),
``history.json`` (the closing mean-color chart), and ``frames.npz`` (the full
per-tick geometry).  This lets you tweak the animation -- timing, frame budget,
hold lengths -- and rebuild in seconds instead of waiting on the whole sim.

Usage
-----
    python build_animation.py runs/2026-06-14_12-00-00
    python build_animation.py runs/2026-06-14_12-00-00 --gif custom.gif --fps 15
    python build_animation.py runs/2026-06-14_12-00-00 --max-frames 800

By default the GIF is written to ``run_animations/<run-folder-name>.gif`` (a
sibling of ``runs/``), so rebuilt animations live apart from the run logs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rgb_evo_view.config import load_config
from rgb_evo_view.recording import load_frames


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild a run's GIF from its saved frame log (no re-simulation).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("run_dir", help="A run folder under runs/ (must contain frames.npz).")
    parser.add_argument(
        "--gif",
        type=str,
        default=None,
        help="Output GIF path. Defaults to run_animations/<run-folder-name>.gif.",
    )
    parser.add_argument("--fps", type=int, default=10, help="Base frame rate for ordinary walk frames.")
    parser.add_argument(
        "--max-frames", type=int, default=400, help="Approximate cap on rendered frames (subsampling)."
    )
    parser.add_argument(
        "--cycle-end-seconds", type=float, default=2.0, help="Hold for each cycle's survivors frame."
    )
    parser.add_argument(
        "--mate-seconds", type=float, default=1.0, help="Hold for each mate (newborns) frame."
    )
    parser.add_argument("--final-chart-seconds", type=float, default=9.0, help="Hold for the closing chart.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    frames_path = run_dir / "frames.npz"
    config_path = run_dir / "config.toml"
    history_path = run_dir / "history.json"
    if not frames_path.exists():
        print(f"[error] No frame log found: {frames_path}", file=sys.stderr)
        print("        Re-run the simulation (any mode) to produce one.", file=sys.stderr)
        sys.exit(1)

    frames = load_frames(frames_path)
    history = json.loads(history_path.read_text()) if history_path.exists() else []

    # World size comes from the run's config (it is never CLI-overridable, so the
    # copied config.toml is authoritative).  Cycle/step counts, however, can be
    # overridden at run time without the copied config reflecting it, so derive
    # them from the frames themselves -- the mate frame of each cycle carries
    # tick == steps_per_cycle, and cycle indices are 0-based.
    config = load_config(config_path)
    world_size = (config.world.width, config.world.height)
    num_cycles = max((f.cycle for f in frames), default=0) + 1
    mate_ticks = [f.tick for f in frames if f.phase == "mate"]
    steps_per_cycle = max(mate_ticks) if mate_ticks else max((f.tick for f in frames), default=0) + 1

    if args.gif is not None:
        save_path = Path(args.gif)
    else:
        # Sibling of runs/ (run_dir is runs/<name>), named after the run folder.
        save_path = run_dir.resolve().parent.parent / "run_animations" / f"{run_dir.resolve().name}.gif"
    save_path.parent.mkdir(parents=True, exist_ok=True)

    from visualizer.animate import animate

    animate(
        frames,
        history,
        save_path=save_path,
        world_size=world_size,
        steps_per_cycle=steps_per_cycle,
        num_cycles=num_cycles,
        fps=args.fps,
        max_frames=args.max_frames,
        cycle_end_seconds=args.cycle_end_seconds,
        mate_seconds=args.mate_seconds,
        final_chart_seconds=args.final_chart_seconds,
    )
    print(f"[done] rebuilt {len(frames)} frames -> {save_path}")


if __name__ == "__main__":
    main()
