"""Plan-view layout: shelf outline, fit-coupon profile, cubby reference lines.
Pure Python, no Rhino imports.

Car coordinate frame (used everywhere, see docs/measuring.md):
    x : right, as seen from the driver looking into the cubby (0 = centreline)
    y : from the front lip (y = 0) into the dash toward the rear wall (y = D_cubby)
    z : up from the Qi pad surface (z = 0)

Grid-cell patterns and the flip-drawer swing math will also live here
(shelf / drawer phases).
"""
from __future__ import annotations

from typing import List, Tuple

from .geom2d import GeometryError, Outline, Point
from .params import Derived, Params, cubby_half_width, cubby_width, roof_height


# --------------------------------------------------------------------------
# shelf outline
# --------------------------------------------------------------------------

def shelf_outline(p: Params, d: Derived, z: float, inset: float = 0.0) -> Outline:
    """Outline of the shelf in plan at height z, offset inward by ``inset``.

    The side edges follow the side walls (curved, tapering toward the rear)
    minus side_gap. The front edge sits front_recess behind the lip, the rear
    edge rear_gap in front of the rear wall, with the port notch cut into it.
    Each rear corner is a chamfer from rear_corner_length in front of the rear
    edge to rear_corner_inset in from the side, rounded with rear_corner_r_side
    and rear_corner_r_back.

    Vertex order (counter-clockwise from above):
        front-left, front-right,
        right corner: chamfer start, chamfer end   (or one corner vertex)
        notch: mouth right, front-right, front-left, mouth left   (if enabled)
        left corner: chamfer end, chamfer start   (or one corner vertex)
    """
    yf, yr = d.y_front, d.y_rear
    if yr - yf < 10.0:
        raise GeometryError(
            "shelf depth is only %.1f mm: check D_cubby, front_recess, rear_gap" % (yr - yf))

    def hw(y):
        return cubby_half_width(p, y, z) - p.side_gap

    chamfer = p.rear_corner_length > 0 and p.rear_corner_inset > 0
    yc = yr - p.rear_corner_length
    if chamfer and yc <= yf + 5.0:
        raise GeometryError("rear_corner_length (%.1f) reaches the front of the shelf"
                            % p.rear_corner_length)
    x_back = hw(yr) - (p.rear_corner_inset if chamfer else 0.0)  # where the rear edge ends

    rf, rn = p.corner_radius_front, p.port_notch_radius
    r_side, r_back = p.rear_corner_r_side, p.rear_corner_r_back

    verts: List[Point] = [(-hw(yf), yf), (hw(yf), yf)]
    radii = [rf, rf]
    names = ["front edge", "right side"]
    if chamfer:
        verts += [(hw(yc), yc), (x_back, yr)]
        radii += [r_side, r_back]
        names += ["right rear corner"]
    else:
        verts.append((hw(yr), yr))
        radii.append(r_back)

    if d.notch_enabled:
        nx = d.notch_center_x
        x_r = nx + p.port_notch_width / 2.0
        x_l = nx - p.port_notch_width / 2.0
        y_n = yr - p.port_notch_depth
        if x_r >= x_back or x_l <= -x_back:
            raise GeometryError(
                "port notch (x %.1f .. %.1f) reaches into the rear corners (rear edge +-%.1f): "
                "reduce port_notch_width or move it" % (x_l, x_r, x_back))
        if y_n <= yf + 5.0:
            raise GeometryError(
                "port notch (depth %.1f) reaches the front of the shelf: reduce port_notch_depth"
                % p.port_notch_depth)
        verts += [(x_r, yr), (x_r, y_n), (x_l, y_n), (x_l, yr)]
        radii += [rn, rn, rn, rn]
        names += ["rear edge right of notch", "notch right side", "notch front edge",
                  "notch left side", "rear edge left of notch"]
    else:
        names += ["rear edge"]

    if chamfer:
        verts += [(-x_back, yr), (-hw(yc), yc)]
        radii += [r_back, r_side]
        names += ["left rear corner"]
    else:
        verts.append((-hw(yr), yr))
        radii.append(r_back)
    names.append("left side")

    outline = Outline(verts, radii, names)
    if inset:
        outline = outline.offset(inset)
    return outline


# --------------------------------------------------------------------------
# fit coupon
# --------------------------------------------------------------------------

