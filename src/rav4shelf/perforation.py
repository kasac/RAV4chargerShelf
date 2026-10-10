"""Doubly periodic perforation for flat parts that print standing on their rear
edge: the plate is vertical in the printer and the car's front (-y) is up.
Pure Python, no Rhino imports.

Every hole's upper edges (toward the lip) rise at most ``tip_angle`` from the
vertical, so the holes print without support or bridging:

    diamond   rhombi on a rhombic lattice: uniform bars, all edges at the tip
              angle; the most open area for a given bar width (default)
    teardrop  circles with a pointed cap toward the lip

Holes sit on a centred rectangular lattice (staggered rows), symmetric about
x = 0, and only where they fit completely inside the region with a margin.
Plan coordinates as everywhere: x right, y from the lip toward the rear.
"""
from __future__ import annotations

import math
from typing import List, Sequence

from .geom2d import GeometryError, Point, point_in_polygon, signed_area

STYLES = ("diamond", "teardrop", "none")


class Pattern:
    """A hole shape and its lattice. ``hole`` is CCW around (0, 0)."""

    def __init__(self, style, width, tip_angle, hole, pitch, row_step):
        self.style = style
        self.width = width
        self.tip_angle = tip_angle          # degrees from vertical (print up)
        self.hole = hole
        self.pitch = pitch                  # centre to centre within a row
        self.row_step = row_step            # row to row; odd rows shift pitch / 2
        self.hole_area = signed_area(hole)
        self.open_fraction = self.hole_area / (pitch * row_step)
        ys = [y for _, y in hole]
        self.front = -min(ys)               # extent toward the lip from the centre
        self.back = max(ys)
        self.bar = min_gap(self)            # narrowest bar between neighbours

    def __repr__(self):
        return ("Pattern(%s, width %.1f, pitch %.2f, rows %.2f, open %.2f, bar %.2f)"
                % (self.style, self.width, self.pitch, self.row_step, self.open_fraction,
                   self.bar))


# --------------------------------------------------------------------------
# hole shapes
# --------------------------------------------------------------------------

def diamond(width: float, tip_angle: float) -> List[Point]:
    """Rhombus ``width`` wide whose four edges rise at ``tip_angle`` from the vertical."""
    h = width / math.tan(math.radians(tip_angle))
    return [(width / 2.0, 0.0), (0.0, h / 2.0), (-width / 2.0, 0.0), (0.0, -h / 2.0)]


def teardrop(width: float, tip_angle: float, seg_per_90: int = 8) -> List[Point]:
    """Circle of diameter ``width`` with a cap toward the lip (-y) whose edges
    rise at ``tip_angle`` from the vertical."""
    r = width / 2.0
    a = math.radians(tip_angle)
    a0, a1 = -a, math.pi + a                       # arc from one tangent point round the back
    n = max(4, int(math.ceil((a1 - a0) / (math.pi / 2.0) * seg_per_90)))
    n += n % 2                                     # a vertex on the rear-most point
    pts = [(r * math.cos(a0 + (a1 - a0) * i / n), r * math.sin(a0 + (a1 - a0) * i / n))
           for i in range(n + 1)]
    return pts + [(0.0, -r / math.sin(a))]


# --------------------------------------------------------------------------
# lattice
# --------------------------------------------------------------------------

def pattern(style: str, width: float, open_fraction: float, tip_angle: float = 45.0,
            seg_per_90: int = 8) -> Pattern:
    """Hole shape plus the lattice that removes ``open_fraction`` of the area."""
    if style not in STYLES or style == "none":
        raise GeometryError("no perforation pattern for style %r" % style)
    if not 0.0 < open_fraction < 1.0:
        raise GeometryError("open fraction must be between 0 and 1, got %r" % open_fraction)
    if not 5.0 <= tip_angle <= 60.0:
        raise GeometryError("tip angle %.1f deg is outside 5..60" % tip_angle)
    if style == "diamond":
        hole = diamond(width, tip_angle)
        # the lattice cells are the hole scaled up by 1/sqrt(open): they tile the plane,
        # so the bars between holes have one width everywhere
        k = math.sqrt(open_fraction)
        h = 2.0 * max(y for _, y in hole)
        return Pattern(style, width, tip_angle, hole, width / k, h / k / 2.0)
    hole = teardrop(width, tip_angle, seg_per_90)
    area = signed_area(hole)
    def lattice(ratio):  # row step / pitch at the requested open fraction
        pitch = math.sqrt(area / (open_fraction * ratio))
        return Pattern(style, width, tip_angle, hole, pitch, ratio * pitch)

    # pick the ratio that gives the widest narrowest bar: coarse scan, then refine
    best = max((lattice(0.55 + 0.1 * i) for i in range(13)), key=lambda q: q.bar)
    r0 = best.row_step / best.pitch
    best = max([best] + [lattice(r0 + 0.01 * i) for i in range(-9, 10) if i],
               key=lambda q: q.bar)
    if best.bar <= 0.0:
        raise GeometryError("teardrops of %.1f mm cannot remove %.0f %% of the area: lower "
                            "perforation_open_fraction (or use diamonds)"
                            % (width, 100.0 * open_fraction))
    return best


def neighbours(pat: Pattern):
    """Offsets of the six nearest lattice neighbours."""
    p, v = pat.pitch, pat.row_step
    return [(p, 0.0), (-p, 0.0), (p / 2.0, v), (-p / 2.0, v), (p / 2.0, -v), (-p / 2.0, -v)]


