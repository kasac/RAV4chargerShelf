"""Command line for the pure-Python path (no Rhino needed).

    python tools/rav4shelf.py check            # report + sanity checks
    python tools/rav4shelf.py coupon           # out/fit_coupon.stl + .3mf
    python tools/rav4shelf.py preview          # out/overview.svg + out/fit_template_1to1.svg
    python tools/rav4shelf.py all              # everything above

params/measured.json is applied automatically when it exists; add more
override files with -p. Exit code 1 if a check reports an error.
"""
from __future__ import annotations

import argparse
import os
import sys

from . import checks, fileio, meshing, params, preview_svg
from .geom2d import GeometryError


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _nice(path: str) -> str:
    try:
        return os.path.relpath(path)
    except ValueError:  # Windows: different drive
        return path


def build_coupon_files(p, d, out_dir: str):
    mesh = meshing.to_print_orientation(meshing.coupon_mesh(p, d))
    problems = meshing.check_closed(mesh)
    if problems:
        raise GeometryError("fit coupon mesh is not watertight: " + "; ".join(problems[:5]))
    header = "rav4shelf fit_coupon" + (" PLACEHOLDER-DIMENSIONS" if p.placeholders else "")
    stl = os.path.join(out_dir, "fit_coupon.stl")
    tmf = os.path.join(out_dir, "fit_coupon.3mf")
    fileio.write_stl(stl, mesh.vertices, mesh.faces, header)
    fileio.write_3mf(tmf, mesh.vertices, mesh.faces, "fit_coupon")
    (x0, y0, z0), (x1, y1, z1) = mesh.bbox()
    info = "fit coupon: %.1f x %.1f x %.1f mm, %.1f cm3 (~%.0f g PETG)" % (
        x1 - x0, y1 - y0, z1 - z0, meshing.mesh_volume_cm3(mesh), meshing.petg_grams(mesh))
    return [stl, tmf], info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rav4shelf", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "coupon", "preview", "all"])
    ap.add_argument("-p", "--params", action="append", default=[],
                    help="extra override JSON file (repeatable, applied in order)")
    ap.add_argument("--defaults-only", action="store_true",
                    help="ignore params/measured.json")
    ap.add_argument("-o", "--out", default=os.path.join(params.REPO_ROOT, "out"),
                    help="output folder (default: out/)")
    args = ap.parse_args(argv)

    overrides = [] if args.defaults_only else params.default_override_paths()
    overrides += args.params
    try:
        p = params.load_params(*overrides)
    except (params.ParamError, OSError) as exc:
        print("parameter error: %s" % exc, file=sys.stderr)
        return 2
    d = params.derive(p)
    findings = checks.run_checks(p, d)
    report = checks.format_report(p, d, findings)
    print(report)

    if args.command == "check":
        return 1 if checks.has_errors(findings) else 0

    os.makedirs(args.out, exist_ok=True)
    _write(os.path.join(args.out, "report.txt"), report)
    written = [os.path.join(args.out, "report.txt")]

    if args.command in ("preview", "all"):
        for name, svg in (("overview.svg", preview_svg.overview_svg(p, d, findings)),
                          ("fit_template_1to1.svg", preview_svg.fit_template_svg(p, d))):
            path = os.path.join(args.out, name)
            _write(path, svg)
            written.append(path)

    if args.command in ("coupon", "all"):
        if checks.has_errors(findings):
            print("not writing the fit coupon: fix the errors above first", file=sys.stderr)
            return 1
        files, info = build_coupon_files(p, d, args.out)
        written += files
        print(info)

    for path in written:
        print("wrote " + _nice(path))
    if p.placeholders:
        print("\nNOTE: built from PLACEHOLDER dimensions - measure first (docs/measuring.md).")
    return 1 if checks.has_errors(findings) else 0
