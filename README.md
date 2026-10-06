# RAV4chargerShelf

A parametric, 3D-printable **second-level shelf** for the lower centre-stack cubby of the
**2024 Toyota RAV4 GR Sport Plug-in Hybrid (EU, 5th gen XA50, 10.5" screen)**: the open cubby
below the climate controls, with the Qi charging pad as its floor and the 12 V / USB-A ports on
its rear wall.

The shelf uses the empty space above the plugs. Its deck is perforated, so you can still see the
plugs through it, and it will carry a drawer (a tip-out drawer on a hinge, or a pull-out drawer as
the fallback). It fits without tools, glue or drilling.

> **Status: phase 1 – test prints.** The cubby is described by a parametric envelope of about 20
> numbers. Its walls and corners start from values estimated from a reference model made for a
> slightly different RAV4 version ([Cubby reference model](#cubby-reference-model)); the roof
> follows the GR Sport PHEV. Two quick test prints check the shape in your car. The LED in the roof
> must stay uncovered, which will change the shelf design ([open decisions](#open-decisions-after-the-test-prints)).

_Photos: placeholder until the first print._

| Phase | What | State |
|---|---|---|
| 1 | Repo, parameters, pure-Python core, tests, CI | done |
| 1 | **Cubby envelope**: starting values from the reference model, GR Sport roof with the LED; comparison and fit tools | done |
| 1 | **Test prints**: fit coupon and profile gauge, from the command line (no Rhino), Rhino 8 and Grasshopper | done, Rhino/GH path **untested** |
| 2 | Shelf: frame, perforation styles (hex, square, diamond, round, slot, triangle), ribs, port notch, support concept | after the test prints |
| 3 | Pull-out drawer on rails (baseline) | planned |
| 4 | Tip-out drawer: hinge pin, detent, end stop, swing-collision check | planned |
| 5 | TPU bumpers, assembly preview, print plates | planned |

## Start here

Pick one way in. All of them make the same parts from the same parameters.

| I want to… | Do this |
|---|---|
| **print the two test prints**, nothing else | Download them from the latest GitHub Actions run (artifact **fit-coupon**), or run the [command line](#command-line). Then follow [docs/measuring.md](docs/measuring.md). |
| **see the model in Rhino 8** | One file, copy and paste: [Rhino 8 in one file](#rhino-8-in-one-file). |
| **play with sliders and learn Grasshopper** | [docs/grasshopper_onboarding.md](docs/grasshopper_onboarding.md): from zero to the live model, about 30 minutes. |
| **change the Python code** | [Development](#development), and the repo-linked Grasshopper setup in [docs/grasshopper_setup.md](docs/grasshopper_setup.md). |

## Command line

```bash
# 1. print the two test prints and try them in the car (docs/measuring.md)
python tools/rav4shelf.py coupon       # out/fit_coupon.* + out/profile_gauge.* (STL + 3MF)

# 2. write down what the test prints showed, plus your plugs and phone
cp params/measured.example.json params/measured.json

# 3. check and look at the drawings
python tools/rav4shelf.py check        # report + sanity checks
python tools/rav4shelf.py preview      # overview.svg, fit_template_1to1.svg, cubby_envelope.stl
```

This needs Python 3.9 or newer and nothing else. `params/measured.json` is applied automatically.
Add more override files with `-p file.json`. `out/cubby_envelope.stl` is the cubby as a solid in
the car frame, to design against in any CAD program.

CI builds the test prints from `default.json` + `params/measured.json` on every push. Download
them from the **fit-coupon** artifact of the GitHub Actions run.

## Rhino 8 in one file

[`rhino/rav4shelf_rhino.py`](rhino/rav4shelf_rhino.py) is the whole project in one file. It doesn't
need the rest of the repo.

1. On GitHub, open `rhino/rav4shelf_rhino.py` and click **Copy raw file** (the two-squares icon
   above the code). Or download it.
2. In Rhino 8, make sure the units are **millimetres** (`Units` command).
3. Type `ScriptEditor` and press Enter. Either **File → Open** the downloaded file, or make a new
   script, choose **Python 3** as its language, and paste. Press **Run** (F5).

It is a **Python 3** script. Don't use `EditPythonScript`: that is Rhino's old IronPython 2 editor,
which stops with "This script needs Python 3" (older copies of the file failed with "cannot import
abc from importlib"). `RunPythonScript` works with the saved file, because its first line,
`#! python3`, selects Python 3.

The fit coupon, the profile gauge, the cubby wireframe, the plugs, the phone and the LED free zone
appear on layers `RAV4chargerShelf::<part>`, and a report prints in the output pane. The
`envelope` layer (the cubby as a solid) starts switched off; turn it on in X-Ray display mode to
see the parts inside it.

Change your values in the **SETTINGS** block at the top of the file (`MY_VALUES`), then run again.
Set `EXPORT_FOLDER` to also write STL, 3MF and STEP files in print orientation. To update, replace
the whole file and copy your SETTINGS over.

The same file also works in a Grasshopper **Python 3 Script** component (not the old "Python
Script" component, which is IronPython 2), with live sliders: see
[docs/grasshopper_onboarding.md](docs/grasshopper_onboarding.md).

## The cubby envelope

The cubby is described by a small parametric envelope. Every part derives from it:
- **Side walls:** seen from the front, one circular arc (`wall_radius` ≈ 505 mm, leaning
  `wall_lean_deg` ≈ 6.8° at `z_ref`), moved along the depth with a linear taper (`W_rear_delta`).
- **Rear corners:** a chamfer softened by two fillets.
- **Roof:** flat at `H_cubby` with a straight front edge, and a slight round bulge down in the
  middle (`roof_bulge_depth`, `roof_bulge_diameter`) around the LED that lights the Qi pad and the
  plugs (`led_x`, `led_y`). Some RAV4 versions instead have a raised pocket at the front of the
  roof; `roof_pocket_rise` is 0 for the GR Sport.
- **LED free zone:** no part may enter a 50 mm column under the LED (`led_keepout_diameter`), so it
  stays uncovered.

The walls and rear corners start from values estimated from the cubby-constraint-reference-model,
a model made for a slightly different RAV4 version ([Cubby reference model](#cubby-reference-model)).
They're starting values; the test prints check them. `envelope_offset` covers the unknown distance
between that model and your real walls; the fit coupon measures it.

## The test prints

- **Fit coupon** (~20 g, 30–40 min): the shelf's exact outline and the 8 mm edge band that
  touches the side walls, on a thin plate with an open centre, at shelf height. It tests the
  width, wall lean, taper, rear corners, depth and the port notch against your real plugs.
- **Profile gauge** (~11 g, ~20 min): a flat frame with the cubby cross-section seen from the
  front, 30 mm behind the lip. It tests the wall curve over the full height, the floor height and
  the roof.

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
the generated reference. Your own numbers go in `params/measured.json` (or `MY_VALUES` in the Rhino
file); don't edit `default.json` for them. Unknown names and out-of-range values are rejected with
a clear message.

**Coordinate frame (mm):** x to the right as seen from the driver (0 = cubby centreline), y from the
front lip (0) into the dash, z up from the Qi pad surface (0). Parts are modelled in this frame, so
they sit in the cubby in Rhino. Exports are rotated into print orientation.

## Repo layout

```
params/default.json            all parameters, placeholders marked
params/measured.example.json   worksheet: copy to params/measured.json
params/cubby_reference_fit.json  the envelope fitted to the reference model, with its assumptions
src/rav4shelf/
  params.py      load / validate / derive parameters, cubby model pure Python, tested
  geom2d.py      polygons with fillets, offsets, tessellation     pure Python, tested
  layout.py      shelf and cubby outlines, profiles, boxes        pure Python, tested
  checks.py      sanity checks + build report                     pure Python, tested
  meshing.py     watertight meshes without Rhino                  pure Python, tested
  fileio.py      STL / 3MF writers and STL reader                 pure Python, tested
  reference.py   compare / fit the envelope to a reference model  pure Python, tested
  preview_svg.py overview drawing + 1:1 paper template            pure Python, tested
  cli.py         python tools/rav4shelf.py ...
  geometry.py    RhinoCommon B-rep builders                       Rhino only, mocked tests
  export.py      bake to layers, STEP / 3MF / STL export          Rhino only, mocked tests
  gh.py          Grasshopper glue (named sliders, slider bank)    Rhino only, mocked tests
rhino/rav4shelf_rhino.py       ONE file for Rhino 8 and Grasshopper (generated; copy and paste)
rhino/build_all.py             repo-linked Rhino script (development)
rhino/gh_components/*.py       repo-linked Grasshopper wrappers (development)
grasshopper/                   save your .gh files here
reference/                     the third-party reference model goes here (git-ignored)
docs/                          fitting guide, Grasshopper onboarding and setup, parameter reference
tests/                         pytest (CI: Python 3.9 = Rhino 8, and 3.12)
tools/                         CLI launcher, docs and Rhino-file generators
out/                           generated files (git-ignored)
```

## Development

`pip install pytest numpy trimesh`, then `python -m pytest`. Two files are generated, and CI fails
if either is stale:
- after changing `default.json`: `python tools/gen_param_docs.py` (→ `docs/parameters.md`)
- after changing `src/` or `default.json`: `python tools/bundle_rhino.py` (→ `rhino/rav4shelf_rhino.py`)

For live editing in Rhino, use the repo-linked path: `rhino/build_all.py`, or the Grasshopper
wrappers in [docs/grasshopper_setup.md](docs/grasshopper_setup.md), which pick up edits in `src/`
with a **reload** button.

## First run in Rhino (checklist)

Claude Code can't run Rhino, so the RhinoCommon layer (`geometry.py`, `export.py`, `gh.py`) has
only been exercised against mocks. Please go through this list once and report what fails,
including the exact message.

**Rhino 8, one file (`rhino/rav4shelf_rhino.py`)**

- [ ] Runs without a Python error. The report prints in the output pane.
- [ ] Layers `RAV4chargerShelf::fit_coupon` and `::profile_gauge` each hold one **closed solid
      polysurface** (`What` command).
- [ ] The report says `built by boolean`. If it says `joined faces (boolean failed: …)`, the part is
      still fine, but please send the message.
- [ ] Layers `cubby`, `ports`, `phone` show the cubby wireframe, the plug box and the phone box in
      sensible places. Layer `led_keepout` shows a column in the middle, under the roof LED. The
      profile gauge stands upright about 30 mm behind the lip.
- [ ] Layer `envelope` (switched off at first) holds the cubby as one closed solid, and the coupon's
      edge band touches its side walls.
- [ ] With `EXPORT_FOLDER` set: `fit_coupon.3mf` opens in PrusaSlicer **without** "errors repaired"
      warnings, `fit_coupon.step` opens, and the size matches `python tools/rav4shelf.py coupon`.

**Grasshopper ([onboarding](docs/grasshopper_onboarding.md))**

- [ ] The Script component shows the coupon, the gauge and the envelope; the report reads well in
      a Panel.
- [ ] A slider named `envelope_offset` wired into `S` changes the coupon live.
- [ ] A slider named e.g. `Wref` is listed as "ignored" in the report.
- [ ] The **sliders** button creates wired sliders; the **export** button writes the files.

**Repo-linked (development)**: `rhino/build_all.py` runs, and the wrappers in
[docs/grasshopper_setup.md](docs/grasshopper_setup.md) work, including **reload**.

## Cubby reference model

There is no 3D scan of the cubby. The starting values for its side walls and rear corners were
estimated from a third-party model, called the **cubby-constraint-reference-model** in this
project. It was made for a slightly different RAV4 version and doesn't match the GR Sport PHEV's
roof, so it is only a starting point: the test prints and measurements in the car decide.
**The file is not in this repository and must not be committed**; only the numbers fitted to it
are ([`params/cubby_reference_fit.json`](params/cubby_reference_fit.json)). See
[reference/README.md](reference/README.md) for how to re-run the comparison if you have it.

How the estimate works: the tools sample the model's outer surface (plan sections every 2 mm of
height, the top surface on a grid) and fit the envelope parameters to those points by least
squares. The defaults use the fitted walls and corners (marked `"basis": "reference"`) but not its
roof; a test keeps them in step with the fit record. On CI, where the file is absent, the fitter
is tested on meshes this project generates.

Assumptions about the model that the test prints check: the floor is at its lowest points, its
front is 8 mm behind the lip, and its surface may sit some distance inside the real walls
(`envelope_offset`).

## Design notes and deviations from the brief

- **Pure math vs Rhino:** outlines are computed once in pure Python (`layout.Outline`: polygon plus
  fillet radii). Rhino turns them into true lines and arcs, and the CLI tessellates them, so both
  paths make the same shape and CI can test the geometry.
- **No-Rhino test prints:** the brief asked for Rhino exports. The coupon and the gauge are simple
  enough to also be written as watertight STL/3MF by plain Python. That lets you print them before
  any Rhino debugging, and lets CI check they are watertight.
- **One-file Rhino script:** `rhino/rav4shelf_rhino.py` embeds the package and `default.json`, so
  Rhino and Grasshopper users copy one file instead of linking the repo. It is generated from
  `src/`, so there is still only one copy of the logic.
- **`port_notch_height` → `port_notch_depth`:** the notch is a cut through the whole shelf, so it
  has a depth (how far it reaches forward from the rear edge) rather than a height. The height
  question ("do the plugs reach into the shelf?") is covered by `H_ports_top` and the `ports_collide`
  check.
- **`Z_ports` → `W_ports` + `H_ports_bottom`:** the brief's "lateral position and width" is now
  `X_ports` (centre) and `W_ports` (width). `D_ports` (how far the plugs stick out) was added
  because the notch depth depends on it.
- **`W_top` / `W_bottom` → an envelope:** the brief's floor and roof widths would be interpolated
  with a straight line. The reference model suggested curved walls, so the cubby is now an
  envelope: width at `z_ref`, wall lean and radius, taper, two-radius rear corners, and a roof with
  the LED bulge. Its starting values come from the reference model and the car; the test prints
  confirm or correct them.
- **Added:** `W_lip` (insertion check), `envelope_offset` (distance between the reference surface
  and the real walls), phone and Qi-spot parameters (clearance checks, later the drawer swing
  check), and the roof LED with its free zone.
- **Second test print:** besides the brief's fit coupon there is a profile gauge, which checks the
  curved walls, floor height and roof that the coupon alone can't see.
- **No `.ghx`:** instead of a hand-made, untestable `.ghx`, the Grasshopper component can **generate
  and wire its own sliders** from `default.json` (the sliders button).
- **Metal:** nothing in the design uses metal. If a metal pin or screw is ever used, it must stay
  outside the Qi coil area.

## Open decisions (after the test prints)

1. **What to build.** The LED in the middle of the roof lights the Qi pad and the plugs, and must
   stay uncovered: a 50 mm free zone (`led_keepout_diameter`). A full-width shelf would cover it,
   so the design will probably change to small storage spaces at the sides of the roof. To be
   discussed once the test prints fit.
2. **How it is held.** It could *wedge* between the leaning side walls (they lean 6.8°, so
   a wedge fit works, but the height then depends on the width tolerance), or rest on *side
   plates* that reach down along the walls (exact height, felt pads against the trim). The test
   prints show which suits the car.
3. Shelf height versus drawer height (if a shelf stays): this depends on `H_ports_top` and the
   roof (19.9 mm above a 58 mm shelf, less under the bulge).
