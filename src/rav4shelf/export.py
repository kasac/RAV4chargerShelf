"""Bake parts to named layers and export STEP / 3MF / STL. Rhino only.

STL and 3MF: the B-rep is meshed in Rhino, then written by fileio (plain
Python), so no export dialog can pop up and the files are identical to the
ones the CLI writes. STEP: written by Rhino's own exporter.

Every exported file is in PRINT orientation (deck / plate down on the bed),
millimetres. The baked objects in the document stay in the car frame.

NOT YET RUN IN RHINO: see the first-run checklist in README.md.
"""
from __future__ import annotations

import math
import os

import Rhino
import Rhino.Geometry as rg
import System

from . import fileio, meshing
from .geometry import DEFAULT_TOL, print_transform

ROOT_LAYER = "RAV4chargerShelf"

LAYER_COLORS = {
    "fit_coupon": (47, 109, 181),
    "profile_gauge": (39, 174, 96),
    "shelf": (47, 109, 181),
    "drawer": (230, 126, 34),
    "cubby": (120, 120, 120),
    "envelope": (170, 170, 170),
    "ports": (192, 57, 43),
    "phone": (127, 140, 141),
    "led_keepout": (241, 196, 15),
    "roof_plate": (47, 109, 181),
}

# Created switched off: the envelope solid would hide the parts inside it.
HIDDEN_AT_FIRST = {"envelope"}


# --------------------------------------------------------------------------
# document
# --------------------------------------------------------------------------

def check_units(doc) -> str:
    """Empty string if the document is in millimetres, else a message."""
    if doc.ModelUnitSystem != Rhino.UnitSystem.Millimeters:
        return ("document units are %s, not millimetres: every dimension would be read in "
                "the wrong unit. Run the Units command and pick Millimeters." % doc.ModelUnitSystem)
    return ""


def ensure_layer(doc, name: str) -> int:
    """Index of layer RAV4chargerShelf::<name>, created if missing."""
    root = doc.Layers.FindByFullPath(ROOT_LAYER, -1)
    if root < 0:
        layer = Rhino.DocObjects.Layer()
        layer.Name = ROOT_LAYER
        root = doc.Layers.Add(layer)
    idx = doc.Layers.FindByFullPath(ROOT_LAYER + "::" + name, -1)
    if idx < 0:
        layer = Rhino.DocObjects.Layer()
        layer.Name = name
        layer.ParentLayerId = doc.Layers[root].Id
        rgb = LAYER_COLORS.get(name)
        if rgb:
            layer.Color = System.Drawing.Color.FromArgb(*rgb)
        if name in HIDDEN_AT_FIRST:
            layer.IsVisible = False
        idx = doc.Layers.Add(layer)
    return idx


def bake(doc, name: str, geometry) -> list:
    """Replace everything on layer RAV4chargerShelf::<name> with ``geometry``."""
    idx = ensure_layer(doc, name)
    old = doc.Objects.FindByLayer(doc.Layers[idx])
    for obj in (old or []):
        doc.Objects.Delete(obj, True)
    attr = Rhino.DocObjects.ObjectAttributes()
    attr.LayerIndex = idx
    attr.Name = name
    ids = []
    for g in geometry:
        if isinstance(g, rg.Brep):
            ids.append(doc.Objects.AddBrep(g, attr))
        elif isinstance(g, rg.Curve):
            ids.append(doc.Objects.AddCurve(g, attr))
        elif isinstance(g, rg.Mesh):
            ids.append(doc.Objects.AddMesh(g, attr))
    return ids


# --------------------------------------------------------------------------
# meshing
# --------------------------------------------------------------------------

