# Grasshopper setup, repo-linked (advanced, about 10 minutes)

> **New to Grasshopper, or just want the model?** Use the single Script component in
> [grasshopper_onboarding.md](grasshopper_onboarding.md) instead: one component, one pasted file,
> no repo needed. This page is for working on the Python code in `src/`: each part gets its own
> component that imports the code from your clone, and a **reload** button picks up your edits.

The definition only holds thin wrapper components. All the logic lives in `src/rav4shelf/`, so it
stays diff-able in Git. Each wrapper is pasted from `rhino/gh_components/*.py` and calls one function.

> **Status:** written without access to Rhino and not yet tested there. If a step doesn't work as
> described, note what you saw (the exact error text is most useful) and report it back. Checklist:
> [README → First run in Rhino](../README.md#first-run-in-rhino-checklist).

This phase builds the **fit coupon** plus context geometry. The shelf and drawer components will
follow the same pattern.

```
[sliders ...] ──► S ┐
[Panel: groups] ──► │  PARAMS   P ──┬──► FIT COUPON  coupon ──► EXPORT (name="fit_coupon")
                    │               ├──► PROFILE GAUGE  gauge_print ──► EXPORT (name="profile_gauge")
[Button] ──► sliders│           report ─► Panel     coupon_print, outline, report ─► Panel
[Button] ──► reload ┘               └──► CONTEXT   cubby, ports, phone ─► Custom Preview
```

## 0. Prerequisites

- Rhino 8 with Grasshopper, and this repository cloned locally.
- A new Rhino document with **units = Millimeters**. Use `Units` to check; an absolute tolerance of
  0.01 mm or finer is good. Every component warns if the units are wrong.

## 1. Save the definition inside the repo first

Open Grasshopper and use **File → Save As** to save the empty definition as
`<repo>/grasshopper/RAV4chargerShelf.gh`. The wrappers find the Python code relative to the `.gh`
file, so this step comes first.

If you'd rather keep the `.gh` somewhere else, set the environment variable `RAV4SHELF_REPO` to the
repo folder and restart Rhino.

## 2. How to make a wrapper component (repeat for each)

1. Place a **Python 3 Script** component (Maths tab → Script panel, or double-click the canvas and
   type `Python 3 Script`).
2. Zoom in until the **⊕ / ⊖** icons appear on the component, and add or remove inputs and outputs
   until they match the list below. Right-click each parameter to **rename** it, and to set its
   **type hint** and **access** where the list says so.
3. Double-click the component, delete the template code, paste the wrapper file's content and
   save / apply in the editor.

You can keep the default `out` output; it shows printed messages.

## 3. Params component

Paste `rhino/gh_components/params_component.py`.

| Input | Type hint | Access | Connect |
|---|---|---|---|
| `S` | (none) | **List Access**. This one matters. | the sliders (step 4) |
| `overrides` | str | item | optional: path of an extra override JSON file |
| `sliders` | bool | item | a **Button** |
| `groups` | str | item | a **Panel** containing e.g. `cubby,ports,fit,coupon` |
| `reload` | bool | item | a **Button** |

Outputs: `P`, `report` (connect a Panel to `report`).

The report shows the derived dimensions, every check, and which parameters are still placeholders.
Values are applied in this order, and later ones win:
`default.json` < `params/measured.json` < `overrides` file < sliders.

Press **reload** after editing any `.py` file (or after `git pull`). Rhino caches imported modules
until it restarts.

## 4. Sliders

**Automatic:** type the groups you want into the `groups` Panel and press the **sliders** button.
The component then creates one slider (or a value list or toggle) per parameter in those groups,
stacked to its left and already wired into `S`. Each slider is named after its parameter and set
to the current value (defaults plus `params/measured.json`), so creating sliders doesn't change the
design. Groups: `cubby, ports, phone, fit, strength, perforation, drawer, tolerances, coupon, checks`.
For the coupon phase, `cubby,ports,fit,coupon` is enough. It skips parameters that already have a
slider, so pressing it again is safe.

**Manual** (if the button fails):

1. Place a **Number Slider** and set its range and default from [parameters.md](parameters.md).
2. Rename it (double-click its name) to **exactly** the parameter name, e.g. `W_ref`.
3. Wire it into `S`. Hold **Shift** while dragging to add a wire without replacing the others.

The same works for **Value List** (e.g. `grid_style`, items `"hex"`, `"square"`, …) and
**Boolean Toggle** (e.g. `grid_enabled_shelf`). Anything wired into `S` whose name isn't a parameter
is listed under "Ignored" in the report, which catches typos.

Alternatively, add an input to the Params component and rename it to a parameter name. That also
works.

## 5. Fit coupon component

Paste `rhino/gh_components/fit_coupon_component.py`.

- Input: `P` (no type hint, item access). Connect it to Params → `P`.
- Outputs: `coupon` (in the car frame, so it sits in the cubby), `coupon_print` (print orientation,
  plate down on the XY plane), `outline` (shelf outline curve at shelf height), `report`.

Drag `envelope_offset`, `wall_lean_deg` or `side_gap` and the coupon updates live.

## 5b. Profile gauge component

Paste `rhino/gh_components/profile_gauge_component.py`.

- Input: `P`. Outputs: `gauge` (standing upright in the car frame at `gauge_y`, so you see it in
  the cubby), `gauge_print` (lying flat as printed), `report`.
- To export it, wire `gauge_print` into a second Export component with name `profile_gauge`. The
  export lays it flat anyway.

## 6. Context component (display only)

Paste `rhino/gh_components/context_component.py`.

- Input: `P`. Outputs: `cubby` (wireframe of the cubby and of the free zone under the roof LED),
  `ports` (box around the plug cluster),
  `phone` (box of the phone on the Qi pad).
- To give them colours, feed `ports` and `phone` into **Custom Preview** components (Display tab)
  with a **Colour Swatch** on the Material input (red for the plugs, grey for the phone).

## 7. Export component

Paste `rhino/gh_components/export_component.py`.

| Input | Type hint | Access | Connect |
|---|---|---|---|
| `name` | str | item | Panel with `fit_coupon` |
| `breps` | Brep | **List Access** | Fit coupon → `coupon` (car frame; it's rotated on export) |
| `out_dir` | str | item | optional, default `<repo>/out` |
| `export` | bool | item | a **Button** |

Output: `report`. Press the button and it writes `out/fit_coupon.stl`, `.3mf` and `.step`, in print
orientation and in millimetres. STL and 3MF are written by the repo's own writer, so no dialog pops
up. STEP goes through Rhino's exporter. If STEP fails from Grasshopper, run `rhino/build_all.py`.

## 8. Save and commit

Save the `.gh` and commit `grasshopper/RAV4chargerShelf.gh`. The wrappers are copies of
`rhino/gh_components/*.py`. When one of those files changes, paste it again. They only change when
a component's inputs or outputs change; logic changes happen in `src/` and only need **reload**.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `rav4shelf not found` | Save the `.gh` in `<repo>/grasshopper/` (step 1), or set `RAV4SHELF_REPO`. |
| Params outputs a list of many `P` | Input `S` is not set to **List Access**. The report says so too. |
| Edits to `.py` files have no effect | Press **reload** on the Params component, then recompute (F5). |
| `unknown parameter 'W_reff'` | A typo in `measured.json` or the overrides file. The message suggests the right name. |
| Report says document units are wrong | Run `Units` in Rhino and pick Millimeters. |
| Coupon report says "joined faces (boolean failed …)" | The coupon is still valid. Please send the message after "boolean failed". |
| Anything else | Copy the red error balloon text (right-click the component → *Runtime messages*) and report it. |
