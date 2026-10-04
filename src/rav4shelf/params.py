"""Load, validate and derive parameters. Pure Python, no Rhino imports.

Precedence (later wins):
    params/default.json  <  params/measured.json  <  extra override files/dicts
    (<  Grasshopper sliders, which the GH Params component passes as a dict)

Override files are flat JSON objects {"name": value}. Keys starting with "_"
are comments and ignored. Unknown names are an error, so typos cannot slip by.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
DEFAULT_SPEC_PATH = os.path.join(REPO_ROOT, "params", "default.json")
MEASURED_PATH = os.path.join(REPO_ROOT, "params", "measured.json")

# Cubby widths are measured this far behind the front lip (W_top, W_bottom)
# and this far in front of the rear wall (W_rear_delta). See docs/measuring.md.
MEAS_INSET = 10.0

_TYPES = ("float", "int", "bool", "choice")


class ParamError(ValueError):
    """A parameter file or value is invalid."""


# --------------------------------------------------------------------------
# spec
# --------------------------------------------------------------------------

# The single-file Rhino script (rhino/rav4shelf_rhino.py) has no repo next to
# it: it puts the contents of default.json here instead.
EMBEDDED_SPEC = None


def load_spec(path: str = None) -> Dict[str, dict]:
    """Read default.json and return {name: spec} in file order."""
    if path is None and EMBEDDED_SPEC is not None and not os.path.isfile(DEFAULT_SPEC_PATH):
        data, path = json.loads(EMBEDDED_SPEC), "embedded default.json"
    else:
        path = path or DEFAULT_SPEC_PATH
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    if data.get("_format") != "rav4shelf-params-v1":
        raise ParamError("%s: unknown or missing _format" % path)
    specs = data["params"]
    for name, s in specs.items():
        _check_spec(name, s)
    return specs


def _check_spec(name: str, s: dict) -> None:
    for key in ("group", "type", "doc"):
        if key not in s:
            raise ParamError("spec '%s' is missing '%s'" % (name, key))
    if "value" not in s:
        raise ParamError("spec '%s' is missing 'value'" % name)
    t = s["type"]
    if t not in _TYPES:
        raise ParamError("spec '%s' has unknown type '%s'" % (name, t))
    if t in ("float", "int"):
        for key in ("unit", "min", "max"):
            if key not in s:
                raise ParamError("spec '%s' is missing '%s'" % (name, key))
        if s["min"] > s["max"]:
            raise ParamError("spec '%s' has min > max" % name)
    if t == "choice" and not s.get("choices"):
        raise ParamError("spec '%s' has no choices" % name)
    if s.get("basis", "reference") != "reference":
        raise ParamError("spec '%s' has unknown basis '%s'" % (name, s["basis"]))
    # the default itself must be valid
    _coerce(name, s, s["value"])


def _coerce(name: str, s: dict, value):
    """Convert a raw value to the spec type and range-check it."""
    t = s["type"]
    if value is None:
        if s.get("auto"):
            return None
        raise ParamError("'%s' may not be null: fill in a value or delete the line" % name)
    if t in ("float", "int"):
        if isinstance(value, bool):
            raise ParamError("'%s' must be a number, got %r" % (name, value))
        if not isinstance(value, (int, float)):
            try:
                value = float(value)  # e.g. System.Decimal or numeric string from GH
            except (TypeError, ValueError):
                raise ParamError("'%s' must be a number, got %r" % (name, value))
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            raise ParamError("'%s' must be finite" % name)
        if t == "int":
            if abs(value - round(value)) > 1e-9:
                raise ParamError("'%s' must be a whole number, got %r" % (name, value))
            value = int(round(value))
        if value < s["min"] - 1e-9 or value > s["max"] + 1e-9:
            raise ParamError("'%s' = %s %s is outside [%s, %s]" % (
                name, value, s.get("unit", ""), s["min"], s["max"]))
        return value
    if t == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
        raise ParamError("'%s' must be true or false, got %r" % (name, value))
    # choice
    value = str(value).strip().strip('"')
    if value not in s["choices"]:
        raise ParamError("'%s' must be one of %s, got %r" % (name, s["choices"], value))
    return value


# --------------------------------------------------------------------------
# params
# --------------------------------------------------------------------------

class Params:
    """Validated parameter values with attribute access (p.W_top)."""

    def __init__(self, spec: Dict[str, dict], values: dict, sources: dict, files: List[str]):
        object.__setattr__(self, "_spec", spec)
        object.__setattr__(self, "_values", values)
        object.__setattr__(self, "_sources", sources)
        object.__setattr__(self, "_files", files)

    def __getattr__(self, name):
        values = object.__getattribute__(self, "_values")
        if name in values:
            return values[name]
        raise AttributeError("unknown parameter '%s'" % name)

    def __setattr__(self, name, value):
        raise AttributeError("Params is read-only; use with_overrides()")

    def __getitem__(self, name):
        return self._values[name]

    def __contains__(self, name):
        return name in self._values

    @property
    def spec(self) -> Dict[str, dict]:
        return self._spec

    @property
    def files(self) -> List[str]:
        """Override files that were applied, in order."""
        return list(self._files)

    def source(self, name: str) -> str:
        """'default', a file path, or the label passed to with_overrides()."""
        return self._sources[name]

    def as_dict(self) -> dict:
        return dict(self._values)

    @property
    def reference_based(self) -> List[str]:
        """Placeholders whose default was estimated from the cubby reference model."""
        return [n for n in self.placeholders if self._spec[n].get("basis") == "reference"]

    @property
    def placeholders(self) -> List[str]:
        """Names flagged as placeholder in default.json that nobody overrode."""
        return [n for n, s in self._spec.items()
                if s.get("placeholder") and self._sources[n] == "default"]

    def with_overrides(self, overrides: dict, source: str = "override") -> "Params":
        values = dict(self._values)
        sources = dict(self._sources)
        for name, raw in overrides.items():
            if name.startswith("_"):
                continue
            if name not in self._spec:
                raise ParamError("unknown parameter '%s' (from %s)%s" % (
                    name, source, _suggest(name, self._spec)))
            values[name] = _coerce(name, self._spec[name], raw)
            sources[name] = source
        files = list(self._files)
        if source not in ("override", "default") and source not in files:
            files.append(source)
        return Params(self._spec, values, sources, files)

    def to_json(self) -> str:
        return json.dumps(self._values, indent=2)

    def __repr__(self):
        return "Params(%d values, %d placeholders)" % (len(self._values), len(self.placeholders))


def _suggest(name: str, spec: dict) -> str:
    low = name.lower()
    close = [n for n in spec if n.lower() == low or low in n.lower() or n.lower() in low]
    return "; did you mean %s?" % ", ".join(close[:3]) if close else ""


def default_override_paths() -> List[str]:
    """params/measured.json if it exists, else nothing."""
    return [MEASURED_PATH] if os.path.isfile(MEASURED_PATH) else []


def load_params(*overrides, spec_path: str = None) -> Params:
    """Load default.json and apply overrides in order.

    Each override is a dict or a path to a flat JSON file.
    """
    spec = load_spec(spec_path)
    values = {n: _coerce(n, s, s["value"]) for n, s in spec.items()}
    sources = {n: "default" for n in spec}
    p = Params(spec, values, sources, [])
    for ov in overrides:
        if ov is None:
            continue
        if isinstance(ov, dict):
            p = p.with_overrides(ov, "override")
        else:
            path = os.fspath(ov)
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except ValueError as exc:
                    raise ParamError("%s is not valid JSON: %s" % (path, exc))
            if not isinstance(data, dict):
                raise ParamError("%s must contain a JSON object {name: value}" % path)
            p = p.with_overrides(data, path)
    return p


# --------------------------------------------------------------------------
# cubby model and derived values
# --------------------------------------------------------------------------

def wall_offset(p: Params, z: float) -> float:
    """Sideways position of each side wall at height z, relative to z_ref
    (per side, + = outward).

    Seen from the front the wall is a circular arc of radius wall_radius with
    lean wall_lean_deg at z_ref: it curves in toward the floor. wall_radius 0
    gives a straight wall.
    """
    lean = math.radians(p.wall_lean_deg)
    radius = p.wall_radius
    if radius <= 0:
        return math.tan(lean) * (z - p.z_ref)
    dz = z - (p.z_ref + radius * math.sin(lean))  # height above the arc centre
    if abs(dz) >= radius:
        raise ParamError("height %.1f is outside the side-wall arc (wall_radius %.1f too small)"
                         % (z, radius))
    return math.sqrt(radius * radius - dz * dz) - radius * math.cos(lean)


def cubby_half_width(p: Params, y: float, z: float) -> float:
    """Half the inner cubby width at depth y (from the lip) and height z (above the pad).

    W_ref at z_ref, the curved side walls (wall_offset), a linear taper of
    W_rear_delta between the two measuring stations (MEAS_INSET from the lip
    and from the rear wall), plus envelope_offset.
    """
    hw = p.W_ref / 2.0 + wall_offset(p, z) + p.envelope_offset
    y0 = MEAS_INSET
    y1 = p.D_cubby - MEAS_INSET
    if y1 - y0 > 1e-6:
        hw += p.W_rear_delta / 2.0 * (y - y0) / (y1 - y0)
    return hw


def cubby_width(p: Params, y: float, z: float) -> float:
    """Inner cubby width at depth y and height z."""
    return 2.0 * cubby_half_width(p, y, z)


def roof_height(p: Params, x: float, y: float) -> float:
    """Height of the cubby roof above the pad at (x, y): flat at H_cubby,
    raised by the roof pocket some RAV4 versions have (0 on the GR Sport) and
    lowered by the bulge around the LED."""
    return p.H_cubby + roof_pocket(p, x, y) - roof_bulge(p, x, y)


def roof_pocket(p: Params, x: float, y: float) -> float:
    """How far the roof pocket lifts the roof at (x, y): full height over the
    middle roof_pocket_width, rising toward the front."""
    if p.roof_pocket_width <= 0 or p.roof_pocket_rise <= 0 or y >= p.roof_pocket_end:
        return 0.0
    along = ((p.roof_pocket_end - y) / (p.roof_pocket_end - MEAS_INSET)) ** p.roof_pocket_shape
    half = p.roof_pocket_width / 2.0
    ax = abs(x)
    if ax <= half:
        across = 1.0
    elif p.roof_pocket_blend > 0 and ax < half + p.roof_pocket_blend:
        t = (ax - half) / p.roof_pocket_blend
        across = 1.0 - t * t * (3.0 - 2.0 * t)  # smoothstep
    else:
        across = 0.0
    return p.roof_pocket_rise * along * across


def roof_bulge(p: Params, x: float, y: float) -> float:
    """How far the roof bulge hangs below H_cubby at (x, y): a smooth round
    bump of roof_bulge_diameter centred on the LED, 0 outside it."""
    r_b = p.roof_bulge_diameter / 2.0
    if r_b <= 0 or p.roof_bulge_depth <= 0:
        return 0.0
    r = math.hypot(x - p.led_x, y - p.led_y)
    if r >= r_b:
        return 0.0
    return p.roof_bulge_depth * 0.5 * (1.0 + math.cos(math.pi * r / r_b))


class Derived:
    """Dimensions computed from Params. Plain attributes, all in mm / deg."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def as_dict(self) -> dict:
        return dict(self.__dict__)

    def __repr__(self):
        return "Derived(%s)" % ", ".join(
            "%s=%s" % (k, _fmt(v)) for k, v in sorted(self.__dict__.items()))


