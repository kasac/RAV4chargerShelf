import math
import json

import pytest

from rav4shelf import params


def test_spec_loads_and_every_default_is_valid():
    spec = params.load_spec()
    assert len(spec) > 40
    for name, s in spec.items():
        assert s["doc"], name


def test_brief_parameters_exist():
    spec = params.load_spec()
    required = [
        "W_ref", "wall_lean_deg", "wall_radius", "D_cubby", "H_cubby", "H_ports_top", "X_ports",
        "shelf_height", "front_recess", "port_notch_width", "port_notch_offset_x",
        "phone_clearance_min", "wall_thickness", "deck_thickness", "frame_width",
        "rib_count", "rib_height", "grid_style", "cell_size", "bar_width", "grid_angle",
        "grid_enabled_shelf", "grid_enabled_drawer_floor", "drawer_type", "drawer_height",
        "drawer_depth", "drawer_width", "hinge_position", "open_angle", "detent_strength",
        "pin_diameter", "clearance_sliding", "clearance_hinge", "clearance_press_fit",
    ]
    missing = [n for n in required if n not in spec]
    assert not missing
    assert set(["hex", "square", "diamond", "round", "slot"]) <= set(spec["grid_style"]["choices"])


def test_all_cubby_measurements_are_marked_placeholder(p):
    for name in ["W_ref", "wall_lean_deg", "D_cubby", "H_cubby", "H_ports_top", "X_ports",
                 "W_ports", "D_ports", "shelf_height"]:
        assert name in p.placeholders


def test_reference_based_values_are_the_fitted_cubby_values(p):
    fitted = set(p.reference_based)
    assert {"W_ref", "wall_radius", "rear_corner_length", "roof_pocket_rise"} <= fitted
    assert "H_ports_top" not in fitted and "shelf_height" not in fitted
    assert fitted <= set(p.placeholders)


def test_attribute_access_and_read_only(p):
    assert p.W_ref == p["W_ref"]
    with pytest.raises(AttributeError):
        p.W_ref = 1.0
    with pytest.raises(AttributeError):
        p.not_a_param


def test_override_clears_placeholder_and_records_source(p):
    p2 = p.with_overrides({"W_ref": 201.5}, "test")
    assert p2.W_ref == 201.5
    assert "W_ref" not in p2.placeholders and "W_ref" not in p2.reference_based
    assert p2.source("W_ref") == "test"
    assert p.W_ref != 201.5  # original untouched


def test_override_file_and_comments(tmp_path):
    f = tmp_path / "measured.json"
    f.write_text(json.dumps({"_note": "measured with calipers", "D_cubby": 131.0, "rib_count": 3.0}))
    p = params.load_params(str(f))
    assert p.D_cubby == 131.0
    assert p.rib_count == 3 and isinstance(p.rib_count, int)
    assert p.files == [str(f)]


@pytest.mark.parametrize("bad, fragment", [
    ({"W_reff": 1}, "unknown parameter"),
    ({"W_ref": 10}, "outside"),
    ({"W_ref": "wide"}, "must be a number"),
    ({"W_ref": True}, "must be a number"),
    ({"rib_count": 2.5}, "whole number"),
    ({"grid_style": "stars"}, "must be one of"),
    ({"grid_enabled_shelf": "maybe"}, "true or false"),
    ({"W_ref": None}, "may not be null"),
])
def test_invalid_overrides_raise(p, bad, fragment):
    with pytest.raises(params.ParamError) as exc:
        p.with_overrides(bad)
    assert fragment in str(exc.value)


def test_typo_suggestion(p):
    with pytest.raises(params.ParamError) as exc:
        p.with_overrides({"w_ref": 230})
    assert "W_ref" in str(exc.value)


def test_auto_params_accept_null_and_derive(p):
    p2 = p.with_overrides({"coupon_rim_height": None, "frame_height": 9.0})
    assert params.derive(p2).coupon_rim_height == 9.0
    p3 = p.with_overrides({"coupon_rim_height": 5.0})
    assert params.derive(p3).coupon_rim_height == 5.0


