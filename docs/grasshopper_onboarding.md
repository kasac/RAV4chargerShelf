# Grasshopper onboarding: from zero to the live shelf model

This guide assumes you have never used Grasshopper. It takes about 30 minutes:
1. A 10-minute warm-up that teaches the basics.
2. The RAV4chargerShelf model in **one** Script component, with live sliders.
3. A few exercises that use the model to learn more Grasshopper.

> **Status:** written without access to Rhino and not yet tested there. If something looks
> different from what's described, or a component turns red, copy the message and report it.

## Why Grasshopper, and what it does here

Grasshopper is the visual programming editor built into Rhino. You place **components** (boxes
that do one thing, such as make a circle or extrude a curve) on a **canvas** and connect them with
**wires**. Data flows from left to right: each component's outputs on its right side feed other
components' inputs on their left. Change a number anywhere, for example by dragging a slider,
and everything downstream recomputes at once.

Grasshopper shows its results as a **preview** in the Rhino viewports. The preview isn't part of the
Rhino document until you **bake** it.

In this project all the geometry is computed by Python code (the repo's `src/rav4shelf`, tested on
CI). Grasshopper is the **live dashboard** on top of it:
- one slider per parameter, so you can drag `shelf_height` or `side_gap` and watch the coupon
  follow, inside the cubby envelope;
- regular Grasshopper components next to it, to measure, cut sections or colour the parts.

That split suits Grasshopper well. The logic stays in versioned, tested code, and the `.gh` file
stays small. The single Script component is all you need to start; the
[advanced setup](grasshopper_setup.md) splits it into one component per part for development.

## Part 1 – warm-up (10 minutes)

Start Rhino 8 with a new model in **millimetres**, then type `Grasshopper` and press Enter. The
Grasshopper window opens with an empty canvas.

**Moving around the canvas**
- Zoom: mouse wheel.
- Pan: drag with the **right** mouse button.
- Place a component: **double-click** on empty canvas, type its name, press Enter. All
  components also sit in the tabs at the top (Params, Maths, Curve, Surface…), but searching is
  faster.

**Build a cylinder from sliders**

1. Double-click the canvas and type `Circle`. Pick **Circle** (the one with inputs *P* and *R*:
   plane and radius).
2. Double-click the canvas, type `0<20<50` and press Enter. This makes a **Number Slider** from 0 to
   50, set to 20.
3. Drag from the slider's output (the small half-circle on its right) to the circle's **R** input.
   A circle appears in Rhino's viewports, previewed in red.
4. Add **Unit Z** (a vector pointing up; input *F* = length) and a second slider `0<30<100` wired
   into **F**.
5. Add **Extrude**. Wire the circle's output into **B** (base) and Unit Z's output into **D**
   (direction). You now have a tube.
6. Add **Cap Holes** after the extrusion to close it into a solid.
7. Add **Volume**, wire the solid into it, and add a **Panel** (search `Panel`) on its **V** output.
   The panel shows the volume in mm³.
8. Drag the sliders and watch the tube and the number change.

**What to notice**
- **Hover** over any input or output to see what it holds; a Panel shows it permanently.
- Component colours: grey = fine, **orange** = warning, **red** = error. Click the small balloon
  on the component to read the message.
- Preview colours in Rhino: **red** = not selected, **green** = the selected component's geometry.
  Right-click a component → **Preview** to hide its geometry.
- **Wires:** hold **Shift** while dragging to add a wire without replacing the existing one, and
  **Ctrl** to remove one.
- **Bake:** right-click a component (or one output) → **Bake…** to copy the geometry into the Rhino
  document as real objects.
- **Save** with *File → Save Document As*. A `.gh` file stores the canvas, not the geometry.

Delete everything (Ctrl+A, Delete) before part 2, or start a new definition with *File → New*.

## Part 2 – the shelf model in one Script component

### 2.1 Get the code

You need the single file [`rhino/rav4shelf_rhino.py`](../rhino/rav4shelf_rhino.py). On GitHub,
open it and click **Copy raw file** (the two-squares icon above the code). It is long (about 2,700
lines); that's expected, because the whole project is inside.

### 2.2 Place and wire the Script component

1. Double-click the canvas, type `Python 3 Script`, press Enter.
2. Zoom in on the component until small **⊕ / ⊖** icons appear next to its inputs and outputs. Use
   them to add and remove parameters.
3. **Inputs:** keep one input and remove the rest. Right-click it, rename it to **`S`**, and set it
   to **List Access** in the same menu. This matters: with the default *Item Access* the script
   would run once per slider.
4. **Outputs:** make five outputs, renamed (right-click each) to **`coupon`**, **`gauge`**,
   **`envelope`**, **`cubby`** and **`report`**. If the component also has an `out` output, keep
   it: it shows printed text and Python errors.
5. Double-click the component to open the script editor. Select everything (Ctrl+A), paste the file
   (Ctrl+V), press the editor's **Run** button (or F5), and close the editor.
6. Add a **Panel** and wire `report` into it. Make the Panel bigger by dragging its corner.

