# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Project footprints for the packages that KiCad does not ship; written to ../kicad/archet.pretty.

Every dimension is taken from the drawing cited next to it. Run with KiCad's Python (or any Python 3).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PRETTY = os.path.join(HERE, "..", "kicad", "archet.pretty")


def _f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def pad(num, x, y, w, h, shape="roundrect", paste=True, rr=0.25):
    layers = '"F.Cu" "F.Mask"' + (' "F.Paste"' if paste else "")
    extra = f" (roundrect_rratio {rr})" if shape == "roundrect" else ""
    return f'  (pad "{num}" smd {shape} (at {_f(x)} {_f(y)}) (size {_f(w)} {_f(h)}) (layers {layers}){extra})'


def rect(layer, x0, y0, x1, y1, width):
    return (f'  (fp_rect (start {_f(x0)} {_f(y0)}) (end {_f(x1)} {_f(y1)}) '
            f'(stroke (width {width}) (type solid)) (fill no) (layer "{layer}"))')


def line(layer, x0, y0, x1, y1, width=0.12):
    return f'  (fp_line (start {_f(x0)} {_f(y0)}) (end {_f(x1)} {_f(y1)}) (stroke (width {width}) (type solid)) (layer "{layer}"))'


def footprint(name, descr, body, items, model=None):
    bw, bh = body
    out = [f'(footprint "{name}"', '  (version 20240108)', '  (generator "archet-footprints")', '  (layer "F.Cu")',
           f'  (descr "{descr}")', '  (attr smd)',
           f'  (property "Reference" "REF**" (at 0 {_f(-bh / 2 - 1.2)} 0) (layer "F.SilkS") '
           '(effects (font (size 1 1) (thickness 0.15))))',
           f'  (property "Value" "{name}" (at 0 {_f(bh / 2 + 1.2)} 0) (layer "F.Fab") '
           '(effects (font (size 1 1) (thickness 0.15))))']
    out += items
    if model:
        out.append(f'  (model "{model}" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
    out.append(")")
    return "\n".join(out) + "\n"


def dsj14():
    """TI DSJ (R-PVSON-N14), TPS63020. Drawings in SLVS916I: 4208212-3/C (body 4 x 3 mm, pitch 0.5),
    4208549-3/G (exposed pad 2.85 x 1.58, 4 end tabs 0.20 wide, 0.46 apart), 4210895-2/E (lands 0.24 x 0.6,
    row centres 2.8 apart, thermal land 4.4 long). Drawn rotated 90°: pins 1-7 down the left column."""
    items = []
    for i in range(7):
        y = -1.5 + 0.5 * i
        items.append(pad(str(i + 1), -1.4, y, 0.6, 0.24))
        items.append(pad(str(14 - i), 1.4, y, 0.6, 0.24))
    # thermal land: pad 2.85 x 1.58 and the four tabs out to 4.4 overall (lands to the tab ends)
    items.append(pad("15", 0, 0, 1.58, 2.85, shape="rect", paste=False))
    for sx in (-0.33, 0.33):
        for sy in (-1, 1):
            items.append(pad("15", sx, sy * (1.425 + 2.2) / 2, 0.2, 2.2 - 1.425, shape="rect", paste=False))
    # paste: 2 x 2 windows, ~75 % of the central pad (TI stencil example: 81 %)
    for sx in (-0.39, 0.39):
        for sy in (-0.7, 0.7):
            items.append(f'  (pad "" smd rect (at {_f(sx)} {_f(sy)}) (size 0.66 1.25) (layers "F.Paste"))')
    items.append(rect("F.Fab", -1.5, -2.0, 1.5, 2.0, 0.1))
    items.append(line("F.Fab", -1.5, -1.5, -1.0, -2.0, 0.1))
    items.append(rect("F.CrtYd", -1.95, -2.45, 1.95, 2.45, 0.05))
    for sx in (-1, 1):                                    # silk on the short edges, clear of the tabs
        for sy in (-1, 1):
            items.append(line("F.SilkS", sx * 0.55, sy * 2.11, sx * 1.5, sy * 2.11))
    items.append('  (fp_circle (center -1.9 -1.9) (end -1.8 -1.9) (stroke (width 0.2) (type solid)) (fill yes) (layer "F.SilkS"))')
    name = "Texas_DSJ0014A_VSON-14_3x4mm_P0.5mm"
    return footprint(name, "TI DSJ VSON-14 3x4 mm pitch 0.5 mm, exposed pad 2.85x1.58 mm (SLVS916I package drawings)",
                     (3.0, 4.0), items, model=f"${{KIPRJMOD}}/archet.3dshapes/{name}.step")


def dsj14_3d():
    """Same drawings: body 3 x 4 (2.85-3.15 x 3.85-4.15), height 0.80-1.00, standoff 0-0.05, terminals
    0.18-0.30 wide x 0.30-0.50 long x 0.20 thick, exposed pad 2.85 x 1.58. Nominal values; 3D frame Y up,
    so pin 1 (footprint top left) sits at +Y."""
    body, metal, mark = (0.15, 0.15, 0.15), (0.80, 0.80, 0.82), (0.85, 0.85, 0.85)
    boxes = [((-1.5, -2.0, 0.02, 1.5, 2.0, 0.9), body),
             ((-0.79, -1.425, 0.0, 0.79, 1.425, 0.02), metal)]
    for i in range(7):
        y = 1.5 - 0.5 * i
        boxes.append(((-1.51, y - 0.12, 0.0, -1.1, y + 0.12, 0.2), metal))   # 0.01 proud: no coplanar faces
        boxes.append(((1.1, y - 0.12, 0.0, 1.51, y + 0.12, 0.2), metal))
    boxes.append(((-1.2, 1.4, 0.9, -0.9, 1.7, 0.91), mark))          # pin 1 dot (index area, top)
    return boxes


RRK_NAME = "Texas_RRK0016A_WQFN-16-1EP_3.5x4mm_P0.5mm_EP2.05x2.55mm"


def _rrk_pins():
    """Pin centres of the RRK0016A in the footprint frame (pin 1 top left): 2-7 down the left side, 8-9 on the
    bottom edge, 10-15 up the right side, 16 and 1 on the top edge. Drawing 4424663/B: 10 x 0.5 pitch on the long
    sides (2.5 overall), 1.5 between the two pins of each short side; land pattern 4424663/B: rows 3.3 and 3.8
    apart (pad centres), lands 0.6 x 0.24."""
    pins = {}
    for i in range(6):
        pins[str(2 + i)] = (-1.65, -1.25 + 0.5 * i, "h")
        pins[str(15 - i)] = (1.65, -1.25 + 0.5 * i, "h")
    pins.update({"1": (-0.75, -1.9, "v"), "16": (0.75, -1.9, "v"), "8": (-0.75, 1.9, "v"), "9": (0.75, 1.9, "v")})
    return pins


def rrk16():
    """TI RRK0016A WQFN-16, TPS27S100 (SLVSE42B package drawings 4424663/B): body 3.5 x 4.0, exposed pad
    2.05 x 2.55, lands 0.6 x 0.24. Paste on the pad: 2 x 2 windows 0.92 x 1.13 (stencil example, 80 %)."""
    items = []
    for num, (x, y, o) in _rrk_pins().items():
        items.append(pad(num, x, y, 0.6, 0.24) if o == "h" else pad(num, x, y, 0.24, 0.6))
    items.append(pad("17", 0, 0, 2.05, 2.55, shape="rect", paste=False))
    for sx in (-0.51, 0.51):
        for sy in (-0.635, 0.635):
            items.append(f'  (pad "" smd rect (at {_f(sx)} {_f(sy)}) (size 0.92 1.13) (layers "F.Paste"))')
    items.append(rect("F.Fab", -1.75, -2.0, 1.75, 2.0, 0.1))
    items.append(line("F.Fab", -1.75, -1.5, -1.25, -2.0, 0.1))
    items.append(rect("F.CrtYd", -2.2, -2.45, 2.2, 2.45, 0.05))
    for sx in (-1, 1):                                    # silk at the corners, clear of the lands
        for sy in (-1, 1):
            items.append(line("F.SilkS", sx * 1.86, sy * 1.65, sx * 1.86, sy * 2.11))
            items.append(line("F.SilkS", sx * 1.86, sy * 2.11, sx * 1.15, sy * 2.11))
    items.append('  (fp_circle (center -2.15 -2.2) (end -2.05 -2.2) (stroke (width 0.2) (type solid)) (fill yes) (layer "F.SilkS"))')
    return footprint(RRK_NAME, "TI RRK0016A WQFN-16 3.5x4 mm pitch 0.5 mm, exposed pad 2.05x2.55 mm "
                     "(SLVSE42B package drawings 4424663/B)", (3.5, 4.0), items,
                     model=f"${{KIPRJMOD}}/archet.3dshapes/{RRK_NAME}.step")


def rrk16_3d():
    """Same drawing: body 3.35-3.65 x 3.85-4.15, height 0.7-0.8, standoff 0-0.05, terminals 0.19-0.29 wide x
    0.3-0.5 long, exposed pad 2.05 x 2.55. Nominal values; 3D frame Y up (footprint y negated)."""
    body, metal, mark = (0.15, 0.15, 0.15), (0.80, 0.80, 0.82), (0.85, 0.85, 0.85)
    boxes = [((-1.75, -2.0, 0.02, 1.75, 2.0, 0.75), body),
             ((-1.025, -1.275, 0.0, 1.025, 1.275, 0.02), metal)]
    for x, y, o in _rrk_pins().values():
        y = -y
        if o == "h":
            x0, x1 = (-1.76, -1.36) if x < 0 else (1.36, 1.76)
            boxes.append(((x0, y - 0.12, 0.0, x1, y + 0.12, 0.2), metal))
        else:
            y0, y1 = (1.61, 2.01) if y > 0 else (-2.01, -1.61)
            boxes.append(((x - 0.12, y0, 0.0, x + 0.12, y1, 0.2), metal))
    boxes.append(((-1.45, 1.45, 0.75, -1.15, 1.75, 0.76), mark))      # pin 1 dot (top left)
    return boxes


MLT_PAD = 2.3 / 2 + 4.8 / 2          # pad centres: 2.3 mm pads, 4.8 mm apart (soldering pattern §5.2)


def mlt8530():
    """Jiangsu Huaneng MLT-8530 SMD magnetic buzzer, specification of 2017-05-22: body 8.5 x 8.5 mm with chamfered
    corners (§2), soldering pattern §5.2: four 2.3 x 2.3 mm pads, 4.8 mm gaps. + lead top left, - lead bottom left,
    two dummy pads on the right (MP, unconnected); sound port on the right edge."""
    b = 8.5 / 2
    items = [pad("1", -MLT_PAD, -MLT_PAD, 2.3, 2.3, rr=0.1), pad("2", -MLT_PAD, MLT_PAD, 2.3, 2.3, rr=0.1),
             pad("MP", MLT_PAD, -MLT_PAD, 2.3, 2.3, rr=0.1), pad("MP", MLT_PAD, MLT_PAD, 2.3, 2.3, rr=0.1)]
    items.append(rect("F.Fab", -b, -b, b, b, 0.1))
    items.append(rect("F.CrtYd", -MLT_PAD - 1.65, -MLT_PAD - 1.65, MLT_PAD + 1.65, MLT_PAD + 1.65, 0.05))
    for s in (-1, 1):                                    # silk between the pads, outside the body
        items.append(line("F.SilkS", -2.1, s * (b + 0.15), 2.1, s * (b + 0.15)))
        items.append(line("F.SilkS", s * (b + 0.15), -2.1, s * (b + 0.15), 2.1))
    items.append(line("F.Fab", b - 1.0, -0.6, b - 1.0, 0.6, 0.1))          # sound port arrow, as the drawing
    items.append(line("F.Fab", b - 1.0, -0.6, b, 0, 0.1))
    items.append(line("F.Fab", b - 1.0, 0.6, b, 0, 0.1))
    items.append('  (fp_text user "+" (at -6.1 -3.55 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))')
    name = "Buzzer_HNDZ_MLT-8530"
    return footprint(name, "Magnetic buzzer MLT-8530, 8.5 x 8.5 x 3 mm SMD (Jiangsu Huaneng specification, 2017)",
                     (8.5, 8.5), items, model=f"${{KIPRJMOD}}/archet.3dshapes/{name}.step")


def mlt8530_3d():
    """Same specification: body 8.5 x 8.5, 3.0 high (2.4 to the top of the housing step), terminals at the
    chamfered corners. Black LCP; boxes only, chamfers left square."""
    body, metal, mark = (0.08, 0.08, 0.08), (0.80, 0.80, 0.82), (0.85, 0.85, 0.85)
    b = 8.5 / 2
    boxes = [((-b, -b, 0.05, b, b, 3.0), body)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * MLT_PAD, sy * MLT_PAD
            boxes.append(((x - 0.6, y - 0.6, 0.0, x + 0.6, y + 0.6, 0.06), metal))
    boxes.append(((-0.5, -0.5, 3.0, 0.5, 0.5, 3.01), mark))             # top centre mark
    boxes.append(((-b + 0.3, MLT_PAD - 0.3, 3.0, -b + 1.1, MLT_PAD + 0.3, 3.01), mark))   # + lead side (top left)
    return boxes


def _from_kicad(lib, name, model=None):
    """KiCad library footprint whose 3D model the KiCad library lacks: copied as is, model pointed at the project
    (or at `model`, a KiCad model of the same package filed under another name)."""
    import re
    import sys
    sys.path.insert(0, os.path.join(HERE, "..", "lib"))
    from kicadgen.kicad import footprint_dir
    text = open(os.path.join(footprint_dir(), lib + ".pretty", name + ".kicad_mod"), encoding="utf-8").read()
    model = model or f"${{KIPRJMOD}}/archet.3dshapes/{name}.step"
    text, n = re.subn(r'\(model "[^"]*"', f'(model "{model}"', text)
    assert n == 1, name
    return text


def dsg8():
    """TI DSG0008A (TPS2595): KiCad points it at a missing file; the generic WSON-8 2 x 2, 0.5 pitch, EP 0.9 x 1.6
    model is the same package."""
    return _from_kicad("Package_SON", "Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
                       "${KICAD10_3DMODEL_DIR}/Package_SON.3dshapes/WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm.step")


def ts1187a():
    return _from_kicad("Button_Switch_SMD", "SW_Push_1P1T_XKB_TS-1187A")


def ts1187a_3d():
    """XKB TS-1187A-X-X-X drawing rev. A2 (2025-09-11), variant B-A-B (height code A: 1.50 mm): housing 5.2 x 5.2,
    cover 0.90 high, round button to 1.50, four gull-wing leads 0.5 wide, 3.7 apart, 6.4 tip to tip. Leads along
    X as the KiCad footprint (pads at x = +-3, y = +-1.875)."""
    body, metal, button = (0.12, 0.12, 0.12), (0.80, 0.80, 0.82), (0.85, 0.70, 0.25)
    boxes = [((-2.6, -2.6, 0.05, 2.6, 2.6, 0.9), body),
             ((-1.2, -1.2, 0.9, 1.2, 1.2, 1.5), button)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            y = sy * 1.85
            boxes.append(((min(sx * 2.4, sx * 3.2), y - 0.25, 0.0, max(sx * 2.4, sx * 3.2), y + 0.25, 0.15), metal))
    return boxes


def msk12c02():
    return _from_kicad("Button_Switch_SMD", "SW_SPDT_Shouhan_MSK12C02")


def msk12c02_3d():
    """Shou Han MSK12C02 specification drawing: body 6.7 x 2.8 x 1.4 (8.0 over the side tabs), knob 1.3 wide,
    1.45 out of the front face, 1.0 thick, 1.6 travel; terminals 1.0 out of the back face; two pegs 0.75 x 0.55
    under the board line. KiCad footprint frame: terminals at -y, knob at +y between x 0.15 and 1.45; 3D Y up."""
    body, metal, knob = (0.10, 0.10, 0.10), (0.80, 0.80, 0.82), (0.92, 0.92, 0.90)
    boxes = [((-3.35, -1.4, 0.05, 3.35, 1.4, 1.4), metal),          # steel cover over the LCP base
             ((0.15, -2.85, 0.3, 1.45, -1.4, 1.3), knob),
             ((-1.5 - 0.37, -0.37, -0.55, -1.5 + 0.37, 0.37, 0.05), body),
             ((1.5 - 0.37, -0.37, -0.55, 1.5 + 0.37, 0.37, 0.05), body)]
    for x in (-2.25, 0.75, 2.25):
        boxes.append(((x - 0.2, 1.4, 0.0, x + 0.2, 2.4, 0.15), metal))
    for sx in (-1, 1):
        for sy in (-1, 1):
            boxes.append(((min(sx * 3.35, sx * 4.0), sy * 1.1 - 0.25, 0.0,
                           max(sx * 3.35, sx * 4.0), sy * 1.1 + 0.25, 0.15), metal))
    return boxes


FOOTPRINTS = [(dsj14, dsj14_3d), (mlt8530, mlt8530_3d), (ts1187a, ts1187a_3d), (msk12c02, msk12c02_3d), (dsg8, None),
              (rrk16, rrk16_3d)]


def write():
    import sys
    sys.path.insert(0, HERE)
    import step3d
    shapes = os.path.join(os.path.dirname(PRETTY), "archet.3dshapes")
    os.makedirs(PRETTY, exist_ok=True)
    os.makedirs(shapes, exist_ok=True)
    for fn, model in FOOTPRINTS:
        text = fn()
        name = text.split('"')[1].split(":")[-1]
        with open(os.path.join(PRETTY, name + ".kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        if model:
            step3d.write(os.path.join(shapes, name + ".step"), name, model())
    return [fn.__name__ for fn, _ in FOOTPRINTS]


if __name__ == "__main__":
    print(write())
