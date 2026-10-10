# Parameter reference

Generated from `params/default.json` by `python tools/gen_param_docs.py`. Do not edit by hand.

**PH** = not confirmed for your car yet. **PH R** = an estimate for the test prints to
confirm; plain **PH** = a guess to measure. Range = slider range in Grasshopper; values
outside it are rejected.
`auto` = derived from other parameters unless you set a value.

## cubby

Used by: the cubby model: fit coupon, profile gauge, all parts

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `W_ref` | 231.55 | mm | 80 .. 350 | PH R | Cubby width 10 mm behind the front lip, at height z_ref. Estimate; see envelope_offset. |
| `z_ref` | 55 | mm | 0 .. 200 |  | Height above the Qi pad at which W_ref and wall_lean_deg are given. If you measure, measure there. |
| `wall_lean_deg` | 6.84 | deg | -30 .. 30 | PH R | Lean of each side wall at z_ref, seen from the front. Positive = the cubby gets wider going up. |
| `wall_radius` | 504.98 | mm | 0 .. 5000 | PH R | Radius of the side walls seen from the front: they curve in toward the floor. 0 = straight walls. |
| `W_rear_delta` | -9.44 | mm | -40 .. 40 | PH R | Width 10 mm in front of the rear wall minus width 10 mm behind the lip, at the same height. Negative = the cubby narrows toward the rear. |
| `D_cubby` | 129.88 | mm | 40 .. 300 | PH R | Depth from the front lip to the rear wall, above the plugs. Estimate. |
| `H_cubby` | 77.85 | mm | 20 .. 200 | PH R | Height of the flat part of the roof above the Qi pad. Estimate; the profile gauge checks it. |
| `rear_corner_length` | 22.3 | mm | 0 .. 100 | PH R | Rear corners seen from above: a chamfer that starts this far in front of the rear wall on the side wall ... (0 = plain corner rounded with rear_corner_r_back). |
| `rear_corner_inset` | 4.84 | mm | 0 .. 50 | PH R | ... and ends this far in from the side wall on the rear wall. |
| `rear_corner_r_side` | 67.33 | mm | 0 .. 300 | PH R | Fillet radius where the rear-corner chamfer meets the side wall. |
| `rear_corner_r_back` | 12.57 | mm | 0 .. 100 | PH R | Fillet radius where the rear-corner chamfer meets the rear wall. |
| `roof_pocket_rise` | 0 | mm | 0 .. 100 |  | Some RAV4 versions have a raised pocket in the middle of the roof toward the front (an arch-shaped recess at the cabin-facing edge): how much higher than H_cubby it is, 10 mm behind the lip. 0 = no pocket: on the GR Sport PHEV the front edge of the roof is straight. |
| `roof_pocket_width` | 135.86 | mm | 0 .. 350 |  | Roof pocket (only used if roof_pocket_rise > 0): width of its full-height part. |
| `roof_pocket_blend` | 9.82 | mm | 0 .. 100 |  | Roof pocket (only used if roof_pocket_rise > 0): width of the smooth transition on each side. |
| `roof_pocket_end` | 107.68 | mm | 10 .. 300 |  | Roof pocket (only used if roof_pocket_rise > 0): distance from the lip where it has flattened out to H_cubby. |
| `roof_pocket_shape` | 1.47 |  | 0.5 .. 4 |  | Roof pocket (only used if roof_pocket_rise > 0): shape of the rise along the depth, 1 = straight ramp, 2 = parabola. |
| `led_x` | 0 | mm | -100 .. 100 |  | Lateral position of the LED in the roof (it lights the Qi pad and the plugs), from the cubby centreline. It sits in the middle. |
| `led_y` | 65 | mm | 0 .. 300 | PH | Distance from the front lip to the centre of the roof LED. Guess: the middle of the cubby. |
| `roof_bulge_depth` | 3 | mm | 0 .. 30 | PH | The roof bulges down slightly in the middle, with the LED at its centre: how far its lowest point is below H_cubby. 0 = flat roof. Guess. |
| `roof_bulge_diameter` | 60 | mm | 0 .. 250 | PH | Diameter of the roof bulge, modelled as a smooth round bump centred on the LED. Guess. |
| `W_lip` | 236 | mm | 60 .. 350 | PH R | Narrowest width of the opening at the front lip, at shelf height. Only used to check that the shelf can be inserted flat. Estimate. |

## ports

Used by: checks, previews

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `H_ports_top` | 40 | mm | 0 .. 150 | PH | Highest point of the plugs WITH your real adapters and cables inserted, above the Qi pad. Measure your longest 12 V adapter. |
| `H_ports_bottom` | 15 | mm | 0 .. 150 | PH | Lowest point of the plug cluster above the Qi pad. Preview only. |
| `X_ports` | 0 | mm | -150 .. 150 | PH | Lateral centre of the port cluster, from the cubby centreline (+ = right as seen from the driver). |
| `W_ports` | 60 | mm | 0 .. 250 | PH | Lateral width of the port cluster including plugs, adapters and cables. |
| `D_ports` | 45 | mm | 0 .. 200 | PH | How far plugs, adapters and cable bends stick out from the rear wall into the cubby. |

