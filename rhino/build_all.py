#! python3
"""RAV4chargerShelf: standalone Rhino 8 build (fallback if Grasshopper breaks).

Run it from Rhino 8 with  _RunPythonScript  or open it in the ScriptEditor
and press Run. It
  1. loads params/default.json + params/measured.json (+ EXTRA_OVERRIDES),
  2. prints the report and stops if a check reports an error,
  3. bakes every part and the cubby context to layers RAV4chargerShelf::<part>
     (car frame; objects from a previous run on those layers are replaced),
  4. exports each part in print orientation to out/<part>.step/.3mf/.stl.

The document must be in millimetres.
"""
import os
import sys


def _repo_root():
    try:
        here = os.path.dirname(os.path.abspath(__file__))
    except NameError:  # __file__ is not set in some script-editor modes
        here = None
    if here and os.path.isdir(os.path.join(here, os.pardir, "src", "rav4shelf")):
        return os.path.abspath(os.path.join(here, os.pardir))
    env = os.environ.get("RAV4SHELF_REPO")
    if env:
        return env
    import rhinoscriptsyntax as rs
    folder = rs.BrowseForFolder(message="Select the RAV4chargerShelf repository folder")
    if not folder:
        raise SystemExit("cancelled")
    return folder


REPO = _repo_root()
if os.path.join(REPO, "src") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "src"))

import Rhino  # noqa: E402

import rav4shelf  # noqa: E402

rav4shelf.reload_all()  # pick up edits without restarting Rhino

from rav4shelf import checks, export, geometry, params  # noqa: E402

# ---- settings -------------------------------------------------------------
EXTRA_OVERRIDES = []  # e.g. [os.path.join(REPO, "params", "tight_fit.json")]
PARTS = ["fit_coupon", "profile_gauge"]  # shelf, drawer, hinge_pin, tpu_bumpers: later
FORMATS = ("step", "3mf", "stl")
OUT_DIR = os.path.join(REPO, "out")
# ---------------------------------------------------------------------------


def main():
    doc = Rhino.RhinoDoc.ActiveDoc
    units = export.check_units(doc)
    if units:
        print("STOP: " + units)
        return
    tol = min(doc.ModelAbsoluteTolerance, geometry.DEFAULT_TOL)

    p = params.load_params(*(params.default_override_paths() + EXTRA_OVERRIDES))
    d = params.derive(p)
    findings = checks.run_checks(p, d)
    report = [checks.format_report(p, d, findings)]
    if checks.has_errors(findings):
        print(report[0])
        print("STOP: fix the errors above first.")
        return

    ctx = geometry.build_context(p, d)
    for name, geo in ctx.items():
        export.bake(doc, name, geo)

    def coupon(p, d, tol):
        brep, method = geometry.build_fit_coupon(p, d, tol)
        return brep, brep, method

    # each builder returns (part to export, part to bake in the car frame, method)
    builders = {"fit_coupon": coupon, "profile_gauge": geometry.build_profile_gauge}
    for part in PARTS:
        to_export, to_bake, method = builders[part](p, d, tol)
        problems = geometry.check_solid(to_export, part)
        report.append("%s: built by %s, %.1f cm3" % (part, method, geometry.volume_cm3(to_export)))
        report.extend("  PROBLEM: " + m for m in problems)
        export.bake(doc, part, [to_bake])
        paths, msgs = export.export_part(part, [to_export], OUT_DIR, FORMATS, tol, doc)
        report.extend("  wrote " + x for x in paths)
        report.extend("  PROBLEM: " + m for m in msgs)

    if p.placeholders:
        report.append("\nNOTE: %d values are not confirmed for your car yet - check them with "
                      "the test prints (docs/measuring.md)." % len(p.placeholders))
    text = "\n".join(report)
    print(text)
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    with open(os.path.join(OUT_DIR, "report_rhino.txt"), "w") as f:
        f.write(text + "\n")
    doc.Views.Redraw()


if __name__ == "__main__":
    main()
