# Fitting the shelf to your car

The cubby shape doesn't need to be measured any more. Its defaults are **fitted to the Vela3D
module**, a tested design whose outer surface appears to follow a 3D scan of the cubby (see
README → Reference comparison). Two quick test prints check that shape in *your* car. You only
need to measure the plugs, the phone and anything a test print shows to be different.

Allow about an hour of printing and 15 minutes in the car.

## What you need

- The two test prints (step 1)
- A ruler, and paper strips or feeler gauges (80 g/m² paper is about 0.1 mm per sheet)
- **The adapters, cables and phone you actually use.** A long 12 V USB adapter is the most common
  reason these shelves don't seat (see the D-Lumina review in the brief).

## Coordinate frame

The same frame is used everywhere: parameters, the Rhino model, the previews.

```
PLAN (looking down into the cubby)            FRONT (looking into the cubby from the driver seat)

          rear wall  y = D_cubby                            _____/‾‾‾‾‾‾‾‾\_____   roof, H_cubby,
   +-------------[ plugs ]-------------+                   /    roof pocket     \  higher in the
   |               |X_ports|           |                  |<------ W_ref ------>|  middle (pocket)
   |                                   |                  |    at z = z_ref     |
-x |                 + x = 0           | +x                \                    /  side walls: an arc
   |            (centreline)           |                    \                  /   (wall_radius) with
   \                                   /  rear corners       \________________/    wall_lean_deg at z_ref
    +---------------------------------+                         Qi pad, z = 0
          front lip  y = 0  (driver)

SIDE (section through the plugs, lip on the left)

   y = 0 (lip)                             y = D_cubby (rear wall)
   |<------------------ D_cubby ------------------>|
   \__ roof pocket rises toward the front          |
   |      ‾‾‾‾‾‾‾‾‾\__________________________ ____|  z = H_cubby (flat roof)
   |          shelf top = shelf_height        [adapter]  <- H_ports_top  (highest point of plug + cable)
   |      ===========================        [ plugs ]
   |                                          [       ]  <- H_ports_bottom
   |                              |<- D_ports ->|
   |___________ Qi pad ____________________________|  z = 0
```

- **x** runs to the right as seen from the driver, with 0 on the cubby centreline.
- **y** runs from the front lip (y = 0) into the dash toward the rear wall.
- **z** runs up from the Qi pad surface (z = 0).

## The cubby envelope (fitted, about 15 numbers)

These values describe the cubby. They were fitted to the outer surface of the Vela3D module:
side walls RMS 0.14 mm, rear corners within ±0.5 mm, roof RMS 0.09 mm.

| Parameter | What it describes |
|---|---|
| `W_ref`, `z_ref` | width 10 mm behind the lip, at height `z_ref` above the pad |
| `wall_lean_deg` | how much each side wall leans at `z_ref` (wider going up) |
| `wall_radius` | seen from the front, the side walls are an arc of this radius: they curve in toward the floor |
| `W_rear_delta` | how much narrower the cubby is near the rear wall than near the lip |
| `D_cubby` | lip to rear wall |
| `H_cubby` | height of the flat part of the roof |
| `rear_corner_length`, `rear_corner_inset`, `rear_corner_r_side`, `rear_corner_r_back` | rear corners seen from above: a chamfer from `rear_corner_length` in front of the rear wall to `rear_corner_inset` in from the side, rounded with the two radii |
| `roof_pocket_width`, `roof_pocket_blend`, `roof_pocket_rise`, `roof_pocket_end`, `roof_pocket_shape` | the roof is higher over the middle 136 mm toward the front (by `roof_pocket_rise` near the lip, flattening out at `roof_pocket_end`) |
| `W_lip` | opening width at the lip (only used to check that the shelf goes in) |

Three things the file can't tell, so they're assumptions:
- **Foam allowance.** Vela3D mounts its module with foam, so your walls are some unknown distance
  outside this envelope. That distance is `envelope_offset`, and the fit coupon measures it.
- **Floor height.** The floor is assumed to be where the module's side wings end. That's the
  highest it can be (the module has to fit), so the profile gauge can only show a gap under it,
  never jam.
- **Fore-aft position.** The module's front is assumed to sit 8 mm behind the lip.

## Step 1 – print the two test prints

```bash
python tools/rav4shelf.py coupon      # out/fit_coupon.* and out/profile_gauge.*
```

- **Fit coupon** (~20 g, 30–40 min): the shelf's exact outline and 8 mm edge band at shelf height,
  on a thin plate with an open centre. Print it plate down.
- **Profile gauge** (~11 g, ~20 min): a flat frame that has the cubby's cross-section seen from
  the front, at `gauge_y` = 30 mm behind the lip, 0.3 mm smaller all round. It shows the curved
  walls, the floor and the roof pocket at once. Print it flat.

Use PETG for both, like the real shelf, so the shrinkage matches. With `side_gap` 0 and
`envelope_offset` 0 (the defaults), the coupon is exactly the size of the Vela3D module at that
height.

Optional, before printing anything: `python tools/rav4shelf.py preview` writes a 1:1 paper template
(`out/fit_template_1to1.svg`). Print it at 100 % and check that the 50 mm bar measures 50 mm.

## Step 2 – try them in the car

**Profile gauge.** Stand it upright in the cubby, about 30 mm behind the lip, with its long straight
edge on the Qi pad and the raised middle of its top edge up.

