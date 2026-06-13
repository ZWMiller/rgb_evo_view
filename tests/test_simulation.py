"""End-to-end checks: reproducibility and that selection actually drifts color."""

from dataclasses import replace

import numpy as np

from rgb_evo_view.config import (
    EnergyConfig,
    FoodConfig,
    LocomotionConfig,
    MatingConfig,
    SeedConfig,
    SimulationConfig,
    WorldConfig,
)
from rgb_evo_view.simulation import SimulationManager


def _config(**overrides) -> SimulationConfig:
    cfg = SimulationConfig(
        num_cycles=8,
        steps_per_cycle=60,
        seed=7,
        output_dir="runs",
        world=WorldConfig(width=60.0, height=60.0, contact_radius=3.0),
        seeding=SeedConfig(count=120, init_mode="random", starting_energy=40.0),
        locomotion=LocomotionConfig(walk_mode="brownian", step_size=2.5),
        food=FoodConfig(count=300, genome_mode="fixed", fixed_rgb=[1.0, 0.0, 1.0], energy_value=30.0),
        energy=EnergyConfig(overlap_model="penalized_projection", move_cost=1.0),
        mating=MatingConfig(offspring_per_pair=2, mutation_sigma=0.02),
    )
    return replace(cfg, **overrides)


def _run_means(config):
    m = SimulationManager(config)  # no config_path -> no files written
    m.world.creatures = []
    # Seed without touching the filesystem: replicate setup()'s population step.
    from rgb_evo_view.seeding import seed_population

    m.world.creatures = seed_population(config.seeding, config.locomotion, m.world, m.rng, m._next_id)
    m.run()
    return m.history


def test_run_is_reproducible_with_same_seed():
    h1 = _run_means(_config())
    h2 = _run_means(_config())
    assert [h["mean_rgb"] for h in h1] == [h["mean_rgb"] for h in h2]


def test_different_seed_changes_the_run():
    h1 = _run_means(_config(seed=1))
    h2 = _run_means(_config(seed=2))
    assert [h["mean_rgb"] for h in h1] != [h["mean_rgb"] for h in h2]


def test_population_drifts_toward_purple():
    history = _run_means(_config())
    assert len(history) >= 2
    first = np.array(history[0]["mean_rgb"])
    last = np.array(history[-1]["mean_rgb"])
    purple = np.array([1.0, 0.0, 1.0])
    # The population should end closer to purple than it began.
    assert np.linalg.norm(last - purple) < np.linalg.norm(first - purple)


def test_green_is_selected_down_under_penalized_projection():
    history = _run_means(_config())
    assert history[-1]["mean_rgb"][1] < history[0]["mean_rgb"][1]
