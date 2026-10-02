# RAV4chargerShelf

A parametric, 3D-printable **second-level shelf** for the lower centre-stack cubby of the
**2024 Toyota RAV4 GR Sport Plug-in Hybrid (EU, 5th gen XA50, 10.5" screen)**: the open cubby
below the climate controls, with the Qi charging pad as its floor and the 12 V / USB-A ports on
its rear wall.

The shelf uses the empty space above the plugs. Its deck is perforated, so you can still see the
plugs through it, and it will carry a drawer (a tip-out drawer on a hinge, or a pull-out drawer as
the fallback). It fits without tools, glue or drilling.

> **Status: phase 1 – fit coupon.** Nothing has been measured yet. Every dimension is a clearly
> marked **placeholder**, and anything built now is built from guesses. Start with
> [docs/measuring.md](docs/measuring.md).

_Photos: placeholder until the first print._

| Phase | What | State |
|---|---|---|
| 1 | Repo, parameters, measuring guide, pure-Python core, tests, CI | done |
| 1 | **Fit coupon**: CLI (STL/3MF, no Rhino), Rhino builder, Grasshopper wrappers, 1:1 paper template | done, Rhino/GH path **untested** |
| 2 | Shelf: frame, perforation styles (hex, square, diamond, round, slot, triangle), ribs, port notch, support concept | after the coupon test |
| 3 | Pull-out drawer on rails (baseline) | planned |
| 4 | Tip-out drawer: hinge pin, detent, end stop, swing-collision check | planned |
| 5 | TPU bumpers, assembly preview, print plates | planned |

## Quick start

```bash
# 1. measure the cubby (docs/measuring.md), then:
cp params/measured.example.json params/measured.json   # fill in your numbers

# 2. check the numbers and look at the drawings
python tools/rav4shelf.py check        # report + sanity checks
python tools/rav4shelf.py preview      # out/overview.svg, out/fit_template_1to1.svg

# 3. print the fit coupon
python tools/rav4shelf.py coupon       # out/fit_coupon.stl + out/fit_coupon.3mf
```

This needs Python 3.9 or newer and nothing else. `params/measured.json` is applied automatically
everywhere. Add more override files with `-p file.json`.

The same parts come from Rhino:

- **Grasshopper** (main path, live sliders): [docs/grasshopper_setup.md](docs/grasshopper_setup.md)
- **Standalone script** (fallback): run `rhino/build_all.py` in Rhino 8 (`_RunPythonScript` or the
  ScriptEditor). It bakes each part to a layer `RAV4chargerShelf::<part>` and exports
  STEP + 3MF + STL to `out/`.

CI builds the coupon from `default.json` + `params/measured.json` on every push. Download it from
the **fit-coupon** artifact of the GitHub Actions run.

## The fit coupon

The coupon is a thin slice of the shelf: its exact outline and the 8 mm edge band that touches the
side walls, on a 6-layer plate with an open centre. It prints in about 30–40 minutes (~18 g) and
tests the width at shelf height, the wall lean, the taper toward the rear, the rear corner radii,
the front recess and the port notch against your real plugs. See
[docs/measuring.md → Step 1](docs/measuring.md#step-1--print-and-test-the-fit-coupon) for the test
procedure and which parameter to change for each observation.

## Print settings

Printer: Prusa XL (5 toolheads, 360 × 360 mm), PrusaSlicer, 0.4 mm nozzle unless noted.
**PETG for every structural part.** PLA softens in a parked car, so use PLA only as a support
interface. Exported files are already in print orientation.

| Part | Material | Orientation | Supports | Perimeters | Infill | Notes |
|---|---|---|---|---|---|---|
| `fit_coupon` | PETG (same as the shelf, so shrinkage matches) | plate on the bed (as exported) | none | 4 (the 1.6 mm rim is then solid) | n/a (all walls) | 0.2 mm layers; ~18 g, 30–40 min |
| `shelf` | PETG | deck on the bed | none (design goal) | 4 | 30–40 % gyroid | phase 2 |
| `drawer` | PETG | chosen so layer lines don't cross the hinge knuckles or snap arms | none, or PLA interface | 4 | 30 % | phase 3/4 |
| `hinge_pin` | PETG printed lying flat, or a piece of 1.75 / 2.85 mm PETG filament | lying flat | none | all solid | 100 % | phase 4; **no metal near the Qi coil** |
| `tpu_bumpers` | TPU 95A | flat | none | 3 | 20 % | optional, phase 5 |

## Parameters

Everything is in **one file**, [`params/default.json`](params/default.json): value, unit, slider
range, whether it's a placeholder, and what it means. [docs/parameters.md](docs/parameters.md) is
the generated reference. Your own numbers go in `params/measured.json`; don't edit
`default.json` for them. Unknown names and out-of-range values are rejected with a clear message.

**Coordinate frame (mm):** x to the right as seen from the driver (0 = cubby centreline), y from the
front lip (0) into the dash, z up from the Qi pad surface (0). Parts are modelled in this frame, so
they sit in the cubby in Rhino. Exports are rotated into print orientation.

## Repo layout

```
params/default.json            all parameters, placeholders marked
params/measured.example.json   worksheet: copy to params/measured.json
src/rav4shelf/
  params.py      load / validate / derive parameters             pure Python, tested
  geom2d.py      polygons with fillets, offsets, tessellation     pure Python, tested
  layout.py      shelf outline, coupon profile, reference boxes   pure Python, tested
  checks.py      sanity checks + build report                     pure Python, tested
  meshing.py     watertight coupon mesh without Rhino             pure Python, tested
  fileio.py      STL / 3MF writers and STL reader                 pure Python, tested
  reference.py   compare / fit against a reference model (Vela3D) pure Python, tested
  preview_svg.py overview drawing + 1:1 paper template            pure Python, tested
  cli.py         python tools/rav4shelf.py ...
  geometry.py    RhinoCommon B-rep builders                       Rhino only, mocked tests
  export.py      bake to layers, STEP / 3MF / STL export          Rhino only, mocked tests
  gh.py          Grasshopper glue (named sliders, slider bank)    Rhino only, mocked tests
rhino/build_all.py             standalone Rhino 8 entry point
rhino/gh_components/*.py       thin wrappers pasted into GH Python 3 Script components
grasshopper/                   save RAV4chargerShelf.gh here
reference/                     paid reference models go here (git-ignored)
docs/                          measuring guide, Grasshopper setup, parameter reference
tests/                         pytest (CI: Python 3.9 = Rhino 8, and 3.12)
tools/                         CLI launcher, docs generator
out/                           generated files (git-ignored)
```

Development: `pip install pytest numpy trimesh`, then `python -m pytest`. After changing
`default.json`, run `python tools/gen_param_docs.py`; CI fails if `docs/parameters.md` is stale.

## First run in Rhino (checklist)

Claude Code can't run Rhino, so the RhinoCommon layer (`geometry.py`, `export.py`, `gh.py`) has
only been exercised against mocks. Please go through this list once and report what fails,
including the exact message.

**Standalone script (`rhino/build_all.py`)**

- [ ] Runs without a Python error. The report prints in the output pane.
- [ ] Layer `RAV4chargerShelf::fit_coupon` holds one **closed solid polysurface** (`What` command).
- [ ] The report says `built by boolean`. If it says `joined faces (boolean failed: …)`, the part is
      still fine, but please send the message.
- [ ] Layers `cubby`, `ports`, `phone` show the cubby wireframe, the plug box and the phone box in
      sensible places.
- [ ] `out/fit_coupon.step` exists and opens (for example re-imported in Rhino).
- [ ] `out/fit_coupon.3mf` opens in PrusaSlicer **without** "errors repaired" warnings.
- [ ] Its bounding box matches the CLI's coupon (same params): `python tools/rav4shelf.py coupon`
      prints the size.

**Grasshopper ([setup guide](docs/grasshopper_setup.md))**

- [ ] The Params component outputs `P` and a report. The **sliders** button creates wired sliders.
- [ ] Dragging `W_top` / `side_gap` / `port_notch_width` updates the coupon live.
- [ ] Wiring a slider named e.g. `Wtop` shows up under "Ignored" in the report.
- [ ] The Export button writes STL / 3MF (and STEP) to `out/`.
- [ ] **reload** picks up an edit to a `.py` file without restarting Rhino.

## Reference comparison (Vela3D, a tested design)

The Vela3D "Toyota RAV4 Tray Drawer Organizer" (Cults3D, paid) is a tested design for this cubby.
Its STL files are **not** in the repo. Put `TOYOTA_RAV4_TRAY_DRAWER_ORGANIZER_MODULE.stl` into
`reference/` ([reference/README.md](reference/README.md)) and run:

```bash
python tools/rav4shelf.py reference    # compare your outline, print fitted values, out/reference_compare.svg
python -m pytest tests/test_reference.py
```

The comparison slices the reference housing in plan and measures its outer half-width every
0.5 mm of depth, at two heights 8 mm apart. It does the same for our generated outline, aligned
at the rear edge, and reports how far ours sticks out beyond it or falls short of it. On CI, the
tests that need the paid file skip. The comparison code itself is tested there on meshes this
project generates.

**What the files are:**
- **MODULE** is the drawer housing: 235 mm wide, 121 mm deep, 89 mm tall including its side wings,
  printed standing and turned 45° on the bed.
- **LEFT/RIGHT** are two mirrored drawers. They slide on the housing's floor plate, held by side
  ribs.
- The housing sits high in the cubby. Its curved side wings reach down along the walls, with foam
  between wing and wall. The phone and the plugs stay free underneath.

**Findings: my placeholders vs the tested outline**

| | placeholder | tested design |
|---|---|---|
| width at shelf height (front) | 198 mm | ≈ 234 mm (ours **~20 mm smaller per side**) |
| narrowing toward the rear | 0 | 8.4 mm per 100 mm of depth |
| rear corner | R 5 | a long free-form curve; best single radius R 17 |
| side-wall lean | 1.5° per side | ≈ 6° per side, curving in much more toward the floor |
| depth (rear wall → front) | 121 mm | 121 mm (coincidence) |

[`params/reference_vela3d.json`](params/reference_vela3d.json) holds parameters that make our
generator reproduce the tested outline: **sides within 0.23 mm, rear corners within 1.4 mm**. The
residual is a single circular fillet against their free-form corner. Two cautions about this file:
- Its heights rest on stated assumptions, and `side_gap` is 0 because Vela3D's foam thickness is
  unknown.
- Use it *instead of* measurements (`-p params/reference_vela3d.json`), not together with them.
  It's applied after `params/measured.json`, so it would override your numbers.

## Design notes and deviations from the brief

- **Pure math vs Rhino:** outlines are computed once in pure Python (`layout.Outline`: polygon plus
  fillet radii). Rhino turns them into true lines and arcs, and the CLI tessellates them, so both
  paths make the same shape and CI can test the geometry.
- **No-Rhino coupon:** the brief asked for Rhino exports. The coupon is simple enough to also be
  written as a watertight STL/3MF by plain Python. That lets you print it before any Rhino
  debugging, and lets CI check it is watertight.
- **`port_notch_height` → `port_notch_depth`:** the notch is a cut through the whole shelf, so it
  has a depth (how far it reaches forward from the rear edge) rather than a height. The height
  question ("do the plugs reach into the shelf?") is covered by `H_ports_top` and the `ports_collide`
  check.
- **`Z_ports` → `W_ports` + `H_ports_bottom`:** the brief's "lateral position and width" is now
  `X_ports` (centre) and `W_ports` (width). `D_ports` (how far the plugs stick out) was added
  because the notch depth depends on it.
- **Added measurements:** `W_rear_delta` (taper toward the rear), `R_rear_corner`, `W_lip`
  (insertion check), phone and Qi-spot parameters (clearance checks, later the drawer swing check).
- **No `.ghx`:** instead of a hand-made, untestable `.ghx`, the Params component can **generate and
  wire its own sliders** from `default.json` (the sliders button).
- **Metal:** nothing in the design uses metal. If a metal pin or screw is ever used, it must stay
  outside the Qi coil area.

## Open decisions (after the coupon test)

1. **How the shelf is held.** It could *wedge* between leaning side walls (only works if
   `W_top > W_bottom`, and the height then depends on the width tolerance), or stand on *legs* or
   side plates down to the floor beside the Qi pad (exact height, needs floor space). The coupon
   test shows which one fits the car.
2. Shelf height versus drawer height: this depends on `H_ports_top` and `H_cubby`.
3. **Width model.** The Vela3D comparison shows the side walls are curved, not straight from floor
   to roof. The model should take two widths measured just above and below the shelf band, instead
   of interpolating between the floor and the roof.