The first run takes a few seconds. Then the fit coupon, the profile gauge (standing upright 30 mm
behind the lip) and the cubby envelope appear in red in the viewports. The `cubby` output also
holds a column in the middle: the free zone under the roof LED, where no part may go. If you see nothing, zoom out
in Rhino: the cubby is about 240 mm wide, around the origin.

The report lists the derived dimensions, every check, and the values still unconfirmed for your
car (the test prints confirm them, see [measuring.md](measuring.md)).

### 2.3 Your first slider

1. Place a Number Slider (double-click, type `slider`, pick **Number Slider**).
2. Double-click the slider's name (its left part) to open its settings:
   - **Name:** `shelf_height` (it must match the parameter name exactly, including case)
   - **Numeric domain:** min 30, max 75
   - **Value:** 58, with **floating point** numbers and 1 decimal place
3. Wire the slider into `S`.
4. Drag it. The coupon moves up and down in the cubby and gets wider or narrower with the leaning
   walls. The report follows.

Add more the same way, holding **Shift** when wiring into `S` so the existing wires stay. Good ones
to try: `side_gap` (−3 to 5), `envelope_offset` (−5 to 10), `port_notch_width`, `gauge_y`. The
allowed range of every parameter is in [parameters.md](parameters.md); values outside it are
reported as errors. A slider whose name isn't a parameter is listed under "ignored" in the report,
which catches typos.

### 2.4 Many sliders at once

1. Add two more inputs to the Script component: **`sliders`** and **`groups`**.
2. Wire a **Button** (search `Button`) into `sliders`, and a Panel into `groups`. Type the groups you
   want into that Panel, for example `fit,coupon` or `cubby`. All groups: `cubby, ports, phone, fit,
   strength, perforation, drawer, tolerances, coupon, checks`.
3. Press the button. One slider per parameter in those groups appears to the left of the component,
   named, set to the current value and already wired into `S`. Choices such as `grid_style` become a
   Value List, and on/off settings a Boolean Toggle.

Creating sliders doesn't change the design. Parameters that already have a slider are skipped, so
pressing the button again is safe.

### 2.5 Your own values, baking and exporting

- **Your values:** open the script (double-click the component) and fill in `MY_VALUES` in the
  SETTINGS block at the top, for example `"envelope_offset": 0.8,` after the fit coupon test.
  Sliders win over `MY_VALUES`, and `MY_VALUES` wins over the defaults.
- **Bake:** right-click an output, for example `coupon`, → **Bake…** to put it into the Rhino
  document.
- **Export:** add an input **`export`** and wire a Button into it. Save the `.gh` file first: the
  STL, 3MF and STEP files are written to a folder `rav4shelf_out` next to it, in print orientation.
  To choose the folder, set `EXPORT_FOLDER` in the SETTINGS.
- **Update** to a newer version of the file: copy your `MY_VALUES`, paste the new file over the
  whole script, and put `MY_VALUES` back. The sliders and wires stay.

Save the definition (for example in the repo's `grasshopper/` folder).

## Part 3 – learn more with the model

Each exercise uses ordinary Grasshopper components on the Script component's outputs.

1. **Colour the parts.** Right-click the Script component → turn **Preview** off. Add a **Custom
   Preview** for each of `coupon`, `gauge` and `envelope`, each with a **Colour Swatch** on its
   material input. Pick a pale, transparent colour for the envelope (in the Colour Swatch, lower the
   alpha).
2. **Weigh the test prints.** Wire `gauge` into **Volume**. The volume is in mm³; one cm³ of PETG
   weighs about 1.27 g. Add a **Multiplication** component (search `A*B`) with a Panel containing
   `0.00127` to see grams.
3. **Cut the cubby at shelf height.** Add **Construct Point** (X 0, Y 0, Z from a slider 0 to 78),
   feed it into the **Origin** of an **XY Plane**, and use **Brep | Plane** with `envelope` and that
   plane. The curve is the cubby's outline at that height; drag the slider to watch the walls lean.
4. **Look at the data.** Wire `cubby` into a Panel: a list of curves and boxes. Use **List Item**
   with an index slider to pick one of them out.

Good next resources, both free: *The Grasshopper Primer* by Mode Lab, and McNeel's "Getting
Started with Grasshopper" videos.

## Troubleshooting

| Symptom | Fix |
|---|---|
| The component is red | Click its balloon, or read the `out` output. Report the message. |
| The parts appear many times, or the report repeats | Input `S` is on Item Access: right-click it → **List Access**. The report says so too. |
| A slider has no effect | Its name must be the parameter name exactly (case matters). Mistyped names are listed as "ignored" in the report. |
| "document units are … not millimetres" | Run `Units` in Rhino and pick Millimeters. |
| Nothing visible in Rhino | Zoom out (the cubby is ~240 mm wide); check that the component's Preview is on. |
| "export: save the .gh file first, or set EXPORT_FOLDER" | Save the definition, or set `EXPORT_FOLDER` in the SETTINGS. |
| "the component needs an input named 'S' for the sliders" | Add the `S` input (2.2, step 3). |
| "Nothing built: fix the problems above" | A check failed; the report above it says which value is the problem. |
