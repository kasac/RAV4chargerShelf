"""SVG drawings without Rhino:

* fit_template_svg : 1:1 plan view of the shelf outline. Print it at 100 %,
  cut it out of card and hold it in the cubby before printing anything.
* overview_svg     : plan, front and side views with the ports, the phone and
  the check results, to confirm the measurements were read the right way.
* reference_overlay_svg : our outline drawn over a reference model's section.
* roof_plate_svg   : the roof plate as printed (lip up) and its depression.
"""
from __future__ import annotations

import textwrap
from typing import List, Sequence, Tuple
from xml.sax.saxutils import escape

from . import layout, perforation
from .checks import Finding
from .layout import (cubby_walls, led_keepout, phone_box, ports_box, profile_section,
                     shelf_outline)
from .params import Derived, Params, cubby_width, roof_height

C_WALL = "#333333"
C_SHELF = "#2f6db5"
C_PORTS = "#c0392b"
C_PHONE = "#7f8c8d"
C_WARN = "#c0392b"
C_DIM = "#555555"
C_LED = "#d4a017"


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
    wmax = max(cubby_width(p, y, z) for y in (0.0, p.D_cubby) for z in (0.0, p.H_cubby)) / 2.0 + 6.0
    htop = max(p.H_cubby, roof_height(p, 0.0, 0.0))  # highest roof point (a pocket is at the lip)
    led_x, led_y, led_r, led_z = led_keepout(p)

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
    if led_r > 0:
        s.add('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" fill-opacity="0.15" stroke="%s" '
              'stroke-width="0.4" stroke-dasharray="1.5,1"/>'
              % (px(led_x), py(led_y), led_r, C_LED, C_LED))
        s.add(_text(px(led_x), py(led_y) + 1, "LED free zone", 2.4, "middle", C_LED))
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
        return top_front + htop - z

    s.add(_text(fx0, oy - 4, "FRONT (looking into the cubby)", 3.6, weight="bold"))
    wl0 = cubby_width(p, ym, 0.0) / 2.0
    section = profile_section(p, ym, step=2.0, corner=0.0).ring()  # curved walls, roof pocket
    s.add('<polygon points="%s" fill="none" stroke="%s" stroke-width="0.5"/>'
          % (_pts(section, qx, qz), C_WALL))
    x0, x1, _, _, z0, z1 = phone_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.18" stroke="%s" stroke-width="0.3"/>'
          % (_pts(_rect_pts(x0, x1, z0, z1), qx, qz), C_PHONE, C_PHONE))
    x0, x1, _, _, z0, z1 = ports_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.3" stroke="%s" stroke-width="0.3" '
          'stroke-dasharray="1.5,1"/>' % (_pts(_rect_pts(x0, x1, z0, z1), qx, qz), C_PORTS, C_PORTS))
    if led_r > 0:
        s.add('<polygon points="%s" fill="%s" fill-opacity="0.12" stroke="%s" stroke-width="0.3" '
              'stroke-dasharray="1.5,1"/>' % (_pts(_rect_pts(led_x - led_r, led_x + led_r, 0.0,
                                                             led_z), qx, qz), C_LED, C_LED))
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
    sy0 = top_front + htop + pad + 8
    side_ox = fx0

    def sx(y):
        return side_ox + y

    def sz(z):
        return sy0 + htop - z

    s.add(_text(side_ox, sy0 - 4, "SIDE (section at the plugs, x %.1f; lip on the left)" % p.X_ports,
                3.6, weight="bold"))
    s.add('<polyline points="%s" fill="none" stroke="%s" stroke-width="0.5"/>' % (
        _pts([(0, 0), (p.D_cubby, 0)] + [(yy, roof_height(p, p.X_ports, yy)) for yy in
                                         [p.D_cubby * (1 - i / 40.0) for i in range(41)]],
             sx, sz), C_WALL))
    s.add(_text(sx(0), sz(0) + 4, "lip", 2.6, "middle", C_DIM))
    s.add(_text(sx(p.D_cubby), sz(0) + 4, "rear wall", 2.6, "middle", C_DIM))
    _, _, y0, y1, z0, z1 = phone_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.18" stroke="%s" stroke-width="0.3"/>'
          % (_pts(_rect_pts(y0, y1, z0, z1), sx, sz), C_PHONE, C_PHONE))
    _, _, y0, y1, z0, z1 = ports_box(p)
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.3" stroke="%s" stroke-width="0.3"/>'
          % (_pts(_rect_pts(y0, y1, z0, z1), sx, sz), C_PORTS, C_PORTS))
    if led_r > 0:
        s.add('<polygon points="%s" fill="%s" fill-opacity="0.12" stroke="%s" stroke-width="0.3" '
              'stroke-dasharray="1.5,1"/>' % (_pts(_rect_pts(led_y - led_r, led_y + led_r, 0.0,
                                                             led_z), sx, sz), C_LED, C_LED))
    shelf_end = d.y_rear
    nx0 = d.notch_center_x - p.port_notch_width / 2.0
    nx1 = d.notch_center_x + p.port_notch_width / 2.0
    if d.notch_enabled and nx0 < p.X_ports < nx1:
        shelf_end = d.y_rear - p.port_notch_depth
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.35" stroke="%s" stroke-width="0.4"/>' % (
        _pts(_rect_pts(d.y_front, shelf_end, d.z_frame_bottom, d.z_top), sx, sz), C_SHELF, C_SHELF))

    # ---- text block ----
    ty = max(oy + plan_h + pad, sy0 + htop + pad)
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


