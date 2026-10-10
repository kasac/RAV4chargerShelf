import math

import pytest

from rav4shelf import perforation as P
from rav4shelf.geom2d import GeometryError, signed_area

from conftest import make

REGION = [(-110.0, 0.0), (110.0, 0.0), (105.0, 120.0), (-105.0, 120.0)]  # convex, CCW


def _centre(h):
    xs, ys = zip(*h)
    return (round((max(xs) + min(xs)) / 2.0, 6), round(sum(ys) / len(ys), 6))


def test_diamond_lattice_has_one_bar_width():
    pat = P.pattern("diamond", 10.0, 0.5, 45.0)
    assert pat.pitch == pytest.approx(10.0 / math.sqrt(0.5))
    assert pat.row_step == pytest.approx(pat.pitch / 2.0)
    assert pat.open_fraction == pytest.approx(0.5)
    assert pat.bar == pytest.approx((pat.pitch - 10.0) / math.sqrt(2.0))  # uniform bars


@pytest.mark.parametrize("style", ["diamond", "teardrop"])
@pytest.mark.parametrize("phi", [0.2, 0.5, 0.7])
def test_open_fraction_and_bars(style, phi):
    pat = P.pattern(style, 10.0, phi, 45.0)
    assert pat.open_fraction == pytest.approx(phi)
    assert pat.bar > 0.0
    # the bar is the real distance between placed neighbours
    holes = P.holes_in_region([(-200, 0), (200, 0), (200, 300), (-200, 300)], pat, 0.0)
    a = min(holes, key=lambda h: sum(x * x + (y - 150) ** 2 for x, y in h))
    gaps = [P._convex_gap(a, b) for b in holes if b is not a]
    assert min(gaps) == pytest.approx(pat.bar, abs=1e-9)


@pytest.mark.parametrize("style", ["diamond", "teardrop"])
@pytest.mark.parametrize("tip", [45.0, 35.0, 25.0])
def test_hole_ceilings_respect_the_tip_angle(style, tip):
    """Standing on its rear edge the lip is up (-y): every edge that overhangs
    a hole may lean at most `tip` from the vertical."""
    hole = P.pattern(style, 12.0, 0.4, tip).hole
    assert signed_area(hole) > 0
    for (x0, y0), (x1, y1) in zip(hole, hole[1:] + hole[:1]):
        ln = math.hypot(x1 - x0, y1 - y0)
        n_down = (x1 - x0) / ln  # y of the normal into the hole = material facing the bed
        assert n_down <= math.sin(math.radians(tip)) + 1e-9
    assert min(y for _, y in hole) < 0  # the tip points to the lip


def test_lattice_density_and_symmetry():
    pat = P.pattern("teardrop", 8.0, 0.45)
    holes = P.holes_in_region(REGION, pat, 5.0)
    centres = {_centre(h) for h in holes}
    assert centres == {(-x if x else 0.0, y) for x, y in centres}  # mirror-symmetric
    rows = sorted({y for _, y in centres})
    assert all(b - a == pytest.approx(pat.row_step) for a, b in zip(rows, rows[1:]))


def test_holes_keep_the_margin():
    pat = P.pattern("diamond", 9.0, 0.5)
    holes = P.holes_in_region(REGION, pat, 6.0, y_min=30.0)
    assert holes
    for h in holes:
        for pt in h:
            assert pt[1] >= 36.0 - 1e-9
            for a, b in zip(REGION, REGION[1:] + REGION[:1]):
                assert P._point_segment(pt, a, b) >= 6.0 - 1e-9


def test_bad_input():
    with pytest.raises(GeometryError):
        P.pattern("hex", 10.0, 0.5)
    with pytest.raises(GeometryError):
        P.pattern("diamond", 10.0, 1.2)
    concave = [(0, 0), (10, 0), (5, 2), (10, 10), (0, 10)]
    with pytest.raises(GeometryError):
        P.holes_in_region(concave, P.pattern("diamond", 2.0, 0.3), 0.5)


def test_open_share():
    big = [(-50.0, -50.0), (50.0, -50.0), (50.0, 50.0), (-50.0, 50.0)]
    assert P.open_share([big], 0.0, 0.0, 10.0) == 1.0
    assert P.open_share([], 0.0, 0.0, 10.0) == 0.0


def test_teardrops_reach_as_much_open_area_as_diamonds():
    """The reason teardrop is the default: same 2 mm bars, at least as open."""
    def max_open(style):
        return max(i / 100.0 for i in range(5, 81)
                   if P.pattern(style, 10.0, i / 100.0).bar >= 2.0)
    assert max_open("teardrop") >= max_open("diamond")


def test_roof_pattern_follows_params():
    p, _ = make(perforation_style="diamond", perforation_size=12.0, perforation_open_fraction=0.4,
                perforation_tip_angle=40.0)
    pat = P.pattern("diamond", 12.0, 0.4, 40.0)
    from rav4shelf import layout
    assert layout.roof_pattern(p).pitch == pytest.approx(pat.pitch)
    p, _ = make(perforation_style="none")
    assert layout.roof_pattern(p) is None
