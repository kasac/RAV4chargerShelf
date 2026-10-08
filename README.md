# RAV4chargerShelf

Parametric, 3D-printable storage for the lower centre-stack cubby of the **2024 Toyota RAV4 GR Sport
PHEV** (EU, XA50): the cubby below the climate controls, with the Qi pad as its floor and the
12 V / USB ports on its rear wall. PETG; no tools, glue or drilling.

**Status: test prints.** The cubby shape is estimated from the outside dimensions of other models and
from inspection and measurements of the car; two test prints confirm it. The Rhino path has not been
run in Rhino yet.

## Start here

| Goal | How |
|---|---|
| Print the test prints | `python tools/rav4shelf.py coupon`, or the **fit-coupon** artifact of the latest CI run; then [docs/measuring.md](docs/measuring.md) |
| See the model in Rhino 8 | [Rhino 8 and Grasshopper](#rhino-8-and-grasshopper) |
| Learn Grasshopper with live sliders | [docs/grasshopper_onboarding.md](docs/grasshopper_onboarding.md) |
| Change the code | [Development](#development) |

## Command line

```bash
python tools/rav4shelf.py coupon    # test prints: out/fit_coupon.*, out/profile_gauge.* (STL, 3MF)
python tools/rav4shelf.py check     # report and checks
python tools/rav4shelf.py preview   # drawings and out/cubby_envelope.stl
```

Python 3.9+, nothing else. Your values go in `params/measured.json` (start from
`params/measured.example.json`); it is applied automatically.

## Rhino 8 and Grasshopper

[`rhino/rav4shelf_rhino.py`](rhino/rav4shelf_rhino.py) is the whole project in one Python 3 file.

- **Rhino 8:** units in millimetres; `ScriptEditor` → **File → Open** the file (or paste it into a new
  Python 3 script) → **Run**. Not `EditPythonScript`: that is the old Python 2 editor.
- **Grasshopper:** paste it into a **Python 3 Script** component, see
  [docs/grasshopper_onboarding.md](docs/grasshopper_onboarding.md).

Your values and an export folder go in the SETTINGS block at the top of the file. Parts appear on
layers `RAV4chargerShelf::<part>`; the `envelope` layer (the cubby as a solid) starts hidden.

## The cubby model

- **Side walls:** an arc seen from the front (`wall_radius`, `wall_lean_deg`), narrowing toward the
  rear (`W_rear_delta`).
- **Rear corners:** a chamfer with two fillets.
- **Roof:** flat at `H_cubby`, a straight front edge, a slight bulge around the roof LED.
- **LED free zone:** no part inside a 50 mm column under the LED (`led_keepout_diameter`).

Frame in mm: x to the right seen from the driver, y from the lip into the dash, z up from the Qi pad.
All parameters are in [`params/default.json`](params/default.json), explained in
[docs/parameters.md](docs/parameters.md).

## Test prints

- **Fit coupon** (~20 g): the shelf outline and its edge band at shelf height.
- **Profile gauge** (~11 g): the cubby cross-section 30 mm behind the lip.

Print both in PETG as exported (coupon plate down, gauge flat), 0.2 mm layers, 4 perimeters, no
supports. PETG for every part: PLA softens in a parked car. No metal near the Qi coil.

## Development

`pip install pytest numpy trimesh`, then `python -m pytest` (CI: Python 3.9 as in Rhino 8, and 3.12).
After changing `params/default.json` or `src/`, regenerate both generated files (CI checks them):
`python tools/gen_param_docs.py` and `python tools/bundle_rhino.py`.

- `src/rav4shelf/`: pure-Python core (parameters, outlines, checks, STL/3MF) plus the Rhino layer
  (`geometry.py`, `export.py`, `gh.py`), which CI tests against mocks.
- `rhino/build_all.py`, `rhino/gh_components/`: repo-linked Rhino and Grasshopper setup for live code
  edits, see [docs/grasshopper_setup.md](docs/grasshopper_setup.md).
- `reference/`: optional comparison with another model's STL, see [reference/README.md](reference/README.md).

## First run in Rhino

Please report the exact message if one of these fails:

- [ ] The one-file script runs; `fit_coupon` and `profile_gauge` are closed solids and the report
      says `built by boolean`.
- [ ] The gauge stands 30 mm behind the lip inside the cubby wireframe; the `led_keepout` column
      sits in the middle.
- [ ] With `EXPORT_FOLDER` set, `fit_coupon.3mf` opens in PrusaSlicer without repairs.
- [ ] In Grasshopper, a slider named `shelf_height` wired into `S` moves the coupon.

## Open decisions

1. **What to build:** the roof LED must stay uncovered, so probably small storage at the sides of the
   roof instead of a full-width shelf.
2. **How it is held:** wedged between the leaning side walls, or on plates down the walls.
