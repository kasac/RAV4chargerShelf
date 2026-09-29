# Parameter reference

Generated from `params/default.json` by `python tools/gen_param_docs.py`. Do not edit by hand.

**PH** = placeholder: a guess that must be measured or decided (the build report lists
every placeholder still in use). Range = slider range in Grasshopper; values outside
it are rejected. `auto` = derived from other parameters unless you set a value.

## cubby

Used by: coupon, shelf

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `W_top` | 200 | mm | 80 .. 350 | PH | Cubby inner width just below the roof, measured 10 mm behind the front lip. |
| `W_bottom` | 196 | mm | 80 .. 350 | PH | Cubby inner width just above the Qi pad surface, measured 10 mm behind the front lip. |
| `W_rear_delta` | 0 | mm | -40 .. 40 | PH | Width 10 mm in front of the rear wall minus width 10 mm behind the lip, both at shelf height. Negative = cubby narrows toward the rear. |
| `D_cubby` | 130 | mm | 40 .. 300 | PH | Depth from the front lip to the rear wall, at shelf height. |
| `H_cubby` | 75 | mm | 20 .. 200 | PH | Height from the Qi pad surface to the roof (lowest point of the roof above the shelf area). |
| `R_rear_corner` | 5 | mm | 0 .. 30 | PH | Inner radius where the side walls meet the rear wall, seen from above (0 = sharp corner). |
| `W_lip` | 200 | mm | 60 .. 350 | PH | Narrowest width of the opening at the front lip, at shelf height. Only used to check that the shelf can be inserted flat. |

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

Used by: coupon, shelf

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `shelf_height` | 52 | mm | 5 .. 190 | PH | Height of the shelf's TOP surface above the Qi pad. Decide after measuring H_ports_top and H_cubby. |
| `front_recess` | 8 | mm | 0 .. 60 |  | How far the shelf's front edge sits behind the front lip (hides the shelf, looks closer to stock). |
| `rear_gap` | 1 | mm | 0 .. 20 |  | Gap between the shelf's rear edge and the rear wall. |
| `side_gap` | 0.5 | mm | -1 .. 5 |  | Gap per side between shelf edge and side wall. Tune with the fit coupon. Negative = interference (press fit). Use the pad thickness if you add felt/foam. |
| `corner_radius_front` | 4 | mm | 0 .. 30 |  | Corner radius of the shelf's front corners (cosmetic). |
| `port_notch_width` | 76 | mm | 0 .. 250 |  | Width of the cut-out in the shelf's rear edge over the port cluster. 0 disables the notch. |
| `port_notch_depth` | 50 | mm | 0 .. 200 |  | How far the notch reaches forward into the shelf, from its rear edge. (The brief's port_notch_height: the notch is a through-cut, so it has a depth, not a height.) |
| `port_notch_offset_x` | 0 | mm | -100 .. 100 |  | Lateral shift of the notch centre relative to X_ports. |
| `port_notch_radius` | 3 | mm | 0 .. 20 |  | Corner radius of the notch. |
| `port_clearance` | 3 | mm | 0 .. 20 |  | Minimum air gap the checks demand around plugs and cables. |
| `phone_clearance_min` | 20 | mm | 5 .. 100 |  | Minimum free height under the lowest part of the shelf, for the phone on the Qi pad plus room to slide it in and out. |

## strength

Used by: shelf (coupon uses frame_height)

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `wall_thickness` | 2 | mm | 0.8 .. 6 |  | Thickness of the shelf skirt, ribs and drawer walls. |
| `deck_thickness` | 2.4 | mm | 1 .. 8 |  | Thickness of the perforated deck. |
| `frame_width` | 8 | mm | 3 .. 30 |  | Width of the solid rim around the grid, seen from above. |
| `frame_height` | 8 | mm | 2 .. 30 |  | Height of the solid edge band, from the deck top down (skirt). This band is what touches the side walls. |
| `rib_count` | 2 |  | 0 .. 10 |  | Number of stiffening ribs under the deck, running side to side. |
| `rib_height` | 5 | mm | 0 .. 30 |  | Rib height below the deck. |

## perforation

Used by: shelf, drawer (planned)

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `grid_style` | hex |  | hex, square, diamond, round, slot, triangle |  | Perforation pattern. |
| `cell_size` | 8 | mm | 3 .. 40 |  | Opening size of one grid cell (across flats for hex). |
| `bar_width` | 1.8 | mm | 0.8 .. 10 |  | Width of the web between openings. At least 2 perimeters of your nozzle. |
| `grid_angle` | 0 | deg | -90 .. 90 |  | Rotation of the grid pattern. |
| `grid_enabled_shelf` | true |  | true / false |  | Perforate the shelf deck. |
| `grid_enabled_drawer_floor` | true |  | true / false |  | Perforate the drawer floor. |

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

Used by: fit coupon

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `coupon_plate_thickness` | 1.2 | mm | 0.4 .. 4 |  | Fit coupon: thickness of the flat outline plate (a few layers). |
| `coupon_flange_width` | 8 | mm | 2 .. 40 |  | Fit coupon: width of the plate ring, measured inward from the outline. The centre is open. |
| `coupon_rim_width` | 1.6 | mm | 0.8 .. 6 |  | Fit coupon: wall thickness of the rim that stands on the outline. |
| `coupon_rim_height` | auto | mm | 1 .. 40 |  | Fit coupon: rim height incl. the plate. null = frame_height, so the coupon has the same edge band as the real shelf. |

## checks

Used by: checks, export

| Name | Default | Unit | Range / choices | PH | Meaning |
|---|---|---|---|---|---|
| `min_bar_width` | 0.9 | mm | 0.2 .. 5 |  | Warn if grid bars are thinner (default = 2 perimeters at a 0.4 mm nozzle). |
| `min_wall` | 0.9 | mm | 0.2 .. 5 |  | Warn if walls or rims are thinner. |
| `min_deck_thickness` | 1.2 | mm | 0.2 .. 5 |  | Warn if the shelf deck is thinner. |
| `arc_segments_per_90` | 8 |  | 2 .. 64 |  | Arc tessellation for the pure-Python STL/3MF export (segments per 90 degrees). |