def test_gh_style_values_are_coerced(p):
    p2 = p.with_overrides({"grid_style": '"square"', "grid_enabled_shelf": 0, "W_ref": "199.5"})
    assert p2.grid_style == "square"
    assert p2.grid_enabled_shelf is False
    assert p2.W_ref == 199.5


def test_invalid_json_file(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not json")
    with pytest.raises(params.ParamError):
        params.load_params(str(f))


def test_cubby_width_model(p):
    m = params.MEAS_INSET
    p2 = p.with_overrides({"W_ref": 200, "z_ref": 50, "wall_lean_deg": 5.0, "wall_radius": 0,
                           "W_rear_delta": -4, "D_cubby": 120, "envelope_offset": 0})
    assert params.cubby_width(p2, m, 50) == pytest.approx(200)
    # straight wall: 2 x tan(5 deg) per mm of height
    assert params.cubby_width(p2, m, 60) == pytest.approx(200 + 20 * math.tan(math.radians(5)))
    assert params.cubby_width(p2, 120 - m, 50) == pytest.approx(196)
    assert params.cubby_width(p2.with_overrides({"envelope_offset": 1.5}), m, 50) == pytest.approx(203)


def test_curved_wall_has_the_given_lean_and_radius(p):
    p2 = p.with_overrides({"z_ref": 50, "wall_lean_deg": 6.0, "wall_radius": 500})
    h = 1e-3
    slope = (params.wall_offset(p2, 50 + h) - params.wall_offset(p2, 50 - h)) / (2 * h)
    assert params.wall_offset(p2, 50) == pytest.approx(0, abs=1e-9)
    assert math.degrees(math.atan(slope)) == pytest.approx(6.0, abs=1e-4)
    # curvature of x(z) at z_ref equals 1/R (projected): x'' = -1/(R cos^3)
    curv = (params.wall_offset(p2, 50 + 1) - 2 * params.wall_offset(p2, 50)
            + params.wall_offset(p2, 50 - 1))
    assert curv == pytest.approx(-1 / (500 * math.cos(math.radians(6)) ** 3), rel=1e-3)
    # it curves inward toward the floor: lower = narrower than the tangent line
    assert params.wall_offset(p2, 0) < -50 * slope


def test_wall_outside_its_arc_raises(p):
    with pytest.raises(params.ParamError):
        params.wall_offset(p.with_overrides({"wall_radius": 30}), 0.0)


def test_roof_pocket(p):
    p2 = p.with_overrides({"H_cubby": 78, "roof_pocket_width": 100, "roof_pocket_blend": 10,
                           "roof_pocket_rise": 12, "roof_pocket_end": 110, "roof_pocket_shape": 1})
    assert params.roof_height(p2, 0, params.MEAS_INSET) == pytest.approx(90)
    assert params.roof_height(p2, 0, 60) == pytest.approx(84)       # linear ramp
    assert params.roof_height(p2, 0, 115) == pytest.approx(78)      # behind the pocket
    assert params.roof_height(p2, 55, params.MEAS_INSET) == pytest.approx(84)  # half-way blend
    assert params.roof_height(p2, 70, 20) == pytest.approx(78)      # beside it
    assert params.roof_height(p2.with_overrides({"roof_pocket_width": 0}), 0, 10) == 78


def test_derived_values(p, d):
    assert d.z_top == p.shelf_height
    assert d.z_frame_bottom == pytest.approx(p.shelf_height - p.frame_height)
    assert d.shelf_depth == pytest.approx(p.D_cubby - p.front_recess - p.rear_gap)
    assert d.space_above == pytest.approx(p.H_cubby - p.shelf_height)
    w = params.cubby_width(p, d.y_front, d.z_top) - 2 * p.side_gap
    assert d.shelf_width_front_top == pytest.approx(w)
