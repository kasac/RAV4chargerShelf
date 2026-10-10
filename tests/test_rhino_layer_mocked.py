"""Run the Rhino / Grasshopper glue against mocked Rhino, System and
Grasshopper modules. This cannot prove the RhinoCommon calls are right (that
needs Rhino), but it executes every line of our own logic, so typos, wrong
parameter names and broken call flow show up on CI instead of in Rhino.
"""
import os
import sys
from unittest import mock

import pytest

import rav4shelf
from rav4shelf import params

RHINO_MODS = ["rav4shelf.geometry", "rav4shelf.export", "rav4shelf.gh"]


def _forget_rhino_modules():
    """Drop the Rhino-layer modules so the next import binds to fresh mocks
    (both the sys.modules entry and the attribute on the package)."""
    for name in RHINO_MODS:
        sys.modules.pop(name, None)
        short = name.split(".")[-1]
        if hasattr(rav4shelf, short):
            delattr(rav4shelf, short)


@pytest.fixture
def fake(monkeypatch):
    rhino = mock.MagicMock(name="Rhino")
    system = mock.MagicMock(name="System")
    grasshopper = mock.MagicMock(name="Grasshopper")
    modules = {
        "Rhino": rhino,
        "Rhino.Geometry": rhino.Geometry,
        "Rhino.DocObjects": rhino.DocObjects,
        "System": system,
        "System.Collections": system.Collections,
        "System.Collections.Generic": system.Collections.Generic,
        "System.Drawing": system.Drawing,
        "Grasshopper": grasshopper,
        "Grasshopper.Kernel": grasshopper.Kernel,
        "Grasshopper.Kernel.Special": grasshopper.Kernel.Special,
        "Grasshopper.GUI": grasshopper.GUI,
        "Grasshopper.GUI.Base": grasshopper.GUI.Base,
    }
    for name, mod in modules.items():
        monkeypatch.setitem(sys.modules, name, mod)
    _forget_rhino_modules()
    yield mock.Mock(rhino=rhino, rg=rhino.Geometry, gh=grasshopper, system=system)
    _forget_rhino_modules()


def _solid():
    b = mock.MagicMock(name="brep")
    b.IsSolid = True
    b.IsValid = True
    return b


def _setup_booleans(rg, boolean_ok=True):
    loft = mock.MagicMock(name="loft")
    loft.CapPlanarHoles.return_value = _solid()
    rg.Brep.CreateFromLoft.return_value = [loft]
    rg.Brep.CreateBooleanDifference.return_value = [_solid()] if boolean_ok else None
    rg.Brep.CreatePlanarBreps.return_value = [_solid()]
    rg.Brep.JoinBreps.return_value = [_solid()]
    pc = rg.PolyCurve.return_value
    pc.Append.return_value = True
    pc.IsClosed = True
    return pc


def test_build_fit_coupon_boolean_path(fake):
    from rav4shelf import geometry, layout
    pc = _setup_booleans(fake.rg)
    p = params.load_params()
    d = params.derive(p)
    brep, method = geometry.build_fit_coupon(p, d)
    assert method == "boolean"
    assert fake.rg.Brep.CreateFromLoft.call_count == 3
    # 6 outline curves, each appended segment by segment
    n_segs = sum(len(layout.shelf_outline(p, d, z, i).segments())
                 for i, z in [(0, 0), (0, 0), (p.coupon_rim_width, 0), (p.coupon_rim_width, 0),
                              (p.coupon_flange_width, 0), (p.coupon_flange_width, 0)])
    assert pc.Append.call_count == n_segs
    zs = {round(c.args[2], 6) for c in fake.rg.Point3d.call_args_list if len(c.args) == 3}
    top, t, h = d.z_top, p.coupon_plate_thickness, d.coupon_rim_height
    e = geometry.CUTTER_OVERSHOOT
    assert {round(z, 6) for z in (top, top - h, top - h - e, top - t, top + e)} <= zs
    assert geometry.check_solid(brep, "x") == []


def test_build_fit_coupon_falls_back_to_joined_faces(fake):
    from rav4shelf import geometry
    _setup_booleans(fake.rg, boolean_ok=False)
    p = params.load_params()
    brep, method = geometry.build_fit_coupon(p, params.derive(p))
    assert method.startswith("joined faces")
    # 6 profile edges: 3 horizontal ring faces + 3 walls
    assert fake.rg.Brep.CreatePlanarBreps.call_count == 3
    assert fake.rg.Brep.JoinBreps.call_count == 1


def test_build_profile_gauge(fake):
    from rav4shelf import geometry
    _setup_booleans(fake.rg)
    p = params.load_params()
    flat, standing, method = geometry.build_profile_gauge(p, params.derive(p))
    assert method == "boolean"
    assert fake.rg.Brep.CreateFromLoft.call_count == 2  # outer plate + window cutter
    assert fake.rg.Brep.CreateBooleanDifference.call_count == 1
    fake.rg.Transform.Rotation.assert_called_once()     # stood up into the car frame


def test_build_envelope(fake):
    from rav4shelf import geometry, layout
    _setup_booleans(fake.rg)
    p = params.load_params()
    geometry.build_envelope(p, params.derive(p))
    curves = fake.rg.Brep.CreateFromLoft.call_args.args[0]
    assert curves.Add.call_count == len(layout.envelope_levels(p))  # one section per level


