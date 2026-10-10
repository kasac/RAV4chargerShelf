"""Pure-Python triangle meshes: the test prints, the cubby envelope and the
roof plate. No Rhino needed, so parts can be printed before the Rhino path is
set up, and CI can check they are watertight.

The Rhino path (geometry.py) builds the coupon and gauge as B-reps.
"""
from __future__ import annotations

import bisect
import math
from typing import Callable, Dict, List, Sequence, Tuple

from . import layout
from .geom2d import GeometryError, signed_area
from .layout import coupon_profile, profile_section, shelf_outline
from .params import Derived, Params

Vec3 = Tuple[float, float, float]


class Mesh:
    """Indexed triangle mesh. Faces are counter-clockwise seen from outside."""

    def __init__(self, vertices: List[Vec3], faces: List[Tuple[int, int, int]]):
        self.vertices = vertices
        self.faces = faces

    def transformed(self, fn: Callable[[Vec3], Vec3]) -> "Mesh":
        return Mesh([fn(v) for v in self.vertices], list(self.faces))

    def flipped(self) -> "Mesh":
        return Mesh(list(self.vertices), [(a, c, b) for a, b, c in self.faces])

    def bbox(self) -> Tuple[Vec3, Vec3]:
        xs, ys, zs = zip(*self.vertices)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def signed_volume(self) -> float:
        vol = 0.0
        v = self.vertices
        for a, b, c in self.faces:
            ax, ay, az = v[a]
            bx, by, bz = v[b]
            cx, cy, cz = v[c]
            vol += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
        return vol / 6.0

    def triangles(self):
        v = self.vertices
        for a, b, c in self.faces:
            yield v[a], v[b], v[c]


def sweep_rings(rings: Sequence[Sequence[Vec3]]) -> Mesh:
    """Stitch K closed rings of M points each into a closed torus-like mesh.

    Ring k is joined to ring k+1 and the last ring back to the first, so the
    rings must describe a closed cross-section loop. The result is oriented
    so that its volume is positive.
    """
    k_count = len(rings)
    m = len(rings[0])
    if k_count < 3 or any(len(r) != m for r in rings):
        raise ValueError("need >= 3 rings with the same number of points")
    vertices = [pt for ring in rings for pt in ring]
    faces = []
    for k in range(k_count):
        k2 = (k + 1) % k_count
        for j in range(m):
            j2 = (j + 1) % m
            a, b = k * m + j, k * m + j2
            c, e = k2 * m + j2, k2 * m + j
            faces.append((a, b, c))
            faces.append((a, c, e))
    mesh = Mesh(vertices, faces)
    if mesh.signed_volume() < 0:
        mesh = mesh.flipped()
    return mesh


def check_closed(mesh: Mesh) -> List[str]:
    """Problems that would make a slicer complain; empty list = watertight.

    Every edge must be used exactly twice, once in each direction.
    """
    problems = []
    directed: Dict[Tuple[int, int], int] = {}
    for f in mesh.faces:
        if len(set(f)) < 3:
            problems.append("degenerate face %r" % (f,))
        for i in range(3):
            e = (f[i], f[(i + 1) % 3])
            directed[e] = directed.get(e, 0) + 1
    for (a, b), n in directed.items():
        if n != 1:
            problems.append("edge %d-%d used %d times in the same direction" % (a, b, n))
        if directed.get((b, a), 0) != 1:
            problems.append("edge %d-%d has no opposite partner" % (a, b))
        if len(problems) > 20:
            problems.append("...")
            break
    if not problems and mesh.signed_volume() <= 0:
        problems.append("mesh is inside out (negative volume)")
    return problems


# --------------------------------------------------------------------------
# parts
# --------------------------------------------------------------------------

def coupon_mesh(p: Params, d: Derived) -> Mesh:
    """Fit coupon in the car frame (plate on top at shelf height, rim down)."""
    rings = []
    for inset, z in coupon_profile(p, d):
        ring2d = shelf_outline(p, d, z, inset).ring(p.arc_segments_per_90)
        rings.append([(x, y, z) for x, y in ring2d])
    return sweep_rings(rings)


