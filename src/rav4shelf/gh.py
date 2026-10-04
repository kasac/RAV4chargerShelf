"""Grasshopper glue. Each GH Script component (rhino/gh_components/*.py) is a
thin wrapper that calls exactly one function from here.

Parameters reach the Params component in two ways; both use the NickName of
the object as the parameter name:
  * any number of sliders / value lists / toggles wired into its input "S"
    (the slider's NickName must be the parameter name, e.g. "W_top");
  * an extra input whose NickName is a parameter name.
Precedence: default.json < params/measured.json < overrides file < GH values.

NOT YET RUN IN GRASSHOPPER: see the first-run checklist in README.md.
"""
from __future__ import annotations

import os

import Rhino

from . import checks, export, geometry, layout, params

SLIDER_INPUT = "S"


# --------------------------------------------------------------------------
# reading named inputs
# --------------------------------------------------------------------------

def _first_value(gh_param):
    for goo in gh_param.VolatileData.AllData(True):
        if goo is None:
            continue
        try:
            return goo.ScriptVariable()
        except Exception:
            return getattr(goo, "Value", None)
    return None


def read_named_inputs(component, spec):
    """({name: value}, [ignored nicknames], [notes]) from the component inputs."""
    from Grasshopper.Kernel import GH_ParamAccess

    values, ignored, notes = {}, [], []
    for prm in component.Params.Input:
        nick = prm.NickName
        if nick == SLIDER_INPUT:
            if prm.SourceCount > 1 and prm.Access != GH_ParamAccess.list:
                notes.append("set input '%s' to List Access (right-click it), otherwise the "
                             "component runs once per slider" % SLIDER_INPUT)
            for src in prm.Sources:
                value = _first_value(src)
                if value is None:
                    continue
                if src.NickName in spec:
                    values[src.NickName] = value
                else:
                    ignored.append(src.NickName)
        elif nick in spec:
            value = _first_value(prm)
            if value is not None:
                values[nick] = value
    return values, ignored, notes


# --------------------------------------------------------------------------
# components
# --------------------------------------------------------------------------

def params_component(component, overrides_path=None, make_sliders=False, groups=None):
    """Params component -> (P, report)."""
    files = params.default_override_paths()
    if overrides_path:
        files.append(overrides_path)
    p = params.load_params(*files)
    gh_values, ignored, notes = read_named_inputs(component, p.spec)
    if gh_values:
        p = p.with_overrides(gh_values, "grasshopper")
    d = params.derive(p)
    report = checks.format_report(p, d, checks.run_checks(p, d))
    if gh_values:
        report += "\nFrom Grasshopper: %s\n" % ", ".join(sorted(gh_values))
    if ignored:
        report += "Ignored (NickName is not a parameter name): %s\n" % ", ".join(ignored)
    for note in notes:
        report += "NOTE: %s\n" % note
    units = export.check_units(Rhino.RhinoDoc.ActiveDoc)
    if units:
        report += "WARNING: %s\n" % units
    if make_sliders:
        wanted = [g.strip() for g in (groups or "").split(",") if g.strip()]
        n = schedule_slider_bank(component, p, wanted)
        report += "\nCreating %d sliders...\n" % n
    return p, report


def coupon_component(P, tol=geometry.DEFAULT_TOL):
    """Fit coupon component -> (coupon car frame, coupon print orientation, outline, report)."""
    d = params.derive(P)
    brep, method = geometry.build_fit_coupon(P, d, tol)
    msgs = geometry.check_solid(brep, "fit_coupon")
    printed = brep.DuplicateBrep()
    printed.Transform(geometry.print_transform([brep]))
    outline = geometry.outline_curve(layout.shelf_outline(P, d, d.z_top), d.z_top)
    report = ["fit_coupon built by %s" % method,
              "volume %.1f cm3 (~%.0f g PETG)" % (geometry.volume_cm3(brep),
                                                  geometry.volume_cm3(brep) * 1.27)]
    report += msgs or ["closed valid solid: OK"]
    if P.placeholders:
        report.append("%d values not confirmed for your car yet" % len(P.placeholders))
    return brep, printed, outline, "\n".join(report)


