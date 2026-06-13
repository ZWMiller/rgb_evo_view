import numpy as np

from rgb_evo_view.genome import RGBGenome


def test_channels_are_clamped_into_unit_range():
    g = RGBGenome.from_array([1.5, -0.2, 0.5])
    assert np.allclose(g.rgb, [1.0, 0.0, 0.5])


def test_blend_is_channelwise_average():
    a = RGBGenome.from_channels(1.0, 0.0, 1.0)
    b = RGBGenome.from_channels(0.0, 1.0, 1.0)
    assert np.allclose(a.blend(b).rgb, [0.5, 0.5, 1.0])


def test_distance_is_euclidean():
    a = RGBGenome.from_channels(0.0, 0.0, 0.0)
    b = RGBGenome.from_channels(1.0, 0.0, 0.0)
    assert a.distance(b) == 1.0


def test_random_is_in_range_and_reproducible():
    g1 = RGBGenome.random(np.random.default_rng(0))
    g2 = RGBGenome.random(np.random.default_rng(0))
    assert np.allclose(g1.rgb, g2.rgb)
    assert np.all((g1.rgb >= 0) & (g1.rgb <= 1))


def test_to_hex():
    assert RGBGenome.from_channels(1.0, 0.0, 1.0).to_hex() == "#ff00ff"


def test_as_array_returns_a_copy():
    g = RGBGenome.from_channels(0.2, 0.4, 0.6)
    arr = g.as_array()
    arr[0] = 1.0
    assert g.rgb[0] == 0.2  # mutating the copy must not touch the genome