def test_build_roof_plate_and_component(fake):
    from rav4shelf import geometry, gh, meshing
    p = params.load_params()
    mesh, pure = geometry.build_roof_plate(p, params.derive(p))
    assert meshing.check_closed(pure) == []
    assert mesh.Vertices.Add.call_count == len(pure.vertices)
    assert mesh.Faces.AddFace.call_count == len(pure.faces)
    _, report = gh.roof_plate_component(p)
    assert "roof_plate:" in report and "closed mesh: OK" in report


def test_profile_gauge_component(fake):
    from rav4shelf import gh
    _setup_booleans(fake.rg)
    fake.rg.VolumeMassProperties.Compute.return_value.Volume = 9000.0
    standing, flat, report = gh.profile_gauge_component(params.load_params())
    assert "profile_gauge" in report and "9.0 cm3" in report


def test_check_solid_reports_problems(fake):
    from rav4shelf import geometry
    b = mock.MagicMock()
    b.IsValid = False
    b.IsSolid = False
    b.IsValidWithLog.return_value = (False, "bad trim")
    msgs = geometry.check_solid(b, "part")
    assert len(msgs) == 2 and "bad trim" in msgs[0]
    assert geometry.check_solid(None, "part")


def test_build_context(fake):
    from rav4shelf import geometry
    p = params.load_params()
    ctx = geometry.build_context(p, params.derive(p))
    assert set(ctx) == {"cubby", "ports", "phone", "led_keepout"}
    assert len(ctx["cubby"]) == 2 + 4
    assert len(ctx["led_keepout"]) == 2 + 4  # circles at pad and roof, four vertical lines
    p0 = p.with_overrides({"led_keepout_diameter": 0})
    assert geometry.build_context(p0, params.derive(p0))["led_keepout"] == []


def _gh_source(nick, value):
    src = mock.MagicMock()
    src.NickName = nick
    goo = mock.MagicMock()
    goo.ScriptVariable.return_value = value
    src.VolatileData.AllData.return_value = [goo]
    return src


def _gh_component(fake, sources, extra_inputs=()):
    s_input = mock.MagicMock()
    s_input.NickName = "S"
    s_input.Sources = sources
    s_input.SourceCount = len(sources)
    s_input.Access = fake.gh.Kernel.GH_ParamAccess.list
    comp = mock.MagicMock()
    comp.Params.Input = [s_input] + list(extra_inputs)
    return comp


def test_params_component_reads_named_sliders(fake):
    from rav4shelf import gh
    fake.rhino.RhinoDoc.ActiveDoc.ModelUnitSystem = fake.rhino.UnitSystem.Millimeters
    extra = _gh_source("D_cubby", 133.0)  # an input named like a parameter
    comp = _gh_component(fake, [_gh_source("W_ref", 231.0), _gh_source("perforation_style", "diamond"),
                                _gh_source("Slider", 5.0)], [extra])
    P, report = gh.params_component(comp)
    assert P.W_ref == 231.0
    assert P.perforation_style == "diamond"
    assert P.D_cubby == 133.0
    assert "Ignored" in report and "Slider" in report
    assert "not millimetres" not in report


def test_params_component_warns_about_item_access_and_units(fake):
    from rav4shelf import gh
    comp = _gh_component(fake, [_gh_source("W_ref", 231.0), _gh_source("wall_lean_deg", 6.0)])
    comp.Params.Input[0].Access = "item"
    P, report = gh.params_component(comp)
    assert "List Access" in report
    assert "not millimetres" in report  # ModelUnitSystem is a mock, not Millimeters


def test_slider_bank_schedules_all_missing(fake):
    from rav4shelf import gh
    comp = _gh_component(fake, [_gh_source("W_ref", 231.0)])
    p = params.load_params()
    n = gh.schedule_slider_bank(comp, p, ["cubby"])
    cubby = [k for k, s in p.spec.items() if s["group"] == "cubby"]
    assert n == len(cubby) - 1  # W_ref is already wired
    # run the scheduled callback and check every object got wired
    delegate = fake.gh.Kernel.GH_Document.GH_ScheduleDelegate
    callback = delegate.call_args.args[0]
    gh_doc = mock.MagicMock()
    callback(gh_doc)
    assert gh_doc.AddObject.call_count == n
    assert comp.Params.Input[0].AddSource.call_count == n


def test_breps_to_triangles_and_export(fake, tmp_path):
    from rav4shelf import export
    # a tetrahedron as the "Rhino mesh"
    pts = [(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10)]
    tris = [(0, 2, 1), (0, 1, 3), (1, 2, 3), (0, 3, 2)]
    mesh = mock.MagicMock()
    mesh.Vertices.Count = len(pts)
    mesh.Vertices.__getitem__.side_effect = lambda i: mock.Mock(X=pts[i][0], Y=pts[i][1], Z=pts[i][2])
    mesh.Faces.Count = len(tris)
    mesh.Faces.__getitem__.side_effect = lambda i: mock.Mock(A=tris[i][0], B=tris[i][1], C=tris[i][2])
    fake.rg.Mesh.return_value = mesh
    fake.rg.Mesh.CreateFromBrep.return_value = [mock.MagicMock()]
    verts, faces = export.breps_to_triangles([mock.MagicMock()])
    assert len(verts) == 4 and len(faces) == 4
    paths, msgs = export.export_part("tetra", [mock.MagicMock()], str(tmp_path), ("stl", "3mf"))
    assert msgs == []
    assert sorted(os.path.basename(x) for x in paths) == ["tetra.3mf", "tetra.stl"]


def test_export_component_needs_button(fake):
    from rav4shelf import gh
    assert "press the button" in gh.export_component("fit_coupon", [mock.MagicMock()], None, False)
    assert gh.export_component("fit_coupon", [], None, True) == "nothing to export"
