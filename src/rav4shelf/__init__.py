"""RAV4chargerShelf: parametric 3D-printable shelf for the RAV4 XA50 charger cubby.

Pure-Python modules (no Rhino, unit-tested on CI):
    geom2d, params, layout, checks, meshing, fileio, preview_svg, cli

RhinoCommon modules (run inside Rhino 8 / Grasshopper only):
    geometry, export, gh

Importing this package never imports Rhino.
"""
import importlib
import sys

__version__ = "0.1.0"

# Dependency order: a module is listed after everything it imports.
_MODULES = [
    "geom2d",
    "params",
    "layout",
    "checks",
    "meshing",
    "fileio",
    "preview_svg",
    "cli",
    "geometry",
    "export",
    "gh",
]


def reload_all():
    """Re-import every already-loaded rav4shelf module.

    Rhino keeps imported modules cached until it restarts. Call this after
    editing the .py files (or after a git pull) to pick up the changes.
    """
    reloaded = []
    for name in _MODULES:
        full = __name__ + "." + name
        if full in sys.modules:
            importlib.reload(sys.modules[full])
            reloaded.append(name)
    return reloaded
