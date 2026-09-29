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
from .params import Derived, Params, cubby_width


# --------------------------------------------------------------------------
# shelf outline
# --------------------------------------------------------------------------

def shelf_outline(p: Params, d: Derived, z: float, inset: float = 0.0) -> Outline:
    """Outline of the shelf in plan at height z, offset inward by ``inset``.

    The side edges follow the side walls (taper with z and with depth) minus
    side_gap. The front edge sits front_recess behind the lip, the rear edge
    rear_gap in front of the rear wall, with the port notch cut into it.

    Vertex order (counter-clockwise from above), with the notch:
        0 front-left, 1 front-right, 2 rear-right,
        3 notch mouth right, 4 notch front-right, 5 notch front-left,
        6 notch mouth left, 7 rear-left
    """
    yf, yr = d.y_front, d.y_rear
    if yr - yf < 10.0:
        raise GeometryError(
            "shelf depth is only %.1f mm: check D_cubby, front_recess, rear_gap" % (yr - yf))

    def hw(y):
        return cubby_width(p, y, z) / 2.0 - p.side_gap

    rf = p.corner_radius_front
    rr = p.R_rear_corner
    rn = p.port_notch_radius

    verts: List[Point] = [(-hw(yf), yf), (hw(yf), yf), (hw(yr), yr)]
    radii = [rf, rf, rr]
    names = ["front edge", "right side"]

    if d.notch_enabled:
        nx = d.notch_center_x
        x_r = nx + p.port_notch_width / 2.0
        x_l = nx - p.port_notch_width / 2.0
        y_n = yr - p.port_notch_depth
        if x_r >= hw(yr) or x_l <= -hw(yr):
            raise GeometryError(
                "port notch (x %.1f .. %.1f) reaches past the shelf side edges (+-%.1f): "
                "reduce port_notch_width or move it" % (x_l, x_r, hw(yr)))
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

    verts.append((-hw(yr), yr))
    radii.append(rr)
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
