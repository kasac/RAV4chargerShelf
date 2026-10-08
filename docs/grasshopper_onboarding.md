# Grasshopper onboarding

From zero to the live model in about 30 minutes: a warm-up, then the whole project in one Python 3
Script component with sliders. Not yet tried in Rhino: please report anything that differs.

Grasshopper is Rhino's visual programming editor. **Components** (boxes) on a **canvas** are joined by
**wires**; data flows left to right, and moving a slider recomputes everything after it. Results show
as a **preview** in the Rhino viewports and become real objects only when you **bake** them. Here the
geometry comes from the project's tested Python code; Grasshopper is the dashboard on top.

## 1. Warm-up (10 minutes)

New Rhino model in millimetres, then type `Grasshopper`. Zoom with the wheel, pan with the right
mouse button, and place a component by double-clicking the canvas and typing its name.

1. Place **Circle** (inputs *P* plane, *R* radius).
2. Double-click, type `0<20<50`: a **Number Slider** from 0 to 50, set to 20. Wire it into **R**.
3. Add **Unit Z** with a second slider `0<30<100` on **F**, then **Extrude**: circle into **B**,
   Unit Z into **D**.
4. Add **Cap Holes**, then **Volume** with a **Panel** on its **V** output (mm³).
5. Drag the sliders.

Good to know: hover over an input or output to see its data. Orange or red components have a message
in their balloon. Shift-drag adds a wire, Ctrl-drag removes one. Right-click → **Preview** hides,
**Bake…** copies to Rhino.

## 2. The model in one component

1. Copy [`rhino/rav4shelf_rhino.py`](../rhino/rav4shelf_rhino.py) (on GitHub: **Copy raw file**).
2. Place a **Python 3 Script** component. Not "Python Script" or "IronPython 2 Script": those run
   Python 2.
3. Zoom in until **⊕ / ⊖** appear. Keep one input: rename it **`S`** and set **List Access**
   (right-click). Make five outputs: **`coupon`**, **`gauge`**, **`envelope`**, **`cubby`**, **`report`**.
4. Double-click the component, replace its code with the file, press **Run**, close the editor.
5. Wire `report` into a Panel.

The coupon, the gauge, the cubby envelope and the LED free zone appear in the viewports (zoom out if
needed: the cubby is ~240 mm wide).

**Sliders:** a Number Slider named exactly like a parameter, e.g. `shelf_height` (double-click its
name: name, range 30–75, value 58, floating point), wired into `S`. Ranges are in
[parameters.md](parameters.md); unknown names are listed as "ignored" in the report.

**Many sliders:** add inputs **`sliders`** (a Button) and **`groups`** (a Panel, e.g. `fit,coupon`).
Pressing the button creates and wires one slider per parameter of those groups, set to the current
values.

**Values, baking, export:** your values go in `MY_VALUES` at the top of the script (sliders win over
them). Right-click an output → **Bake…**. Add an input **`export`** with a Button to write STL, 3MF
and STEP next to the saved `.gh` (or to `EXPORT_FOLDER`). To update, paste the new file and copy your
`MY_VALUES` back.

## 3. Next steps

- **Colours:** turn the component's Preview off and feed each output into a **Custom Preview** with a
  **Colour Swatch**.
- **Weight:** `gauge` → **Volume** → × 0.00127 = grams of PETG.
- **Sections:** **Brep | Plane** of `envelope` with an **XY Plane** raised by a slider shows the cubby
  outline at that height.
- Learn more: *The Grasshopper Primer* (Mode Lab) and McNeel's "Getting Started" videos.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "This script needs Python 3" or "cannot import abc from importlib" | use a **Python 3 Script** component; in Rhino, `ScriptEditor`, not `EditPythonScript` |
| Parts appear many times | input `S` → **List Access** |
| A slider does nothing | its name must match the parameter exactly; see "ignored" in the report |
| "document units are … not millimetres" | `Units` → Millimeters |
| "export: save the .gh file first…" | save the definition, or set `EXPORT_FOLDER` |
| Red component, anything else | read its balloon or the `out` output and report the message |
