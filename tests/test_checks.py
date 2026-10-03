import pytest

from rav4shelf import checks, params

from conftest import make


def codes(findings, level=None):
    return {f.code for f in findings if level is None or f.level == level}


def test_defaults_have_no_errors_but_flag_placeholders(p, d):
    f = checks.run_checks(p, d)
    assert not checks.has_errors(f)
    assert {"placeholders", "unconfirmed_reference"} <= codes(f, "warning")
    msg = [x.message for x in f if x.code == "unconfirmed_reference"][0]
    assert "W_ref" in msg and "H_ports_top" not in msg


def test_measured_everything_clears_placeholder_warnings(p):
    all_ph = {n: p[n] for n in p.placeholders}
    p2, d2 = make(**all_ph)
    found = codes(checks.run_checks(p2, d2))
    assert "placeholders" not in found and "unconfirmed_reference" not in found


def test_wall_arc_too_small_is_reported():
    p, d = make(wall_radius=60.0, wall_lean_deg=30.0)  # valid at the shelf, not at the floor
    found = checks.run_checks(p, d)
    assert codes(found, "error") == {"wall_arc"}
    with pytest.raises(params.ParamError):
        make(wall_radius=5.0)  # not even valid at the shelf band


def test_tall_adapter_without_notch_is_flagged():
    # the D-Lumina lesson: a long 12 V adapter sticks up into the shelf
    p, d = make(H_ports_top=50.0, port_notch_width=0.0)
    assert "ports_collide" in codes(checks.run_checks(p, d), "warning")


def test_notch_too_shallow_is_flagged():
    p, d = make(H_ports_top=50.0, D_ports=70.0, port_notch_depth=30.0)
    f = [x for x in checks.run_checks(p, d) if x.code == "ports_collide"]
    assert f and "deepen port_notch_depth" in f[0].message


def test_notch_that_clears_the_plugs_passes():
    p, d = make(H_ports_top=50.0, D_ports=40.0, W_ports=50.0, port_notch_width=60.0,
                port_notch_depth=48.0)
    assert "ports_in_notch" in codes(checks.run_checks(p, d), "info")


def test_shelf_above_roof_is_an_error():
    p, d = make(shelf_height=80.0, H_cubby=75.0)
    assert "shelf_above_roof" in codes(checks.run_checks(p, d), "error")


def test_phone_clearance():
    p, d = make(shelf_height=25.0, frame_height=8.0, phone_clearance_min=20.0)
    assert "phone_clearance" in codes(checks.run_checks(p, d), "warning")


def test_thin_bars_warn():
    p, d = make(bar_width=0.8, min_bar_width=0.9)
    assert "thin_bar_width" in codes(checks.run_checks(p, d), "warning")


def test_geometry_error_becomes_finding():
    p, d = make(port_notch_width=195.0)
    assert "geometry" in codes(checks.run_checks(p, d), "error")


def test_report_mentions_key_numbers(p, d):
    text = checks.format_report(p, d, checks.run_checks(p, d))
    assert "shelf top z" in text and "PLACEHOLDER" in text
