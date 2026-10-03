"""RhinoCommon B-rep builders. Runs only inside Rhino 8 (CPython 3.9).

All dimensions and outlines come from the pure-Python layer (params, layout),
which is unit-tested on CI. This module only turns outlines into curves and
curves into solids, so it stays short and easy to debug in Rhino.

NOT YET RUN IN RHINO: see the first-run checklist in README.md.
"""
from __future__ import annotations

import math

import Rhino.Geometry as rg
from System.Collections.Generic import List as NetList

from . import layout
from .geom2d import Outline
from .params import Derived, Params

DEFAULT_TOL = 0.01  # mm; used when no document tolerance is given
CUTTER_OVERSHOOT = 1.0  # mm; boolean cutters poke through to avoid coplanar faces


class BuildError(RuntimeError):
    """A Rhino geometry operation failed."""


def _net_list(net_type, items):
    """Python list -> .NET List<T> (pythonnet does not always convert lists)."""
    lst = NetList[net_type]()
    for item in items:
        lst.Add(item)
    return lst


# --------------------------------------------------------------------------
# curves and simple solids
# --------------------------------------------------------------------------

def outline_curve(outline: Outline, z: float) -> rg.PolyCurve:
    """Closed planar PolyCurve (true lines and arcs) at height z."""
    pc = rg.PolyCurve()
    for seg in outline.segments():
        a = rg.Point3d(seg.a[0], seg.a[1], z)
        b = rg.Point3d(seg.b[0], seg.b[1], z)
        if seg.kind == "line":
            crv = rg.LineCurve(a, b)
        else:
            m = seg.mid()
            crv = rg.ArcCurve(rg.Arc(a, rg.Point3d(m[0], m[1], z), b))
        if not pc.Append(crv):
            raise BuildError("could not append %r to the outline curve" % (seg,))
    if not pc.IsClosed:
        pc.MakeClosed(DEFAULT_TOL)
    if not pc.IsClosed:
        raise BuildError("outline curve at z=%.2f is not closed" % z)
    return pc


def _outward(brep: rg.Brep) -> rg.Brep:
    if brep.SolidOrientation == rg.BrepSolidOrientation.Inward:
        brep.Flip()
    return brep


def loft_solid(bottom: rg.Curve, top: rg.Curve, tol: float) -> rg.Brep:
    """Closed solid between two closed planar curves with the same segment
    structure (a ruled 'prism' that may be drafted)."""
    lofts = rg.Brep.CreateFromLoft(_net_list(rg.Curve, [bottom, top]),
                                   rg.Point3d.Unset, rg.Point3d.Unset,
                                   rg.LoftType.Straight, False)
    if not lofts:
        raise BuildError("loft failed")
    capped = lofts[0].CapPlanarHoles(tol)
    if capped is None or not capped.IsSolid:
        raise BuildError("capping the loft did not give a closed solid")
    return _outward(capped)


def boolean_difference(base: rg.Brep, cutters, tol: float) -> rg.Brep:
    result = rg.Brep.CreateBooleanDifference(_net_list(rg.Brep, [base]),
                                             _net_list(rg.Brep, cutters), tol)
    if not result:
        raise BuildError("boolean difference failed")
    if len(result) != 1:
        raise BuildError("boolean difference gave %d pieces, expected 1" % len(result))
    brep = result[0]
    brep.MergeCoplanarFaces(tol)
    return _outward(brep)


def box_brep(x0, x1, y0, y1, z0, z1) -> rg.Brep:
    return rg.Box(rg.Plane.WorldXY, rg.Interval(x0, x1), rg.Interval(y0, y1),
                  rg.Interval(z0, z1)).ToBrep()


def swept_profile_solid(p: Params, d: Derived, profile, tol: float) -> rg.Brep:
    """Solid made by sweeping a closed (inset, z) profile around the shelf
    outline, built face by face and joined, with no booleans. Same topology
    as meshing.coupon_mesh."""
    curves = [outline_curve(layout.shelf_outline(p, d, z, inset), z) for inset, z in profile]
    faces = []
    n = len(profile)
    for k in range(n):
        k2 = (k + 1) % n
        (_, za), (_, zb) = profile[k], profile[k2]
        if abs(za - zb) < 1e-9:  # horizontal ring face
            planar = rg.Brep.CreatePlanarBreps(_net_list(rg.Curve, [curves[k], curves[k2]]), tol)
            if not planar:
                raise BuildError("planar face %d of the profile failed" % k)
            faces.extend(planar)
        else:  # vertical or drafted wall
            lofts = rg.Brep.CreateFromLoft(_net_list(rg.Curve, [curves[k], curves[k2]]),
                                           rg.Point3d.Unset, rg.Point3d.Unset,
                                           rg.LoftType.Straight, False)
            if not lofts:
                raise BuildError("wall face %d of the profile failed" % k)
            faces.extend(lofts)
    joined = rg.Brep.JoinBreps(_net_list(rg.Brep, faces), tol)
    if not joined or len(joined) != 1 or not joined[0].IsSolid:
        raise BuildError("joining the profile faces did not give one closed solid")
    return _outward(joined[0])


# --------------------------------------------------------------------------
# parts
# --------------------------------------------------------------------------

