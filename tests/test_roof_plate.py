import math

import pytest

from rav4shelf import layout, meshing, params
from rav4shelf.geom2d import signed_area

from conftest import make


def test_depression_profile(p):
    a, ramp, h = p.roof_depression_start, p.roof_depression_ramp, p.roof_depression_depth
    assert (a, ramp, h) == (15.0, 10.0, 4.0)
    assert layout.roof_depression(p, 0.0) == 0.0
    assert layout.roof_depression(p, a) == 0.0
    assert layout.roof_depression(p, a + ramp / 2) == pytest.approx(h / 2)
    assert layout.roof_depression(p, a + ramp) == pytest.approx(h)
    samples = [layout.roof_depression(p, a + ramp * i / 50) for i in range(51)]
    assert samples == sorted(samples)  # gradual: never goes back up
    steepest = max((b - c) / (ramp / 50) for c, b in zip(samples, samples[1:]))
    assert math.degrees(math.atan(steepest)) == pytest.approx(layout.roof_ramp_overhang_deg(p),
                                                              abs=0.2)
    assert layout.roof_ramp_overhang_deg(p) < p.max_overhang_deg


@pytest.mark.parametrize("over", [
    {},
    {"perforation_style": "diamond"},
    {"perforate_roof": False},
    {"roof_depression_depth": 0.0},
    {"roof_depression_ramp": 4.0, "roof_depression_start": 30.0},
    {"perforation_tip_angle": 30.0, "perforation_open_fraction": 0.3},
    {"perforation_size": 6.0, "perforation_open_fraction": 0.65},
])
def test_roof_plate_is_watertight(over):
    p, d = make(**over)
    m = meshing.roof_plate_mesh(p, d)
    assert meshing.check_closed(m) == []


@pytest.mark.parametrize("over", [{"perforate_roof": False}, {}])
def test_volume_is_plan_area_times_thickness(over):
    """The plate keeps its thickness vertically, so its volume is exactly the
    perforated plan area times the thickness, depression or not."""
    p, d = make(**over)
    outline = layout.roof_plate_outline(p, d)
    area = signed_area(outline) - sum(abs(signed_area(h)) for h in layout.roof_plate_holes(p, d))
    m = meshing.roof_plate_mesh(p, d)
    assert m.signed_volume() == pytest.approx(area * p.roof_thickness, rel=1e-9)


def test_plate_mesh_with_holes_is_exact():
    outer = [(0.0, 0.0), (40.0, 0.0), (40.0, 30.0), (0.0, 30.0)]
    holes = [[(10.0, 10.0), (15.0, 10.0), (15.0, 20.0), (10.0, 20.0)],
             [(25.0, 8.0), (30.0, 15.0), (25.0, 22.0), (20.0, 15.0)]]
    m = meshing.plate_mesh(outer, holes, lambda y: 5.0 + 0.1 * y, 2.0, extra_y=[3.0, 12.5])
    assert meshing.check_closed(m) == []
    assert m.signed_volume() == pytest.approx((1200.0 - 50.0 - 70.0) * 2.0)


def test_top_stays_below_the_roof_and_holes_stay_flat(p, d):
    m = meshing.roof_plate_mesh(p, d)
    for x, y, z in m.vertices:
        assert z <= params.roof_height(p, x, y) - p.roof_clearance + 1e-9
    flat = layout.roof_flat_from(p, d) + p.perforation_margin
    for h in layout.roof_plate_holes(p, d):
        assert min(y for _, y in h) >= flat - 1e-9
    front = [z for x, y, z in m.vertices if y == pytest.approx(d.y_front)]
    assert max(front) == pytest.approx(p.H_cubby - p.roof_clearance)


def test_outline_prints_standing(p, d):
    """No side leans out more than max_overhang_deg above the bed edge."""
    ring = layout.roof_plate_outline(p, d)
    y_rear = max(y for _, y in ring)
    limit = math.sin(math.radians(p.max_overhang_deg)) + 1e-9
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        if y0 == pytest.approx(y_rear) and y1 == pytest.approx(y_rear):
            continue  # the edge on the bed
        assert -(x1 - x0) / math.hypot(x1 - x0, y1 - y0) <= limit


def test_standing_print_orientation(p, d):
    m = meshing.standing_print_orientation(meshing.roof_plate_mesh(p, d))
    (x0, y0, z0), (x1, y1, z1) = m.bbox()
    assert z0 == pytest.approx(0.0)
    assert z1 == pytest.approx(d.y_rear - d.y_front)  # the plate's depth stands up
    assert y1 - y0 == pytest.approx(p.roof_thickness + p.roof_depression_depth)
    assert meshing.check_closed(m) == []  # a rotation, not a mirror
