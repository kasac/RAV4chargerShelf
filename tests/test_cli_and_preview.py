import json
import os
import xml.etree.ElementTree as ET

from rav4shelf import checks, cli, preview_svg


def test_cli_all_writes_files(tmp_path, capsys):
    rc = cli.main(["all", "--defaults-only", "-o", str(tmp_path)])
    assert rc == 0
    names = set(os.listdir(str(tmp_path)))
    assert {"fit_coupon.stl", "fit_coupon.3mf", "overview.svg", "fit_template_1to1.svg",
            "report.txt"} <= names
    assert "PLACEHOLDER" in capsys.readouterr().out


def test_cli_uses_override_file(tmp_path, capsys):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({"D_cubby": 140.0, "front_recess": 8.0, "rear_gap": 1.0}))
    rc = cli.main(["check", "--defaults-only", "-p", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert str(f) in out
    assert "131.00" in out  # shelf depth = 140 - 8 - 1


def test_cli_refuses_coupon_on_error(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"shelf_height": 80.0, "H_cubby": 75.0}))
    rc = cli.main(["coupon", "--defaults-only", "-p", str(f), "-o", str(tmp_path)])
    assert rc == 1
    assert not os.path.exists(os.path.join(str(tmp_path), "fit_coupon.stl"))


def test_cli_bad_param_file(tmp_path):
    f = tmp_path / "typo.json"
    f.write_text(json.dumps({"Wtop": 1}))
    assert cli.main(["check", "--defaults-only", "-p", str(f)]) == 2


def test_svgs_are_well_formed(p, d):
    findings = checks.run_checks(p, d)
    for svg in (preview_svg.overview_svg(p, d, findings), preview_svg.fit_template_svg(p, d)):
        root = ET.fromstring(svg.encode("utf-8"))
        assert root.tag.endswith("svg")


def test_template_is_true_scale(p, d):
    root = ET.fromstring(preview_svg.fit_template_svg(p, d).encode("utf-8"))
    w_mm = float(root.get("width").replace("mm", ""))
    vb_w = float(root.get("viewBox").split()[2])
    assert w_mm == vb_w  # 1 user unit = 1 mm
