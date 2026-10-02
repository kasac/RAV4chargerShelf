"""Compare the shelf outline with the outer boundary of a reference model, and
fit our parameters to it. Pure Python (no Rhino, no numpy).

Reference: the Vela3D "Toyota RAV4 Tray Drawer Organizer" (Cults3D, a paid
download, tested in the car). Its STL files are NOT part of this repository
(licence). Put them in reference/, which is git-ignored. Only dimensions are
derived from them, as the brief allows ("use them only for constraints").

How MODULE.stl was read (from sections of the file, see README):
* It is the drawer housing, printed standing and rotated 135 deg about z on
  the bed. Un-rotated, print x = car width, print z = car depth (max z is the
  front, where the drawers come out) and print y points DOWN in the car: the
  drawers slide on the plate at print y 29..36 (their side ribs run in grooves
  parallel to it), the curved top plate is at print y 0..12 and the side wings
  reach down to print y 89.
* Its outer sides press against the cubby walls through foam pads, so its
  outline corresponds to our shelf outline with side_gap = foam thickness.

Frame used here: x centred on the part, depth measured from the part's front
into the dash, level measured DOWN in the file's print coordinates.
"""
from __future__ import annotations

import bisect
import glob
import json
import math
import os
from typing import Dict, List, Optional, Sequence, Tuple

from . import fileio, layout
from . import params as P
from .params import Derived, Params

REFERENCE_DIR = os.path.join(P.REPO_ROOT, "reference")

Pt2 = Tuple[float, float]
Seg2 = Tuple[Pt2, Pt2]


class ReferenceError(ValueError):
    """The reference file is missing or is not the version that was analysed."""


class ReferenceSpec:
    """How to place a reference STL in the (x, depth, level) frame.

    rotate_z_deg   rotation about z applied first (undoes the diagonal bed placement)
    extents        expected bounding box after the rotation; None = do not check
    x_axis         axis (0, 1, 2) that becomes x (car width)
    depth_axis/sign  axis that becomes depth; sign -1 = the front is at the axis maximum
    level_axis/sign  axis that becomes level; sign +1 = level grows with the axis
    compare_level  level that corresponds to our shelf's TOP surface
    floor_level    level of the Qi pad (ASSUMPTION, only used for fitted heights)
    roof_level     level of the cubby roof above the shelf (ASSUMPTION, ditto)
    rear_zone      the last rear_zone mm of depth are the rear corners, compared apart
    """

    def __init__(self, name, file_glob, rotate_z_deg, extents, x_axis, depth_axis, depth_sign,
                 level_axis, level_sign, compare_level, floor_level, roof_level, rear_zone):
        self.name = name
        self.file_glob = file_glob
        self.rotate_z_deg = rotate_z_deg
        self.extents = extents
        self.x_axis = x_axis
        self.depth_axis = depth_axis
        self.depth_sign = depth_sign
        self.level_axis = level_axis
        self.level_sign = level_sign
        self.compare_level = compare_level
        self.floor_level = floor_level
        self.roof_level = roof_level
        self.rear_zone = rear_zone


VELA3D_MODULE = ReferenceSpec(
    name="Vela3D Toyota RAV4 Tray Drawer Organizer, MODULE.stl (drawer housing)",
    file_glob="*TRAY_DRAWER_ORGANIZER_MODULE*.stl",
    rotate_z_deg=-135.0,
    extents=(235.20, 89.41, 120.88),
    x_axis=0, depth_axis=2, depth_sign=-1, level_axis=1, level_sign=1,
    # 10.5 mm below the housing top at the back. Our 8 mm edge band then lies
    # between print y 22 and 30, where the housing outline is closed at the back.
    compare_level=22.0,
    floor_level=89.41,  # ASSUMPTION: the wing tips touch the floor
    roof_level=11.55,   # ASSUMPTION: the housing top touches the roof at the back
    rear_zone=36.0,     # the sides are straight up to 85 mm behind the front
)


def find_reference_file(spec: ReferenceSpec = VELA3D_MODULE, folder: str = REFERENCE_DIR):
    """Path of the reference STL in ``folder``, or None."""
    hits = sorted(glob.glob(os.path.join(folder, spec.file_glob)))
    return hits[0] if hits else None