# --------------------------------------------------------------------------
# reference overlay
# --------------------------------------------------------------------------

def reference_overlay_svg(ref_segments, our_ring, lines: List[str], title: str) -> str:
    """Plan view in the reference frame (x, depth; front at the bottom): the
    reference section in red, our outline in blue, plus text lines."""
    xs = [x for seg in ref_segments for x, _ in seg] + [x for x, _ in our_ring]
    ds = [dd for seg in ref_segments for _, dd in seg] + [dd for _, dd in our_ring]
    x0, x1, d0, d1 = min(xs), max(xs), min(ds), max(ds)
    pad, head = 10.0, 16.0

    def fx(x):
        return pad + (x - x0)

    def fy(dd):
        return head + (d1 - dd)  # rear wall at the top, front at the bottom

    s = _Svg()
    s.add(_text(pad, 7, title, 4.0, weight="bold"))
    s.add(_text(pad, 12.5, "red: reference section   blue: our shelf outline (aligned at the rear edge)",
                3.0, color=C_DIM))
    s.add('<path d="%s" fill="none" stroke="%s" stroke-width="0.35"/>' % (
        " ".join("M%.2f,%.2f L%.2f,%.2f" % (fx(a[0]), fy(a[1]), fx(b[0]), fy(b[1]))
                 for a, b in ref_segments), C_WARN))
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.10" stroke="%s" stroke-width="0.35"/>'
          % (_pts(our_ring, fx, fy), C_SHELF, C_SHELF))
    y = head + (d1 - d0) + 9
    for line in lines:
        s.add(_text(pad, y, line, 3.0))
        y += 4.6
    return s.render(2 * pad + (x1 - x0), y + pad, physical=False)


# --------------------------------------------------------------------------
# roof plate
# --------------------------------------------------------------------------

