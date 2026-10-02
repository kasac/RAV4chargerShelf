"""Checks for code that cannot run on CI: the Rhino / Grasshopper layer.

Rhino 8 runs CPython 3.9, so every file must parse with the 3.9 grammar, and
the pure modules must never import Rhino (CI has no Rhino).
"""
import ast
import glob
import os

import pytest

from conftest import REPO

ALL_PY = sorted(
    glob.glob(os.path.join(REPO, "src", "rav4shelf", "*.py"))
    + glob.glob(os.path.join(REPO, "rhino", "**", "*.py"), recursive=True)
    + glob.glob(os.path.join(REPO, "tools", "*.py"))
)

PURE = ["geom2d", "params", "layout", "checks", "meshing", "fileio", "reference", "preview_svg",
        "cli"]
RHINO_ONLY = ("Rhino", "System", "Grasshopper", "rhinoscriptsyntax", "scriptcontext")


@pytest.mark.parametrize("path", ALL_PY, ids=lambda p: os.path.relpath(p, REPO))
def test_parses_as_python39(path):
    with open(path, encoding="utf-8") as f:
        ast.parse(f.read(), filename=path, feature_version=(3, 9))


def _imports(path):
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.add(node.module.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            names.add("." + node.module.split(".")[0])
    return names


@pytest.mark.parametrize("mod", PURE)
def test_pure_modules_do_not_import_rhino(mod):
    imports = _imports(os.path.join(REPO, "src", "rav4shelf", mod + ".py"))
    assert not imports & set(RHINO_ONLY)
    rhino_modules = {".geometry", ".export", ".gh"}
    assert not imports & rhino_modules


def test_package_import_does_not_pull_rhino():
    import sys
    import rav4shelf  # noqa: F401
    assert "Rhino" not in sys.modules


def test_gh_wrappers_share_the_same_bootstrap():
    wrappers = glob.glob(os.path.join(REPO, "rhino", "gh_components", "*.py"))
    assert wrappers
    blocks = set()
    for w in wrappers:
        text = open(w, encoding="utf-8").read()
        start = text.index("# ---- bootstrap")
        end = text.index("# ------", start + 10)
        blocks.add(text[start:end])
    assert len(blocks) == 1, "keep the bootstrap block identical in every wrapper"
