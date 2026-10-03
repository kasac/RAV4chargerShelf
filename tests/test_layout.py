import math

import pytest

from rav4shelf import layout, params
from rav4shelf.geom2d import GeometryError, is_simple, point_in_polygon

from conftest import make


def test_outline_matches_cubby_width(p, d):
    o = layout.shelf_outline(p, d, d.z_top)
    v = o.verts
    front_w = v[1][0] - v[0][0]
    assert front_w == pytest.approx(d.shelf_width_front_top)
    assert v[0][1] == pytest.approx(p.front_recess)
    # right rear corner: chamfer from the side wall to the rear edge
    assert v[2][1] == pytest.approx(d.y_rear - p.rear_corner_length)
    assert v[3][1] == pytest.approx(d.y_rear)
    assert v[3][0] == pytest.approx(params.cubby_half_width(p, d.y_rear, d.z_top) - p.side_gap
                                    - p.rear_corner_inset)


def test_outline_is_simple_and_ccw(p, d):
    o = layout.shelf_outline(p, d, d.z_top)
    ring = o.ring(8)
    assert is_simple(ring)
    assert o.area() > 0


def test_notch_position_and_size():
    p, d = make(X_ports=20.0, port_notch_offset_x=-5.0, port_notch_width=60.0,
                port_notch_depth=40.0)
    o = layout.shelf_outline(p, d, d.z_top)
    assert len(o) == 10
    xs = sorted(x for x, _ in o.verts[4:8])
    assert xs[0] == pytest.approx(15 - 30) and xs[-1] == pytest.approx(15 + 30)
    y_front_of_notch = o.verts[5][1]
    assert y_front_of_notch == pytest.approx(d.y_rear - 40)
    ring = o.ring(8)
    assert not point_in_polygon((15.0, d.y_rear - 5), ring)  # inside the notch = no shelf
    assert point_in_polygon((15.0, d.y_rear - 45), ring)


def test_notch_disabled_and_plain_rear_corners():
    p, d = make(port_notch_width=0.0)
    assert len(layout.shelf_outline(p, d, d.z_top)) == 6
    p, d = make(port_notch_width=0.0, rear_corner_length=0.0, rear_corner_r_back=5.0)
    o = layout.shelf_outline(p, d, d.z_top)
    assert len(o) == 4 and o.radii[2] == 5.0


def test_side_edges_follow_the_curved_wall():
    p, d = make(z_ref=50.0, wall_lean_deg=6.0, wall_radius=0.0)
    lo = layout.shelf_outline(p, d, 40.0)
    hi = layout.shelf_outline(p, d, 60.0)
    grow = (hi.verts[1][0] - hi.verts[0][0]) - (lo.verts[1][0] - lo.verts[0][0])
    assert grow == pytest.approx(2 * 20 * math.tan(math.radians(6.0)))
    # with a radius the wall curves in more toward the floor
    p2, d2 = make(z_ref=50.0, wall_lean_deg=6.0, wall_radius=300.0)
    lo2 = layout.shelf_outline(p2, d2, 40.0)
    assert lo2.verts[1][0] < lo.verts[1][0]


def test_rear_corner_follows_parameters():
    p, d = make(rear_corner_length=30.0, rear_corner_inset=6.0, rear_corner_r_side=50.0,
                rear_corner_r_back=10.0, port_notch_width=0.0)
    o = layout.shelf_outline(p, d, d.z_top)
    assert o.radii[2:4] == [50.0, 10.0]
    assert is_simple(o.ring(16))
    p, d = make(rear_corner_length=100.0, front_recess=30.0)  # reaches the front edge
    with pytest.raises(GeometryError):
        layout.shelf_outline(p, d, d.z_top)


def test_rear_taper():
    p, d = make(W_rear_delta=-6.0)
    o = layout.shelf_outline(p, d, d.z_top)
    front_w = o.verts[1][0] - o.verts[0][0]
    rear_w = o.verts[2][0] - o.verts[-1][0]  # at the start of the rear corners
    assert rear_w < front_w


@pytest.mark.parametrize("over", [
    {"port_notch_width": 210.0},
    {"X_ports": 100.0},
    {"port_notch_depth": 125.0},
    {"D_cubby": 45.0, "front_recess": 30.0, "port_notch_depth": 5.0},
])
def test_impossible_notch_or_depth_raises(over):
    p, d = make(**over)
    with pytest.raises(GeometryError):
        layout.shelf_outline(p, d, d.z_top).segments()


def test_coupon_profile_follows_parameters(p, d):
    prof = layout.coupon_profile(p, d)
    zs = [z for _, z in prof]
    assert max(zs) == pytest.approx(d.z_top)
    assert min(zs) == pytest.approx(d.z_top - d.coupon_rim_height)
    insets = sorted(set(i for i, _ in prof))
    assert insets == [0.0, p.coupon_rim_width, p.coupon_flange_width]


def test_coupon_profile_rejects_flange_narrower_than_rim():
    p, d = make(coupon_flange_width=2.0, coupon_rim_width=2.0)
    with pytest.raises(GeometryError):
        layout.coupon_profile(p, d)


def test_reference_boxes(p):
    x0, x1, y0, y1, z0, z1 = layout.ports_box(p)
    assert x1 - x0 == pytest.approx(p.W_ports)
    assert y1 == pytest.approx(p.D_cubby)
    assert z1 == pytest.approx(p.H_ports_top)
    walls = layout.cubby_walls(p, 0.0)
    assert walls[0][0] == pytest.approx(-params.cubby_width(p, 0.0, 0.0) / 2)


def test_profile_section_is_the_cubby_cross_section(p):
    sec = layout.profile_section(p, 30.0, corner=0.0)
    ring = sec.ring()
    assert is_simple(ring)
    x0, z0, x1, z1 = sec.bbox()
    assert z0 == pytest.approx(0.0)
    assert x1 == pytest.approx(params.cubby_half_width(p, 30.0, p.H_cubby), abs=0.01)
    assert z1 == pytest.approx(params.roof_height(p, 0.0, 30.0), abs=0.05)  # pocket peak
    assert x1 - x0 == pytest.approx(2 * x1)  # symmetric
    floor_w = max(x for x, z in ring if z == 0.0) * 2
    assert floor_w == pytest.approx(params.cubby_width(p, 30.0, 0.0))