def roof_plate_svg(p: Params, d: Derived, mesh_grams: float = None) -> str:
    """Plan of the roof plate with the lip at the top, as it stands in the
    printer, plus a section through the middle showing the depression."""
    outline = layout.roof_plate_outline(p, d)
    pat = layout.roof_pattern(p)
    holes = layout.roof_plate_holes(p, d, outline)
    xmax = max(abs(x) for x, _ in outline)
    y0, y1 = min(y for _, y in outline), max(y for _, y in outline)
    pad, head = 14.0, 30.0
    width = 2 * xmax + 2 * pad + 18.0 + 28.0  # arrow on the left, labels on the right

    def fx(x):
        return pad + 18.0 + xmax + x

    def fy(y):  # lip at the top
        return head + (y - y0)

    s = _Svg()
    s.add(_text(pad, 9, "Roof plate as printed: standing on its rear edge, lip at the top", 4.2,
                weight="bold"))
    s.add(_text(pad, 15, "Seen from above. Hole tips point to the lip, so they print without "
                         "support; the rear corners are cut to the overhang limit.", 2.8,
                color=C_DIM))
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.12" stroke="%s" stroke-width="0.45"/>'
          % (_pts(outline, fx, fy), C_SHELF, C_SHELF))
    for h in holes:
        s.add('<polygon points="%s" fill="#ffffff" stroke="%s" stroke-width="0.25"/>'
              % (_pts(h, fx, fy), C_WALL))
    for y, label in ((d.y_front + p.roof_depression_start, "front strip ends"),
                     (layout.roof_flat_from(p, d), "lowered from here")):
        if p.roof_depression_depth > 0:
            s.add('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.3" '
                  'stroke-dasharray="2,1.2"/>' % (fx(-xmax), fy(y), fx(xmax), fy(y), C_DIM))
            s.add(_text(fx(xmax) + 1.5, fy(y) + 1, label, 2.4, color=C_DIM))
    lx, ly, lr, _ = led_keepout(p)
    if lr > 0:
        s.add('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="%s" stroke-width="0.45" '
              'stroke-dasharray="2,1"/>' % (fx(lx), fy(ly), lr, C_LED))
        s.add('<circle cx="%.2f" cy="%.2f" r="3" fill="%s"/>' % (fx(lx), fy(ly), C_LED))
    ax = pad + 6.0
    s.add('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.5"/>'
          % (ax, fy(y1), ax, fy(y0) + 4, C_DIM))
    s.add('<path d="M%.2f %.2fl-2 4h4z" fill="%s"/>' % (ax, fy(y0), C_DIM))
    s.add('<text x="%.2f" y="%.2f" font-size="2.6" fill="%s" text-anchor="middle" '
          'transform="rotate(-90 %.2f %.2f)">print direction</text>'
          % (ax - 2.5, (fy(y0) + fy(y1)) / 2, C_DIM, ax - 2.5, (fy(y0) + fy(y1)) / 2))
    s.add(_text(fx(0), fy(y0) - 2.5, "front edge (lip side) = top of the print", 2.6, "middle",
                C_DIM))
    s.add(_text(fx(0), fy(y1) + 5, "rear edge on the bed", 2.6, "middle", C_DIM))

    # section at x = 0, true length, heights x3
    ex = 3.0
    title_y = fy(y1) + 16.0
    z_hi = p.H_cubby + 2.0
    z_lo = p.H_cubby - p.roof_clearance - p.roof_depression_depth - p.roof_thickness - 2.0

    def sx(y):
        return fx(-xmax) + (y - y0)

    def sz(z):
        return title_y + 5.0 + (z_hi - z) * ex

    s.add(_text(fx(-xmax), title_y, "Section through the middle (lip on the left, heights x%.0f)"
                % ex, 3.2, weight="bold"))
    steps = [y0 + (y1 - y0) * i / 240.0 for i in range(241)]
    roof = [(y, roof_height(p, 0.0, y)) for y in steps]
    s.add('<polyline points="%s" fill="none" stroke="%s" stroke-width="0.4"/>'
          % (_pts(roof, sx, sz), C_WALL))
    s.add(_text(sx(y1) + 1.5, sz(p.H_cubby) + 1, "cubby roof", 2.4, color=C_WALL))
    plate = ([(y, layout.roof_plate_top(p, d, y)) for y in steps]
             + [(y, layout.roof_plate_top(p, d, y) - p.roof_thickness) for y in reversed(steps)])
    s.add('<polygon points="%s" fill="%s" fill-opacity="0.35" stroke="%s" stroke-width="0.3"/>'
          % (_pts(plate, sx, sz), C_SHELF, C_SHELF))
    s.add(_text(sx(y1) + 1.5, sz(layout.roof_plate_top(p, d, y1) - p.roof_thickness / 2) + 1,
                "roof plate", 2.4, color=C_SHELF))

    lines = ["front strip %.0f mm, then %.1f mm lower over a %.0f mm ramp (overhang %.0f deg, "
             "limit %.0f)" % (p.roof_depression_start, p.roof_depression_depth,
                              p.roof_depression_ramp, layout.roof_ramp_overhang_deg(p),
                              p.max_overhang_deg)]
    if pat is not None:
        lines.append("%s holes %.0f mm, %d of them; %.0f %% open in the pattern, bars %.1f mm"
                     % (pat.style, pat.width, len(holes), 100 * pat.open_fraction, pat.bar))
        if lr > 0:
            lines.append("LED free zone: %.0f %% open"
                         % (100 * perforation.open_share(holes, lx, ly, lr)))
    else:
        lines.append("not perforated")
    if mesh_grams is not None:
        lines.append("about %.0f g PETG" % mesh_grams)
    ty = sz(z_lo) + 8.0
    for i, line in enumerate(lines):
        s.add(_text(fx(-xmax), ty + 4.5 * i, line, 3.0))
    height = ty + 4.5 * len(lines) + pad
    return s.render(width, height, physical=False)
