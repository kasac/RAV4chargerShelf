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
    assert v[2][1] == pytest.approx(p.D_cubby - p.rear_gap)


def test_outline_is_simple_and_ccw(p, d):
    o = layout.shelf_outline(p, d, d.z_top)
    ring = o.ring(8)
    assert is_simple(ring)
    assert o.area() > 0


def test_notch_position_and_size():
    p, d = make(X_ports=20.0, port_notch_offset_x=-5.0, port_notch_width=60.0,
                port_notch_depth=40.0)
    o = layout.shelf_outline(p, d, d.z_top)
    assert len(o) == 8
    xs = sorted(x for x, _ in o.verts[3:7])
    assert xs[0] == pytest.approx(15 - 30) and xs[-1] == pytest.approx(15 + 30)
    y_front_of_notch = o.verts[4][1]
    assert y_front_of_notch == pytest.approx(d.y_rear - 40)
    ring = o.ring(8)
    assert not point_in_polygon((15.0, d.y_rear - 5), ring)  # inside the notch = no shelf
    assert point_in_polygon((15.0, d.y_rear - 45), ring)


def test_notch_disabled_gives_four_corners():
    p, d = make(port_notch_width=0.0)
    assert len(layout.shelf_outline(p, d, d.z_top)) == 4


def test_side_edges_follow_the_draft():
    p, d = make(W_bottom=190.0, W_top=200.0, H_cubby=100.0)
    lo = layout.shelf_outline(p, d, 40.0)
    hi = layout.shelf_outline(p, d, 60.0)
    # 10 mm wider over 100 mm height -> 1 mm wider over 20 mm
    assert (hi.verts[1][0] - hi.verts[0][0]) - (lo.verts[1][0] - lo.verts[0][0]) == pytest.approx(2.0)


def test_rear_taper():
    p, d = make(W_rear_delta=-6.0)
    o = layout.shelf_outline(p, d, d.z_top)
    front_w = o.verts[1][0] - o.verts[0][0]
    rear_w = o.verts[2][0] - o.verts[-1][0]
    assert rear_w < front_w


@pytest.mark.parametrize("over", [
    {"port_notch_width": 190.0},
    {"X_ports": 90.0},
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
