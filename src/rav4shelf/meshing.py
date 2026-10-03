"""Pure-Python triangle meshes for parts that are a profile swept around an
outline (currently: the fit coupon). No Rhino needed, so the coupon can be
printed before the Rhino path is set up, and CI can check it is watertight.

The Rhino path (geometry.py) builds the same shape as a B-rep.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Sequence, Tuple

from .geom2d import GeometryError
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
