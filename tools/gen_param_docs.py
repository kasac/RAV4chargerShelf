"""Regenerate docs/parameters.md from params/default.json.

    python tools/gen_param_docs.py

CI fails if docs/parameters.md is out of date (tests/test_docs.py).
"""
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
sys.path.insert(0, os.path.join(REPO, "src"))

from rav4shelf import params  # noqa: E402

OUT = os.path.join(REPO, "docs", "parameters.md")

# phase in which a group is first used by geometry
USED_BY = {
    "cubby": "the envelope: fit coupon, profile gauge, shelf (defaults estimated from the "
             "cubby reference model, see README)", "ports": "checks, previews",
    "phone": "checks, previews",
    "fit": "fit coupon, shelf", "strength": "shelf (fit coupon uses frame_height)",
    "perforation": "shelf, drawer (planned)", "drawer": "drawer (planned)",
    "tolerances": "drawer, hinge (planned)", "coupon": "fit coupon, profile gauge",
    "checks": "checks, export",
}


def _fmt(v):
    if v is None:
        return "auto"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return ("%.2f" % v).rstrip("0").rstrip(".")
    return str(v)


def render() -> str:
    spec = params.load_spec()
    lines = [
        "# Parameter reference",
        "",
        "Generated from `params/default.json` by `python tools/gen_param_docs.py`. Do not edit by hand.",
        "",
        "**PH** = not confirmed for your car yet (the build report lists them). **R** = the",
        "default is estimated from the cubby reference model; confirm it with the test prints.",
        "Plain **PH** = a guess to measure. Range = slider range in Grasshopper; values outside",
        "it are rejected.",
        "`auto` = derived from other parameters unless you set a value.",
        "",
    ]
    groups = []
    for s in spec.values():
        if s["group"] not in groups:
            groups.append(s["group"])
    for g in groups:
        lines += ["## %s" % g, "", "Used by: %s" % USED_BY.get(g, "-"), "",
                  "| Name | Default | Unit | Range / choices | PH | Meaning |",
                  "|---|---|---|---|---|---|"]
        for name, s in spec.items():
            if s["group"] != g:
                continue
            if s["type"] == "choice":
                rng = ", ".join(s["choices"])
            elif s["type"] == "bool":
                rng = "true / false"
            else:
                rng = "%s .. %s" % (_fmt(float(s["min"])), _fmt(float(s["max"])))
            lines.append("| `%s` | %s | %s | %s | %s | %s |" % (
                name, _fmt(s["value"]), s.get("unit", ""), rng,
                ("PH R" if s.get("basis") == "reference" else "PH") if s.get("placeholder") else "",
                s["doc"].replace("|", "/")))
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(render())
    print("wrote " + os.path.relpath(OUT, REPO))
