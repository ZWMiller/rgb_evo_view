"""``run_loader`` turns a run folder back into a renderable bundle.

The cycle/step counts must come from the frames (so a ``--cycles`` override is
honored even though the copied config doesn't reflect it), while the world size
comes from the copied config.
"""

import json
import shutil

import pytest

from rgb_evo_view.recording import save_frames
from rgb_evo_view.run_loader import latest_run, load_run
from tests.test_recording import _live_frames
from tests.test_simulation import _config


def _write_run(run_dir, *, num_cycles, steps_per_cycle):
    """Materialize a run folder on disk: config.toml + history.json + frames.npz."""
    config = _config(num_cycles=num_cycles, steps_per_cycle=steps_per_cycle)
    frames, history = _live_frames(config)

    run_dir.mkdir(parents=True, exist_ok=True)
    save_frames(run_dir / "frames.npz", frames)
    (run_dir / "history.json").write_text(json.dumps(history))
    # A real config.toml so load_config can read world width/height.
    shutil.copy("simulation_configs/default.toml", run_dir / "config.toml")
    return frames


def test_load_run_round_trips(tmp_path):
    run_dir = tmp_path / "2026-06-14_12-00-00"
    frames = _write_run(run_dir, num_cycles=3, steps_per_cycle=20)

    run = load_run(run_dir)

    assert run.run_dir == run_dir
    assert len(run.frames) == len(frames)
    assert run.history  # founding row + per-cycle rows
    assert run.world_size[0] > 0 and run.world_size[1] > 0


def test_cycle_and_step_counts_derived_from_frames(tmp_path):
    """Counts come from the frames, not the config -- mirrors build_animation."""
    run_dir = tmp_path / "2026-06-14_12-00-00"
    _write_run(run_dir, num_cycles=4, steps_per_cycle=15)

    run = load_run(run_dir)

    assert run.num_cycles == 4
    assert run.steps_per_cycle == 15


def test_load_run_without_frames_raises(tmp_path):
    run_dir = tmp_path / "empty"
    run_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        load_run(run_dir)


def test_latest_run_picks_newest(tmp_path):
    older = tmp_path / "2026-06-14_10-00-00"
    newer = tmp_path / "2026-06-14_12-00-00"
    _write_run(older, num_cycles=2, steps_per_cycle=10)
    _write_run(newer, num_cycles=2, steps_per_cycle=10)

    assert latest_run(tmp_path) == newer


def test_latest_run_empty_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        latest_run(tmp_path)
