"""STL and 3MF writers using only the standard library.

Used by the pure-Python CLI and by export.py inside Rhino (after meshing the
B-reps there), so both paths write identical, predictable files without any
export dialog.
"""
from __future__ import annotations

import struct
import zipfile
from typing import Dict, List, Sequence, Tuple
from xml.sax.saxutils import escape

Vec3 = Tuple[float, float, float]


def weld(vertices: Sequence[Vec3], faces: Sequence[Tuple[int, int, int]], tol: float = 1e-4):
    """Merge vertices closer than ``tol`` (grid snapping) and drop faces that
    collapse. Rhino meshes every B-rep face separately; welding makes the
    shared edges shared again, which 3MF readers expect."""
    key_to_new: Dict[Tuple[int, int, int], int] = {}
    new_vertices: List[Vec3] = []
    remap = []
    inv = 1.0 / tol
    for x, y, z in vertices:
        key = (int(round(x * inv)), int(round(y * inv)), int(round(z * inv)))
        idx = key_to_new.get(key)
        if idx is None:
            idx = len(new_vertices)
            key_to_new[key] = idx
            new_vertices.append((float(x), float(y), float(z)))
        remap.append(idx)
    new_faces = []
    for a, b, c in faces:
        a2, b2, c2 = remap[a], remap[b], remap[c]
        if a2 != b2 and b2 != c2 and a2 != c2:
            new_faces.append((a2, b2, c2))
    return new_vertices, new_faces


def _normal(a: Vec3, b: Vec3, c: Vec3) -> Vec3:
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    n = (nx * nx + ny * ny + nz * nz) ** 0.5
    if n == 0:
        return (0.0, 0.0, 0.0)
    return (nx / n, ny / n, nz / n)


def write_stl(path: str, vertices: Sequence[Vec3], faces: Sequence[Tuple[int, int, int]],
              header: str = "rav4shelf") -> None:
    """Binary STL, millimetres."""
    head = header.encode("ascii", "replace")[:80].ljust(80, b" ")
    with open(path, "wb") as f:
        f.write(head)
        f.write(struct.pack("<I", len(faces)))
        for a, b, c in faces:
            va, vb, vc = vertices[a], vertices[b], vertices[c]
            f.write(struct.pack("<12fH", *_normal(va, vb, vc), *va, *vb, *vc, 0))


def read_stl(path: str):
    """Read a binary STL back as a list of triangles (for tests)."""
    with open(path, "rb") as f:
        data = f.read()
    (count,) = struct.unpack_from("<I", data, 80)
    tris = []
    for i in range(count):
        vals = struct.unpack_from("<12f", data, 84 + i * 50)
        tris.append((vals[3:6], vals[6:9], vals[9:12]))
    return tris


_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
    '</Types>'
)

_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
    '</Relationships>'
)


def write_3mf(path: str, vertices: Sequence[Vec3], faces: Sequence[Tuple[int, int, int]],
              name: str = "part") -> None:
    """Minimal 3MF core-spec file with one object, unit = millimetre."""
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
        '<metadata name="Title">%s</metadata>\n'
        '<metadata name="Application">rav4shelf</metadata>\n'
        '<resources>\n<object id="1" type="model" name="%s">\n<mesh>\n<vertices>\n'
        % (escape(name), escape(name))
    ]
    parts.extend('<vertex x="%.5f" y="%.5f" z="%.5f"/>\n' % v for v in vertices)
    parts.append('</vertices>\n<triangles>\n')
    parts.extend('<triangle v1="%d" v2="%d" v3="%d"/>\n' % f for f in faces)
    parts.append('</triangles>\n</mesh>\n</object>\n</resources>\n'
                 '<build>\n<item objectid="1"/>\n</build>\n</model>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("3D/3dmodel.model", "".join(parts))
