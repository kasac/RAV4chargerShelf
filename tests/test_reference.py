"""The cubby envelope vs the cubby-constraint-reference-model.

The reference model is a third-party file and is not in the repo, so the
tests that need it skip on CI. Put it into reference/ as
cubby-constraint-reference-model.stl to run them locally. The machinery
(slicing, comparing, fitting) is tested on CI with meshes this project
generates.
"""
import json
import os

import pytest

from rav4shelf import checks, fileio, layout, meshing, params, reference

from conftest import REPO, make

REF_PARAMS = os.path.join(REPO, "params", "cubby_reference_fit.json")


def own_spec(p, d, rim):
    """Read a coupon made by this project (already in the car frame) like a
    reference part: depth from its front edge, level measured down from its top."""
    return reference.ReferenceSpec(
        "own coupon", "*.stl", 0.0, None, x_axis=0, depth_axis=1, depth_sign=1,
        level_axis=2, level_sign=-1, floor_level=d.z_top, front_recess=p.front_recess,
        rear_gap=p.rear_gap, wall_levels=(2.0, rim - 1.0), closed_back_levels=(2.0, rim - 1.0),
        rear_zone=36.0, side_end_margin=0.0, roof_depths=None)


def write_coupon_stl(tmp_path, p, d):
    m = meshing.coupon_mesh(p, d)  # car frame
    path = str(tmp_path / "coupon.stl")
    fileio.write_stl(path, m.vertices, m.faces)
    return path, m


# --------------------------------------------------------------------------
# machinery (always runs)
# --------------------------------------------------------------------------

def test_read_stl_binary_and_ascii(tmp_path, p, d):
    path, m = write_coupon_stl(tmp_path, p, d)
    tris = fileio.read_stl(path)
    assert len(tris) == len(m.faces)
    ascii_path = tmp_path / "coupon_ascii.stl"
    lines = ["solid t"]
    for t in tris[:50]:
        lines += ["facet normal 0 0 0", "outer loop"]
        lines += ["vertex %r %r %r" % v for v in t]
        lines += ["endloop", "endfacet"]
    ascii_path.write_text("\n".join(lines + ["endsolid t"]))
    assert fileio.read_stl(str(ascii_path)) == [tuple(t) for t in tris[:50]]


def test_section_profile_of_own_coupon_equals_its_outline(tmp_path):
    p, d = make(coupon_rim_height=14.0)
    path, _ = write_coupon_stl(tmp_path, p, d)
    ref = reference.load_reference(own_spec(p, d, 14.0), path)
    depths = reference.frange(0.5, ref.depth - 0.5, 0.5)
    theirs = ref.profile(2.0, depths)
    ring = reference.ring_segments(
        layout.shelf_outline(p, d, d.z_top - 2.0).ring(p.arc_segments_per_90), d.y_front)
    ours = reference.extents_profile(ring, depths)
    worst = max(max(abs(o[0] - t[0]), abs(o[1] - t[1])) for o, t in zip(ours, theirs))
    # the coupon's rim is a straight ruled face between its top and bottom
    # outlines; the curved wall differs from it by up to h^2 / (8 R) ~ 0.05 mm
    assert worst < 0.05


def test_compare_reports_signed_deviation(tmp_path):
    p, d = make(coupon_rim_height=14.0)
    path, _ = write_coupon_stl(tmp_path, p, d)
    ref = reference.load_reference(own_spec(p, d, 14.0), path)
    wider, dw = make(coupon_rim_height=14.0, side_gap=p.side_gap - 1.0)  # 1 mm wider per side
    s = reference.compare(wider, dw, ref).stats("sides")
    assert s["max_out"] == pytest.approx(1.0, abs=0.1)  # positive = sticks out
    assert s["max_in"] == pytest.approx(1.0, abs=0.1)


def test_nelder_mead_finds_a_minimum():
    x, val = reference.nelder_mead(lambda v: (v[0] - 3) ** 2 + 10 * (v[1] + 1) ** 2, [0, 0], [1, 1])
    assert x == pytest.approx([3, -1], abs=1e-3)


def write_tube_stl(tmp_path, p, d, height):
    """A thin-walled tube following our shelf outline from z_top down by
    ``height``, with a ring every 2 mm, so its walls carry the wall curvature
    (the coupon only has rings at the top and bottom of its rim)."""
    zs = [d.z_top - k * 2.0 for k in range(int(height / 2.0) + 1)]
    outer = [[(x, y, z) for x, y in layout.shelf_outline(p, d, z).ring(32)] for z in zs]
    inner = [[(x, y, z) for x, y in layout.shelf_outline(p, d, z, 2.0).ring(32)]
             for z in reversed(zs)]
    m = meshing.sweep_rings(outer + inner)
    assert meshing.check_closed(m) == []
    path = str(tmp_path / "tube.stl")
    fileio.write_stl(path, m.vertices, m.faces)
    return path


TRUE = dict(W_ref=228.0, z_ref=55.0, wall_lean_deg=5.0, wall_radius=400.0, W_rear_delta=-7.0,
            rear_corner_length=25.0, rear_corner_inset=5.0, rear_corner_r_side=50.0,
            rear_corner_r_back=10.0, side_gap=0.0, envelope_offset=0.0, port_notch_width=0.0,
            corner_radius_front=0.0, shelf_height=70.0, H_cubby=80.0, D_cubby=125.0,
            front_recess=8.0, rear_gap=1.0)


