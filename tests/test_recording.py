"""The frame log round-trips: a saved run replays into equivalent frames."""

import numpy as np

from rgb_evo_view.recording import load_frames, save_frames
from rgb_evo_view.simulation import Frame, SimulationManager
from tests.test_simulation import _config


def _live_frames(config):
    """Run a sim without touching the output filesystem and collect its frames."""
    from rgb_evo_view.seeding import seed_population

    m = SimulationManager(config)  # no config_path -> writes nothing
    m.world.creatures = seed_population(config.seeding, config.locomotion, m.world, m.rng, m._next_id)
    return list(m.frames()), m.history


def test_frames_round_trip(tmp_path):
    frames, _ = _live_frames(_config(num_cycles=3, steps_per_cycle=20))
    path = tmp_path / "frames.npz"
    n = save_frames(path, frames)
    assert n == len(frames)

    replayed = load_frames(path)
    assert len(replayed) == len(frames)
    for original, copy in zip(frames, replayed, strict=True):
        assert (copy.cycle, copy.tick, copy.phase) == (original.cycle, original.tick, original.phase)
        assert copy.population == original.population
        # float16 storage is lossy, so compare with a tolerance rather than exactly.
        np.testing.assert_allclose(copy.creature_positions, original.creature_positions, atol=0.1)
        np.testing.assert_allclose(copy.creature_colors, original.creature_colors, atol=1e-2)
        np.testing.assert_allclose(copy.food_positions, original.food_positions, atol=0.1)
        np.testing.assert_allclose(copy.food_colors, original.food_colors, atol=1e-2)


def test_empty_frame_round_trips(tmp_path):
    """A frame with no creatures and no food survives the flat-storage split."""
    empty = Frame(
        cycle=0,
        tick=0,
        phase="mate",
        creature_positions=np.empty((0, 2)),
        creature_colors=np.empty((0, 3)),
        food_positions=np.empty((0, 2)),
        food_colors=np.empty((0, 3)),
    )
    path = tmp_path / "frames.npz"
    save_frames(path, [empty])
    (replayed,) = load_frames(path)
    assert replayed.population == 0
    assert replayed.food_positions.shape == (0, 2)
