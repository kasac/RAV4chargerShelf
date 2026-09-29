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
        "W_top", "W_bottom", "D_cubby", "H_cubby", "H_ports_top", "X_ports",
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
    for name in ["W_top", "W_bottom", "D_cubby", "H_cubby", "H_ports_top", "X_ports",
                 "W_ports", "D_ports", "shelf_height"]:
        assert name in p.placeholders


def test_attribute_access_and_read_only(p):
    assert p.W_top == p["W_top"]
    with pytest.raises(AttributeError):
        p.W_top = 1.0
    with pytest.raises(AttributeError):
        p.not_a_param


def test_override_clears_placeholder_and_records_source(p):
    p2 = p.with_overrides({"W_top": 201.5}, "test")
    assert p2.W_top == 201.5
    assert "W_top" not in p2.placeholders
    assert p2.source("W_top") == "test"
    assert p.W_top != 201.5  # original untouched


def test_override_file_and_comments(tmp_path):
    f = tmp_path / "measured.json"
    f.write_text(json.dumps({"_note": "measured with calipers", "D_cubby": 131.0, "rib_count": 3.0}))
    p = params.load_params(str(f))
    assert p.D_cubby == 131.0
    assert p.rib_count == 3 and isinstance(p.rib_count, int)
    assert p.files == [str(f)]


@pytest.mark.parametrize("bad, fragment", [
    ({"W_topp": 1}, "unknown parameter"),
    ({"W_top": 10}, "outside"),
    ({"W_top": "wide"}, "must be a number"),
    ({"W_top": True}, "must be a number"),
    ({"rib_count": 2.5}, "whole number"),
    ({"grid_style": "stars"}, "must be one of"),
    ({"grid_enabled_shelf": "maybe"}, "true or false"),
    ({"W_top": None}, "may not be null"),
])
def test_invalid_overrides_raise(p, bad, fragment):
    with pytest.raises(params.ParamError) as exc:
        p.with_overrides(bad)
    assert fragment in str(exc.value)


def test_typo_suggestion(p):
    with pytest.raises(params.ParamError) as exc:
        p.with_overrides({"w_top": 190})
    assert "W_top" in str(exc.value)


def test_auto_params_accept_null_and_derive(p):
    p2 = p.with_overrides({"coupon_rim_height": None, "frame_height": 9.0})
    assert params.derive(p2).coupon_rim_height == 9.0
    p3 = p.with_overrides({"coupon_rim_height": 5.0})
    assert params.derive(p3).coupon_rim_height == 5.0


def test_gh_style_values_are_coerced(p):
    p2 = p.with_overrides({"grid_style": '"square"', "grid_enabled_shelf": 0, "W_top": "199.5"})
    assert p2.grid_style == "square"
    assert p2.grid_enabled_shelf is False
    assert p2.W_top == 199.5


def test_invalid_json_file(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not json")
    with pytest.raises(params.ParamError):
        params.load_params(str(f))


def test_cubby_width_model(p):
    p2 = p.with_overrides({"W_bottom": 190, "W_top": 200, "H_cubby": 100,
                           "W_rear_delta": -4, "D_cubby": 120})
    assert params.cubby_width(p2, params.MEAS_INSET, 0) == pytest.approx(190)
    assert params.cubby_width(p2, params.MEAS_INSET, 100) == pytest.approx(200)
    assert params.cubby_width(p2, params.MEAS_INSET, 50) == pytest.approx(195)
    assert params.cubby_width(p2, 120 - params.MEAS_INSET, 0) == pytest.approx(186)


def test_derived_values(p, d):
    assert d.z_top == p.shelf_height
    assert d.z_frame_bottom == pytest.approx(p.shelf_height - p.frame_height)
    assert d.shelf_depth == pytest.approx(p.D_cubby - p.front_recess - p.rear_gap)
    assert d.space_above == pytest.approx(p.H_cubby - p.shelf_height)
    w = params.cubby_width(p, d.y_front, d.z_top) - 2 * p.side_gap
    assert d.shelf_width_front_top == pytest.approx(w)