def coupon_profile(p: Params, d: Derived) -> List[Tuple[float, float]]:
    """Cross-section of the fit coupon as a closed loop of (inset, z) pairs.

    Car frame: the plate is on top at shelf height, the rim hangs down like the
    real shelf's edge band. Sweeping this loop around the shelf outline gives
    the coupon (see meshing.coupon_mesh and geometry.build_fit_coupon).

        inset 0      w_rim      w_flange
          |  plate top           |      z_top
          |  +---- plate --------+      z_top - t
          |  |
          +--+  rim                     z_top - h
    """
    top = d.z_top
    t = p.coupon_plate_thickness
    h = d.coupon_rim_height
    w_rim = p.coupon_rim_width
    w_fl = p.coupon_flange_width
    if w_fl <= w_rim + 0.4:
        raise GeometryError(
            "coupon_flange_width (%.1f) must exceed coupon_rim_width (%.1f) by 0.4 mm or more"
            % (w_fl, w_rim))
    if h < t + 0.2:
        raise GeometryError(
            "coupon rim height (%.1f) must exceed coupon_plate_thickness (%.1f)" % (h, t))
    return [
        (0.0, top),          # outer edge, top
        (0.0, top - h),      # outer edge, rim bottom
        (w_rim, top - h),    # rim inner edge, bottom
        (w_rim, top - t),    # rim meets plate underside
        (w_fl, top - t),     # window edge, bottom
        (w_fl, top),         # window edge, top
    ]


# --------------------------------------------------------------------------
# profile gauge: the cubby cross-section seen from the front
# --------------------------------------------------------------------------

def profile_section(p: Params, y: float, step: float = 3.0, gap: float = 6.0,
                    corner: float = None) -> Outline:
    """Cubby cross-section at depth y, seen from the driver: x right, z up.

    Floor at z = 0 (Qi pad level), curved side walls, roof with the pocket.
    All four corners are chamfered by ``corner`` (default gauge_corner), so a
    rounded transition in the car cannot hold the gauge off the walls.
    Counter-clockwise, no fillets.
    Curve samples keep ``gap`` from the corners, so the outline can be offset
    inward by up to about gap without collapsing an edge there (the walls are
    large arcs, so this costs no accuracy).
    """
    c = p.gauge_corner if corner is None else corner

    def hw(z):
        return cubby_half_width(p, y, z)

    h_side = roof_height(p, hw(p.H_cubby), y)  # roof height at the side walls
    right = [(hw(0.0) - c, 0.0)] if c > 0 else []
    right.append((hw(c), c))
    z = c + gap
    while z < h_side - c - gap:
        right.append((hw(z), z))
        z += step
    right.append((hw(h_side - c), h_side - c))
    x_edge = hw(h_side) - c
    if c > 0:
        right.append((x_edge, h_side))
    roof = []  # right to left, sampled only where the pocket lifts the roof
    if p.roof_pocket_width > 0 and p.roof_pocket_rise > 0 and y < p.roof_pocket_end:
        half = min(p.roof_pocket_width / 2.0 + p.roof_pocket_blend, x_edge - gap)
        n = max(2, int(2 * half / step))
        for i in range(n + 1):
            x = half - 2.0 * half * i / n
            roof.append((x, roof_height(p, x, y)))
    left = [(-x, zz) for x, zz in reversed(right)]  # ends on the floor
    pts = right + roof + left
    pts = pts[-1:] + pts[:-1]  # start at the left floor point: first edge = floor
    return Outline(pts, None, ["floor"] + ["profile %d" % i for i in range(1, len(pts))])


# --------------------------------------------------------------------------
# reference geometry for previews
# --------------------------------------------------------------------------

def cubby_walls(p: Params, z: float) -> List[Point]:
    """Side and rear walls at height z as an open polyline (front is open):
    front-left -> rear-left -> rear-right -> front-right."""
    D = p.D_cubby
    return [
        (-cubby_width(p, 0.0, z) / 2.0, 0.0),
        (-cubby_width(p, D, z) / 2.0, D),
        (cubby_width(p, D, z) / 2.0, D),
        (cubby_width(p, 0.0, z) / 2.0, 0.0),
    ]


def ports_box(p: Params) -> Tuple[float, float, float, float, float, float]:
    """(x0, x1, y0, y1, z0, z1) of the plug cluster incl. adapters and cables."""
    return (
        p.X_ports - p.W_ports / 2.0, p.X_ports + p.W_ports / 2.0,
        p.D_cubby - p.D_ports, p.D_cubby,
        p.H_ports_bottom, p.H_ports_top,
    )


def phone_box(p: Params) -> Tuple[float, float, float, float, float, float]:
    """(x0, x1, y0, y1, z0, z1) of the phone lying crosswise on the Qi pad."""
    return (
        p.qi_center_x - p.phone_length / 2.0, p.qi_center_x + p.phone_length / 2.0,
        p.qi_center_y - p.phone_width / 2.0, p.qi_center_y + p.phone_width / 2.0,
        0.0, p.phone_thickness,
    )