def min_gap(pat: Pattern) -> float:
    """Narrowest bar between a hole and its neighbours (negative if they overlap).
    The holes are mirror-symmetric in x and the lattice is point-symmetric, so
    two neighbours stand for all six."""
    return min(_convex_gap(pat.hole, [(x + dx, y + dy) for x, y in pat.hole])
               for dx, dy in ((pat.pitch, 0.0), (pat.pitch / 2.0, pat.row_step)))


def _convex_gap(a: Sequence[Point], b: Sequence[Point]) -> float:
    """Distance between two convex polygons; negative when they overlap
    (minus the depth of the shallowest separating direction)."""
    best = None
    for poly in (a, b):
        n = len(poly)
        for i in range(n):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
            ex, ey = x1 - x0, y1 - y0
            le = math.hypot(ex, ey)
            if le < 1e-12:
                continue
            nx, ny = ey / le, -ex / le  # outward normal of a CCW polygon
            amax = max(nx * x + ny * y for x, y in a)
            amin = min(nx * x + ny * y for x, y in a)
            bmax = max(nx * x + ny * y for x, y in b)
            bmin = min(nx * x + ny * y for x, y in b)
            sep = max(bmin - amax, amin - bmax)
            if best is None or sep > best:
                best = sep
    if best is not None and best <= 0.0:
        return best
    # separated: the true distance is between a vertex and an edge
    return min(min(_point_segment(pt, q[i], q[(i + 1) % len(q)]) for pt in p for i in range(len(q)))
               for p, q in ((a, b), (b, a)))


def _point_segment(pt: Point, a: Point, b: Point) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    den = dx * dx + dy * dy
    t = 0.0 if den < 1e-24 else max(0.0, min(1.0, ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / den))
    return math.hypot(pt[0] - ax - t * dx, pt[1] - ay - t * dy)


# --------------------------------------------------------------------------
# placing holes
# --------------------------------------------------------------------------

def holes_in_region(region: Sequence[Point], pat: Pattern, margin: float,
                    y_min: float = None) -> List[List[Point]]:
    """Holes of ``pat`` that fit inside ``region`` (a convex CCW ring) at
    least ``margin`` from its edges, and no closer to the lip than y_min.

    The rows are centred on the usable depth and each row on x = 0, so the
    pattern is symmetric left to right.
    """
    lines = _inward_lines(region)
    ys = [y for _, y in region]
    lo = max(min(ys), y_min if y_min is not None else -1e18) + margin + pat.front
    hi = max(ys) - margin - pat.back
    if hi < lo:
        return []
    rows = int(math.floor((hi - lo) / pat.row_step + 1e-9)) + 1
    start = lo + ((hi - lo) - (rows - 1) * pat.row_step) / 2.0
    reach = max(math.hypot(x, y) for x, y in pat.hole)
    xmax = max(abs(x) for x, _ in region)
    i_max = int(math.ceil(xmax / pat.pitch)) + 1
    holes = []
    for j in range(rows):
        cy = start + j * pat.row_step
        shift = (j % 2) * pat.pitch / 2.0
        for i in range(-i_max, i_max + 1):
            cx = i * pat.pitch + shift
            if min(nx * cx + ny * cy - c for nx, ny, c in lines) < margin:
                continue  # the centre itself is too close
            if min(nx * cx + ny * cy - c for nx, ny, c in lines) >= margin + reach:
                holes.append([(cx + x, cy + y) for x, y in pat.hole])
                continue  # clearly inside
            hole = [(cx + x, cy + y) for x, y in pat.hole]
            if all(nx * x + ny * y - c >= margin for x, y in hole for nx, ny, c in lines):
                holes.append(hole)
    return holes


def _inward_lines(region):
    """(nx, ny, c) per edge of a convex CCW ring: n . p - c = distance inside."""
    n = len(region)
    if n < 3 or signed_area(region) <= 0:
        raise GeometryError("the perforated region must be a counter-clockwise polygon")
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = region[i], region[(i + 1) % n]
        le = math.hypot(x1 - x0, y1 - y0)
        if le < 1e-9:
            continue
        nx, ny = -(y1 - y0) / le, (x1 - x0) / le  # left normal = inward for CCW
        lines.append((nx, ny, nx * x0 + ny * y0))
    for i in range(n):  # convex: every vertex is inside every edge's half-plane
        if min(nx * region[i][0] + ny * region[i][1] - c for nx, ny, c in lines) < -1e-6:
            raise GeometryError("the perforated region must be convex")
    return lines


def open_share(holes, cx: float, cy: float, r: float, n: int = 24) -> float:
    """Share of the disc (cx, cy, r) that lies in the holes (sampled on a grid)."""
    near = [h for h in holes
            if min(x for x, _ in h) < cx + r and max(x for x, _ in h) > cx - r
            and min(y for _, y in h) < cy + r and max(y for _, y in h) > cy - r]
    inside = total = 0
    for i in range(n):
        for j in range(n):
            x = cx - r + (i + 0.5) * 2.0 * r / n
            y = cy - r + (j + 0.5) * 2.0 * r / n
            if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                continue
            total += 1
            if any(point_in_polygon((x, y), h) for h in near):
                inside += 1
    return inside / total if total else 0.0
