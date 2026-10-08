"""Sanity checks and the human-readable build report. Pure Python.

Levels: "error" (the part cannot be built or will not fit), "warning" (it can
be built, but something is likely wrong), "info" (worth knowing).
"""
from __future__ import annotations

from typing import List

from .geom2d import GeometryError, is_simple
from .layout import coupon_profile, shelf_outline
from .params import Derived, ParamError, Params, cubby_width, roof_height


class Finding:
    __slots__ = ("level", "code", "message")

    def __init__(self, level: str, code: str, message: str):
        self.level = level
        self.code = code
        self.message = message

    def __repr__(self):
        return "Finding(%s, %s)" % (self.level, self.code)

    def __str__(self):
        return "[%s] %s" % (self.level.upper(), self.message)


def has_errors(findings: List[Finding]) -> bool:
    return any(f.level == "error" for f in findings)


def run_checks(p: Params, d: Derived) -> List[Finding]:
    out: List[Finding] = []

    def add(level, code, msg):
        out.append(Finding(level, code, msg))

    # -- placeholders ---------------------------------------------------------
    fitted = p.reference_based
    guesses = [n for n in p.placeholders if n not in fitted]
    if fitted:
        add("warning", "unconfirmed_reference",
            "%d cubby values are estimates, not confirmed for your car yet: %s. Print the fit "
            "coupon and the profile gauge (docs/measuring.md)."
            % (len(fitted), ", ".join(fitted)))
    if guesses:
        add("warning", "placeholders",
            "%d values are still PLACEHOLDER guesses, not measurements: %s. "
            "Put your measurements in params/measured.json." % (len(guesses), ", ".join(guesses)))

    # -- the cubby model must be defined from the floor to the roof -------------
    try:
        for z in (0.0, p.H_cubby, roof_height(p, 0.0, 0.0)):
            cubby_width(p, 0.0, z)
    except ParamError as exc:
        add("error", "wall_arc", "%s: the side walls must reach from the floor to the roof" % exc)
        return out

    # -- vertical stack -------------------------------------------------------
    if d.z_top >= p.H_cubby:
        add("error", "shelf_above_roof",
            "shelf top (%.1f) is at or above the cubby roof (H_cubby %.1f)" % (d.z_top, p.H_cubby))
    elif d.space_above < 10.0:
        add("warning", "little_space_above",
            "only %.1f mm free above the shelf for the drawer" % d.space_above)
    if d.z_frame_bottom <= 0 or d.z_underside <= 0:
        add("error", "below_floor",
            "the shelf's underside (z %.1f) is at or below the Qi pad" % d.z_underside)
    if d.z_underside < p.phone_clearance_min:
        add("warning", "phone_clearance",
            "lowest point under the shelf is z %.1f mm, below phone_clearance_min %.1f mm"
            % (d.z_underside, p.phone_clearance_min))
    if p.phone_clearance_min < p.phone_thickness + 3.0:
        add("warning", "phone_clearance_min_small",
            "phone_clearance_min (%.1f) leaves less than 3 mm over the phone (%.1f thick)"
            % (p.phone_clearance_min, p.phone_thickness))
    if p.phone_length > cubby_width(p, p.qi_center_y, 0.0):
        add("info", "phone_crosswise",
            "a %.0f mm phone is longer than the cubby is wide at the floor (%.0f): "
            "the phone does not lie crosswise" % (p.phone_length, cubby_width(p, p.qi_center_y, 0.0)))

    # -- ports ----------------------------------------------------------------
    _check_ports(p, d, add)

    # -- roof LED -------------------------------------------------------------
    r = p.led_keepout_diameter / 2.0
    if r > 0 and (abs(p.led_x) + r > cubby_width(p, p.led_y, p.H_cubby) / 2.0
                  or p.led_y - r < 0.0 or p.led_y + r > p.D_cubby):
        add("warning", "led_position",
            "the free zone around the roof LED (diameter %.0f at x %.1f, y %.1f) reaches outside "
            "the cubby: check led_x and led_y" % (p.led_keepout_diameter, p.led_x, p.led_y))
    if p.roof_bulge_depth > 0 and p.roof_bulge_diameter > p.led_keepout_diameter:
        add("info", "roof_bulge",
            "the roof bulge (diameter %.0f, %.1f mm deep) is wider than the LED free zone "
            "(%.0f): parts near the roof must clear it, and the envelope solid has a flat roof"
            % (p.roof_bulge_diameter, p.roof_bulge_depth, p.led_keepout_diameter))

    # -- insertion through the lip ---------------------------------------------
    if d.shelf_width_max > p.W_lip:
        add("warning", "insertion",
            "the shelf (%.1f mm wide) is wider than the lip opening (W_lip %.1f): it cannot be "
            "inserted flat and must be tilted in" % (d.shelf_width_max, p.W_lip))

    # -- side walls -----------------------------------------------------------
    if abs(d.side_draft_deg) > 0.05:
        lean = "outward" if d.side_draft_deg > 0 else "inward"
        add("info", "side_draft",
            "over the shelf's edge band the side walls lean %s by %.2f deg per side going up "
            "(the shelf edge follows them)" % (lean, abs(d.side_draft_deg)))

    # -- printability ----------------------------------------------------------
    for name, minimum in (("coupon_rim_width", p.min_wall), ("wall_thickness", p.min_wall),
                          ("deck_thickness", p.min_deck_thickness),
                          ("bar_width", p.min_bar_width)):
        if p[name] < minimum:
            add("warning", "thin_" + name,
                "%s = %.2f mm is below the minimum %.2f mm" % (name, p[name], minimum))
    if p.frame_height < p.deck_thickness:
        add("error", "frame_height",
            "frame_height (%.1f) is less than deck_thickness (%.1f)"
            % (p.frame_height, p.deck_thickness))
    if p.coupon_plate_thickness < 0.6:
        add("warning", "coupon_plate_thin",
            "coupon plate %.2f mm is only 2-3 layers and may warp" % p.coupon_plate_thickness)

    # -- outlines can be built -------------------------------------------------
    try:
        outline = shelf_outline(p, d, d.z_top)
        if not is_simple(outline.ring(p.arc_segments_per_90)):
            add("error", "outline_self_intersects", "the shelf outline intersects itself")
        for inset, z in coupon_profile(p, d):
            ring = shelf_outline(p, d, z, inset).ring(p.arc_segments_per_90)
            if not is_simple(ring):
                add("error", "coupon_self_intersects",
                    "fit coupon outline at inset %.1f mm intersects itself" % inset)
                break
    except (GeometryError, ParamError) as exc:
        add("error", "geometry", str(exc))

    return out


