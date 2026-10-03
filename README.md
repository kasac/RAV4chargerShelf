# RAV4chargerShelf

A parametric, 3D-printable **second-level shelf** for the lower centre-stack cubby of the
**2024 Toyota RAV4 GR Sport Plug-in Hybrid (EU, 5th gen XA50, 10.5" screen)**: the open cubby
below the climate controls, with the Qi charging pad as its floor and the 12 V / USB-A ports on
its rear wall.

The shelf uses the empty space above the plugs. Its deck is perforated, so you can still see the
plugs through it, and it will carry a drawer (a tip-out drawer on a hinge, or a pull-out drawer as
the fallback). It fits without tools, glue or drilling.

> **Status: phase 1 – test prints.** The cubby shape is a ~15-number parametric envelope fitted
> to the tested Vela3D module (side walls RMS 0.14 mm). Two quick test prints confirm it in your
> car; only the plugs and the phone still need measuring. Start with
> [docs/measuring.md](docs/measuring.md).

_Photos: placeholder until the first print._

| Phase | What | State |
|---|---|---|
| 1 | Repo, parameters, pure-Python core, tests, CI | done |
| 1 | **Cubby envelope** fitted to the Vela3D module; comparison and fit tools | done |
| 1 | **Test prints**: fit coupon and profile gauge. CLI (STL/3MF, no Rhino), Rhino builders, Grasshopper wrappers | done, Rhino/GH path **untested** |
| 2 | Shelf: frame, perforation styles (hex, square, diamond, round, slot, triangle), ribs, port notch, support concept | after the test prints |
| 3 | Pull-out drawer on rails (baseline) | planned |
| 4 | Tip-out drawer: hinge pin, detent, end stop, swing-collision check | planned |
| 5 | TPU bumpers, assembly preview, print plates | planned |

## Quick start

```bash
# 1. print the two test prints and try them in the car (docs/measuring.md)
python tools/rav4shelf.py coupon       # out/fit_coupon.* + out/profile_gauge.* (STL + 3MF)

# 2. write down what the test prints showed, plus your plugs and phone
cp params/measured.example.json params/measured.json

# 3. check and look at the drawings
python tools/rav4shelf.py check        # report + sanity checks
python tools/rav4shelf.py preview      # out/overview.svg, out/fit_template_1to1.svg
```

This needs Python 3.9 or newer and nothing else. `params/measured.json` is applied automatically
everywhere. Add more override files with `-p file.json`.

The same parts come from Rhino:

- **Grasshopper** (main path, live sliders): [docs/grasshopper_setup.md](docs/grasshopper_setup.md)
- **Standalone script** (fallback): run `rhino/build_all.py` in Rhino 8 (`_RunPythonScript` or the
  ScriptEditor). It bakes each part to a layer `RAV4chargerShelf::<part>` and exports
  STEP + 3MF + STL to `out/`.

CI builds the test prints from `default.json` + `params/measured.json` on every push. Download
them from the **fit-coupon** artifact of the GitHub Actions run.

## The cubby envelope

The cubby is described by a small parametric envelope. Every part derives from it:
- **Side walls:** seen from the front, one circular arc (`wall_radius` ≈ 505 mm, leaning
  `wall_lean_deg` ≈ 6.8° at `z_ref`), moved along the depth with a linear taper (`W_rear_delta`).
- **Rear corners:** a chamfer softened by two fillets.
- **Roof:** flat at `H_cubby`, with a pocket in the middle that rises toward the front.

The defaults are fitted to the Vela3D module, a tested design whose outer surface appears to
follow a 3D scan of the cubby (see [Reference comparison](#reference-comparison-vela3d-a-tested-design)).
The approximation is a model, not a copy of their mesh. `envelope_offset` covers their unknown
foam allowance.

## The test prints

- **Fit coupon** (~20 g, 30–40 min): the shelf's exact outline and the 8 mm edge band that
  touches the side walls, on a thin plate with an open centre, at shelf height. It tests the
  width, wall lean, taper, rear corners, depth and the port notch against your real plugs.
- **Profile gauge** (~11 g, ~20 min): a flat frame with the cubby cross-section seen from the
  front, 30 mm behind the lip. It tests the wall curve over the full height, the floor height and
  the roof pocket.

If both fit, the cubby needs no measuring. [docs/measuring.md](docs/measuring.md) explains how to
try them and which parameter to change for each observation.

## Print settings

Printer: Prusa XL (5 toolheads, 360 × 360 mm), PrusaSlicer, 0.4 mm nozzle unless noted.
**PETG for every structural part.** PLA softens in a parked car, so use PLA only as a support
interface. Exported files are already in print orientation.

| Part | Material | Orientation | Supports | Perimeters | Infill | Notes |
|---|---|---|---|---|---|---|
| `fit_coupon` | PETG (same as the shelf, so shrinkage matches) | plate on the bed (as exported) | none | 4 (the 1.6 mm rim is then solid) | n/a (all walls) | 0.2 mm layers; ~20 g, 30–40 min |
| `profile_gauge` | PETG | flat (as exported) | none | 4 | 100 % | 0.2 mm layers; ~11 g, ~20 min |
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
docs/                          fitting/measuring guide, Grasshopper setup, parameter reference
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
- [ ] Layer `RAV4chargerShelf::profile_gauge` holds the gauge **standing upright** about 30 mm
      behind the lip, inside the cubby wireframe. `out/profile_gauge.3mf` lies flat.

**Grasshopper ([setup guide](docs/grasshopper_setup.md))**

- [ ] The Params component outputs `P` and a report. The **sliders** button creates wired sliders.
- [ ] Dragging `envelope_offset` / `wall_lean_deg` / `port_notch_width` updates the coupon live.
- [ ] The profile gauge component shows the gauge standing in the cubby.
- [ ] Wiring a slider named e.g. `Wref` shows up under "Ignored" in the report.
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

How the comparison works:
- **Placing the file.** The module is turned back into the car frame: un-rotated from the
  print bed, with depth from its front and height from the assumed floor.
- **Side walls.** At every 2 mm of height, the plan section's outer half-width is measured every
  2 mm of depth.
- **Rear corners and roof.** The corners are compared where the module has a back face. The roof
  is the module's top surface on a 5 × 4 mm grid.
- **Result.** The same points are compared with our envelope, and the report says how far ours is
  bigger or smaller.
- `tools/rav4shelf.py reference` also re-fits all envelope parameters (pure Python, a few
  seconds). It compares your shelf at its edge band and draws `out/reference_compare.svg`.
- On CI the tests that need the paid file skip. The fitter itself is tested there: it recovers
  known parameters, straight or curved walls, from meshes this project generates.

**What the files are:**
- **MODULE** is the drawer housing: 235 mm wide, 121 mm deep, 89 mm tall including its side wings,
  printed standing and turned 45° on the bed.
- **LEFT/RIGHT** are two mirrored drawers. They slide on the housing's floor plate, held by side
  ribs.
- The housing sits high in the cubby. Its curved side wings reach down along the walls, with foam
  between wing and wall. The phone and the plugs stay free underneath.
- Its top is flat at the sides but rises toward the front in the middle 136 mm. That's probably
  the climate panel's underside, and it is modelled as the roof pocket.

**How well ~15 numbers reproduce it**

| Feature | Model | Deviation from the module |
|---|---|---|
| side walls (1150 points, housing top to wing tips) | one arc R ≈ 505 mm, lean 6.8° at z 55, taper −9.4 mm | RMS 0.14 mm, max 0.83 mm (at the cut wing ends) |
| rear corners | chamfer + R67 / R12.6 fillets | ±0.47 mm |
| roof (1212 points) | flat + pocket 136 wide, +11.6 mm toward the front | RMS 0.09 mm, max 0.83 mm |
| shelf band at z 50–58 | — | sides +0.29 / −0.14 mm |

My first placeholders were far off: the cubby is about 40 mm wider than I guessed, narrows
9 mm toward the rear, has 4× larger rear corners and leans 6.8° instead of 1.5°.

The fitted values are the defaults in `params/default.json` (marked `"basis": "vela3d"`).
[`params/reference_vela3d.json`](params/reference_vela3d.json) records the fit and its
assumptions. A test checks that the two stay identical.

## Design notes and deviations from the brief

- **Pure math vs Rhino:** outlines are computed once in pure Python (`layout.Outline`: polygon plus
  fillet radii). Rhino turns them into true lines and arcs, and the CLI tessellates them, so both
  paths make the same shape and CI can test the geometry.
- **No-Rhino test prints:** the brief asked for Rhino exports. The coupon and the gauge are simple
  enough to also be written as watertight STL/3MF by plain Python. That lets you print them before
  any Rhino debugging, and lets CI check they are watertight.
- **`port_notch_height` → `port_notch_depth`:** the notch is a cut through the whole shelf, so it
  has a depth (how far it reaches forward from the rear edge) rather than a height. The height
  question ("do the plugs reach into the shelf?") is covered by `H_ports_top` and the `ports_collide`
  check.
- **`Z_ports` → `W_ports` + `H_ports_bottom`:** the brief's "lateral position and width" is now
  `X_ports` (centre) and `W_ports` (width). `D_ports` (how far the plugs stick out) was added
  because the notch depth depends on it.
- **`W_top` / `W_bottom` → a fitted envelope:** the brief's floor and roof widths would be
  interpolated with a straight line. The Vela3D comparison showed the walls are curved, so the
  cubby is now an envelope: width at `z_ref`, wall lean and radius, taper, two-radius rear corners,
  and a roof with a pocket. It's fitted to the tested Vela3D module and confirmed by test prints
  instead of being measured.
- **Added:** `W_lip` (insertion check), `envelope_offset` (Vela3D's foam allowance), and phone and
  Qi-spot parameters (clearance checks, later the drawer swing check).
- **Second test print:** besides the brief's fit coupon there is a profile gauge, which checks the
  curved walls, floor height and roof that the coupon alone can't see.
- **No `.ghx`:** instead of a hand-made, untestable `.ghx`, the Params component can **generate and
  wire its own sliders** from `default.json` (the sliders button).
- **Metal:** nothing in the design uses metal. If a metal pin or screw is ever used, it must stay
  outside the Qi coil area.

## Open decisions (after the test prints)

1. **How the shelf is held.** It could *wedge* between the leaning side walls (they lean 6.8°, so
   a wedge fit works, but the height then depends on the width tolerance), or stand on *side
   plates* down the walls like Vela3D's wings (exact height, foam against the walls). The test
   prints show which suits the car.
2. Shelf height versus drawer height: this depends on `H_ports_top` and the roof (19.9 mm above a
   58 mm shelf at the sides, up to 31 mm under the roof pocket at the front).
