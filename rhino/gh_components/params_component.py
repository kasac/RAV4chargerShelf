#! python3
# RAV4chargerShelf GH component: Params
# Paste into a Rhino 8 "Script" component set to Python 3.
#   Inputs : S        (List Access!) wire sliders here; slider NickName = parameter name
#            overrides (str, optional) extra override JSON file, applied after measured.json
#            sliders  (bool) button: create the missing sliders for 'groups'
#            groups   (str, optional) e.g. "cubby,ports,fit" (empty = all groups)
#            reload   (bool) button: re-import the python modules after editing them
#   Outputs: P, report
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
import rav4shelf  # noqa: E402

if reload:  # noqa: F821
    rav4shelf.reload_all()

from rav4shelf import gh  # noqa: E402

P, report = gh.params_component(ghenv.Component, overrides, sliders, groups)  # noqa: F821
