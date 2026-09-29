"""SVG drawings without Rhino:

* fit_template_svg : 1:1 plan view of the shelf outline. Print it at 100 %,
  cut it out of card and hold it in the cubby before printing anything.
* overview_svg     : plan, front and side views with the ports, the phone and
  the check results, to confirm the measurements were read the right way.
"""
from __future__ import annotations

import textwrap
from typing import List, Sequence, Tuple
from xml.sax.saxutils import escape

from .checks import Finding
from .layout import cubby_walls, phone_box, ports_box, shelf_outline
from .params import Derived, Params, cubby_width

C_WALL = "#333333"
C_SHELF = "#2f6db5"
C_PORTS = "#c0392b"
C_PHONE = "#7f8c8d"
C_WARN = "#c0392b"
C_DIM = "#555555"


class _Svg:
    """Tiny SVG builder. Drawing coordinates are in mm, y up; ``flip`` maps
    them to SVG's y-down page coordinates."""

    def __init__(self):
        self.items: List[str] = []

    def add(self, s: str):
        self.items.append(s)

    def render(self, width: float, height: float, physical: bool) -> str:
        size = ('width="%.2fmm" height="%.2fmm"' % (width, height) if physical
                else 'width="%.0f" height="%.0f"' % (width * 3, height * 3))
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" %s viewBox="0 0 %.2f %.2f" '
            'font-family="Helvetica, Arial, sans-serif">\n'
            '<rect x="0" y="0" width="%.2f" height="%.2f" fill="#ffffff"/>\n%s\n</svg>\n'
            % (size, width, height, width, height, "\n".join(self.items)))


def _pts(points: Sequence[Tuple[float, float]], fx, fy) -> str:
    return " ".join("%.3f,%.3f" % (fx(x), fy(y)) for x, y in points)


def _text(x, y, s, size=3.0, anchor="start", color="#000000", weight="normal"):
    return ('<text x="%.2f" y="%.2f" font-size="%.2f" text-anchor="%s" fill="%s" '
            'font-weight="%s">%s</text>' % (x, y, size, anchor, color, weight, escape(s)))


def _rect_pts(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# --------------------------------------------------------------------------
# 1:1 template
# --------------------------------------------------------------------------

def fit_template_svg(p: Params, d: Derived) -> str:
    """True-scale plan view (units: mm)."""
    z = d.z_top
    walls = cubby_walls(p, z)
    xmax = max(abs(x) for x, _ in walls) + 2.0
    margin, head = 12.0, 26.0
    width = 2 * xmax + 2 * margin
    height = p.D_cubby + head + margin + 14.0

    def fx(x):
        return x + xmax + margin

    def fy(y):
        return head + (p.D_cubby - y)

    s = _Svg()
    s.add(_text(margin, 7, "RAV4chargerShelf - 1:1 shelf outline at shelf height (z %.1f mm)" % z,
                4.0, weight="bold"))
    s.add(_text(margin, 12, "Print at 100 % (no 'fit to page'), check the 50 mm bar, cut along the "
                            "solid blue line.", 3.0))
    if p.placeholders:
        s.add(_text(margin, 17, "PLACEHOLDER VALUES - NOT MEASURED: this outline is a guess.",
                    3.2, color=C_WARN, weight="bold"))

    # cubby walls (dashed), lip line
    s.add('<polyline points="%s" fill="none" stroke="%s" stroke-width="0.3" '
          'stroke-dasharray="2,1.2"/>' % (_pts(walls, fx, fy), C_WALL))
    s.add('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.3" '
          'stroke-dasharray="0.6,1.2"/>' % (fx(walls[0][0]), fy(0), fx(walls[-1][0]), fy(0), C_WALL))
    s.add(_text(fx(0), fy(0) + 5, "FRONT LIP (driver side)", 3.0, "middle", C_DIM))
    s.add(_text(fx(0), fy(p.D_cubby) - 1.5, "REAR WALL", 3.0, "middle", C_DIM))

    # ports footprint
    x0, x1, y0, y1, _, _ = ports_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.15" stroke="%s" stroke-width="0.25"/>'
          % (_pts(_rect_pts(x0, x1, y0, y1), fx, fy), C_PORTS, C_PORTS))
    s.add(_text(fx((x0 + x1) / 2), fy(y0) + 4, "plugs", 2.6, "middle", C_PORTS))

    # shelf outline + coupon window
    ring = shelf_outline(p, d, z).ring(16)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.08" stroke="%s" stroke-width="0.35"/>'
          % (_pts(ring, fx, fy), C_SHELF, C_SHELF))
    try:
        inner = shelf_outline(p, d, z, p.coupon_flange_width).ring(16)
        s.add('<polygon points="%s" fill="none" stroke="%s" stroke-width="0.2" '
              'stroke-dasharray="1,1"/>' % (_pts(inner, fx, fy), C_SHELF))
    except ValueError:
        pass

    # centreline and dimensions
    s.add('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.15" '
          'stroke-dasharray="4,1,1,1"/>' % (fx(0), fy(-3), fx(0), fy(p.D_cubby + 3), C_DIM))
    s.add(_text(fx(0), fy(d.y_front) - 2, "front edge %.1f wide" % d.shelf_width_front_top,
                2.8, "middle", C_SHELF))
    s.add(_text(fx(0), fy(d.y_front + d.shelf_depth / 2), "depth %.1f" % d.shelf_depth,
                2.8, "middle", C_SHELF))

    # scale bar
    by = head + p.D_cubby + 10
    s.add('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#000" stroke-width="0.5"/>'
          % (margin, by, margin + 50, by))
    for k in range(6):
        s.add('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#000" stroke-width="0.3"/>'
              % (margin + 10 * k, by - 1.5, margin + 10 * k, by + 1.5))
    s.add(_text(margin + 53, by + 1, "this bar must measure 50 mm", 2.8))
    return s.render(width, height, physical=True)