def _fmt(v):
    return "%.2f" % v if isinstance(v, float) else repr(v)


def derive(p: Params) -> Derived:
    z_top = p.shelf_height
    z_deck_bottom = z_top - p.deck_thickness
    z_frame_bottom = z_top - p.frame_height
    has_ribs = p.rib_count > 0 and p.rib_height > 0
    z_rib_bottom = z_deck_bottom - p.rib_height if has_ribs else z_deck_bottom
    z_underside = min(z_frame_bottom, z_rib_bottom)

    y_front = p.front_recess
    y_rear = p.D_cubby - p.rear_gap

    # mean wall lean over the shelf's edge band (dx/dz per side)
    side_slope = (wall_offset(p, z_top) - wall_offset(p, z_frame_bottom)) / max(p.frame_height, 1e-6)

    def shelf_w(y, z):
        return cubby_width(p, y, z) - 2.0 * p.side_gap

    coupon_rim_height = p.coupon_rim_height if p.coupon_rim_height is not None else p.frame_height

    return Derived(
        z_top=z_top,
        z_deck_bottom=z_deck_bottom,
        z_frame_bottom=z_frame_bottom,
        z_rib_bottom=z_rib_bottom,
        z_underside=z_underside,
        space_above=p.H_cubby - z_top,
        y_front=y_front,
        y_rear=y_rear,
        shelf_depth=y_rear - y_front,
        side_slope=side_slope,
        side_draft_deg=math.degrees(math.atan(side_slope)),
        shelf_width_front_top=shelf_w(y_front, z_top),
        shelf_width_rear_top=shelf_w(y_rear, z_top),
        shelf_width_front_bottom=shelf_w(y_front, z_frame_bottom),
        shelf_width_max=max(shelf_w(y, z) for y in (y_front, y_rear)
                            for z in (z_top, z_frame_bottom)),
        notch_enabled=p.port_notch_width > 0 and p.port_notch_depth > 0,
        notch_center_x=p.X_ports + p.port_notch_offset_x,
        coupon_rim_height=coupon_rim_height,
    )