1. **Sides:** is the gap to the side walls even from top to bottom? This checks the wall lean and
   curve.
2. **Top:** does it reach the roof, and does the raised middle match the roof pocket?
3. **Bottom:** is there a gap between its bottom edge and the Qi pad? Measure it.

**Fit coupon.** Plate up, rim down, notch toward the rear wall, exactly as the shelf will sit. Hold
it with its top at `shelf_height` (default 58 mm) above the Qi pad. A stack of books or a block cut
to height helps.

4. **Side gaps:** slide paper strips or feeler gauges between the rim and the wall at the front
   and at the rear, on both sides. Note the four gaps.
5. **Rear:** does it reach the rear wall? Do the rear corners touch before the sides do?
6. **Plugs:** with your plugs inserted, is there air around them (in the notch, or under the
   shelf)? Also look from the driver seat: can you still see the plugs?

## Step 3 – what to change

Put any changes in `params/measured.json`, then reprint the part that was off.

| What you saw | Change |
|---|---|
| The same gap `g` per side on the coupon and the gauge | `envelope_offset` = `g`. Then choose `side_gap`: 0 for a snug fit, the pad thickness for felt or foam (like Vela3D), or slightly negative for a press fit. |
| Gap bigger at the front than at the rear (or the other way round) | `W_rear_delta` |
| Gauge: the gap changes from top to bottom along the side | `wall_lean_deg` (and `wall_radius` if it changes unevenly) |
| Gauge: gap `h` under its bottom edge | the floor is lower than assumed: add `h` to `z_ref`, `H_cubby` and the `shelf_height` you want |
| Gauge: sits on the pad but doesn't reach the roof (gap `t`) | add `t` to `H_cubby` (and to `roof_pocket_rise` if only the middle is off) |
| Rear corners touch first | increase `rear_corner_inset` or `rear_corner_length` |
| Coupon too long or too short front to back | `D_cubby` |
| Plugs touch the coupon | raise `shelf_height`, or size the notch: `port_notch_width`, `port_notch_depth`, `port_notch_offset_x` |
| It doesn't go through the opening flat | `W_lip` (the checks then warn) |

If both prints fit, the cubby is described well enough and the shelf can be designed on top of it.

## Step 4 – measure the plugs and the phone

These are still guesses. They decide the shelf height and the port notch.

| Parameter | How to measure |
|---|---|
| `H_ports_top` | Plug in your **real** adapters and cables, routed as you normally route them. Measure the highest point of any plug, adapter body or cable bend, above the Qi pad. This single number decides whether plugs can pass under the shelf. |
| `H_ports_bottom` | Lowest point of the plug cluster above the Qi pad. Only used in the previews. |
| `W_ports` | Lateral width of the whole cluster (plugs, adapters, cable bends). Measure from the left wall to the cluster's left edge (a) and to its right edge (b), at plug height: `W_ports = b - a`. |
| `X_ports` | Lateral centre of the cluster relative to the cubby centreline, positive to the right. With a and b from above and the cubby width W at that height: `X_ports = (a + b) / 2 - W / 2`. |
| `D_ports` | How far the plugs, adapters and cable bends stick out from the rear wall into the cubby. |
| `qi_center_x`, `qi_center_y` | Centre of the charging spot (where the phone has to lie): lateral position from the centreline, and distance from the lip. |
| `phone_length`, `phone_width`, `phone_thickness` | Your phone **in its case**, including the camera bump. The model assumes the phone lies crosswise (long side along x). |

**Shelf height.** `shelf_height` is the height of the shelf's top surface above the Qi pad. The
shelf's edge band reaches `frame_height` (8 mm) below it. The default, 58 mm, is about where the
Vela3D drawers sit.
- Plugs pass under the shelf if `shelf_height >= H_ports_top + port_clearance + frame_height`.
- Otherwise they poke up through the rear notch. The checks tell you whether the notch clears them.
- The phone needs `phone_clearance_min` (20 mm) under the lowest part of the shelf.
- Whatever is left up to the roof (`H_cubby - shelf_height`, more under the roof pocket) is the
  space for the drawer.

Write these into `params/measured.json` (start from `params/measured.example.json`) and run
`python tools/rav4shelf.py check`. The report lists every value that is still unconfirmed.

## If you would rather measure the cubby yourself

Measure `W_ref` 10 mm behind the lip at height `z_ref`. Measure a second width `W_low` 20 mm lower;
then `wall_lean_deg = atan((W_ref - W_low) / 40)` in degrees. Keep the fitted `wall_radius`, which
is hard to measure. For `W_rear_delta`, measure the width 10 mm in front of the rear wall at the
same height and subtract `W_ref`. For the rear corners, press card into a corner and trace it.
Measure each value three times and take the median. For widths, take the smallest reading: trim
panels bulge, and they flex if you push.

If you have the Vela3D model in `reference/`, `python tools/rav4shelf.py reference` compares your
numbers with the tested design. A difference of more than about 5 mm per side usually means a
wrong measurement, or that your car has the other dash variant.

## Reporting back

Please send:
- your `params/measured.json`
- what you saw in step 2: the four coupon gaps, the gauge gaps (sides, top, bottom), and anything
  that touched
- photos of both prints in the cubby, from the driver seat and from above

The shelf phase starts from there.
