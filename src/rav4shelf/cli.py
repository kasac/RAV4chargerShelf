"""Command line for the pure-Python path (no Rhino needed).

    python tools/rav4shelf.py check            # report + sanity checks
    python tools/rav4shelf.py coupon           # test prints: fit coupon + profile gauge
    python tools/rav4shelf.py preview          # overview, 1:1 template, cubby_envelope.stl
    python tools/rav4shelf.py roof             # roof plate: STL + 3MF (standing) + drawing
    python tools/rav4shelf.py all              # everything above
    python tools/rav4shelf.py reference        # compare with the cubby reference model

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
    """The two test prints: fit coupon and profile gauge (STL + 3MF each)."""
    header = " UNCONFIRMED-DIMENSIONS" if p.placeholders else ""
    parts = [("fit_coupon", "fit coupon", meshing.to_print_orientation(meshing.coupon_mesh(p, d))),
             ("profile_gauge", "profile gauge (at %.0f mm behind the lip)" % p.gauge_y,
              meshing.profile_gauge_mesh(p, d))]
    files, info = [], []
    for name, label, mesh in parts:
        problems = meshing.check_closed(mesh)
        if problems:
            raise GeometryError("%s mesh is not watertight: %s" % (name, "; ".join(problems[:5])))
        stl = os.path.join(out_dir, name + ".stl")
        tmf = os.path.join(out_dir, name + ".3mf")
        fileio.write_stl(stl, mesh.vertices, mesh.faces, "rav4shelf " + name + header)
        fileio.write_3mf(tmf, mesh.vertices, mesh.faces, name)
        files += [stl, tmf]
        (x0, y0, z0), (x1, y1, z1) = mesh.bbox()
        info.append("%s: %.1f x %.1f x %.1f mm, %.1f cm3 (~%.0f g PETG)" % (
            label, x1 - x0, y1 - y0, z1 - z0, meshing.mesh_volume_cm3(mesh),
            meshing.petg_grams(mesh)))
    return files, "\n".join(info)


def build_roof_files(p, d, out_dir: str):
    """The roof plate, standing on its rear edge as printed, plus its drawing."""
    mesh = meshing.roof_plate_mesh(p, d)
    problems = meshing.check_closed(mesh)
    if problems:
        raise GeometryError("roof plate mesh is not watertight: %s" % "; ".join(problems[:5]))
    grams = meshing.petg_grams(mesh)
    printed = meshing.standing_print_orientation(mesh)
    files = [os.path.join(out_dir, "roof_plate" + ext) for ext in (".stl", ".3mf", ".svg")]
    fileio.write_stl(files[0], printed.vertices, printed.faces, "rav4shelf roof_plate")
    fileio.write_3mf(files[1], printed.vertices, printed.faces, "roof_plate")
    _write(files[2], preview_svg.roof_plate_svg(p, d, grams))
    (x0, y0, z0), (x1, y1, z1) = printed.bbox()
    info = ("roof plate (standing on its rear edge): %.1f x %.1f x %.1f mm, ~%.0f g PETG"
            % (x1 - x0, y1 - y0, z1 - z0, grams))
    return files, info


def run_reference(p, d, args) -> int:
    """Compare our envelope and shelf with the reference model, fit the envelope to it."""
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
             "YOUR ENVELOPE (%s) vs the reference's outer surface:" % used]
    try:
        env_lines = reference.envelope_lines(reference.envelope_report(p, ref))
        cmp_lines = reference.compare(p, d, ref).summary_lines()
    except (GeometryError, params.ParamError) as exc:
        env_lines, cmp_lines = ["cannot build your envelope: %s" % exc], []
    lines += ["  " + x for x in env_lines]
    if p.roof_pocket_rise == 0 or p.roof_bulge_depth > 0:
        lines.append("  (the roof is expected to differ: the GR Sport PHEV has no roof pocket and "
                     "a bulge around the roof LED)")
    lines += ["", "YOUR SHELF at its edge band vs the reference at the same heights "
                  "(includes side_gap and envelope_offset):"]
    lines += ["  " + x for x in cmp_lines]
    values, quality = reference.fit_params(ref)
    lines += ["", "FITTED ENVELOPE (params/cubby_reference_fit.json; the defaults start from it, "
                  "except the roof):"]
    lines += ["  %-20s %s" % (k, v) for k, v in values.items()]
    lines += ["  " + x for x in reference.envelope_lines(quality)]
    text = "\n".join(lines)
    print(text)

    os.makedirs(args.out, exist_ok=True)
    shift = d.y_rear - ref.depth
    ring = [(x, y - shift) for x, y in layout.shelf_outline(p, d, d.z_top).ring(16)]
    svg = preview_svg.reference_overlay_svg(
        ref.section(spec.floor_level - d.z_top), ring, ["params: " + used] + env_lines + cmp_lines,
        "Your shelf outline at z %.1f vs %s at the same height" % (d.z_top, spec.name))
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
    ap.add_argument("command", choices=["check", "coupon", "preview", "roof", "all", "reference"])
    ap.add_argument("-p", "--params", action="append", default=[],
                    help="extra override JSON file (repeatable, applied in order)")
    ap.add_argument("--defaults-only", action="store_true",
                    help="ignore params/measured.json")
    ap.add_argument("-o", "--out", default=os.path.join(params.REPO_ROOT, "out"),
                    help="output folder (default: out/)")
    ap.add_argument("--ref", default=None,
                    help="reference: STL to compare with (default: "
                         "reference/cubby-constraint-reference-model.stl)")
    ap.add_argument("--write-params", default=None, metavar="FILE",
                    help="reference: also write the fitted parameters to FILE")
    args = ap.parse_args(argv)

    overrides = [] if args.defaults_only else params.default_override_paths()
    overrides += args.params
    try:
        p = params.load_params(*overrides)
        d = params.derive(p)
    except (params.ParamError, OSError) as exc:
        print("parameter error: %s" % exc, file=sys.stderr)
        return 2
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
        try:  # the cubby as a solid, to design against in any CAD program
            env = meshing.envelope_mesh(p, d)
            path = os.path.join(args.out, "cubby_envelope.stl")
            fileio.write_stl(path, env.vertices, env.faces, "rav4shelf cubby envelope (car frame)")
            written.append(path)
        except GeometryError as exc:
            print("not writing cubby_envelope.stl: %s" % exc, file=sys.stderr)

    if args.command in ("coupon", "all"):
        if checks.has_errors(findings):
            print("not writing the fit coupon: fix the errors above first", file=sys.stderr)
            return 1
        files, info = build_coupon_files(p, d, args.out)
        written += files
        print(info)

    if args.command in ("roof", "all"):
        try:
            files, info = build_roof_files(p, d, args.out)
        except (GeometryError, params.ParamError) as exc:
            print("not writing the roof plate: %s" % exc, file=sys.stderr)
            return 1
        written += files
        print(info)

    for path in written:
        print("wrote " + _nice(path))
    if p.placeholders:
        print("\nNOTE: %d values are not confirmed for your car yet: check them with the test "
              "prints (docs/measuring.md)." % len(p.placeholders))
    return 1 if checks.has_errors(findings) else 0