def breps_to_triangles(breps, tol: float = DEFAULT_TOL):
    """Mesh B-reps into one welded (vertices, faces) triangle list."""
    mp = rg.MeshingParameters()
    mp.Tolerance = tol                  # max chord deviation on curved faces
    mp.JaggedSeams = False              # shared edges get shared vertices
    mp.SimplePlanes = True
    mp.RefineGrid = True
    mp.GridAngle = math.radians(10.0)
    mp.MinimumEdgeLength = 0.0001
    verts, faces = [], []
    for brep in breps:
        pieces = rg.Mesh.CreateFromBrep(brep, mp)
        if not pieces:
            raise RuntimeError("meshing failed")
        mesh = rg.Mesh()
        for piece in pieces:
            mesh.Append(piece)
        mesh.Faces.ConvertQuadsToTriangles()
        base = len(verts)
        for i in range(mesh.Vertices.Count):
            v = mesh.Vertices[i]
            verts.append((float(v.X), float(v.Y), float(v.Z)))
        for i in range(mesh.Faces.Count):
            f = mesh.Faces[i]
            faces.append((base + f.A, base + f.B, base + f.C))
    return fileio.weld(verts, faces, 1e-4)


# --------------------------------------------------------------------------
# files
# --------------------------------------------------------------------------

def export_step(breps, path: str, doc=None) -> bool:
    """Write STEP through a headless document; if that fails and ``doc`` is
    given (not while Grasshopper is solving), use the -Export command."""
    if os.path.exists(path):
        os.remove(path)
    headless = Rhino.RhinoDoc.CreateHeadless(None)
    try:
        headless.ModelUnitSystem = Rhino.UnitSystem.Millimeters
        for b in breps:
            headless.Objects.AddBrep(b)
        headless.Export(path)
    except Exception:
        pass
    finally:
        headless.Dispose()
    if os.path.isfile(path):
        return True
    if doc is None:
        return False
    ids = [doc.Objects.AddBrep(b) for b in breps]
    try:
        doc.Objects.UnselectAll()
        doc.Objects.Select(_net_guids(ids), True)
        Rhino.RhinoApp.RunScript('_-Export "%s" _Enter _Enter' % path, False)
    finally:
        for i in ids:
            doc.Objects.Delete(i, True)
    return os.path.isfile(path)


def _net_guids(ids):
    lst = System.Collections.Generic.List[System.Guid]()
    for i in ids:
        lst.Add(i)
    return lst


def export_mesh_part(name: str, pure_mesh, out_dir: str, formats=("3mf", "stl")):
    """Write a pure-Python mesh, stood on its rear edge as printed, to STL/3MF.
    Returns (paths, messages)."""
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    printed = meshing.standing_print_orientation(pure_mesh)
    problems = meshing.check_closed(printed)
    msgs = ["%s mesh is not watertight: %s" % (name, "; ".join(problems[:3]))] if problems else []
    paths = []
    if "stl" in formats:
        paths.append(os.path.join(out_dir, name + ".stl"))
        fileio.write_stl(paths[-1], printed.vertices, printed.faces, "rav4shelf " + name)
    if "3mf" in formats:
        paths.append(os.path.join(out_dir, name + ".3mf"))
        fileio.write_3mf(paths[-1], printed.vertices, printed.faces, name)
    return paths, msgs


def export_part(name: str, breps, out_dir: str, formats=("step", "3mf", "stl"),
                tol: float = DEFAULT_TOL, doc=None):
    """Export one part in print orientation. Returns (paths, messages)."""
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    xform = print_transform(breps)
    placed = []
    for b in breps:
        dup = b.DuplicateBrep()
        dup.Transform(xform)
        placed.append(dup)
    paths, msgs = [], []
    if "stl" in formats or "3mf" in formats:
        verts, faces = breps_to_triangles(placed, tol)
        problems = meshing.check_closed(meshing.Mesh(verts, faces))
        if problems:
            msgs.append("%s mesh is not watertight: %s" % (name, "; ".join(problems[:3])))
        if "stl" in formats:
            path = os.path.join(out_dir, name + ".stl")
            fileio.write_stl(path, verts, faces, "rav4shelf " + name)
            paths.append(path)
        if "3mf" in formats:
            path = os.path.join(out_dir, name + ".3mf")
            fileio.write_3mf(path, verts, faces, name)
            paths.append(path)
    if "step" in formats:
        path = os.path.join(out_dir, name + ".step")
        if export_step(placed, path, doc):
            paths.append(path)
        else:
            msgs.append("%s: STEP export failed (run rhino/build_all.py, or export by hand)" % name)
    return paths, msgs