def profile_gauge_component(P, tol=geometry.DEFAULT_TOL):
    """Profile gauge component -> (gauge standing in the car frame, gauge flat as printed, report)."""
    d = params.derive(P)
    flat, standing, method = geometry.build_profile_gauge(P, d, tol)
    msgs = geometry.check_solid(flat, "profile_gauge")
    report = ["profile_gauge (%.0f mm behind the lip) built by %s" % (P.gauge_y, method),
              "volume %.1f cm3 (~%.0f g PETG)" % (geometry.volume_cm3(flat),
                                                  geometry.volume_cm3(flat) * 1.27)]
    report += msgs or ["closed valid solid: OK"]
    return standing, flat, "\n".join(report)


def context_component(P):
    """Context component -> (cubby wireframe + LED free zone, plug cluster box, phone box)."""
    ctx = geometry.build_context(P, params.derive(P))
    return ctx["cubby"] + ctx["led_keepout"], ctx["ports"], ctx["phone"]


def export_component(name, breps, out_dir=None, run=False):
    """Export component -> report. Writes STL + 3MF (+ STEP) when run is True."""
    if not run:
        return "press the button to export '%s'" % name
    breps = [b for b in (breps or []) if b is not None]
    if not breps:
        return "nothing to export"
    out_dir = out_dir or os.path.join(params.REPO_ROOT, "out")
    paths, msgs = export.export_part(name, breps, out_dir)
    return "\n".join(["wrote " + x for x in paths] + msgs)


# --------------------------------------------------------------------------
# slider bank
# --------------------------------------------------------------------------

def _make_input_object(name, spec, value):
    import System
    from Grasshopper.GUI.Base import GH_SliderAccuracy
    from Grasshopper.Kernel.Special import (GH_BooleanToggle, GH_NumberSlider, GH_ValueList,
                                            GH_ValueListItem, GH_ValueListMode)

    t = spec["type"]
    if t in ("float", "int"):
        obj = GH_NumberSlider()
        obj.CreateAttributes()
        obj.Slider.Type = GH_SliderAccuracy.Integer if t == "int" else GH_SliderAccuracy.Float
        obj.Slider.DecimalPlaces = 0 if t == "int" else 2
        obj.Slider.Minimum = System.Decimal(float(spec["min"]))
        obj.Slider.Maximum = System.Decimal(float(spec["max"]))
        obj.SetSliderValue(System.Decimal(float(value)))
    elif t == "bool":
        obj = GH_BooleanToggle()
        obj.CreateAttributes()
        obj.Value = bool(value)
    else:
        obj = GH_ValueList()
        obj.CreateAttributes()
        obj.ListMode = GH_ValueListMode.DropDown
        obj.ListItems.Clear()
        for choice in spec["choices"]:
            obj.ListItems.Add(GH_ValueListItem(choice, '"%s"' % choice))
        obj.SelectItem(spec["choices"].index(value))
    obj.NickName = name
    return obj


def schedule_slider_bank(component, p, groups):
    """Create sliders (value lists, toggles) for every parameter in ``groups``
    (all groups if empty) that is not wired yet, set to the current value, and
    wire them into input "S". Runs after the current solution finishes."""
    import System
    from Grasshopper.Kernel import GH_Document

    target = next((prm for prm in component.Params.Input if prm.NickName == SLIDER_INPUT), None)
    if target is None:
        raise ValueError("the component needs an input named '%s' for the sliders" % SLIDER_INPUT)
    existing = set(src.NickName for src in target.Sources)
    names = [n for n, s in p.spec.items()
             if (not groups or s["group"] in groups) and n not in existing and p[n] is not None]
    if not names:
        return 0

    def callback(gh_doc):
        pivot = component.Attributes.Pivot
        x = pivot.X - 420
        y = pivot.Y - 11 * len(names)
        last_group = None
        for name in names:
            spec = p.spec[name]
            if last_group is not None and spec["group"] != last_group:
                y += 14  # gap between groups
            last_group = spec["group"]
            obj = _make_input_object(name, spec, p[name])
            obj.Attributes.Pivot = System.Drawing.PointF(x, y)
            gh_doc.AddObject(obj, False)
            target.AddSource(obj)
            y += 22
        component.ExpireSolution(False)

    component.OnPingDocument().ScheduleSolution(5, GH_Document.GH_ScheduleDelegate(callback))
    return len(names)
