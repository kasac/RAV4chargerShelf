"""Outer-boundary comparison with a tested reference design (Vela3D).

The Vela3D STL is a paid download and is not in the repo, so the tests that
need it skip on CI. Put TOYOTA_RAV4_TRAY_DRAWER_ORGANIZER_MODULE.stl into
reference/ to run them locally. The machinery itself is tested on CI with
meshes this project generates.
"""
import json
import os

import pytest

from rav4shelf import checks, fileio, layout, meshing, params, reference

from conftest import REPO, make

REF_PARAMS = os.path.join(REPO, "params", "reference_vela3d.json")


def own_spec(compare_level, floor_level, roof_level, rear_zone=30.0):
    """Placement for meshes made by this project, already in the car frame:
    depth from the front edge (min y), level measured down from the top."""
    return reference.ReferenceSpec(
        "own mesh", "*.stl", 0.0, None, x_axis=0, depth_axis=1, depth_sign=1,
        level_axis=2, level_sign=-1, compare_level=compare_level,
        floor_level=floor_level, roof_level=roof_level, rear_zone=rear_zone)


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
    spec = own_spec(compare_level=2.0, floor_level=d.z_top, roof_level=d.z_top - p.H_cubby)
    ref = reference.load_reference(spec, path)
    depths = reference.frange(0.5, ref.depth - 0.5, 0.5)
    theirs = ref.profile(2.0, depths)
    ring = reference.ring_segments(
        layout.shelf_outline(p, d, d.z_top - 2.0).ring(p.arc_segments_per_90), d.y_front)
    ours = reference.extents_profile(ring, depths)
    worst = max(max(abs(o[0] - t[0]), abs(o[1] - t[1])) for o, t in zip(ours, theirs))
    assert worst < 0.01


def test_compare_reports_signed_deviation(tmp_path):
    p, d = make(coupon_rim_height=14.0)
    path, _ = write_coupon_stl(tmp_path, p, d)
    ref = reference.load_reference(own_spec(2.0, d.z_top, d.z_top - p.H_cubby), path)
    wider, dw = make(coupon_rim_height=14.0, side_gap=p.side_gap - 1.0)  # 1 mm wider per side
    s = reference.compare(wider, dw, ref).stats("sides")
    assert s["max_out"] == pytest.approx(1.0, abs=0.1)  # positive = sticks out
    assert s["max_in"] > 0.8


def test_fit_recovers_known_parameters(tmp_path):
    true = dict(W_top=228.0, W_bottom=212.0, H_cubby=80.0, shelf_height=56.0, W_rear_delta=-7.0,
                R_rear_corner=15.0, side_gap=0.0, port_notch_width=0.0, corner_radius_front=1.0,
                coupon_rim_height=16.0, frame_height=8.0, D_cubby=125.0, front_recess=8.0,
                rear_gap=1.0, W_lip=240.0, arc_segments_per_90=32)
    p, d = make(**true)
    path, _ = write_coupon_stl(tmp_path, p, d)
    # level 2 below the coupon top; floor at level shelf_height; roof H_cubby above the floor
    spec = own_spec(compare_level=2.0, floor_level=56.0, roof_level=56.0 - 80.0)
    values, quality = reference.fit_params(reference.load_reference(spec, path))
    assert values["D_cubby"] == pytest.approx(125.0, abs=0.01)
    assert values["W_rear_delta"] == pytest.approx(-7.0, abs=0.3)
    assert values["R_rear_corner"] == pytest.approx(15.0, abs=0.6)
    assert values["W_top"] - values["W_bottom"] == pytest.approx(16.0, abs=0.5)
    assert quality["sides"]["max_abs"] < 0.1
    assert quality["rear_corners"]["max_abs"] < 0.3
    # the fitted outline at its shelf top equals the true outline 2 mm below the true top
    fp = params.load_params(values)
    fd = params.derive(fp)
    assert fd.shelf_width_front_top == pytest.approx(
        params.cubby_width(p, d.y_front, 54.0), abs=0.3)


