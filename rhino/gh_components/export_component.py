#! python3
# RAV4chargerShelf GH component: Export one part
# Paste into a Rhino 8 "Script" component set to Python 3.
#   Inputs : name    (str) part name, e.g. "fit_coupon" -> out/fit_coupon.stl/.3mf/.step
#            breps   (List Access) the part in the CAR frame (e.g. 'coupon'); it is
#                    rotated into print orientation on export
#            out_dir (str, optional) default <repo>/out
#            export  (bool) button
#   Outputs: report
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

report = gh.export_component(name, breps, out_dir, export)  # noqa: F821