@pytest.mark.parametrize("radius", [400.0, 0.0])
def test_fit_recovers_known_parameters(tmp_path, radius):
    p, d = make(**dict(TRUE, wall_radius=radius))
    path = write_tube_stl(tmp_path, p, d, 60.0)
    ref = reference.load_reference(own_spec(p, d, 60.0), path)
    values, quality = reference.fit_params(ref, z_ref=55.0)
    assert values["D_cubby"] == pytest.approx(125.0, abs=0.01)
    assert values["W_ref"] == pytest.approx(228.0, abs=0.05)
    assert values["wall_lean_deg"] == pytest.approx(5.0, abs=0.05)
    if radius:
        assert values["wall_radius"] == pytest.approx(radius, rel=0.05)
    else:
        assert values["wall_radius"] == 0.0  # straight walls come back as straight
    assert values["W_rear_delta"] == pytest.approx(-7.0, abs=0.05)
    assert quality["walls"]["max_abs"] < 0.03
    assert quality["rear_corners"]["max_abs"] < 0.2


def test_reference_params_file_is_valid():
    with open(REF_PARAMS, encoding="utf-8") as f:
        doc = json.load(f)
    for key in ("_source", "_model", "_assumptions", "_fit"):
        assert key in doc
    p = params.load_params(REF_PARAMS)
    assert not checks.has_errors(checks.run_checks(p, params.derive(p)))


def test_defaults_are_the_fitted_values():
    with open(REF_PARAMS, encoding="utf-8") as f:
        fitted = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    spec = params.load_spec()
    assert {k: spec[k]["value"] for k in fitted} == fitted
    assert all(spec[k].get("basis") == "reference" for k in fitted if k != "z_ref")


# --------------------------------------------------------------------------
# against the reference model itself (skips when the file is absent)
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def refmodel():
    path = reference.find_reference_file(reference.CUBBY_REFERENCE)
    if path is None:
        pytest.skip("reference/cubby-constraint-reference-model.stl is not there (third-party "
                    "file, kept out of the repo)")
    try:
        return reference.load_reference(reference.CUBBY_REFERENCE, path)
    except reference.ReferenceError as exc:
        pytest.skip(str(exc))


def test_reference_file_is_the_analysed_one(refmodel):
    assert refmodel.width == pytest.approx(235.20, abs=0.05)
    assert refmodel.depth == pytest.approx(120.88, abs=0.05)
    prof = refmodel.profile(22.0, reference.frange(5, 110, 5))
    assert max(abs(lo + hi) for lo, hi in prof) < 0.05  # symmetric about the centreline


def test_envelope_matches_reference_model(refmodel):
    """The default envelope (about 15 numbers) approximates the reference
    model's outer surface: side walls over their full height, rear corners
    and roof."""
    rep = reference.envelope_report(params.load_params(), refmodel)
    lines = "\n".join(reference.envelope_lines(rep))
    assert rep["walls"]["n"] > 1000 and rep["walls"]["rms"] < 0.2, lines
    assert rep["walls"]["max_abs"] < 1.0, lines
    assert rep["rear_corners"]["max_abs"] < 0.6, lines
    assert rep["roof"]["rms"] < 0.15 and rep["roof"]["max_abs"] < 1.0, lines


def test_shelf_band_matches_reference_model(refmodel):
    p = params.load_params()  # side_gap 0, envelope_offset 0: the envelope's own size
    c = reference.compare(p, params.derive(p), refmodel)
    sides = c.stats("sides")
    assert sides["n"] > 300 and sides["max_abs"] < 0.5, "\n".join(c.summary_lines())


def test_reference_params_file_is_up_to_date(refmodel):
    values, _ = reference.fit_params(refmodel)
    with open(REF_PARAMS, encoding="utf-8") as f:
        stored = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    assert stored == pytest.approx(values, abs=0.011), \
        "re-run: python tools/rav4shelf.py reference --write-params params/cubby_reference_fit.json"


def test_measured_outline_is_close_to_reference_model(refmodel):
    """Guard against gross measuring errors: a shelf built from your
    measurements should be within 5 mm per side of the reference estimate."""
    if not os.path.isfile(params.MEASURED_PATH):
        pytest.skip("no params/measured.json yet")
    p = params.load_params(params.MEASURED_PATH)
    c = reference.compare(p, params.derive(p), refmodel)
    s = c.stats("sides")
    msg = ("your outline differs from the reference estimate by more than 5 mm per side. "
           "Check W_ref / wall_lean_deg / W_rear_delta, or your car has another dash variant.\n"
           + "\n".join(c.summary_lines()))
    assert -5.0 <= s["max_in"] and s["max_out"] <= 5.0, msg


def test_cli_reference_without_file(tmp_path, capsys):
    from rav4shelf import cli
    rc = cli.main(["reference", "--defaults-only", "--ref", str(tmp_path / "missing.stl"),
                   "-o", str(tmp_path)])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_cli_reference_with_file(refmodel, tmp_path, capsys):
    from rav4shelf import cli
    rc = cli.main(["reference", "--defaults-only", "--ref", refmodel.path, "-o", str(tmp_path),
                   "--write-params", str(tmp_path / "fitted.json")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "side walls" in out and "rear_corner_r_side" in out
    assert os.path.isfile(str(tmp_path / "reference_compare.svg"))
    assert json.load(open(str(tmp_path / "fitted.json"))) == json.load(open(REF_PARAMS))