def frange(start: float, stop: float, step: float) -> List[float]:
    n = int(math.floor((stop - start) / step + 1e-9))
    return [start + i * step for i in range(n + 1)]


# --------------------------------------------------------------------------
# sections and boundary profiles
# --------------------------------------------------------------------------

def extents_profile(segments: Sequence[Seg2], depths: Sequence[float]):
    """For each depth (ascending): (x_min, x_max) of a plan section along the
    line depth = const, or None where the section has no material."""
    n = len(depths)
    lo = [math.inf] * n
    hi = [-math.inf] * n
    for (x0, d0), (x1, d1) in segments:
        if d0 == d1:
            continue  # parallel to the probe lines; its neighbours cover its ends
        if d0 > d1:
            x0, d0, x1, d1 = x1, d1, x0, d0
        k = (x1 - x0) / (d1 - d0)
        for i in range(bisect.bisect_left(depths, d0), bisect.bisect_right(depths, d1)):
            x = x0 + k * (depths[i] - d0)
            if x < lo[i]:
                lo[i] = x
            if x > hi[i]:
                hi[i] = x
    return [(lo[i], hi[i]) if lo[i] <= hi[i] else None for i in range(n)]


def ring_segments(ring: Sequence[Pt2], depth_shift: float = 0.0) -> List[Seg2]:
    """Closed ring (x, y) -> segments (x, depth) with depth = y - depth_shift."""
    pts = [(x, y - depth_shift) for x, y in ring]
    return [(pts[i - 1], pts[i]) for i in range(len(pts))]


class PlacedReference:
    """A reference STL placed in the (x, depth, level) frame."""

    def __init__(self, spec: ReferenceSpec, path: str, triangles):
        self.spec = spec
        self.path = path
        a = math.radians(spec.rotate_z_deg)
        c, s = math.cos(a), math.sin(a)
        rot = [[(c * x - s * y, s * x + c * y, z) for (x, y, z) in t] for t in triangles]
        mins = [min(v[i] for t in rot for v in t) for i in range(3)]
        maxs = [max(v[i] for t in rot for v in t) for i in range(3)]
        ext = [maxs[i] - mins[i] for i in range(3)]
        self.raw_extents = tuple(ext)
        if spec.extents and any(abs(e - x) > 0.1 for e, x in zip(ext, spec.extents)):
            raise ReferenceError(
                "%s: bounding box %s does not match the analysed file %s; a different file "
                "or version needs a new ReferenceSpec" % (
                    os.path.basename(path), tuple(round(e, 2) for e in ext), spec.extents))
        xa, da, la = spec.x_axis, spec.depth_axis, spec.level_axis

        def place(v):
            u = (v[0] - mins[0], v[1] - mins[1], v[2] - mins[2])
            depth = u[da] if spec.depth_sign > 0 else ext[da] - u[da]
            level = u[la] if spec.level_sign > 0 else ext[la] - u[la]
            return (u[xa] - ext[xa] / 2.0, depth, level)

        self.triangles = [tuple(place(v) for v in t) for t in rot]
        self.width = ext[xa]
        self.depth = ext[da]
        self.height = ext[la]
        self._cache: Dict[tuple, list] = {}

    def section(self, level: float) -> List[Seg2]:
        """Plan section (x, depth) at a level."""
        key = ("section", level)
        if key not in self._cache:
            h = level + 1e-7  # never exactly through a vertex
            segs = []
            for t in self.triangles:
                pts = []
                for i in range(3):
                    a, b = t[i], t[(i + 1) % 3]
                    da, db = a[2] - h, b[2] - h
                    if (da < 0) != (db < 0):
                        f = da / (da - db)
                        pts.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
                if len(pts) == 2:
                    segs.append((pts[0], pts[1]))
            self._cache[key] = segs
        return self._cache[key]

    def profile(self, level: float, depths: Sequence[float]):
        key = ("profile", level, tuple(depths))
        if key not in self._cache:
            self._cache[key] = extents_profile(self.section(level), depths)
        return self._cache[key]


def load_reference(spec: ReferenceSpec = VELA3D_MODULE, path: str = None) -> PlacedReference:
    path = path or find_reference_file(spec)
    if not path or not os.path.isfile(path):
        raise ReferenceError("reference STL not found: put %s into %s" % (spec.file_glob, REFERENCE_DIR))
    return PlacedReference(spec, path, fileio.read_stl(path))