def _check_ports(p: Params, d: Derived, add) -> None:
    c = p.port_clearance
    reach = p.H_ports_top + c
    if reach <= d.z_underside:
        add("info", "ports_below_shelf",
            "plugs stay below the shelf: top %.1f + clearance %.1f <= underside %.1f"
            % (p.H_ports_top, c, d.z_underside))
        return
    # plugs reach up into the shelf's edge band -> the notch must clear them
    need_x0 = p.X_ports - p.W_ports / 2.0 - c
    need_x1 = p.X_ports + p.W_ports / 2.0 + c
    need_y = p.D_cubby - p.D_ports - c  # notch must reach at least this far forward
    if not d.notch_enabled:
        add("warning", "ports_collide",
            "plugs reach z %.1f (incl. clearance) but the shelf underside is z %.1f and the port "
            "notch is disabled: the plugs will hit the shelf" % (reach, d.z_underside))
        return
    nx0 = d.notch_center_x - p.port_notch_width / 2.0
    nx1 = d.notch_center_x + p.port_notch_width / 2.0
    ny = d.y_rear - p.port_notch_depth
    problems = []
    if nx0 > need_x0 + 1e-6:
        problems.append("left edge at x %.1f, needs <= %.1f" % (nx0, need_x0))
    if nx1 < need_x1 - 1e-6:
        problems.append("right edge at x %.1f, needs >= %.1f" % (nx1, need_x1))
    if ny > need_y + 1e-6:
        problems.append("reaches y %.1f, needs <= %.1f (deepen port_notch_depth by %.1f)"
                        % (ny, need_y, ny - need_y))
    if problems:
        add("warning", "ports_collide",
            "plugs reach into the shelf band (z %.1f > underside %.1f) and the notch does not "
            "clear them: %s" % (reach, d.z_underside, "; ".join(problems)))
    else:
        add("info", "ports_in_notch", "plugs reach into the shelf band but pass through the notch")


def format_report(p: Params, d: Derived, findings: List[Finding], title: str = "") -> str:
    lines = []
    lines.append(title or "RAV4chargerShelf build report")
    lines.append("=" * len(lines[0]))
    files = p.files
    lines.append("params: default.json" + ("".join(" + " + f for f in files) if files else
                                           "  (no params/measured.json found)"))
    lines.append("")
    lines.append("Derived dimensions (mm, car frame: z up from the Qi pad):")
    rows = [
        ("shelf top z", d.z_top),
        ("edge band bottom z (frame_height)", d.z_frame_bottom),
        ("lowest point under the shelf z", d.z_underside),
        ("free height above the shelf", d.space_above),
        ("shelf depth (front edge y %.1f -> rear edge y %.1f)" % (d.y_front, d.y_rear), d.shelf_depth),
        ("shelf width at front edge, top", d.shelf_width_front_top),
        ("shelf width at rear edge, top", d.shelf_width_rear_top),
        ("shelf width at front edge, band bottom", d.shelf_width_front_bottom),
        ("side wall draft per side [deg]", d.side_draft_deg),
        ("coupon rim height", d.coupon_rim_height),
    ]
    for label, value in rows:
        lines.append("  %-52s %8.2f" % (label, value))
    lines.append("")
    if findings:
        lines.append("Checks:")
        order = {"error": 0, "warning": 1, "info": 2}
        for f in sorted(findings, key=lambda f: order.get(f.level, 3)):
            lines.append("  " + str(f))
    else:
        lines.append("Checks: all passed")
    return "\n".join(lines) + "\n"
