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


def _carry_config(carryover: bool) -> SimulationConfig:
    """A config with overlapping generations and the carryover toggle set.

    Carryover only bites with ``parents_survive`` (otherwise no parent persists),
    so that is forced on here.
    """
    base = _config()
    return replace(
        base,
        energy=replace(base.energy, carryover_energy=carryover),
        mating=replace(base.mating, parents_survive=True),
    )


def _parent_energies_across_one_boundary(config: SimulationConfig) -> tuple[dict, dict]:
    """Drive cycle 0 (food -> walk -> mate) then begin cycle 1, returning each
    surviving parent's energy just after mating and again right after the next
    cycle starts -- the exact moment the per-cycle reset would fire."""
    from rgb_evo_view.seeding import seed_population

    m = SimulationManager(config)  # no config_path -> writes nothing
    m.world.creatures = seed_population(config.seeding, config.locomotion, m.world, m.rng, m._next_id)

    m.cycle = 0
    m._begin_cycle()
    for _ in range(config.steps_per_cycle):
        m._step_tick()
        if not m._alive():
            break
    m._record_stats()
    m.world.clear_food()
    m._reproduce()

    # Surviving founders (generation 0) are the parents carried into cycle 1.
    parents = [c for c in m.world.creatures if c.generation == 0]
    before = {c.id: c.energy for c in parents}

    m.cycle = 1
    m._begin_cycle()  # this is where energy is either kept or reset
    after = {c.id: c.energy for c in parents}
    return before, after


def test_carryover_keeps_parent_energy_across_the_cycle_boundary():
    before, after = _parent_energies_across_one_boundary(_carry_config(carryover=True))
    assert before, "expected at least one surviving parent to test"
    # Each parent enters the next cycle holding exactly its leftover energy.
    assert after == before


def test_reset_replaces_parent_energy_at_each_cycle():
    config = _carry_config(carryover=False)
    before, after = _parent_energies_across_one_boundary(config)
    assert before, "expected at least one surviving parent to test"
    # Survivors had varied leftover energy, but the reset wipes it to one fresh budget.
    assert any(e != config.seeding.starting_energy for e in before.values())
    assert set(after.values()) == {config.seeding.starting_energy}
