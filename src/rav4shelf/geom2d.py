"""Pure-Python 2D helpers: polygons with filleted corners, inward offsets and
tessellation. No Rhino imports; unit-tested with pytest.

An ``Outline`` is a closed counter-clockwise polygon with an optional fillet
radius per vertex. Both the RhinoCommon layer (true lines and arcs) and the
pure-Python mesher (tessellated points) are built from the same ``Outline``,
so the two paths produce the same shape.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

Point = Tuple[float, float]

EPS = 1e-9

# A corner that is rounded in the base outline stays rounded (at least this
# radius) after any offset. That keeps the number of segments constant, which
# the mesher and Rhino lofts rely on.
MIN_FILLET = 0.5


class GeometryError(ValueError):
    """The parameters describe an outline that cannot be built."""


# --------------------------------------------------------------------------
# vector helpers
# --------------------------------------------------------------------------

def add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1])


def sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def mul(a: Point, s: float) -> Point:
    return (a[0] * s, a[1] * s)


def dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def length(a: Point) -> float:
    return math.hypot(a[0], a[1])


def normalize(a: Point) -> Point:
    n = length(a)
    if n < EPS:
        raise GeometryError("zero-length vector")
    return (a[0] / n, a[1] / n)


def left_normal(d: Point) -> Point:
    """Normal pointing to the left of direction d (= inward for a CCW polygon)."""
    return (-d[1], d[0])


def line_intersection(p: Point, d: Point, q: Point, e: Point) -> Point:
    """Intersection of the lines p + t*d and q + s*e."""
    den = cross(d, e)
    if abs(den) < EPS:
        raise GeometryError("parallel lines do not intersect")
    t = cross(sub(q, p), e) / den
    return add(p, mul(d, t))


def signed_area(pts: Sequence[Point]) -> float:
    s = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return 0.5 * s


def _segments_cross(a: Point, b: Point, c: Point, d: Point) -> bool:
    """True if segment ab properly crosses or touches segment cd."""
    d1 = cross(sub(b, a), sub(c, a))
    d2 = cross(sub(b, a), sub(d, a))
    d3 = cross(sub(d, c), sub(a, c))
    d4 = cross(sub(d, c), sub(b, c))
    if ((d1 > EPS and d2 < -EPS) or (d1 < -EPS and d2 > EPS)) and (
        (d3 > EPS and d4 < -EPS) or (d3 < -EPS and d4 > EPS)
    ):
        return True
    return False


def is_simple(ring: Sequence[Point]) -> bool:
    """True if the closed ring has no self-intersections (O(n^2), n is small)."""
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue  # adjacent through the closing edge
            c, d = ring[j], ring[(j + 1) % n]
            if _segments_cross(a, b, c, d):
                return False
    return True


def point_in_polygon(pt: Point, ring: Sequence[Point]) -> bool:
    x, y = pt
    inside = False
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xc = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xc:
                inside = not inside
    return inside


# --------------------------------------------------------------------------
# segments
# --------------------------------------------------------------------------

class Segment:
    """A line (a -> b) or a circular arc (a -> b around center).

    ``sweep`` is the signed arc angle in radians (+ = counter-clockwise).
    """

    __slots__ = ("kind", "a", "b", "center", "radius", "sweep")

    def __init__(self, kind, a, b, center=None, radius=0.0, sweep=0.0):
        self.kind = kind
        self.a = a
        self.b = b
        self.center = center
        self.radius = radius
        self.sweep = sweep

    def point_at(self, t: float) -> Point:
        """Point at normalised parameter t in [0, 1]."""
        if self.kind == "line":
            return add(self.a, mul(sub(self.b, self.a), t))
        ang0 = math.atan2(self.a[1] - self.center[1], self.a[0] - self.center[0])
        ang = ang0 + self.sweep * t
        return (
            self.center[0] + self.radius * math.cos(ang),
            self.center[1] + self.radius * math.sin(ang),
        )

    def mid(self) -> Point:
        return self.point_at(0.5)

    def length(self) -> float:
        if self.kind == "line":
            return length(sub(self.b, self.a))
        return abs(self.sweep) * self.radius

    def __repr__(self):
        if self.kind == "line":
            return "Line(%r -> %r)" % (self.a, self.b)
        return "Arc(%r -> %r, r=%.3f, sweep=%.1f deg)" % (
            self.a, self.b, self.radius, math.degrees(self.sweep))


class _Fillet:
    __slots__ = ("t", "a", "b", "center", "radius", "sweep")

    def __init__(self, t, a, b, center, radius, sweep):
        self.t = t
        self.a = a
        self.b = b
        self.center = center
        self.radius = radius
        self.sweep = sweep


def arc_steps(sweep: float, seg_per_90: int) -> int:
    """Number of straight pieces used to tessellate an arc of this sweep.

    Depends only on the sweep angle (not the radius), so offset copies of an
    outline tessellate to the same point count. The small epsilon stops float
    noise at exact multiples of 90 deg from changing the count.
    """
    x = abs(sweep) / (math.pi / 2.0) * seg_per_90
    return max(1, int(math.ceil(x - 1e-6)))


# --------------------------------------------------------------------------
# outline
# --------------------------------------------------------------------------

class Outline:
    """Closed counter-clockwise polygon with an optional fillet per vertex.

    verts[i]  : sharp corner point i
    radii[i]  : fillet radius at vertex i (0 = sharp)
    names[i]  : label of edge i (vertex i -> vertex i+1), used in errors
    """

    def __init__(self, verts, radii=None, names=None):
        self.verts = [(float(x), float(y)) for x, y in verts]
        n = len(self.verts)
        if n < 3:
            raise GeometryError("an outline needs at least 3 vertices")
        self.radii = [float(r) for r in (radii if radii is not None else [0.0] * n)]
        self.names = list(names) if names is not None else ["edge %d" % i for i in range(n)]
        if len(self.radii) != n or len(self.names) != n:
            raise GeometryError("verts, radii and names must have the same length")
        if any(r < 0 for r in self.radii):
            raise GeometryError("fillet radii must be >= 0")
        for i in range(n):
            if length(sub(self.verts[(i + 1) % n], self.verts[i])) < 1e-6:
                raise GeometryError("edge '%s' has zero length" % self.names[i])
        if signed_area(self.verts) <= 0:
            raise GeometryError("outline must be counter-clockwise with positive area")

    # -- topology ---------------------------------------------------------

    def __len__(self):
        return len(self.verts)

    def edge_dir(self, i: int) -> Point:
        n = len(self.verts)
        return normalize(sub(self.verts[(i + 1) % n], self.verts[i % n]))

    def edge_length(self, i: int) -> float:
        n = len(self.verts)
        return length(sub(self.verts[(i + 1) % n], self.verts[i % n]))

    def is_convex(self, i: int) -> bool:
        """True if the polygon turns left (inward corner < 180 deg) at vertex i."""
        return cross(self.edge_dir(i - 1), self.edge_dir(i)) > 0

    # -- offset -----------------------------------------------------------

    def offset(self, dist: float) -> "Outline":
        """Uniform offset; dist > 0 moves every edge inward (into the material).

        Fillets stay concentric: convex corners shrink (r - dist), reflex
        corners grow (r + dist). A rounded corner never drops below MIN_FILLET.
        """
        if abs(dist) < EPS:
            return Outline(self.verts, self.radii, self.names)
        n = len(self.verts)
        lines = []
        for i in range(n):
            d = self.edge_dir(i)
            p = add(self.verts[i], mul(left_normal(d), dist))
            lines.append((p, d))
        new_verts = []
        for i in range(n):
            p0, d0 = lines[i - 1]
            p1, d1 = lines[i]
            new_verts.append(line_intersection(p0, d0, p1, d1))
        for i in range(n):
            new_d = sub(new_verts[(i + 1) % n], new_verts[i])
            if dot(new_d, self.edge_dir(i)) <= 1e-6:
                raise GeometryError(
                    "an inset of %.2f mm collapses edge '%s'" % (dist, self.names[i]))
        new_radii = []
        for i, r in enumerate(self.radii):
            if r <= 0:
                new_radii.append(0.0)
                continue
            r2 = r - dist if self.is_convex(i) else r + dist
            new_radii.append(max(r2, MIN_FILLET))
        return Outline(new_verts, new_radii, self.names)

    # -- fillets ----------------------------------------------------------

    def _fillet(self, i: int) -> Optional[_Fillet]:
        r = self.radii[i]
        if r <= 0:
            return None
        n = len(self.verts)
        v = self.verts[i]
        u = normalize(sub(self.verts[i - 1], v))       # toward previous vertex
        w = normalize(sub(self.verts[(i + 1) % n], v))  # toward next vertex
        theta = math.acos(max(-1.0, min(1.0, dot(u, w))))  # angle between edges
        if theta > math.pi - 1e-6:
            return None  # straight through, nothing to round
        half = theta / 2.0
        t = r / math.tan(half)
        a = add(v, mul(u, t))
        b = add(v, mul(w, t))
        center = add(v, mul(normalize(add(u, w)), r / math.sin(half)))
        turn = math.pi - theta
        sweep = turn if self.is_convex(i) else -turn
        return _Fillet(t, a, b, center, r, sweep)

    def fillets(self) -> List[Optional[_Fillet]]:
        fl = [self._fillet(i) for i in range(len(self.verts))]
        n = len(self.verts)
        for i in range(n):
            t0 = fl[i].t if fl[i] else 0.0
            t1 = fl[(i + 1) % n].t if fl[(i + 1) % n] else 0.0
            if t0 + t1 > self.edge_length(i) + 1e-7:
                raise GeometryError(
                    "edge '%s' (%.1f mm) is too short for its corner radii "
                    "(needs %.1f mm)" % (self.names[i], self.edge_length(i), t0 + t1))
        return fl

    def segments(self) -> List[Segment]:
        """Lines and arcs in order, starting with the corner at vertex 0."""
        fl = self.fillets()
        n = len(self.verts)
        segs = []
        for i in range(n):
            f = fl[i]
            if f is not None:
                segs.append(Segment("arc", f.a, f.b, f.center, f.radius, f.sweep))
            start = f.b if f is not None else self.verts[i]
            fn = fl[(i + 1) % n]
            end = fn.a if fn is not None else self.verts[(i + 1) % n]
            if length(sub(end, start)) > 1e-9:
                segs.append(Segment("line", start, end))
        return segs

    def ring(self, seg_per_90: int = 8) -> List[Point]:
        """Tessellated closed ring (last point != first point).

        Every vertex contributes 1 point (sharp) or steps+1 points (rounded),
        independent of the offset, so offset copies have equal point counts.
        """
        pts = []
        for i, f in enumerate(self.fillets()):
            if f is None:
                pts.append(self.verts[i])
                continue
            steps = arc_steps(f.sweep, seg_per_90)
            seg = Segment("arc", f.a, f.b, f.center, f.radius, f.sweep)
            pts.append(f.a)
            for k in range(1, steps):
                pts.append(seg.point_at(k / float(steps)))
            pts.append(f.b)
        return pts

    def area(self, seg_per_90: int = 16) -> float:
        return signed_area(self.ring(seg_per_90))

    def bbox(self, seg_per_90: int = 16):
        pts = self.ring(seg_per_90)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))