def profile_gauge_mesh(p: Params, d: Derived) -> Mesh:
    """Profile gauge, lying flat as printed: a frame gauge_band wide along the
    cubby cross-section at depth gauge_y, gauge_clearance smaller all round."""
    a = p.gauge_clearance
    b = p.gauge_clearance + p.gauge_band
    # a chamfer shorter than ~0.7 x the band would collapse when the frame's
    # inner edge is offset from it, so small chamfers are raised to that
    corner = max(p.gauge_corner, 0.7 * b) if p.gauge_corner > 0 else 0.0
    section = profile_section(p, p.gauge_y, gap=max(6.0, 1.3 * b), corner=corner)
    t = p.gauge_thickness
    rings = []
    for inset, z in ((a, 0.0), (a, t), (b, t), (b, 0.0)):
        try:
            ring2d = section.offset(inset).ring() if inset else section.ring()
        except GeometryError:
            raise GeometryError(
                "profile gauge: gauge_band + gauge_clearance (%.1f mm) is wider than the "
                "tightest curve of the cross-section (the edge of the roof pocket): reduce "
                "gauge_band or gauge_clearance" % b)
        rings.append([(x, y, z) for x, y in ring2d])
    mesh = sweep_rings(rings)
    (x0, y0, _), (x1, y1, _) = mesh.bbox()
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    return mesh.transformed(lambda v: (v[0] - cx, v[1] - cy, v[2]))


def envelope_mesh(p: Params, d: Derived) -> Mesh:
    """The cubby envelope as a closed solid, floor to flat roof (the roof
    pocket and bulge are left out). A reference body to design against."""
    from .layout import cubby_outline, envelope_levels

    rings = [[(x, y, z) for x, y in cubby_outline(p, z).ring(p.arc_segments_per_90)]
             for z in envelope_levels(p)]
    m = len(rings[0])
    vertices = [v for ring in rings for v in ring]
    faces = []
    for k in range(len(rings) - 1):
        for j in range(m):
            a, b = k * m + j, k * m + (j + 1) % m
            faces += [(a, b, b + m), (a, b + m, a + m)]
    # caps: the outline is convex, so a fan around its centre closes it
    for ring, k, flip in ((rings[0], 0, True), (rings[-1], len(rings) - 1, False)):
        cx = sum(v[0] for v in ring) / m
        cy = sum(v[1] for v in ring) / m
        c = len(vertices)
        vertices.append((cx, cy, ring[0][2]))
        for j in range(m):
            a, b = k * m + j, k * m + (j + 1) % m
            faces.append((c, b, a) if flip else (c, a, b))
    mesh = Mesh(vertices, faces)
    return mesh.flipped() if mesh.signed_volume() < 0 else mesh


