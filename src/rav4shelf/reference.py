"""Approximate a reference model's outer shape with our cubby envelope, and
compare the two. Pure Python (no Rhino, no numpy).

Reference: the Vela3D "Toyota RAV4 Tray Drawer Organizer" (Cults3D, a paid
download, tested in the car; its outer surface looks like it follows a 3D
scan of the cubby). Its STL files are NOT part of this repository (licence).
Put them in reference/, which is git-ignored. Only a handful of numbers are
derived from them: our envelope is a small parametric model (see
params.cubby_half_width, params.roof_height, layout.shelf_outline), not a
copy of their mesh.

How MODULE.stl was read (from sections of the file, see README):
* It is the drawer housing, printed standing and rotated 135 deg about z on
  the bed. Un-rotated, print x = car width, print z = car depth (max z is the
  front, where the drawers come out) and print y points DOWN in the car: the
  drawers slide on the plate at print y 29..36 (their side ribs run in grooves
  parallel to it), the top plate is at print y 0..12 and the side wings reach
  down to print y 89.
* Its outer sides press against the cubby walls through foam pads, so its
  outline is the cubby minus their (unknown) foam allowance: envelope_offset.

Frame used here: x centred on the part, depth measured from the part's front
into the dash, level measured DOWN in the file's print coordinates. Car
coordinates follow from the spec's assumptions: y = front_recess + depth,
z = floor_level - level.
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
from .geom2d import GeometryError
from .params import Derived, Params

REFERENCE_DIR = os.path.join(P.REPO_ROOT, "reference")

Pt2 = Tuple[float, float]
Seg2 = Tuple[Pt2, Pt2]


class ReferenceError(ValueError):
    """The reference file is missing or is not the version that was analysed."""


class ReferenceSpec:
    """How to read a reference STL.

    rotate_z_deg       rotation about z applied first (undoes the diagonal bed placement)
    extents            expected bounding box after the rotation; None = do not check
    x_axis             axis (0, 1, 2) that becomes x (car width)
    depth_axis/sign    axis that becomes depth; sign -1 = the front is at the axis maximum
    level_axis/sign    axis that becomes level; sign +1 = level grows with the axis
    floor_level        level of the Qi pad                          (ASSUMPTION)
    front_recess       the part's front is this far behind the lip  (ASSUMPTION)
    rear_gap           its back is this far in front of the rear wall (ASSUMPTION)
    wall_levels        (min, max) levels where its sides follow the cubby walls
    closed_back_levels (min, max) levels where it has a back face (rear corners)
    rear_zone          the last rear_zone mm of depth are the rear corners
    wing_end_margin    ignore this much before the side data ends (cut wing edges)
    roof_depths        (min, max) depth range of its top surface to fit the roof to;
                       None = it says nothing about the roof
    """

    def __init__(self, name, file_glob, rotate_z_deg, extents, x_axis, depth_axis, depth_sign,
                 level_axis, level_sign, floor_level, front_recess, rear_gap, wall_levels,
                 closed_back_levels, rear_zone, wing_end_margin, roof_depths):
        self.name = name
        self.file_glob = file_glob
        self.rotate_z_deg = rotate_z_deg
        self.extents = extents
        self.x_axis = x_axis
        self.depth_axis = depth_axis
        self.depth_sign = depth_sign
        self.level_axis = level_axis
        self.level_sign = level_sign
        self.floor_level = floor_level
        self.front_recess = front_recess
        self.rear_gap = rear_gap
        self.wall_levels = wall_levels
        self.closed_back_levels = closed_back_levels
        self.rear_zone = rear_zone
        self.wing_end_margin = wing_end_margin
        self.roof_depths = roof_depths


VELA3D_MODULE = ReferenceSpec(
    name="Vela3D Toyota RAV4 Tray Drawer Organizer, MODULE.stl (drawer housing)",
    file_glob="*TRAY_DRAWER_ORGANIZER_MODULE*.stl",
    rotate_z_deg=-135.0,
    extents=(235.20, 89.41, 120.88),
    x_axis=0, depth_axis=2, depth_sign=-1, level_axis=1, level_sign=1,
    floor_level=89.41,         # ASSUMPTION: the wing tips reach the floor
    front_recess=8.0,          # ASSUMPTION
    rear_gap=1.0,              # ASSUMPTION
    wall_levels=(16.0, 86.0),  # above 16 the housing's top edge is rounded
    closed_back_levels=(16.0, 28.0),
    rear_zone=36.0,            # the sides are straight up to 85 mm behind the front
    wing_end_margin=15.0,
    roof_depths=(4.0, 115.0),
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

def extents_profile(segments: Sequence[Seg2], probes: Sequence[float]):
    """For each probe value v (ascending): (min, max) of the first coordinate
    where the segments cross the line second-coordinate = v, or None."""
    n = len(probes)
    lo = [math.inf] * n
    hi = [-math.inf] * n
    for (x0, d0), (x1, d1) in segments:
        if d0 == d1:
            continue  # parallel to the probe lines; its neighbours cover its ends
        if d0 > d1:
            x0, d0, x1, d1 = x1, d1, x0, d0
        k = (x1 - x0) / (d1 - d0)
        for i in range(bisect.bisect_left(probes, d0), bisect.bisect_right(probes, d1)):
            x = x0 + k * (probes[i] - d0)
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

    def slice(self, axis: int, value: float) -> List[Seg2]:
        """Section with the plane coordinate[axis] = value, as 2D segments in the
        other two coordinates (in axis order): axis 2 (level) -> (x, depth),
        axis 1 (depth) -> (x, level)."""
        key = ("slice", axis, value)
        if key not in self._cache:
            h = value + 1e-7  # never exactly through a vertex
            i0, i1 = [i for i in range(3) if i != axis]
            segs = []
            for t in self.triangles:
                pts = []
                for k in range(3):
                    a, b = t[k], t[(k + 1) % 3]
                    da, db = a[axis] - h, b[axis] - h
                    if (da < 0) != (db < 0):
                        f = da / (da - db)
                        pts.append((a[i0] + (b[i0] - a[i0]) * f, a[i1] + (b[i1] - a[i1]) * f))
                if len(pts) == 2:
                    segs.append((pts[0], pts[1]))
            self._cache[key] = segs
        return self._cache[key]

    def section(self, level: float) -> List[Seg2]:
        """Plan section (x, depth) at a level."""
        return self.slice(2, level)

    def profile(self, level: float, depths: Sequence[float]):
        """(x_min, x_max) of the plan section at each depth, or None."""
        key = ("profile", level, tuple(depths))
        if key not in self._cache:
            self._cache[key] = extents_profile(self.section(level), depths)
        return self._cache[key]

    def top_levels(self, depth: float, xs: Sequence[float]):
        """Level of the top surface (smallest level with material) at each x, or None."""
        swapped = [((l0, x0), (l1, x1)) for (x0, l0), (x1, l1) in self.slice(1, depth)]
        return [pr[0] if pr else None for pr in extents_profile(swapped, xs)]

    def to_y(self, depth: float) -> float:
        return self.spec.front_recess + depth

    def to_z(self, level: float) -> float:
        return self.spec.floor_level - level


def load_reference(spec: ReferenceSpec = VELA3D_MODULE, path: str = None) -> PlacedReference:
    path = path or find_reference_file(spec)
    if not path or not os.path.isfile(path):
        raise ReferenceError("reference STL not found: put %s into %s" % (spec.file_glob, REFERENCE_DIR))
    return PlacedReference(spec, path, fileio.read_stl(path))


# --------------------------------------------------------------------------
# samples of the reference surface (car coordinates)
# --------------------------------------------------------------------------

def wall_samples(ref: PlacedReference, level_step: float = 2.0, depth_step: float = 2.0):
    """(y, z, half-width) on the side walls, outside the rear corners and away
    from the cut ends of the wings."""
    spec = ref.spec
    depths = frange(0.5, ref.depth - 0.5, depth_step)
    rear_start = ref.depth - spec.rear_zone
    out = []
    for level in frange(spec.wall_levels[0], spec.wall_levels[1], level_step):
        prof = ref.profile(level, depths)
        have = [dd for dd, pr in zip(depths, prof) if pr]
        if not have:
            continue
        last = min(rear_start, max(have) - spec.wing_end_margin)
        for dd, pr in zip(depths, prof):
            if pr and dd <= last:
                out.append((ref.to_y(dd), ref.to_z(level), (pr[1] - pr[0]) / 2.0))
    return out


def roof_samples(ref: PlacedReference, x_step: float = 5.0, depth_step: float = 4.0,
                 side_margin: float = 8.0):
    """(x, y, z) on the top surface, away from the rounded side edges."""
    spec = ref.spec
    if not spec.roof_depths:
        return []
    out = []
    for dd in frange(spec.roof_depths[0], spec.roof_depths[1], depth_step):
        prof = ref.profile(spec.closed_back_levels[0], [dd])[0]  # side walls at that depth
        if not prof:
            continue
        xs = frange(prof[0] + side_margin, prof[1] - side_margin, x_step)
        for x, level in zip(xs, ref.top_levels(dd, xs)):
            if level is not None:
                out.append((x, ref.to_y(dd), ref.to_z(level)))
    return out


# --------------------------------------------------------------------------
# a small optimiser (no numpy / scipy in Rhino)
# --------------------------------------------------------------------------

def nelder_mead(f, x0: Sequence[float], steps: Sequence[float], iters: int = 400,
                tol: float = 1e-7):
    """Minimise f over len(x0) variables. Returns (best x, best value)."""
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (steps[j] if j == i else 0.0) for j in range(n)]
                        for i in range(n)]
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = sorted(range(n + 1), key=lambda i: vals[i])
        pts = [pts[i] for i in order]
        vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol:
            break
        c = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        w = pts[-1]
        r = [c[j] + (c[j] - w[j]) for j in range(n)]
        fr = f(r)
        if fr < vals[0]:
            e = [c[j] + 2.0 * (c[j] - w[j]) for j in range(n)]
            fe = f(e)
            pts[-1], vals[-1] = (e, fe) if fe < fr else (r, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = r, fr
        else:
            k = [c[j] + 0.5 * (w[j] - c[j]) for j in range(n)]
            fk = f(k)
            if fk < vals[-1]:
                pts[-1], vals[-1] = k, fk
            else:
                b = pts[0]
                pts = [b] + [[b[j] + 0.5 * (p[j] - b[j]) for j in range(n)] for p in pts[1:]]
                vals = [vals[0]] + [f(p) for p in pts[1:]]
    i = min(range(n + 1), key=lambda i: vals[i])
    return pts[i], vals[i]


def _stats(devs: Sequence[float]) -> Optional[dict]:
    if not devs:
        return None
    return {"max_out": max(devs), "max_in": min(devs), "max_abs": max(abs(v) for v in devs),
            "rms": math.sqrt(sum(v * v for v in devs) / len(devs)), "n": len(devs)}


# --------------------------------------------------------------------------
# fitting the envelope parameters
# --------------------------------------------------------------------------

def fit_walls(samples, z_ref: float, d_cubby: float):
    """Fit the side walls: half-width = a + b*y + wall(z), where wall(z) is a
    circular arc seen from the front with lean ``lean`` at z_ref and curvature
    k = 1/radius (k = 0: straight). The arc is moved linearly along the depth
    (taper b). Fitting the curvature instead of the radius keeps straight walls
    well-behaved. Returns (values, stats)."""
    ys = [s[0] for s in samples]
    zs = [s[1] for s in samples]
    hs = [s[2] for s in samples]
    n = float(len(samples))
    my = sum(ys) / n
    syy = sum((y - my) ** 2 for y in ys)
    r_max = P.load_spec()["wall_radius"]["max"]

    def wall(z, lean, k):
        if k <= 1.0 / r_max:
            return math.tan(lean) * (z - z_ref)
        radius = 1.0 / k
        dz = z - (z_ref + radius * math.sin(lean))
        if abs(dz) >= radius:
            return None
        return math.sqrt(radius * radius - dz * dz) - radius * math.cos(lean)

    def solve(lean, k):
        g = [wall(z, lean, k) for z in zs]
        if None in g:
            return None
        u = [h - gi for h, gi in zip(hs, g)]
        mu = sum(u) / n
        b = sum((y - my) * (ui - mu) for y, ui in zip(ys, u)) / syy
        a = mu - b * my
        res = [a + b * y - ui for y, ui in zip(ys, u)]  # model - data: + = ours bigger
        return a, b, res

    def rms(v):  # v = (lean in degrees, curvature in 1/m)
        if v[1] < 0 or abs(v[0]) > 60:
            return 1e9
        sol = solve(math.radians(v[0]), v[1] / 1000.0)
        return math.sqrt(sum(r * r for r in sol[2]) / n) if sol else 1e9

    grid = [(lean, k) for lean in (-10.0, 0.0, 5.0, 10.0, 20.0) for k in (0.0, 1.0, 2.0, 4.0, 8.0)]
    start = min(grid, key=rms)
    (lean_deg, k_m), _ = nelder_mead(rms, start, (2.0, 0.5), iters=800, tol=1e-12)
    k_m = max(k_m, 0.0)
    a, b, res = solve(math.radians(lean_deg), k_m / 1000.0)
    radius = 1000.0 / k_m if k_m > 1000.0 / r_max else 0.0
    m = P.MEAS_INSET
    values = {
        # wall(z_ref) = 0, so the width at (y = MEAS_INSET, z_ref) is 2 (a + b m)
        "W_ref": 2.0 * (a + b * m),
        "z_ref": z_ref,
        "wall_lean_deg": lean_deg,
        "wall_radius": radius,
        "W_rear_delta": 2.0 * b * (d_cubby - 2.0 * m),
        "D_cubby": d_cubby,
    }
    return values, _stats(res)


def fit_roof(samples):
    """Fit H_cubby and the roof pocket to (x, y, z) samples of the top surface."""
    if not samples:
        return {}, None
    zs = sorted(s[2] for s in samples)
    names = ("H_cubby", "roof_pocket_width", "roof_pocket_blend", "roof_pocket_rise",
             "roof_pocket_end", "roof_pocket_shape")

    class Roof(object):
        pass

    def model(v):
        r = Roof()
        for k, val in zip(names, v):
            setattr(r, k, val)
        return r

    def err(v):
        if v[1] < 0 or v[2] < 0.5 or v[3] < 0 or v[4] < P.MEAS_INSET + 1 or not 0.5 <= v[5] <= 4:
            return 1e9
        r = model(v)
        return math.sqrt(sum((P.roof_height(r, x, y) - z) ** 2 for x, y, z in samples)
                         / len(samples))

    best = None
    for width in (80.0, 140.0, 200.0):
        for shape in (1.0, 2.0):
            v, e = nelder_mead(err, [zs[len(zs) // 10], width, 10.0, zs[-1] - zs[0], 100.0,
                                     shape], (1.0, 15.0, 5.0, 2.0, 10.0, 0.3), iters=800)
            if best is None or e < best[1]:
                best = (v, e)
    v = best[0]
    res = [P.roof_height(model(v), x, y) - z for x, y, z in samples]
    return dict(zip(names, v)), _stats(res)


def corner_deviations(ref: PlacedReference, p: Params, step: float = 0.5,
                      levels: Sequence[float] = None) -> List[float]:
    """Deviation ours - reference of the half-width in the rear-corner zone, at
    levels where the reference has a back face. Positive = ours is wider."""
    spec = ref.spec
    lo, hi = spec.closed_back_levels
    levels = levels or [lo, (lo + hi) / 2.0, hi]
    depths = frange(ref.depth - spec.rear_zone, ref.depth - 0.4, step)
    d = P.derive(p)
    shift = d.y_rear - ref.depth
    out = []
    for level in levels:
        ring = layout.shelf_outline(p, d, ref.to_z(level)).ring(16)
        ours = extents_profile(ring_segments(ring, shift), depths)
        for o, r in zip(ours, ref.profile(level, depths)):
            if o and r:
                out.append((o[1] - o[0]) / 2.0 - (r[1] - r[0]) / 2.0)
    return out


def fit_rear_corner(ref: PlacedReference, base: Params):
    """Fit the two-radius rear corner (chamfer + side and back fillets) by
    minimising the worst deviation in the rear-corner zone."""
    names = ("rear_corner_length", "rear_corner_inset", "rear_corner_r_side", "rear_corner_r_back")

    def err(v):
        if not (1.0 <= v[0] <= 2.0 * ref.spec.rear_zone and 0.2 <= v[1] <= 40.0
                and 0.0 <= v[2] <= 300.0 and 0.0 <= v[3] <= 100.0):
            return 1e3
        try:
            devs = corner_deviations(ref, base.with_overrides(dict(zip(names, v))))
        except (GeometryError, P.ParamError):
            return 1e3
        return max(abs(x) for x in devs) if devs else 1e3

    # the worst-case objective has local minima: several starts, then a restart
    best = None
    for start in ((25.0, 5.0, 60.0, 12.0), (35.0, 10.0, 30.0, 5.0), (20.0, 3.0, 100.0, 15.0),
                  (30.0, 4.0, 60.0, 8.0), (15.0, 2.0, 40.0, 20.0), (45.0, 15.0, 80.0, 10.0)):
        v, e = nelder_mead(err, start, (5.0, 2.0, 15.0, 3.0), iters=400, tol=1e-5)
        if best is None or e < best[1]:
            best = (v, e)
    best = nelder_mead(err, best[0], (2.0, 1.0, 8.0, 2.0), iters=400, tol=1e-6)
    values = dict(zip(names, best[0]))
    return values, _stats(corner_deviations(ref, base.with_overrides(values)))


ENVELOPE_KEYS = ("W_ref", "z_ref", "wall_lean_deg", "wall_radius", "W_rear_delta", "D_cubby",
                 "H_cubby", "rear_corner_length", "rear_corner_inset", "rear_corner_r_side",
                 "rear_corner_r_back", "roof_pocket_width", "roof_pocket_blend",
                 "roof_pocket_rise", "roof_pocket_end", "roof_pocket_shape", "W_lip")

# settings under which our envelope is compared with the reference part itself
_ENVELOPE_ONLY = {"side_gap": 0.0, "envelope_offset": 0.0, "port_notch_width": 0.0,
                  "corner_radius_front": 0.0}


def fit_params(ref: PlacedReference, z_ref: float = None):
    """All envelope parameters fitted to the reference. Returns (values, quality)."""
    spec = ref.spec
    z_ref = z_ref if z_ref is not None else P.load_spec()["z_ref"]["value"]
    d_cubby = spec.front_recess + ref.depth + spec.rear_gap
    values, wall_stats = fit_walls(wall_samples(ref), z_ref, d_cubby)
    roof_values, roof_stats = fit_roof(roof_samples(ref))
    values.update(roof_values)
    if "H_cubby" not in values:
        values["H_cubby"] = ref.to_z(0.0)
    values["W_lip"] = float(math.ceil(ref.width + 0.5))
    base = P.load_params(dict(_ENVELOPE_ONLY, front_recess=spec.front_recess,
                              rear_gap=spec.rear_gap, **values))
    corner_values, corner_stats = fit_rear_corner(ref, base)
    values.update(corner_values)
    values = {k: round(values[k], 2) for k in ENVELOPE_KEYS if k in values}
    quality = {"walls": wall_stats, "rear_corners": corner_stats, "roof": roof_stats}
    return values, quality


# --------------------------------------------------------------------------
# comparisons
# --------------------------------------------------------------------------

def envelope_report(p: Params, ref: PlacedReference) -> dict:
    """How well the envelope in ``p`` matches the reference part's outer
    surface: side walls at every level, rear corners where it has a back face,
    roof. Deviations ours - reference (positive = our envelope is bigger)."""
    spec = ref.spec
    pe = p.with_overrides(dict(_ENVELOPE_ONLY, front_recess=spec.front_recess,
                               rear_gap=spec.rear_gap))
    walls = [P.cubby_half_width(pe, y, z) - hw for y, z, hw in wall_samples(ref)]
    roof = [P.roof_height(pe, x, y) - z for x, y, z in roof_samples(ref)]
    return {"walls": _stats(walls), "rear_corners": _stats(corner_deviations(ref, pe)),
            "roof": _stats(roof)}


def envelope_lines(report: dict) -> List[str]:
    labels = {"walls": "side walls  ", "rear_corners": "rear corners", "roof": "roof        "}
    out = []
    for key in ("walls", "rear_corners", "roof"):
        s = report.get(key)
        if s:
            out.append("%s rms %.2f mm, ours bigger by up to %.2f, smaller by up to %.2f "
                       "(%d points)" % (labels[key], s["rms"], max(s["max_out"], 0.0),
                                        max(-s["max_in"], 0.0), s["n"]))
    return out


class Comparison:
    """Signed deviations ours - reference of the outer half-width at our
    shelf's edge band. Positive = our shelf sticks out beyond the reference."""

    def __init__(self, depth_ours: float, depth_ref: float, levels):
        self.rows = []  # (zone, level_name, depth, ours, ref, dev)
        self.depth_ours = depth_ours
        self.depth_ref = depth_ref
        self.levels = levels  # [(name, our z, reference level)]

    def stats(self, zone: str, level_name: str = None) -> Optional[dict]:
        rows = [r for r in self.rows if r[0] == zone and (level_name is None or r[1] == level_name)]
        if not rows:
            return None
        s = _stats([r[5] for r in rows])
        s["max_out_at"] = max(rows, key=lambda r: r[5])[2]
        s["max_in_at"] = min(rows, key=lambda r: r[5])[2]
        return s

    def summary_lines(self) -> List[str]:
        out = ["depth: ours %.1f mm, reference %.1f mm (aligned at the rear edge)"
               % (self.depth_ours, self.depth_ref)]
        for name, z, lvl in self.levels:
            for zone in ("sides", "rear corners"):
                s = self.stats(zone, name)
                if s is None:
                    if zone == "rear corners":
                        out.append("rear corners %-12s (z %5.1f): not comparable, the reference has "
                                   "no back face at this height" % (name, z))
                    continue
                out.append("%-12s %-12s (z %5.1f): sticks out up to %+5.2f mm (depth %5.1f), "
                           "smaller by up to %5.2f mm (depth %5.1f)" % (
                               zone, name, z, max(s["max_out"], 0.0), s["max_out_at"],
                               max(-s["max_in"], 0.0), s["max_in_at"]))
        return out


