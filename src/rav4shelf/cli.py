"""Command line for the pure-Python path (no Rhino needed).

    python tools/rav4shelf.py check            # report + sanity checks
    python tools/rav4shelf.py coupon           # out/fit_coupon.stl + .3mf
    python tools/rav4shelf.py preview          # out/overview.svg + out/fit_template_1to1.svg
    python tools/rav4shelf.py all              # everything above
    python tools/rav4shelf.py reference        # compare with the Vela3D reference model

params/measured.json is applied automatically when it exists; add more
override files with -p. Exit code 1 if a check reports an error.
"""
from __future__ import annotations

import argparse
import os
import sys

from . import checks, fileio, layout, meshing, params, preview_svg
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


def run_reference(p, d, args) -> int:
    """Compare our outline with the reference model and fit our parameters to it."""
    from . import reference

    try:
        ref = reference.load_reference(path=args.ref)
    except reference.ReferenceError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    spec = ref.spec
    used = "default.json" + "".join(" + " + _nice(f) for f in p.files)
    lines = ["reference: %s" % spec.name,
             "  %s: %.1f wide, %.1f deep, %.1f tall" % (_nice(ref.path), ref.width, ref.depth,
                                                       ref.height),
             "",
             "YOUR SHELF OUTLINE (%s) vs the reference:" % used]
    try:
        cmp_lines = reference.compare(p, d, ref).summary_lines()
    except GeometryError as exc:
        cmp_lines = ["cannot build your outline: %s" % exc]
    lines += ["  " + x for x in cmp_lines]
    values, quality = reference.fit_params(ref)
    lines += ["",
              "PARAMETERS THAT REPRODUCE THE REFERENCE OUTLINE (side_gap 0, assumptions in "
              "params/reference_vela3d.json):"]
    lines += ["  %-20s %s" % (k, v) for k, v in values.items()]
    lines.append("  fit: sides within %.2f mm, rear corners within %.2f mm; wall lean %.1f deg per "
                 "side; %.1f mm narrower per 100 mm of depth" % (
                     quality["sides"]["max_abs"], quality["rear_corners"]["max_abs"],
                     quality["wall_lean_deg_per_side"], -quality["width_change_per_100mm_depth"]))
    text = "\n".join(lines)
    print(text)

    os.makedirs(args.out, exist_ok=True)
    shift = d.y_rear - ref.depth
    ring = [(x, y - shift) for x, y in
            layout.shelf_outline(p, d, d.z_top).ring(16)]
    svg = preview_svg.reference_overlay_svg(
        ref.section(spec.compare_level), ring, ["params: " + used] + cmp_lines,
        "Your shelf outline vs %s" % spec.name)
    written = []
    for name, content in (("reference_compare.svg", svg), ("reference_compare.txt", text + "\n")):
        path = os.path.join(args.out, name)
        _write(path, content)
        written.append(path)
    if args.write_params:
        reference.write_params_file(args.write_params, values, quality, ref)
        written.append(args.write_params)
    for path in written:
        print("wrote " + _nice(path))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rav4shelf", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "coupon", "preview", "all", "reference"])
    ap.add_argument("-p", "--params", action="append", default=[],
                    help="extra override JSON file (repeatable, applied in order)")
    ap.add_argument("--defaults-only", action="store_true",
                    help="ignore params/measured.json")
    ap.add_argument("-o", "--out", default=os.path.join(params.REPO_ROOT, "out"),
                    help="output folder (default: out/)")
    ap.add_argument("--ref", default=None,
                    help="reference: STL to compare with (default: reference/*MODULE*.stl)")
    ap.add_argument("--write-params", default=None, metavar="FILE",
                    help="reference: also write the fitted parameters to FILE")
    args = ap.parse_args(argv)

    overrides = [] if args.defaults_only else params.default_override_paths()
    overrides += args.params
    try:
        p = params.load_params(*overrides)
    except (params.ParamError, OSError) as exc:
        print("parameter error: %s" % exc, file=sys.stderr)
        return 2
    d = params.derive(p)
    if args.command == "reference":
        return run_reference(p, d, args)
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