# --------------------------------------------------------------------------
# comparison
# --------------------------------------------------------------------------

class Comparison:
    """Signed deviations ours - reference of the outer half-width.
    Positive = our shelf sticks out beyond the reference (risk of touching the
    car); negative = our shelf is smaller."""

    def __init__(self, depth_ours: float, depth_ref: float, levels):
        self.rows = []  # (zone, level_name, depth, ours, ref, dev)
        self.depth_ours = depth_ours
        self.depth_ref = depth_ref
        self.levels = levels  # [(name, our z, reference level)]

    def stats(self, zone: str, level_name: str = None) -> Optional[dict]:
        rows = [r for r in self.rows if r[0] == zone and (level_name is None or r[1] == level_name)]
        if not rows:
            return None
        hi = max(rows, key=lambda r: r[5])
        lo = min(rows, key=lambda r: r[5])
        return {"max_out": hi[5], "max_out_at": hi[2], "max_in": lo[5], "max_in_at": lo[2],
                "max_abs": max(abs(hi[5]), abs(lo[5])), "n": len(rows)}

    def summary_lines(self) -> List[str]:
        out = ["depth: ours %.1f mm, reference %.1f mm (aligned at the rear edge)"
               % (self.depth_ours, self.depth_ref)]
        for name, z, lvl in self.levels:
            for zone in ("sides", "rear corners"):
                s = self.stats(zone, name)
                if s is None:
                    continue
                out.append("%-12s %-12s (our z %5.1f): sticks out up to %+5.2f mm (depth %5.1f), "
                           "smaller by up to %5.2f mm (depth %5.1f)" % (
                               zone, name, z, max(s["max_out"], 0.0), s["max_out_at"],
                               max(-s["max_in"], 0.0), s["max_in_at"]))
        return out


def compare(p: Params, d: Derived, ref: PlacedReference, step: float = 0.5) -> Comparison:
    """Compare our shelf outline with the reference's outer boundary per side.

    Our shelf top (z_top) is matched to spec.compare_level, the bottom of our
    edge band (z_top - frame_height) to compare_level + frame_height. The two
    are aligned at the rear edge (the rear wall is the common stop). The rear
    corner zone is only compared at the top level.
    """
    spec = ref.spec
    shift = d.y_rear - ref.depth  # our y = reference depth + shift
    d_lo = max(0.5, d.y_front - shift)
    d_hi = ref.depth - 0.4  # skip the very edge of the back face
    depths = frange(d_lo, d_hi, step)
    levels = [("top", d.z_top, spec.compare_level),
              ("band bottom", d.z_frame_bottom, spec.compare_level + p.frame_height)]
    cmp = Comparison(d.y_rear - d.y_front, ref.depth, levels)
    rear_start = ref.depth - spec.rear_zone
    for name, z, level in levels:
        ring = layout.shelf_outline(p, d, z).ring(32)
        ours = extents_profile(ring_segments(ring, shift), depths)
        theirs = ref.profile(level, depths)
        for dep, o, r in zip(depths, ours, theirs):
            if o is None or r is None:
                continue
            zone = "sides" if dep <= rear_start else "rear corners"
            if zone == "rear corners" and name != "top":
                continue
            hw_o = (o[1] - o[0]) / 2.0
            hw_r = (r[1] - r[0]) / 2.0
            cmp.rows.append((zone, name, dep, hw_o, hw_r, hw_o - hw_r))
    return cmp


# --------------------------------------------------------------------------
# fitting our parameters to the reference
# --------------------------------------------------------------------------

def _line_fit(pts: Sequence[Pt2]):
    n = float(len(pts))
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    b = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
    a = my - b * mx
    resid = max(abs(p[1] - (a + b * p[0])) for p in pts)
    return a, b, resid