def compare(p: Params, d: Derived, ref: PlacedReference, step: float = 0.5) -> Comparison:
    """Compare our shelf outline (with side_gap etc.) at the top and bottom of
    its edge band with the reference at the same heights, aligned at the rear
    edge. Rear corners only where the reference has a back face."""
    spec = ref.spec
    shift = d.y_rear - ref.depth  # our y = reference depth + shift
    # start behind our own rounded front corners (they are a styling choice)
    depths = frange(max(0.5, d.y_front - shift + p.corner_radius_front), ref.depth - 0.4, step)
    levels = [("top", d.z_top, spec.floor_level - d.z_top),
              ("band bottom", d.z_frame_bottom, spec.floor_level - d.z_frame_bottom)]
    cmp = Comparison(d.y_rear - d.y_front, ref.depth, levels)
    rear_start = ref.depth - spec.rear_zone
    lo, hi = spec.closed_back_levels
    for name, z, level in levels:
        ours = extents_profile(ring_segments(layout.shelf_outline(p, d, z).ring(32), shift), depths)
        theirs = ref.profile(level, depths)
        have = [dd for dd, pr in zip(depths, theirs) if pr]
        last = max(have) - spec.wing_end_margin if have else 0.0
        for dep, o, r in zip(depths, ours, theirs):
            if o is None or r is None:
                continue
            if dep <= min(rear_start, last):
                zone = "sides"
            elif dep > rear_start and lo <= level <= hi:
                zone = "rear corners"
            else:
                continue
            hw_o = (o[1] - o[0]) / 2.0
            hw_r = (r[1] - r[0]) / 2.0
            cmp.rows.append((zone, name, dep, hw_o, hw_r, hw_o - hw_r))
    return cmp


