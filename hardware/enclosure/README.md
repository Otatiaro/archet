# Enclosure

First iteration of the printed enclosure, in OpenSCAD. Design decisions: [architecture.md, Enclosure](../../docs/architecture.md).

![Assembly](out/assembly.png)

## Parts

| Part | Prints | Hardware |
|---|---|---|
| `bottom` | floor down | 6 × ISO 7380 M3 button head, from below |
| `host` (host-end lid) | top face down | 4 × Ruthex M3 × 5.7 inserts (H1, H4, H5, H6); 6 × Bivar PLP2-625 light pipes |
| `target` (target-end lid) | top face down | 2 × Ruthex M3 × 5.7 inserts (H2, H3), set from the top: enclosure screw from below, shield screw from above |
| `plunger` | standing, × 2 | |

No part has an overhang: every face printed over the bed rests on what is under it. Keep it that way.

Joint (H5, H6), a sandwich: board, target lid, host lid. A tongue of the target lid's top plate runs under the host lid to each joint screw, on a post standing on the board; the host lid's insert column lands on the tongue, and its end wall rests on the tongues.

Screws: M3 × 10 at H1 and H4, M3 × 18 at H5 and H6, M3 × 10 at H2 and H3, all from below. The shield sits on two 2 mm M3 spacers (nylon washers from a catalogue, or printed) on the H2 and H3 columns, and takes M3 × 6 from above; the two screws share the insert, about 2 mm each.

**Shield constraint:** nothing may stand more than 2 mm below the shield's board (spacer height): trim through-hole leads to 1.8 mm, no bottom-side part.

Assembly: board into the bottom; target lid on, its posts on the board at H5 and H6; host lid on, over the tongues; six screws from below.

## Files

- `geom.py` (KiCad's Python): reads `../kicad/archet.kicad_pcb`, writes `board.scad` (hole positions, part boxes and heights, footprint origins) and `board.stl`, `parts.stl` (board and the parts the enclosure deals with, for the assembly view). Run it after any board change.
- `enclosure.scad`: the model. `-D 'PART="host"'` selects a part (`bottom`, `host`, `target`, `plunger`, `plungers`, `assembly`, `check`).
- `build.py`: writes `out/*.3mf`, `out/*.png` and `out/kicad/*.wrz`. `--check` intersects every shell with each part body from `board.scad` and fails on any overlap (about 10 minutes with OpenSCAD 2021).
- `out/kicad/*.wrz`: the shells and plungers as VRML models, in KiCad's model frame. `hardware/gen/board.py` hangs them on a board-only footprint (ENC1) at the board origin, semi-transparent: the enclosure shows in KiCad's 3D viewer. Rebuild them after a change to the model.

Frame: the board frame of `hardware/gen/board.py` (x from the host edge, y down) drawn as (x, −y), z = 0 on the board's underside.

Plungers, light pipes and buzzer holes sit on the footprint origins exported by `geom.py`, not on the fab outline centres: the TS-1187A fab outline is 1 mm off its actuator, and an off-axis plunger would tilt in its guide.

## Open points

- The check covers the parts listed in `geom.py`; the rest of the board is not placed yet. After placement, check every part against the lid ceilings (7.2 mm under the target lid, also over the tongues at H5 and H6) and keep the post footprints at H5 and H6 free.
- Test prints: light pipe press fit (2.92 mm hole), plunger guide play (3.8 mm plunger in a 4.1 mm hole, 9 mm guide), USB-C and RJ45 openings, insert holes.
- H6 insert: 0.6 mm of wall between the insert hole and the J12 well. Watch it on the first print.