def build_fit_coupon(p: Params, d: Derived, tol: float = DEFAULT_TOL):
    """Fit coupon in the car frame. Returns (brep, method).

    outer drafted band  -  void under the plate  -  open window in the middle.
    If the boolean fails, the same shape is built face by face instead.
    """
    profile = layout.coupon_profile(p, d)  # validates the coupon parameters
    top = d.z_top
    t = p.coupon_plate_thickness
    h = d.coupon_rim_height
    e = CUTTER_OVERSHOOT

    def crv(z, inset):
        return outline_curve(layout.shelf_outline(p, d, z, inset), z)

    try:
        outer = loft_solid(crv(top - h, 0.0), crv(top, 0.0), tol)
        void = loft_solid(crv(top - h - e, p.coupon_rim_width),
                          crv(top - t, p.coupon_rim_width), tol)
        window = loft_solid(crv(top - h - e, p.coupon_flange_width),
                            crv(top + e, p.coupon_flange_width), tol)
        return boolean_difference(outer, [void, window], tol), "boolean"
    except BuildError as exc:
        brep = swept_profile_solid(p, d, profile, tol)
        return brep, "joined faces (boolean failed: %s)" % exc


def ring_curve(ring, z: float) -> rg.PolylineCurve:
    """Closed polyline through 2D points at height z."""
    pts = [rg.Point3d(x, y, z) for x, y in ring]
    return rg.PolylineCurve(_net_list(rg.Point3d, pts + [pts[0]]))


def build_profile_gauge(p: Params, d: Derived, tol: float = DEFAULT_TOL):
    """Profile gauge: a flat frame with the cubby cross-section at gauge_y.

    Returns (flat, standing, method): ``flat`` lies on the XY plane as printed
    (x = car x, y = height above the pad), ``standing`` stands in the car frame
    at y = gauge_y for the assembly view. Same shape as meshing.profile_gauge_mesh.
    """
    a = p.gauge_clearance
    b = p.gauge_clearance + p.gauge_band
    t = p.gauge_thickness
    e = CUTTER_OVERSHOOT
    corner = max(p.gauge_corner, 0.7 * b) if p.gauge_corner > 0 else 0.0
    section = layout.profile_section(p, p.gauge_y, gap=max(6.0, 1.3 * b), corner=corner)
    outer_ring = section.offset(a).ring() if a else section.ring()
    inner_ring = section.offset(b).ring()
    outer = loft_solid(ring_curve(outer_ring, 0.0), ring_curve(outer_ring, t), tol)
    window = loft_solid(ring_curve(inner_ring, -e), ring_curve(inner_ring, t + e), tol)
    flat = boolean_difference(outer, [window], tol)
    standing = flat.DuplicateBrep()
    # rotate +90 deg about x: (x, y, z) -> (x, -z, y), then centre the plate on gauge_y
    standing.Transform(rg.Transform.Translation(0.0, p.gauge_y + t / 2.0, 0.0)
                       * rg.Transform.Rotation(math.pi / 2.0, rg.Vector3d.XAxis, rg.Point3d.Origin))
    return flat, standing, "boolean"


def build_context(p: Params, d: Derived) -> dict:
    """Reference geometry in the car frame: cubby wireframe, plug cluster,
    phone on the Qi pad. For display only, never exported."""
    curves = []
    for z in (0.0, p.H_cubby):
        pts = [rg.Point3d(x, y, z) for x, y in layout.cubby_walls(p, z)]
        curves.append(rg.PolylineCurve(_net_list(rg.Point3d, pts)))
    for (xa, ya), (xb, yb) in zip(layout.cubby_walls(p, 0.0), layout.cubby_walls(p, p.H_cubby)):
        curves.append(rg.LineCurve(rg.Point3d(xa, ya, 0.0), rg.Point3d(xb, yb, p.H_cubby)))
    return {
        "cubby": curves,
        "ports": [box_brep(*layout.ports_box(p))],
        "phone": [box_brep(*layout.phone_box(p))],
    }


# --------------------------------------------------------------------------
# print orientation and validation
# --------------------------------------------------------------------------

def print_transform(breps) -> rg.Transform:
    """Rotate 180 deg about x (deck down on the bed), centre on x/y = 0, z_min = 0.
    Same as meshing.to_print_orientation."""
    rot = rg.Transform.Rotation(math.pi, rg.Vector3d.XAxis, rg.Point3d.Origin)
    bbox = None
    for b in breps:
        dup = b.DuplicateBrep()
        dup.Transform(rot)
        bb = dup.GetBoundingBox(True)
        # static Union returns a new box; mutating a .NET struct from Python is unreliable
        bbox = bb if bbox is None else rg.BoundingBox.Union(bbox, bb)
    move = rg.Transform.Translation(-(bbox.Min.X + bbox.Max.X) / 2.0,
                                    -(bbox.Min.Y + bbox.Max.Y) / 2.0,
                                    -bbox.Min.Z)
    return move * rot  # rotate first, then move


def check_solid(brep, name: str):
    """Messages about problems; empty list = valid closed solid."""
    if brep is None:
        return ["%s: no geometry" % name]
    msgs = []
    if not brep.IsValid:
        ok, log = brep.IsValidWithLog()
        msgs.append("%s: invalid B-rep: %s" % (name, str(log)[:300]))
    if not brep.IsSolid:
        msgs.append("%s: not a closed solid (it has naked edges)" % name)
    return msgs


def volume_cm3(brep) -> float:
    props = rg.VolumeMassProperties.Compute(brep)
    return props.Volume / 1000.0 if props else float("nan")
