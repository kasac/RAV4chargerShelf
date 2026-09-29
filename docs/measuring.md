# Measuring the cubby

Every fit-critical number in `params/default.json` is a **placeholder guess**. This guide explains
how to replace the guesses with measurements, and then how to check them with a paper template and
the printed fit coupon before the real shelf is printed.

Allow 30–45 minutes in the car.

## What you need

- A digital caliper (150 mm, with a depth rod) and a 300 mm steel ruler
- A flashlight, painter's tape and a pen
- Paper or card strips, and feeler gauges if you have them (80 g/m² paper is about 0.1 mm per sheet)
- **The adapters, cables and phone you actually use.** A long 12 V USB adapter is the most common
  reason these shelves don't seat (see the D-Lumina review in the brief).

## Coordinate frame

The same frame is used everywhere: parameters, the Rhino model, the previews.

```
PLAN (looking down into the cubby)            FRONT (looking into the cubby from the driver seat)

          rear wall  y = D_cubby                 z = H_cubby  ____________________   <- roof
   +-------------[ plugs ]-------------+                     |<----- W_top ----->|
   |               |X_ports|           |                     |                    |
   |                                   |                      \                  /   side walls
-x |                 + x = 0           | +x                     \                /    may lean
   |            (centreline)           |                       |<- W_bottom ->|
   |                                   |          z = 0        |==== Qi pad ====|
   +-----------------------------------+
          front lip  y = 0  (driver)

SIDE (section through the plugs, lip on the left)

   y = 0 (lip)                             y = D_cubby (rear wall)
   |<------------------ D_cubby ------------------>|
   +-----------------------------------------------+  z = H_cubby (roof)
   |                                               |
   |          shelf top = shelf_height        [adapter]  <- H_ports_top  (highest point of plug + cable)
   |      ===========================        [ plugs ]
   |                                          [       ]  <- H_ports_bottom
   |                              |<- D_ports ->|
   |___________ Qi pad ____________________________|  z = 0
```

- **x** runs to the right as seen from the driver, with 0 on the cubby centreline.
- **y** runs from the front lip (y = 0) into the dash toward the rear wall.
- **z** runs up from the Qi pad surface (z = 0). Measure from the pad's surface, not from its frame.

## The measurements

Measure each value three times and write down the median. For widths, take the **smallest**
reading at that spot: trim panels bulge, and the shelf has to fit the narrowest point. Don't push on
the side walls while measuring; they flex.

### Cubby

| Parameter | How to measure |
|---|---|
| `H_cubby` | From the Qi pad surface straight up to the roof. If the roof slopes, use the **lowest** point above where the shelf will be. |
| `D_cubby` | From the front lip (the leading edge of the opening) to the rear wall, at roughly the height where the shelf will sit. Use the caliper's depth rod against the rear wall. |
| `W_bottom` | Inner width just above the Qi pad (about 2 mm up), **10 mm behind the front lip**. |
| `W_top` | Inner width just below the roof, also **10 mm behind the front lip**. `W_top` and `W_bottom` tell the model whether the side walls lean. If they are equal, the walls are vertical. |
| `W_rear_delta` | Width **10 mm in front of the rear wall** minus width **10 mm behind the lip**, both at shelf height. Negative means the cubby narrows toward the rear. Molded parts usually have a slight draft, so expect -2 … 0. |
| `R_rear_corner` | Radius of the rounded inner corner where a side wall meets the rear wall, seen from above. Press a piece of card into the corner and trace it, or compare with coins (a €1 coin has a 11.6 mm radius, a €0.10 coin 9.9 mm). Use 0 if the corner is sharp. |
| `W_lip` | Narrowest width of the **opening** at the front lip, at shelf height. If the lip is narrower than the inside (an undercut), the shelf has to be tilted in, and the checks warn about it. |

### Plugs and cables (rear wall)

Plug in your **real** adapters and cables first, routed the way you normally route them.

| Parameter | How to measure |
|---|---|
| `H_ports_top` | Highest point of any plug, adapter body or cable bend, above the Qi pad. This single number decides whether plugs can pass under the shelf. |
| `H_ports_bottom` | Lowest point of the plug cluster above the Qi pad. Only used in the previews. |
| `W_ports` | Lateral width of the whole cluster (plugs, adapters, cable bends). Measure from the left wall to the cluster's left edge (a) and to its right edge (b), at plug height: `W_ports = b - a`. |
| `X_ports` | Lateral centre of the cluster relative to the cubby centreline, positive to the right. With a and b from above and the cubby width W at that height: `X_ports = (a + b) / 2 - W / 2`. |
| `D_ports` | How far the plugs, adapters and cable bends stick out from the rear wall into the cubby. |

### Phone and Qi spot

