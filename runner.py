"""runner.py -- stand-alone entry point for the RGB evolution visualizer.

Usage
-----
    python runner.py --gif out.gif            # render the run to an animated GIF
    python runner.py --headless               # no rendering; just write history + a stats plot
    python runner.py my_config.toml --gif out.gif --cycles 200 --seed 7

A run must pick a mode: --gif or --headless.  (A live windowed viewer is planned
but not implemented yet.)  Outputs (a copy of the config, per-cycle history.json,
a history.png stats plot, and the full frame log frames.npz) are written to
output_dir/<timestamp>/.  The frame log lets ``build_animation.py`` rebuild the
GIF with different animation settings without re-running the simulation.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from rgb_evo_view.config import load_config
from rgb_evo_view.simulation import SimulationManager

DEFAULT_CONFIG = Path(__file__).resolve().parent / "simulation_configs" / "default.toml"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RGB Evolution Visualizer -- watch natural selection recolor a population.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help=f"Path to a TOML config. Defaults to {DEFAULT_CONFIG.name}.",
    )
    parser.add_argument("--cycles", type=int, default=None, help="Override num_cycles.")
    parser.add_argument("--steps", type=int, default=None, help="Override steps_per_cycle.")
    parser.add_argument("--seed", type=int, default=None, help="Override the RNG seed.")
    parser.add_argument("--gif", type=str, default=None, help="Render the run to this GIF path.")
    parser.add_argument(
        "--headless", action="store_true", help="Run without animation; write history + stats plot."
    )
    args = parser.parse_args()

    config_path = Path(args.config) if args.config is not None else DEFAULT_CONFIG
    if not config_path.exists():
        print(f"[error] Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = load_config(config_path)
    overrides = {}
    if args.cycles is not None:
        overrides["num_cycles"] = args.cycles
    if args.steps is not None:
        overrides["steps_per_cycle"] = args.steps
    if args.seed is not None:
        overrides["seed"] = args.seed
    if overrides:
        config = replace(config, **overrides)

    # A live windowed viewer is not implemented yet (a pygame version is planned).
    # Until then a run must either export a GIF or run headless.
    if not args.headless and args.gif is None:
        print(
            "[error] No live window viewer yet. Re-run with one of:\n"
            "          --gif out.gif   render the run to an animated GIF\n"
            "          --headless      run without a window (writes history + a stats plot)",
            file=sys.stderr,
        )
        sys.exit(2)

    manager = SimulationManager(config, config_path=config_path)
    run_dir = manager.setup()
    print(f"[run] output -> {run_dir}")

    # Drain the run once into memory: this advances the sim, builds history, and
    # writes history.json.  The same frames feed both the GIF and the saved frame
    # log, so the sim runs exactly once regardless of mode.
    from rgb_evo_view.recording import save_frames

    frames = list(manager.frames())
    n_saved = save_frames(run_dir / "frames.npz", frames)
    print(f"[run] saved {n_saved} frames -> {run_dir / 'frames.npz'}")

    if not args.headless:
        from visualizer.animate import animate

        animate(
            frames,
            manager.history,
            save_path=args.gif,
            world_size=(manager.world.width, manager.world.height),
            steps_per_cycle=manager.config.steps_per_cycle,
            num_cycles=manager.config.num_cycles,
        )

    from visualizer.stats import plot_history

    if manager.history:
        plot_history(manager.history, save_path=run_dir / "history.png")

    if manager.history:
        final = manager.history[-1]
        r, g, b = final["mean_rgb"]
        print(
            f"[done] {len(manager.history)} cycles | final pop {final['survivors']} "
            f"| final mean RGB ({r:.2f}, {g:.2f}, {b:.2f})"
        )


if __name__ == "__main__":
    main()