# --------------------------------------------------------------------------
# overview sheet
# --------------------------------------------------------------------------

def overview_svg(p: Params, d: Derived, findings: List[Finding]) -> str:
    """Plan, front and side view plus the check results."""
    s = _Svg()
    pad = 14.0
    wmax = max(p.W_top, p.W_bottom, cubby_width(p, p.D_cubby, p.H_cubby),
               cubby_width(p, p.D_cubby, 0.0)) / 2.0 + 6.0

    # ---- plan view (top left) ----
    ox, oy = pad, pad + 8
    plan_h = p.D_cubby + 12

    def px(x):
        return ox + wmax + x

    def py(y):
        return oy + p.D_cubby + 4 - y

    s.add(_text(ox, oy - 4, "PLAN (from above, driver at the bottom)", 3.6, weight="bold"))
    s.add('<polyline points="%s" fill="none" stroke="%s" stroke-width="0.5"/>'
          % (_pts(cubby_walls(p, d.z_top), px, py), C_WALL))
    x0, x1, y0, y1, _, _ = phone_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.18" stroke="%s" stroke-width="0.3"/>'
          % (_pts(_rect_pts(x0, x1, y0, y1), px, py), C_PHONE, C_PHONE))
    x0, x1, y0, y1, _, _ = ports_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.3" stroke="%s" stroke-width="0.3"/>'
          % (_pts(_rect_pts(x0, x1, y0, y1), px, py), C_PORTS, C_PORTS))
    s.add(_text(px(0), py(0) + 5, "front lip (driver)", 2.6, "middle", C_DIM))
    s.add(_text(px(0), py(p.D_cubby) - 1.5, "rear wall", 2.6, "middle", C_DIM))
    try:
        ring = shelf_outline(p, d, d.z_top).ring(12)
        s.add('<polygon points="%s" fill="%s" fill-opacity="0.15" stroke="%s" stroke-width="0.5"/>'
              % (_pts(ring, px, py), C_SHELF, C_SHELF))
    except ValueError:
        pass

    # ---- front view (top right): section at mid shelf depth, x right, z up ----
    fx0 = ox + 2 * wmax + 2 * pad
    ym = d.y_front + d.shelf_depth / 2.0
    top_front = oy + 4

    def qx(x):
        return fx0 + wmax + x

    def qz(z):
        return top_front + p.H_cubby - z

    s.add(_text(fx0, oy - 4, "FRONT (looking into the cubby)", 3.6, weight="bold"))
    wl0, wl1 = cubby_width(p, ym, 0.0) / 2.0, cubby_width(p, ym, p.H_cubby) / 2.0
    s.add('<polyline points="%s" fill="none" stroke="%s" stroke-width="0.5"/>' % (
        _pts([(-wl1, p.H_cubby), (-wl0, 0), (wl0, 0), (wl1, p.H_cubby)], qx, qz), C_WALL))
    s.add('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.5"/>'
          % (qx(-wl1), qz(p.H_cubby), qx(wl1), qz(p.H_cubby), C_WALL))
    x0, x1, _, _, z0, z1 = phone_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.18" stroke="%s" stroke-width="0.3"/>'
          % (_pts(_rect_pts(x0, x1, z0, z1), qx, qz), C_PHONE, C_PHONE))
    x0, x1, _, _, z0, z1 = ports_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.3" stroke="%s" stroke-width="0.3" '
          'stroke-dasharray="1.5,1"/>' % (_pts(_rect_pts(x0, x1, z0, z1), qx, qz), C_PORTS, C_PORTS))
    hw_t = cubby_width(p, ym, d.z_top) / 2.0 - p.side_gap
    hw_b = cubby_width(p, ym, d.z_frame_bottom) / 2.0 - p.side_gap
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.35" stroke="%s" stroke-width="0.4"/>' % (
        _pts([(-hw_b, d.z_frame_bottom), (hw_b, d.z_frame_bottom), (hw_t, d.z_top), (-hw_t, d.z_top)],
             qx, qz), C_SHELF, C_SHELF))
    s.add('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.25" '
          'stroke-dasharray="2,1"/>' % (qx(-wl0), qz(p.phone_clearance_min), qx(wl0),
                                        qz(p.phone_clearance_min), C_PHONE))
    s.add(_text(qx(wl0) + 2, qz(p.phone_clearance_min) + 1, "phone clearance min", 2.4, color=C_PHONE))
    s.add(_text(qx(wl0) + 2, qz(d.z_top) + 1, "shelf top z %.1f" % d.z_top, 2.4, color=C_SHELF))
    s.add(_text(qx(wl0) + 2, qz(p.H_ports_top) + 1, "plugs top z %.1f" % p.H_ports_top, 2.4,
                color=C_PORTS))

    # ---- side view (below the front view): section through the plugs ----
    sy0 = top_front + p.H_cubby + pad + 8
    side_ox = fx0

    def sx(y):
        return side_ox + y

    def sz(z):
        return sy0 + p.H_cubby - z

    s.add(_text(side_ox, sy0 - 4, "SIDE (section at the plugs, x %.1f; lip on the left)" % p.X_ports,
                3.6, weight="bold"))
    s.add('<polyline points="%s" fill="none" stroke="%s" stroke-width="0.5"/>' % (
        _pts([(0, 0), (p.D_cubby, 0), (p.D_cubby, p.H_cubby), (0, p.H_cubby)], sx, sz), C_WALL))
    s.add(_text(sx(0), sz(0) + 4, "lip", 2.6, "middle", C_DIM))
    s.add(_text(sx(p.D_cubby), sz(0) + 4, "rear wall", 2.6, "middle", C_DIM))
    _, _, y0, y1, z0, z1 = phone_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.18" stroke="%s" stroke-width="0.3"/>'
          % (_pts(_rect_pts(y0, y1, z0, z1), sx, sz), C_PHONE, C_PHONE))
    _, _, y0, y1, z0, z1 = ports_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.3" stroke="%s" stroke-width="0.3"/>'
          % (_pts(_rect_pts(y0, y1, z0, z1), sx, sz), C_PORTS, C_PORTS))
    shelf_end = d.y_rear
    nx0 = d.notch_center_x - p.port_notch_width / 2.0
    nx1 = d.notch_center_x + p.port_notch_width / 2.0
    if d.notch_enabled and nx0 < p.X_ports < nx1:
        shelf_end = d.y_rear - p.port_notch_depth
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.35" stroke="%s" stroke-width="0.4"/>' % (
        _pts(_rect_pts(d.y_front, shelf_end, d.z_frame_bottom, d.z_top), sx, sz), C_SHELF, C_SHELF))

    # ---- text block ----
    ty = max(oy + plan_h + pad, sy0 + p.H_cubby + pad)
    lines = [
        "shelf top z %.1f | underside z %.1f | free above %.1f | shelf %.1f x %.1f mm (w x d)"
        % (d.z_top, d.z_underside, d.space_above, d.shelf_width_front_top, d.shelf_depth),
    ]
    order = {"error": 0, "warning": 1, "info": 2}
    for f in sorted(findings, key=lambda f: order.get(f.level, 3)):
        lines.extend(textwrap.wrap(str(f), 120, subsequent_indent="    "))
    colors = {"[ERROR]": C_WARN, "[WARNING]": "#b9770e"}
    y = ty
    color = "#000000"
    for line in lines:
        if not line.startswith(" "):  # wrapped continuation lines keep the colour
            color = next((c for k, c in colors.items() if line.startswith(k)), "#000000")
        s.add(_text(ox, y, line, 3.0, color=color))
        y += 4.4

    width = fx0 + 2 * wmax + 60
    height = y + pad
    return s.render(width, height, physical=False)