def plate_mesh(outer, holes, top_z: Callable[[float], float], thickness: float,
               extra_y: Sequence[float] = ()) -> Mesh:
    """Closed mesh of a plate: the plan region inside ``outer`` minus ``holes``
    (rings inside it that touch neither each other nor the outline), its top at
    top_z(y) and its bottom ``thickness`` lower. top_z may change along y but
    must be constant across every hole, whose walls are vertical.

    The plan is cut into slabs at the y of every vertex and of extra_y; inside
    a slab the region is a row of trapezoids. Each slab line carries one set of
    points shared by the trapezoids on both sides and by the walls, so the mesh
    has no T-junctions.
    """
    def snap(ring, ccw):
        ring = [(float(x), round(float(y), 9)) for x, y in ring]
        return ring if (signed_area(ring) > 0) == ccw else ring[::-1]

    loops = [snap(outer, True)] + [snap(h, False) for h in holes]
    y_lo = min(y for _, y in loops[0])
    y_hi = max(y for _, y in loops[0])
    ys = sorted({y for loop in loops for _, y in loop}
                | {round(y, 9) for y in extra_y if y_lo < y < y_hi})
    level = {y: k for k, y in enumerate(ys)}
    edges = [(loop[i], loop[(i + 1) % len(loop)]) for loop in loops for i in range(len(loop))]

    def x_at(e, k):
        (x0, y0), (x1, y1) = e
        y = ys[k]
        if y == y0:
            return x0
        if y == y1:
            return x1
        return x0 + (y - y0) * (x1 - x0) / (y1 - y0)

    slabs = [[] for _ in ys]
    for e in edges:
        (_, y0), (_, y1) = e
        if y0 != y1:
            for k in range(level[min(y0, y1)], level[max(y0, y1)]):
                slabs[k].append(e)

    line_x = [[] for _ in ys]
    for loop in loops:
        for x, y in loop:
            line_x[level[y]].append(x)
    traps = []
    for k, crossing in enumerate(slabs):
        if not crossing:
            continue
        spans = sorted(((x_at(e, k), x_at(e, k + 1)) for e in crossing),
                       key=lambda bt: bt[0] + bt[1])
        if len(spans) % 2:
            raise GeometryError("plate outline is not closed at y %.3f" % ys[k])
        for i in range(0, len(spans), 2):
            (bl, tl), (br, tr) = spans[i], spans[i + 1]
            traps.append((k, bl, br, tl, tr))
            line_x[k] += [bl, br]
            line_x[k + 1] += [tl, tr]
    lines = []
    for xs in line_x:
        merged = []
        for x in sorted(xs):
            if not merged or x - merged[-1] > 1e-7:
                merged.append(x)
        lines.append(merged)

    vertices: List[Vec3] = []
    ids: Dict[Tuple[int, int, int], int] = {}

    def vid(k, x, layer):  # layer 1 = top, 0 = bottom
        xs = lines[k]
        i = bisect.bisect_left(xs, x)
        if i == len(xs) or (i > 0 and x - xs[i - 1] < xs[i] - x):
            i -= 1
        key = (k, i, layer)
        if key not in ids:
            z = top_z(ys[k]) - (0.0 if layer else thickness)
            ids[key] = len(vertices)
            vertices.append((xs[i], ys[k], z))
        return ids[key]

    faces = []

    def tri(a, b, c):  # a, b, c = (k, x), counter-clockwise from above
        faces.append((vid(*a, 1), vid(*b, 1), vid(*c, 1)))
        faces.append((vid(*a, 0), vid(*c, 0), vid(*b, 0)))

    def between(k, x0, x1):
        return [x for x in lines[k] if x0 - 1e-7 <= x <= x1 + 1e-7]

    for k, bl, br, tl, tr in traps:  # ladder through each trapezoid
        bot, top = between(k, bl, br), between(k + 1, tl, tr)
        i = j = 0
        while i < len(bot) - 1 or j < len(top) - 1:
            ub = (bot[i + 1] - bl) / (br - bl) if i < len(bot) - 1 and br > bl else 2.0
            ut = (top[j + 1] - tl) / (tr - tl) if j < len(top) - 1 and tr > tl else 2.0
            if j == len(top) - 1 or (i < len(bot) - 1 and ub <= ut):
                tri((k, bot[i]), (k, bot[i + 1]), (k + 1, top[j]))
                i += 1
            else:
                tri((k, bot[i]), (k + 1, top[j + 1]), (k + 1, top[j]))
                j += 1

    for e in edges:  # walls: outline counter-clockwise, holes clockwise
        (x0, y0), (x1, y1) = e
        k0, k1 = level[y0], level[y1]
        if k0 == k1:
            pts = [(k0, x) for x in between(k0, min(x0, x1), max(x0, x1))]
            if x1 < x0:
                pts.reverse()
        else:
            step = 1 if k1 > k0 else -1
            pts = [(k, x_at(e, k)) for k in range(k0, k1 + step, step)]
        for (ka, xa), (kb, xb) in zip(pts, pts[1:]):
            ba, bb, ta, tb = vid(ka, xa, 0), vid(kb, xb, 0), vid(ka, xa, 1), vid(kb, xb, 1)
            faces += [(ba, bb, tb), (ba, tb, ta)]
    return Mesh(vertices, faces)


def roof_plate_mesh(p: Params, d: Derived) -> Mesh:
    """The roof plate in the car frame: front strip, gradual depression,
    perforated flat part."""
    outline = layout.roof_plate_outline(p, d)
    holes = layout.roof_plate_holes(p, d, outline)
    extra = []
    if p.roof_depression_depth > 0:
        a = d.y_front + p.roof_depression_start
        n = max(4, int(math.ceil(p.roof_depression_ramp)))  # about 1 mm steps
        extra = [a + p.roof_depression_ramp * i / n for i in range(n + 1)]
    return plate_mesh(outline, holes, lambda y: layout.roof_plate_top(p, d, y),
                      p.roof_thickness, extra)


def standing_print_orientation(mesh: Mesh) -> Mesh:
    """Stand a part on its rear edge, front up: (x, y, z) -> (x, z, -y), a
    rotation, then centred on x/y = 0 with z_min = 0."""
    rotated = mesh.transformed(lambda v: (v[0], v[2], -v[1]))
    (x0, y0, z0), (x1, y1, _) = rotated.bbox()
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    return rotated.transformed(lambda v: (v[0] - cx, v[1] - cy, v[2] - z0))


def to_print_orientation(mesh: Mesh) -> Mesh:
    """Rotate 180 deg about x (deck/plate down on the bed), then centre it on
    x/y = 0 with z_min = 0. This is a rotation, not a mirror."""
    rotated = mesh.transformed(lambda v: (v[0], -v[1], -v[2]))
    (x0, y0, z0), (x1, y1, _) = rotated.bbox()
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    return rotated.transformed(lambda v: (v[0] - cx, v[1] - cy, v[2] - z0))


def mesh_volume_cm3(mesh: Mesh) -> float:
    return mesh.signed_volume() / 1000.0


def petg_grams(mesh: Mesh, density: float = 1.27) -> float:
    return mesh_volume_cm3(mesh) * density
