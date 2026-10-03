import math

import pytest

from rav4shelf.geom2d import (MIN_FILLET, GeometryError, Outline, arc_steps, is_simple,
                              point_in_polygon, signed_area)

SQUARE = [(0, 0), (100, 0), (100, 50), (0, 50)]
# rectangle with a notch cut into the top edge: the mouth corners (3, 6) are
# convex, the corners at the far end of the notch (4, 5) are reflex
NOTCHED = [(0, 0), (100, 0), (100, 50), (60, 50), (60, 30), (40, 30), (40, 50), (0, 50)]


def test_rejects_clockwise():
    with pytest.raises(GeometryError):
        Outline(list(reversed(SQUARE)))


def test_offset_square():
    o = Outline(SQUARE).offset(5)
    assert o.verts == [pytest.approx(v) for v in [(5, 5), (95, 5), (95, 45), (5, 45)]]


def test_offset_collapse_raises():
    with pytest.raises(GeometryError):
        Outline(SQUARE).offset(26)


def test_convexity():
    o = Outline(NOTCHED)
    assert [o.is_convex(i) for i in range(8)] == [True, True, True, True, False, False, True, True]


def test_fillet_area_of_rounded_square():
    r = 10.0
    o = Outline(SQUARE, [r] * 4)
    exact = 100 * 50 - (4 - math.pi) * r * r
    assert o.area(64) == pytest.approx(exact, rel=1e-3)
    segs = o.segments()
    assert [s.kind for s in segs] == ["arc", "line"] * 4
    for s in segs:
        if s.kind == "arc":
            assert s.radius == pytest.approx(r)
            assert s.sweep == pytest.approx(math.pi / 2)
            assert math.dist(s.mid(), s.center) == pytest.approx(r)


def test_segments_form_a_closed_chain():
    o = Outline(NOTCHED, [3, 3, 5, 2, 2, 2, 2, 5])
    segs = o.segments()
    for s0, s1 in zip(segs, segs[1:] + segs[:1]):
        assert s0.b == pytest.approx(s1.a)


def test_reflex_fillet_sweeps_clockwise():
    o = Outline(NOTCHED, [0, 0, 0, 0, 4, 4, 0, 0])
    arcs = [s for s in o.segments() if s.kind == "arc"]
    assert len(arcs) == 2
    assert all(a.sweep < 0 for a in arcs)


def test_offset_keeps_fillets_concentric():
    base = Outline(NOTCHED, [8, 8, 8, 3, 3, 3, 3, 8])
    off = base.offset(2)
    assert off.radii[0] == pytest.approx(6)  # convex shrinks
    assert off.radii[3] == pytest.approx(1)  # convex notch mouth shrinks
    assert off.radii[4] == pytest.approx(5)  # reflex notch end grows
    c0 = [s.center for s in base.segments() if s.kind == "arc"]
    c1 = [s.center for s in off.segments() if s.kind == "arc"]
    for a, b in zip(c0, c1):
        assert a == pytest.approx(b)


def test_rounded_corner_never_becomes_sharp():
    off = Outline(SQUARE, [3] * 4).offset(10)
    assert all(r == pytest.approx(MIN_FILLET) for r in off.radii)


def test_ring_point_count_is_offset_invariant():
    base = Outline(NOTCHED, [8, 8, 8, 3, 3, 3, 3, 8])
    counts = {len(base.offset(dist).ring(8)) for dist in (0, 0.7, 1.6, 5, 9)}
    assert len(counts) == 1


def test_arc_steps_is_stable_at_exact_quarter_turns():
    assert arc_steps(math.pi / 2, 8) == 8
    assert arc_steps(math.pi / 2 + 1e-12, 8) == 8
    assert arc_steps(math.pi, 8) == 16


def test_edge_too_short_for_fillets():
    with pytest.raises(GeometryError) as exc:
        Outline(SQUARE, [30, 30, 30, 30]).segments()
    assert "too short" in str(exc.value)


def test_is_simple_and_point_in_polygon():
    assert is_simple(Outline(NOTCHED, [3] * 8).ring(8))
    bowtie = [(0, 0), (10, 10), (10, 0), (0, 10)]
    assert not is_simple(bowtie)
    assert point_in_polygon((50, 10), NOTCHED)
    assert not point_in_polygon((50, 40), NOTCHED)  # inside the notch
    assert signed_area(NOTCHED) == pytest.approx(100 * 50 - 20 * 20)


def test_offset_handles_collinear_vertices():
    # a straight-through vertex at (50, 0) must not break the offset
    o = Outline([(0, 0), (50, 0), (100, 0), (100, 50), (0, 50)]).offset(5)
    assert o.verts[1] == pytest.approx((50, 5))
    assert o.verts[0] == pytest.approx((5, 5))
