#! python3
# RAV4chargerShelf GH component: Profile gauge (test print)
# Paste into a Rhino 8 "Script" component set to Python 3.
#   Inputs : P  (from the Params component)
#   Outputs: gauge (standing in the car frame at gauge_y), gauge_print (flat, as printed), report
# ---- bootstrap (identical in every wrapper) -------------------------------
import os
import sys

_repo = os.environ.get("RAV4SHELF_REPO", "")
if not _repo:
    _ghdoc = ghenv.Component.OnPingDocument()  # noqa: F821 (ghenv is provided by GH)
    if _ghdoc is not None and _ghdoc.FilePath:
        _repo = os.path.dirname(os.path.dirname(_ghdoc.FilePath))
_src = os.path.join(_repo, "src")
if not os.path.isdir(os.path.join(_src, "rav4shelf")):
    raise RuntimeError("rav4shelf not found: save this .gh in <repo>/grasshopper/ "
                       "or set the RAV4SHELF_REPO environment variable to the repo folder")
if _src not in sys.path:
    sys.path.insert(0, _src)
# ---------------------------------------------------------------------------
from rav4shelf import gh  # noqa: E402

gauge, gauge_print, report = gh.profile_gauge_component(P)  # noqa: F821