def fit_params(ref: PlacedReference, front_recess: float = 8.0, rear_gap: float = 1.0,
               frame_height: float = 8.0, corner_radius_front: float = 1.0):
    """Parameters that make our generator reproduce the reference outline.

    Returns (values, quality). side_gap is 0, so the outline equals the
    reference part itself (the cubby is wider by Vela3D's foam, unknown).
    Heights use the spec's floor/roof ASSUMPTIONS; W_top / W_bottom are a
    linear fit around the shelf band, not the real roof / floor widths.
    """
    spec = ref.spec
    depths = frange(5.0, ref.depth - spec.rear_zone, 1.0)

    def side_line(level):
        prof = ref.profile(level, depths)
        return _line_fit([(dd, (pr[1] - pr[0]) / 2.0) for dd, pr in zip(depths, prof) if pr])

    a_t, b_t, r_t = side_line(spec.compare_level)
    a_b, b_b, r_b = side_line(spec.compare_level + frame_height)
    b = (b_t + b_b) / 2.0
    z_top = spec.floor_level - spec.compare_level
    h_cubby = spec.floor_level - spec.roof_level
    d_cubby = front_recess + ref.depth + rear_gap
    y0 = P.MEAS_INSET
    w_hi = 2.0 * (a_t + b * (y0 - front_recess))  # width at y0, at our shelf top
    w_lo = 2.0 * (a_b + b * (y0 - front_recess))  # ... frame_height lower
    k = (w_hi - w_lo) / frame_height              # width change per mm of height
    w_bottom = w_hi - k * z_top
    values = {
        "W_top": w_bottom + k * h_cubby,
        "W_bottom": w_bottom,
        "W_rear_delta": 2.0 * b * (d_cubby - 2.0 * P.MEAS_INSET),
        "D_cubby": d_cubby,
        "H_cubby": h_cubby,
        "W_lip": math.ceil(ref.width + 0.5),
        "shelf_height": z_top,
        "front_recess": front_recess,
        "rear_gap": rear_gap,
        "side_gap": 0.0,
        "frame_height": frame_height,
        "corner_radius_front": corner_radius_front,
        "port_notch_width": 0.0,
    }
    values = {k_: round(v, 2) if isinstance(v, float) else v for k_, v in values.items()}

    best = None
    for radius in frange(1.0, 30.0, 0.5):
        pp = P.load_params(dict(values, R_rear_corner=radius))
        s = compare(pp, P.derive(pp), ref).stats("rear corners", "top")
        if s and (best is None or s["max_abs"] < best[1]["max_abs"]):
            best = (radius, s)
    values["R_rear_corner"] = best[0]
    pp = P.load_params(values)
    final = compare(pp, P.derive(pp), ref)
    quality = {
        "side_line_residual": round(max(r_t, r_b), 3),
        "sides": final.stats("sides"),
        "rear_corners": final.stats("rear corners"),
        "wall_lean_deg_per_side": round(math.degrees(math.atan(k / 2.0)), 2),
        "width_change_per_100mm_depth": round(200.0 * b, 2),
    }
    return values, quality


def write_params_file(path: str, values: dict, quality: dict, ref: PlacedReference) -> None:
    sides, rear = quality["sides"], quality["rear_corners"]
    doc = {
        "_source": ("Fitted to the outer boundary of %s by 'python tools/rav4shelf.py reference "
                    "--write-params'. The STL is not in the repo (paid); only these dimensions "
                    "are derived from it." % ref.spec.name),
        "_meaning": ("With these values our shelf outline reproduces the tested Vela3D outline "
                     "(side_gap 0: their foam gap is unknown, the real cubby is wider by 2 x foam). "
                     "Use it BEFORE you have measured: -p params/reference_vela3d.json is applied "
                     "after params/measured.json and would override your measurements."),
        "_assumptions": ("Not in the file, assumed: housing front %.0f mm behind the lip, back "
                         "%.0f mm from the rear wall, wing tips on the floor, housing top at the "
                         "roof at the back. W_top/W_bottom are a linear fit around the shelf band, "
                         "not the real roof/floor widths (the real side walls curve in toward the "
                         "floor)." % (values["front_recess"], values["rear_gap"])),
        "_fit": ("sides within %.2f mm; rear corners within %.2f mm (a single circular fillet "
                 "vs their free-form corner); wall lean %.1f deg per side; %.1f mm narrower per "
                 "100 mm of depth" % (sides["max_abs"], rear["max_abs"],
                                      quality["wall_lean_deg_per_side"],
                                      -quality["width_change_per_100mm_depth"])),
    }
    doc.update(values)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(doc, indent=2) + "\n")
