import numpy as np
import pytest

from rgb_evo_view.energy import (
    cosine,
    energy_fraction,
    get_overlap_model,
    histogram_min,
    penalized_projection,
    projection,
)
from rgb_evo_view.genome import RGBGenome

RED = np.array([1.0, 0.0, 0.0])
PURPLE = np.array([1.0, 0.0, 1.0])
GREY = np.array([0.5, 0.5, 0.5])

ALL_MODELS = [projection, penalized_projection, cosine, histogram_min]


@pytest.mark.parametrize("model", ALL_MODELS)
def test_anchor_r0_gives_nothing(model):
    # A creature with no red gets nothing from pure-red food.
    assert model(np.array([0.0, 0.7, 0.3]), RED) <= 0.0 or model(
        np.array([0.0, 0.7, 0.3]), RED
    ) == pytest.approx(0.0)


@pytest.mark.parametrize("model", ALL_MODELS)
def test_anchor_perfect_match_is_max(model):
    assert model(RED, RED) == pytest.approx(1.0)


@pytest.mark.parametrize("model", ALL_MODELS)
def test_colorless_food_yields_zero(model):
    assert model(GREY, np.array([0.0, 0.0, 0.0])) == 0.0


def test_projection_grey_vs_red_is_half():
    assert projection(GREY, RED) == pytest.approx(0.5)


def test_projection_leaves_green_neutral_for_purple_food():
    # Adding green to a purple creature does not change a projection score.
    assert projection(np.array([1.0, 0.0, 1.0]), PURPLE) == pytest.approx(1.0)
    assert projection(np.array([1.0, 1.0, 1.0]), PURPLE) == pytest.approx(1.0)


def test_penalized_projection_punishes_off_axis_green():
    pure = penalized_projection(np.array([1.0, 0.0, 1.0]), PURPLE)
    wasted = penalized_projection(np.array([1.0, 1.0, 1.0]), PURPLE)
    assert pure == pytest.approx(1.0)
    assert wasted < pure  # the spent green is penalized


def test_cosine_is_brightness_blind():
    # A faint red points the same direction as bright red -> still a perfect match.
    assert cosine(np.array([0.01, 0.0, 0.0]), RED) == pytest.approx(1.0)


def test_histogram_min_is_shared_pigment():
    assert histogram_min(GREY, RED) == pytest.approx(0.5)


def test_gamma_sharpens_selection():
    g = RGBGenome.from_channels(0.5, 0.5, 0.5)
    f = RGBGenome.from_channels(1.0, 0.0, 0.0)
    linear = energy_fraction(g, f, projection, gamma=1.0)
    sharp = energy_fraction(g, f, projection, gamma=2.0)
    assert linear == pytest.approx(0.5)
    assert sharp == pytest.approx(0.25)


def test_energy_fraction_clamps_negative_to_zero():
    # penalized_projection can go negative before clamping.
    f = RGBGenome.from_channels(1.0, 0.0, 0.0)
    g = RGBGenome.from_channels(0.0, 1.0, 1.0)
    assert energy_fraction(g, f, penalized_projection) == 0.0


def test_registry_lookup_and_unknown_name():
    assert get_overlap_model("projection") is projection
    with pytest.raises(ValueError):
        get_overlap_model("nope")
