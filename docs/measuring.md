# Fitting to your car

The cubby shape is estimated from the outside dimensions of other models and from inspection and
measurements of the car. Two test prints check it; then you measure what they can't show. About an
hour of printing and 15 minutes in the car.

You need the two prints, a ruler, paper strips or feeler gauges (80 g/m² paper ≈ 0.1 mm), and the
adapters, cables and phone you actually use.

Frame in mm: x to the right seen from the driver (0 = centreline), y from the lip into the dash,
z up from the Qi pad.

## 1. Print

`python tools/rav4shelf.py coupon` writes both prints to `out/`. Print them in PETG as exported.

- **Fit coupon** (~20 g): the shelf outline and its 8 mm edge band at `shelf_height`, on a thin plate
  with an open centre.
- **Profile gauge** (~11 g): the cubby cross-section 30 mm behind the lip, 0.3 mm smaller all round.

## 2. Try them in the car

**Profile gauge:** stand it upright about 30 mm behind the lip, shorter straight edge on the Qi pad.
Check the side gap from bottom to top, whether the top edge touches the roof all along, and any gap
under the bottom edge.

**Fit coupon:** plate up, rim down, notch toward the rear wall, top at `shelf_height` (58 mm) above the
pad (books help). Note the side gaps at the front and rear on both sides, whether the rear corners
touch first, and whether your plugs clear it.

## 3. What to change

Put changes in `params/measured.json`, then reprint what was off.

| You saw | Change |
|---|---|
| The same gap `g` per side on both prints | `envelope_offset` = `g`; then `side_gap`: 0 snug, pad thickness for felt, negative for a press fit |
| Gap larger at the front than at the rear, or the reverse | `W_rear_delta` |
| Gauge side gap changes from bottom to top | `wall_lean_deg`, and `wall_radius` if uneven |
| Gap `h` under the gauge | add `h` to `z_ref`, `H_cubby` and `shelf_height` |
| Gauge doesn't reach the roof (gap `t`) | add `t` to `H_cubby` |
| Gauge touches the roof only in the middle | the bulge reaches further forward: check `led_y`, `roof_bulge_diameter` |
| Rear corners touch first | more `rear_corner_inset` or `rear_corner_length`; `rear_corner_r_side`, `rear_corner_r_back` round them |
| Coupon too long or too short | `D_cubby` |
| It won't go through the opening flat | `W_lip` |
| Plugs touch the coupon | raise `shelf_height`, or widen the notch (`port_notch_width`, `port_notch_depth`) |

To measure the cubby instead: `W_ref` is the width 10 mm behind the lip at height `z_ref` (55 mm). Take
the smallest of three readings; trim panels flex.

## 4. Measure the plugs, the phone and the roof LED

These are guesses until you measure them.

| Value | How |
|---|---|
| `H_ports_top` | highest point of your real plugs, adapters and cable bends above the pad |
| `H_ports_bottom` | lowest point of the plug cluster (previews only) |
| `W_ports`, `X_ports` | width of the cluster, and its centre from the centreline (+ = right) |
| `D_ports` | how far plugs and cables stick out from the rear wall |
| `qi_center_x`, `qi_center_y` | centre of the charging spot: from the centreline, and from the lip |
| `phone_length`, `phone_width`, `phone_thickness` | your phone in its case, camera bump included |
| `led_y` | lip to the centre of the roof LED; set `led_x` too if it is off-centre |
| `roof_bulge_depth` | roof height at the side minus roof height next to the LED (ruler standing on the pad) |
| `roof_bulge_diameter` | roughly how wide the bulge is |
| `shelf_height` | the height you want for the shelf top; the checks say whether the plugs clear it |

Then run `python tools/rav4shelf.py check`: it lists every value still unconfirmed. Please send your
`params/measured.json`, the gaps from step 2 and photos of both prints in the cubby.