def test_reference_params_file_is_valid():
    p = params.load_params(REF_PARAMS)
    d = params.derive(p)
    assert not checks.has_errors(checks.run_checks(p, d))
    for key in ("_source", "_meaning", "_assumptions", "_fit"):
        assert key in json.load(open(REF_PARAMS, encoding="utf-8"))


# --------------------------------------------------------------------------
# against the real Vela3D model (skips when the paid file is absent)
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def vela3d():
    path = reference.find_reference_file(reference.VELA3D_MODULE)
    if path is None:
        pytest.skip("Vela3D MODULE.stl is not in reference/ (paid file, kept out of the repo)")
    try:
        return reference.load_reference(reference.VELA3D_MODULE, path)
    except reference.ReferenceError as exc:
        pytest.skip(str(exc))


def test_vela3d_file_is_the_analysed_one(vela3d):
    assert vela3d.width == pytest.approx(235.20, abs=0.05)
    assert vela3d.depth == pytest.approx(120.88, abs=0.05)
    # symmetric about the centreline
    prof = vela3d.profile(22.0, reference.frange(5, 110, 5))
    assert max(abs(lo + hi) for lo, hi in prof) < 0.05


def test_generated_outline_matches_vela3d(vela3d):
    """Our generator, fed with params/reference_vela3d.json, reproduces the
    tested outline: sides within 0.5 mm, rear corners within 2 mm (a single
    circular fillet vs Vela3D's free-form corner)."""
    p = params.load_params(REF_PARAMS)
    c = reference.compare(p, params.derive(p), vela3d)
    assert c.depth_ours == pytest.approx(c.depth_ref, abs=0.05)
    sides, rear = c.stats("sides"), c.stats("rear corners")
    assert sides["n"] > 300 and rear["n"] > 50
    assert sides["max_abs"] <= 0.5, "\n".join(c.summary_lines())
    assert rear["max_abs"] <= 2.0, "\n".join(c.summary_lines())


def test_reference_params_file_is_up_to_date(vela3d):
    values, _ = reference.fit_params(vela3d)
    with open(REF_PARAMS, encoding="utf-8") as f:
        stored = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    assert stored == pytest.approx(values, abs=0.011), \
        "re-run: python tools/rav4shelf.py reference --write-params params/reference_vela3d.json"


def test_measured_outline_is_close_to_vela3d(vela3d):
    """Guard against gross measuring errors: a shelf built from your
    measurements should be within 5 mm per side of the tested design."""
    if not os.path.isfile(params.MEASURED_PATH):
        pytest.skip("no params/measured.json yet")
    p = params.load_params(params.MEASURED_PATH)
    c = reference.compare(p, params.derive(p), vela3d)
    s = c.stats("sides")
    msg = ("your outline differs from the tested Vela3D outline by more than 5 mm per side. "
           "Check W_top / W_bottom / W_rear_delta, or your car has the other dash variant.\n"
           + "\n".join(c.summary_lines()))
    assert -5.0 <= s["max_in"] and s["max_out"] <= 5.0, msg


def test_cli_reference_without_file(tmp_path, capsys):
    from rav4shelf import cli
    rc = cli.main(["reference", "--defaults-only", "--ref", str(tmp_path / "missing.stl"),
                   "-o", str(tmp_path)])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_cli_reference_with_file(vela3d, tmp_path, capsys):
    from rav4shelf import cli
    rc = cli.main(["reference", "--defaults-only", "--ref", vela3d.path, "-o", str(tmp_path),
                   "--write-params", str(tmp_path / "fitted.json")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "sticks out" in out and "R_rear_corner" in out
    assert os.path.isfile(str(tmp_path / "reference_compare.svg"))
    assert json.load(open(str(tmp_path / "fitted.json"))) == json.load(open(REF_PARAMS))