## phone

Used by: checks, previews

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `qi_center_x` | 0 | mm | -150 .. 150 | PH | Lateral centre of the Qi charging spot (where the phone lies). |
| `qi_center_y` | 65 | mm | 0 .. 300 | PH | Distance from the front lip to the centre of the Qi charging spot. |
| `phone_length` | 165 | mm | 50 .. 250 | PH | Phone length incl. case. The phone is assumed to lie crosswise (long side along x). |
| `phone_width` | 78 | mm | 30 .. 150 | PH | Phone width incl. case. |
| `phone_thickness` | 11 | mm | 3 .. 40 | PH | Phone thickness incl. case and camera bump. |

## fit

Used by: fit coupon, shelf

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `shelf_height` | 58 | mm | 5 .. 190 | PH | Height of the shelf's TOP surface above the Qi pad. Default 58: about 20 mm above it for a drawer, 50 mm below it for the phone and plugs. Must clear your plugs (H_ports_top). |
| `front_recess` | 8 | mm | 0 .. 60 |  | How far the shelf's front edge sits behind the front lip (hides the shelf, looks closer to stock). |
| `rear_gap` | 1 | mm | 0 .. 20 |  | Gap between the shelf's rear edge and the rear wall. |
| `side_gap` | 0 | mm | -3 .. 5 |  | Gap per side between the shelf edge and the side wall (see envelope_offset). 0 = exactly the size of the fitted envelope at that height. Negative = bigger (press fit). Use the pad thickness if you add felt/foam. |
| `envelope_offset` | 0 | mm | -5 .. 10 |  | How far your car's side walls are outside the estimated envelope. Read it off the fit coupon: the gap you see per side when side_gap is 0. |
| `corner_radius_front` | 4 | mm | 0 .. 30 |  | Corner radius of the shelf's front corners (cosmetic). |
| `port_notch_width` | 76 | mm | 0 .. 250 |  | Width of the cut-out in the shelf's rear edge over the port cluster. 0 disables the notch. |
| `port_notch_depth` | 50 | mm | 0 .. 200 |  | How far the notch reaches forward into the shelf, from its rear edge. (The brief's port_notch_height: the notch is a through-cut, so it has a depth, not a height.) |
| `port_notch_offset_x` | 0 | mm | -100 .. 100 |  | Lateral shift of the notch centre relative to X_ports. |
| `port_notch_radius` | 3 | mm | 0 .. 20 |  | Corner radius of the notch. |
| `port_clearance` | 3 | mm | 0 .. 20 |  | Minimum air gap the checks demand around plugs and cables. |
| `phone_clearance_min` | 20 | mm | 5 .. 100 |  | Minimum free height under the lowest part of the shelf, for the phone on the Qi pad plus room to slide it in and out. |
| `led_keepout_diameter` | 50 | mm | 0 .. 150 |  | Free zone around the roof LED (the LED itself is about 15 mm): no part may be built inside this circle, from the roof down to the Qi pad, so the LED stays uncovered and still lights the charger and plugs. 0 = no free zone. |

## strength

Used by: shelf (fit coupon uses frame_height)

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `wall_thickness` | 2 | mm | 0.8 .. 6 |  | Thickness of the shelf skirt, ribs and drawer walls. |
| `deck_thickness` | 2.4 | mm | 1 .. 8 |  | Thickness of the shelf deck. |
| `frame_width` | 8 | mm | 3 .. 20 |  | Width of the solid rim around the grid, seen from above. |
| `frame_height` | 8 | mm | 2 .. 30 |  | Height of the solid edge band, from the deck top down (skirt). This band is what touches the side walls. |
| `rib_count` | 2 |  | 0 .. 10 |  | Number of stiffening ribs under the deck, running side to side. |
| `rib_height` | 5 | mm | 0 .. 30 |  | Rib height below the deck. |

## roof

Used by: roof plate

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `roof_thickness` | 2 | mm | 0.8 .. 6 |  | Thickness of the roof plate. |
| `roof_clearance` | 0.3 | mm | 0 .. 5 |  | Gap between the roof plate's front strip and the cubby roof. |
| `roof_depression_start` | 15 | mm | 0 .. 80 |  | Front strip of the roof plate that stays at full height, from its front edge. |
| `roof_depression_depth` | 4 | mm | 0 .. 15 |  | How much lower the rest of the roof plate is (clears the roof bulge and the LED). 0 = flat. |
| `roof_depression_ramp` | 10 | mm | 1 .. 60 |  | Length of the smooth (cosine) transition. Longer = gentler overhang when printed standing; see max_overhang_deg. |

## perforation

Used by: roof plate (later also shelves)

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `perforate_roof` | true |  | true / false |  | Perforate the roof plate (its lowered, flat part). |
| `perforation_style` | teardrop |  | teardrop, diamond, none |  | Hole shape. Both print without support with the part standing on its rear edge: the upper edges rise at perforation_tip_angle. teardrop = round with a pointed top; diamond = straight bars of one width. |
| `perforation_size` | 10 | mm | 3 .. 40 |  | Width of one hole. |
| `perforation_open_fraction` | 0.5 |  | 0.05 .. 0.8 |  | Share of the perforated area that is open (material removed). The bar width follows from it. |
| `perforation_tip_angle` | 45 | deg | 20 .. 45 |  | Angle of the holes' upper edges from vertical when printed standing. Smaller = taller holes, safer printing. |
| `perforation_margin` | 5 | mm | 1 .. 30 |  | Solid border between the holes and the plate's edges. |

## drawer

Used by: drawer (planned)

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `drawer_type` | flip |  | flip, slide |  | flip = tip-out drawer on a hinge; slide = pull-out drawer on rails. |
| `drawer_width` | auto | mm | 20 .. 340 |  | Outer drawer width. null = derive from the shelf. |
| `drawer_depth` | auto | mm | 20 .. 280 |  | Outer drawer depth. null = derive from the shelf. |
| `drawer_height` | auto | mm | 8 .. 180 |  | Outer drawer height. null = derive from the free space above the shelf. |
| `hinge_position` | front_bottom |  | front_bottom, front_top |  | Pivot axis of the flip drawer. front_bottom = tip-out bin whose top tilts toward the driver. |
| `open_angle` | 35 | deg | 10 .. 90 |  | Flip drawer: rotation at the open end stop. |
| `detent_strength` | 0.3 | mm | 0 .. 1 |  | Snap/detent interference. Higher = firmer latch. |
| `pin_diameter` | 3 | mm | 1.75 .. 6 |  | Hinge pin diameter (printed pin, or 1.75 / 2.85 mm filament). No metal near the Qi coil. |

## tolerances

Used by: drawer, hinge (planned)

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `clearance_sliding` | 0.3 | mm | 0 .. 1.5 |  | Gap per side for sliding fits (drawer on rails). Tune me for your printer. |
| `clearance_hinge` | 0.4 | mm | 0 .. 1.5 |  | Radial gap for hinge pins and knuckles. Tune me. |
| `clearance_press_fit` | 0.15 | mm | -0.3 .. 1 |  | Gap for parts that are pressed together. Tune me. |

## coupon

Used by: fit coupon, profile gauge

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `coupon_plate_thickness` | 1.2 | mm | 0.4 .. 4 |  | Fit coupon: thickness of the flat outline plate (a few layers). |
| `coupon_flange_width` | 8 | mm | 2 .. 20 |  | Fit coupon: width of the plate ring, measured inward from the outline. The centre is open. |
| `coupon_rim_width` | 1.6 | mm | 0.8 .. 6 |  | Fit coupon: wall thickness of the rim that stands on the outline. |
| `coupon_rim_height` | auto | mm | 1 .. 40 |  | Fit coupon: rim height incl. the plate. null = frame_height, so the coupon has the same edge band as the real shelf. |
| `gauge_y` | 30 | mm | 5 .. 250 |  | Profile gauge: depth behind the lip of the cross-section it reproduces (it stands vertically in the cubby there). |
| `gauge_band` | 8 | mm | 3 .. 10 |  | Profile gauge: width of the frame along the outline. The middle is open. At most 10 mm: wider bands no longer follow the curved edge of the roof pocket. |
| `gauge_thickness` | 2 | mm | 0.8 .. 6 |  | Profile gauge: plate thickness. |
| `gauge_clearance` | 0.3 | mm | 0 .. 3 |  | Profile gauge: gap to the cubby on every side, on top of envelope_offset. |
| `gauge_corner` | 6 | mm | 0 .. 30 |  | Profile gauge: chamfer at its four corners, so a rounded transition in the car cannot hold it off the walls. 0 = sharp; otherwise at least 0.7 x (gauge_band + gauge_clearance), smaller values are raised to that. |

## checks

Used by: checks, export

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `min_bar_width` | 0.9 | mm | 0.2 .. 5 |  | Warn if the bars between perforations are thinner (default = 2 perimeters at a 0.4 mm nozzle). |
| `max_overhang_deg` | 45 | deg | 20 .. 60 |  | Steepest overhang (from vertical) for parts printed standing on their rear edge: the roof ramp and the rear corners are kept within it. |
| `min_wall` | 0.9 | mm | 0.2 .. 5 |  | Warn if walls or rims are thinner. |
| `min_deck_thickness` | 1.2 | mm | 0.2 .. 5 |  | Warn if the shelf deck is thinner. |
| `arc_segments_per_90` | 8 |  | 2 .. 64 |  | Arc tessellation for the pure-Python STL/3MF export (segments per 90 degrees). |