def write_params_file(path: str, values: dict, quality: dict, ref: PlacedReference) -> None:
    spec = ref.spec
    w, c, r = quality["walls"], quality["rear_corners"], quality["roof"]
    doc = {
        "_source": ("Fitted to the outer surface of %s by 'python tools/rav4shelf.py reference "
                    "--write-params'. The STL is not in the repo (paid); only these numbers are "
                    "derived from it. The same values are the defaults in params/default.json."
                    % spec.name),
        "_model": ("Side walls: one circular arc seen from the front (wall_radius, wall_lean_deg at "
                   "z_ref) moved along the depth with a linear taper (W_rear_delta). Rear corners: "
                   "chamfer + two fillets. Roof: flat at H_cubby with a pocket in the middle that "
                   "rises toward the front."),
        "_assumptions": ("Not in the file, assumed: its wing tips reach the Qi pad, its front is "
                         "%.0f mm behind the lip, its back %.0f mm from the rear wall. The car's "
                         "walls are outside this envelope by Vela3D's foam allowance (unknown): "
                         "set envelope_offset from the fit coupon." % (spec.front_recess,
                                                                       spec.rear_gap)),
        "_fit": ("side walls rms %.2f / max %.2f mm (%d points), rear corners max %.2f mm, roof "
                 "rms %.2f / max %.2f mm" % (w["rms"], w["max_abs"], w["n"], c["max_abs"],
                                             r["rms"], r["max_abs"])),
    }
    doc.update(values)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(doc, indent=2) + "\n")