| Parameter | How to measure |
|---|---|
| `qi_center_x` | Lateral position of the charging spot's centre (where the phone has to lie), from the centreline. Many pads have a marking. Otherwise use the spot where your phone charges reliably. |
| `qi_center_y` | Distance from the front lip to that centre. |
| `phone_length`, `phone_width`, `phone_thickness` | Your phone **in its case**, including the camera bump. The model assumes the phone lies crosswise (long side along x). |

### Decide the shelf height

`shelf_height` is the height of the shelf's **top surface** above the Qi pad. It is a decision, not a
measurement, but it depends on the numbers above. The shelf's solid edge band reaches
`frame_height` (default 8 mm) below its top surface.

- **Plugs pass under the shelf** (simplest): `shelf_height >= H_ports_top + port_clearance + frame_height`.
- **Plugs poke up through the rear notch**: the shelf can sit lower. Size `port_notch_width` and
  `port_notch_depth` so the notch clears the cluster; the checks tell you by how much it falls short.
- The phone needs `phone_clearance_min` (default 20 mm) under the lowest part of the shelf.
- Whatever is left above the shelf (`H_cubby - shelf_height`) is the space for the drawer.

The build report prints all of these numbers, so try a value and adjust it.

## Write the numbers down

1. Copy `params/measured.example.json` to `params/measured.json`.
2. Replace every `null` with your value in millimetres. Delete a line to keep the default.
3. Run `python tools/rav4shelf.py check`. Every tool (CLI, `rhino/build_all.py`, Grasshopper)
   applies `params/measured.json` automatically. The report lists any placeholder that is still in
   use, and any check that fails.

Also take a few photos with a ruler in the frame. They help a lot when something doesn't fit.

## Step 0 – paper template (5 minutes, optional)

`python tools/rav4shelf.py preview` writes `out/fit_template_1to1.svg`. Print it at **100 %**, with no
"fit to page". Check that the 50 mm bar measures 50 mm, glue the print to card, cut along the solid
blue line and try it in the cubby at shelf height. This catches gross errors (a wrong depth, a notch
on the wrong side) before anything is printed.

`out/overview.svg` shows plan, front and side views with the plugs and the phone. Use it to check
that the measurements were read the way you meant them.

## Step 1 – print and test the fit coupon

The fit coupon is the shelf's outline and edge band only: a thin plate (6 layers) with the same rim
the real shelf will have, and an open centre. It prints in about half an hour and tests everything
that touches the car.

- **Generate it** with `python tools/rav4shelf.py coupon`, which writes `out/fit_coupon.stl` and
  `out/fit_coupon.3mf`. You can also use `rhino/build_all.py`, or the Grasshopper Export component.
- **Print it** with the settings in the README's print table. Use PETG, like the real shelf, so the
  shrinkage matches.

### Test procedure

1. **Orientation:** plate **up**, rim **down**, exactly as the shelf will sit, with the notch toward
   the rear wall.
2. **Insert** it through the lip opening. If it only goes in tilted, note that.
3. **Height:** hold it with the plate top at `shelf_height` above the Qi pad. A stack of books or a
   block cut to height helps. If the walls lean outward (`W_top > W_bottom`), it will wedge by itself
   at some height. Note that height.
4. **Side gaps:** at the front and at the rear, on both sides, slide paper strips or feeler gauges
   between the rim and the wall. The gap should be about `side_gap` (default 0.5 mm, about 5 sheets).
5. **Rim tilt:** does the rim touch the wall along its full height, or only at its top or bottom
   edge? This tests the wall lean.
6. **Rear corners:** does the rim hit the rounded rear corners before the sides touch?
7. **Plugs:** with your plugs inserted, is there at least `port_clearance` of air around them in the
   notch? Also look from the driver seat: can you still see the plugs?
8. **Front edge:** is the edge where you want it (`front_recess` behind the lip)?

### Adjust and reprint

| Observation | Change |
|---|---|
| Gap too big or too small, the same everywhere | Re-measure `W_top` / `W_bottom`. If the measurement was right and you just want a snugger or looser fit, change `side_gap`. |
| Gap differs between front and rear | `W_rear_delta` |
| Rim touches only at its top or bottom edge | The ratio of `W_top` to `W_bottom` (the wall lean) |
| Rear corners hit first | Increase `R_rear_corner` |
| Plugs touch the notch | `port_notch_width`, `port_notch_depth`, `port_notch_offset_x` |
| It wedges too low or too high | Width values, or plan on legs (see the shelf phase) |

Repeat until the coupon drops in with the gaps you want. Then please report back with:

- your `params/measured.json`
- the gaps you measured (front/rear × left/right) and where it touched
- photos of the coupon in the cubby, from the driver seat and from above

The shelf phase starts from those results. Whether the shelf stands on legs or wedges between the
walls depends on what the coupon shows.
