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


def tht(num, x, y, size, drill, shape="circle"):
    return (f'  (pad "{num}" thru_hole {shape} (at {_f(x)} {_f(y)}) (size {_f(size)} {_f(size)}) (drill {_f(drill)}) '
            '(layers "*.Cu" "*.Mask"))')


def npth(x, y, drill):
    return (f'  (pad "" np_thru_hole circle (at {_f(x)} {_f(y)}) (size {_f(drill)} {_f(drill)}) (drill {_f(drill)}) '
            '(layers "*.Cu" "*.Mask"))')


def footprint(name, descr, body, items, model=None, attr="smd"):
    bw, bh = body
    out = [f'(footprint "{name}"', '  (version 20240108)', '  (generator "archet-footprints")', '  (layer "F.Cu")',
           f'  (descr "{descr}")', f'  (attr {attr})',
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


def hsop8():
    """TI DDA (LMR33630ADDA): KiCad points it at a missing HTSOP-8 file; the HSOP-8 3.9 x 4.9, 1.27 pitch model is
    the same package (body, leads; the exposed pad is hidden under it)."""
    return _from_kicad("Package_SO", "Texas_HSOP-8-1EP_3.9x4.9mm_P1.27mm_ThermalVias",
                       "${KICAD10_3DMODEL_DIR}/Package_SO.3dshapes/HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.1mm.step")


def sg48():
    """Lattice SG48 (iCE40UP5K), FPGA-DS-02053-8.8 section 31 p. 36: 7.0 BSC, e 0.50, b 0.15-0.30,
    L 0.35-0.45, exposed pad D2 = E2 = 5.20 / 5.35 / 5.50. The KiCad EP5.3 land (leads 0.8 x 0.25) fits;
    the EP5.6 used before was above the 5.50 maximum. No EP5.3 model in KiCad: the EP5.15 one has the same
    body and leads."""
    return _from_kicad("Package_DFN_QFN", "QFN-48-1EP_7x7mm_P0.5mm_EP5.3x5.3mm",
                       "${KICAD10_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/QFN-48-1EP_7x7mm_P0.5mm_EP5.15x5.15mm.step")


def vqfn24():
    """LAN8742A-CZ, Microchip DS00001989 package drawing: 4.00 BSC, e 0.50, exposed pad D2 = E2 = 2.40 / 2.50 /
    2.60, recommended centre pad 2.60, contacts 0.30 x 0.85: the KiCad EP2.5 footprint is that land. Its model
    file is missing; the HVQFN-24 4 x 4 model has the same body and leads."""
    return _from_kicad("Package_DFN_QFN", "VQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias",
                       "${KICAD10_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/HVQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm.step")


def usbc():
    return _from_kicad("Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12")


def usbc_3d():
    """HRO TYPE-C-31-M-12 drawing (2020-12-08): body 8.94 x 7.35, shell 8.34 x 2.56 standing 0.70 above the board
    (3.26 overall), 4 shell legs 1.01 below. KiCad frame: body x +-4.47, y +-3.65, mating face at +y, SMD tails at
    y = -4.045, legs on the SH holes. 3D Y up: footprint y negated."""
    body, metal = (0.15, 0.15, 0.15), (0.80, 0.80, 0.82)
    boxes = [((-4.17, -3.65, 0.70, 4.17, 3.65, 3.26), metal),
             ((-4.0, 1.0, 0.0, 4.0, 3.65, 0.70), body)]               # rear housing under the shell, tail side
    for x in (-3.25, -2.45, -1.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 1.75, 2.45, 3.25):
        boxes.append(((x - 0.12, 3.65, 0.0, x + 0.12, 4.6, 0.15), metal))
    for x in (-4.32, 4.32):
        for y in (-3.13, 1.05):
            boxes.append(((x - 0.3, -y - 0.5, -1.01, x + 0.3, -y + 0.5, 0.70), metal))
    return boxes


def microb():
    return _from_kicad("Connector_USB", "USB_Micro-B_Molex-105133-0001")


def microb_3d():
    """Molex SD-105133-001 rev. G, 105133-0001: vertical, 6.7 above the board, housing 6.90 wide (8.0 over the
    shell tabs), 3.0 deep; plug opening 6.90 x 1.85 at the top; 3 shield pegs A = 2.30 below the board, 0.80 wide,
    0.30 shell; 5 tails 0.25 wide, pitch 0.65. KiCad frame: body y -1.435 to 1.565, tails at y = -0.825, pegs at
    (+-2.8, -1.075) and (0, 1.075). 3D Y up: footprint y negated."""
    body, metal = (0.15, 0.15, 0.15), (0.80, 0.80, 0.82)
    boxes = [((-3.45, -1.565, 0.0, 3.45, 1.435, 6.7), metal),
             ((-3.15, -0.8, 6.7, 3.15, 0.8, 6.71), body),             # plug opening, drawn dark
             ((-4.0, -0.6, 0.0, 4.0, 0.6, 0.8), metal)]               # side tabs
    for i in range(5):
        x = -1.3 + 0.65 * i
        boxes.append(((x - 0.125, 0.825 - 0.75, 0.0, x + 0.125, 0.825 + 0.75, 0.15), metal))
    for x, y in ((-2.8, -1.075), (2.8, -1.075), (0.0, 1.075)):
        boxes.append(((x - 0.4, -y - 0.15, -2.30, x + 0.4, -y + 0.15, 0.0), metal))
    return boxes


def wson12():
    return _from_kicad("Package_SON", "WSON-12-1EP_3x2mm_P0.5mm_EP1x2.65")


def wson12_3d():
    """TI DSS0012B (LM5155, SNVSB55 package outline): body 2.0 x 3.0 (1.9-2.1 x 2.9-3.1), 0.8 max high, 12 leads
    0.25 wide (0.2-0.3) x 0.3 long (0.25-0.35), pitch 0.5, exposed pad 1.0 x 2.65. KiCad frame: leads along y,
    pin 1 at (-0.95, -1.25); 3D Y up, so pin 1 sits at +Y."""
    body, metal = (0.15, 0.15, 0.15), (0.80, 0.80, 0.82)
    boxes = [((-1.0, -1.5, 0.02, 1.0, 1.5, 0.75), body),
             ((-0.5, -1.325, 0.0, 0.5, 1.325, 0.02), metal),
             ((-0.85, 1.2, 0.75, -0.65, 1.4, 0.76), (0.85, 0.85, 0.85))]   # pin 1 mark
    for i in range(6):
        y = 1.25 - 0.5 * i
        for sx in (-1, 1):
            boxes.append(((min(sx * 1.0, sx * 0.7), y - 0.125, 0.0, max(sx * 1.0, sx * 0.7), y + 0.125, 0.2), metal))
    return boxes


ARJ_CX = -5.715                     # centre between pin 1 (x = 0) and pin 10 (x = -11.43)
ARJ_POST = 6.35                     # post line, 6.35 in front of the pin 1 row


def _arj_pins():
    """Abracon ARJM11 datasheet (rev. 01-21-20), Pin Layout 7 (p. 14, 10 pins with LED), top view, origin on pin 1:
    10 x 0.90 holes, pitch 1.27 alternating between two rows 2.54 apart (odd pins in the front row); posts 3.25 on
    the pin 1 and pin 10 lines, 8.89 in front of the rear row; shield 1.70 holes 15.75 apart, 3.05 behind the posts;
    LED 1.02 holes 13.45 apart, 2.54 and 4.57 in front of the posts (11-12 on the pin 1 side)."""
    pins = {str(k): (-(k - 1) * 1.27, 0.0 if k % 2 else -2.54) for k in range(1, 11)}
    for num, sx, dy in (("11", 1, 2.54), ("12", 1, 4.57), ("13", -1, 2.54), ("14", -1, 4.57)):
        pins[num] = (ARJ_CX + sx * 13.45 / 2, ARJ_POST + dy)
    return pins


def arjm11():
    """Abracon ARJM11D7-104-AB-EW2 (drawing D, tab up, wave solder; Pin Layout 7 with LED). Hole sizes from p. 14;
    body from drawing D p. 10: 15.70 wide, 21.50 deep, 13.45 high, rear face 1.76 behind the rear pin row (front
    face 10.85 in front of the posts, read off the side view). Plug opening at +y."""
    items = []
    for num, (x, y) in _arj_pins().items():
        if int(num) <= 10:
            items.append(tht(num, x, y, 1.5, 0.9, "rect" if num == "1" else "circle"))
        else:
            items.append(tht(num, x, y, 1.7, 1.02))
    for x in (0.0, -11.43):
        items.append(npth(x, ARJ_POST, 3.25))
    for sx in (-1, 1):
        items.append(tht("SH", ARJ_CX + sx * 15.75 / 2, ARJ_POST - 3.05, 2.7, 1.7))
    x0, x1, y0, y1 = ARJ_CX - 7.85, ARJ_CX + 7.85, -4.30, 17.20
    items.append(rect("F.Fab", x0, y0, x1, y1, 0.1))
    items.append(rect("F.SilkS", x0 - 0.11, y0 - 0.11, x1 + 0.11, y1 + 0.11, 0.12))
    items.append(rect("F.CrtYd", x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5, 0.05))
    items.append('  (fp_circle (center 1.2 -0.9) (end 1.4 -0.9) (stroke (width 0.2) (type solid)) (fill yes) (layer "F.SilkS"))')
    name = "ARJM11_Layout7_10P_LED"
    return footprint(name, "Abracon ARJM11 RJ45 magjack, 100Base-T PoE+, tab up, Pin Layout 7 with LEDs "
                     "(ARJM11 datasheet rev. 01-21-20, p. 10 and 14)", (15.7, 21.5), items,
                     model=f"${{KIPRJMOD}}/archet.3dshapes/{name}.step", attr="through_hole")


def arjm11_3d():
    """Same drawings: shielded body 15.70 x 21.50 x 13.45, opening and LEDs on the front face (green left, yellow
    right seen from the front), tails 3.20 below the board. 3D Y up: footprint y negated."""
    metal, dark, green, yellow = (0.80, 0.80, 0.82), (0.10, 0.10, 0.10), (0.2, 0.8, 0.2), (0.9, 0.8, 0.1)
    x0, x1 = ARJ_CX - 7.85, ARJ_CX + 7.85
    boxes = [((x0, -17.20, 0.0, x1, 4.30, 13.45), metal),
             ((ARJ_CX - 5.85, -17.21, 1.5, ARJ_CX + 5.85, -17.0, 9.5), dark),          # plug opening
             ((ARJ_CX - 7.0, -17.21, 11.0, ARJ_CX - 4.5, -17.0, 12.5), green),
             ((ARJ_CX + 4.5, -17.21, 11.0, ARJ_CX + 7.0, -17.0, 12.5), yellow)]
    for num, (x, y) in _arj_pins().items():
        boxes.append(((x - 0.25, -y - 0.25, -3.2, x + 0.25, -y + 0.25, 0.0), metal))
    for x in (0.0, -11.43):
        boxes.append(((x - 1.5, -ARJ_POST - 1.5, -2.5, x + 1.5, -ARJ_POST + 1.5, 0.0), dark))
    for sx in (-1, 1):
        x = ARJ_CX + sx * 15.75 / 2
        boxes.append(((x - 0.6, -(ARJ_POST - 3.05) - 0.15, -3.2, x + 0.6, -(ARJ_POST - 3.05) + 0.15, 0.0), metal))
    return boxes


DP_X = (-14.505, -12.165, 12.165, 14.505)   # C = 26.67 and D = 2.34: pads 29.01 apart overall, centred
DP_Y = 16.10 / 2                            # E = 16.10 between the pad rows


def _dp_pins():
    """SDaPo DP5700 datasheet, figure 2 (bottom view: 4 top left, 5-6 top right, 3-2 bottom left, 1 bottom right)
    mirrored to the top view of the land pattern (p. 7, pin 1 circled at bottom left)."""
    return {"1": (DP_X[0], DP_Y), "2": (DP_X[2], DP_Y), "3": (DP_X[3], DP_Y),
            "4": (DP_X[3], -DP_Y), "5": (DP_X[1], -DP_Y), "6": (DP_X[0], -DP_Y)}


def dp5700():
    """SDaPo DP5700 PoE PD module, land pattern p. 7: pads A x B = 3.71 x 1.83 (long side across the rows), C 26.67,
    D 2.34, E 16.10. Body 31.75 x 20.32 (A, B nominal), assumed centred on the pad pattern as the drawing shows.
    The drawing also asks for copper keep-out zones under the module (a 3.00, b 5.64, d 7.62, e 8.64, f 2.11,
    g 12.24, h 4.32, i > 10.87): to be drawn as rule areas on the board."""
    items = [pad(num, x, y, 1.83, 3.71, rr=0.1) for num, (x, y) in _dp_pins().items()]
    bx, by = 31.75 / 2, 20.32 / 2
    items.append(rect("F.Fab", -bx, -by, bx, by, 0.1))
    items.append(rect("F.SilkS", -bx - 0.11, -by - 0.11, bx + 0.11, by + 0.11, 0.12))
    items.append(rect("F.CrtYd", -bx - 0.5, -by - 0.5, bx + 0.5, by + 0.5, 0.05))
    items.append(line("F.Fab", -bx, by - 1.5, -bx + 1.5, by, 0.1))
    items.append('  (fp_circle (center -16.6 10.9) (end -16.4 10.9) (stroke (width 0.2) (type solid)) (fill yes) (layer "F.SilkS"))')
    return footprint("DP5700", "SDaPo DP5700 PoE PD module, 6 SMD pads (DP5700 datasheet, package p. 7)",
                     (31.75, 20.32), items, model="${KIPRJMOD}/archet.3dshapes/DP5700.step")


def dp5700_3d():
    """Same page: module board 31.75 x 20.32, 1.6 thick (D), 13.0 overall (L), shielded transformer between the
    keep-outs H 8.00 and G 8.64 (J 33.15 long, K 21.72 wide, F 2.34 margins), parts beside it up to I 2.10."""
    board, metal, dark = (0.05, 0.25, 0.12), (0.80, 0.80, 0.82), (0.12, 0.12, 0.12)
    bx, by = 31.75 / 2, 20.32 / 2
    ty = 21.72 / 2 - 2.34
    boxes = [((-bx, -by, 1.2, bx, by, 2.8), board),
             ((-33.15 / 2 + 8.00, -ty, 2.8, 33.15 / 2 - 8.64, ty, 13.0), metal),
             ((-bx + 0.5, -ty, 2.8, -33.15 / 2 + 7.5, ty, 4.9), dark),
             ((33.15 / 2 - 8.14, -ty, 2.8, bx - 0.5, ty, 4.9), dark)]
    for x, y in _dp_pins().values():
        boxes.append(((x - 0.8, -y - 1.5, 0.0, x + 0.8, -y + 1.5, 1.2), metal))
    return boxes


def _ftsh_pins():
    """Samtec FTSH-1XX-XX-XXX-DV-XXX footprint rev. H, fig. 1: lands 0.74 x 2.79, pitch 1.27, 6.86 over both rows
    (centres 4.07 apart); odd pins in the bottom row, pin 1 at the left."""
    return {str(2 * i + 1 + r): (-3.81 + 1.27 * i, 2.035 if r == 0 else -2.035) for i in range(7) for r in (0, 1)}


def ftsh107():
    """Samtec FTSH-107-01-L-DV-K: 2 x 7, 1.27 mm SMT terminal strip with keying shroud (FTSH-1XX-XX-XXX-DV-XXX-XXX
    rev. FQ, fig. 1 and 2): body 8.89 x 3.43, shroud 5.08 wide, 3.20 above the body."""
    items = [pad(num, x, y, 0.74, 2.79, rr=0.15) for num, (x, y) in _ftsh_pins().items()]
    items.append(rect("F.Fab", -4.445, -1.715, 4.445, 1.715, 0.1))
    items.append(rect("F.CrtYd", -4.95, -3.93, 4.95, 3.93, 0.05))
    for sx in (-1, 1):
        items.append(line("F.SilkS", sx * 4.56, -1.2, sx * 4.56, 1.2))
    items.append('  (fp_circle (center -4.6 3.0) (end -4.4 3.0) (stroke (width 0.2) (type solid)) (fill yes) (layer "F.SilkS"))')
    name = "FTSH-107-01-L-DV-K"
    return footprint(name, "Samtec FTSH-107-01-L-DV-K 2x7 1.27 mm SMT header, keying shroud "
                     "(FTSH-1XX-XX-XXX-DV footprint rev. H)", (8.89, 3.43), items,
                     model=f"${{KIPRJMOD}}/archet.3dshapes/{name}.step")


def ftsh107_3d():
    """Same drawings: body 0.099 [2.51] high, lead style -01 posts 3.05 above it (0.016 square), keying shroud 5.08
    long, 3.20 above the body, centred; SMT tails out to the land ends. 3D Y up."""
    body, metal = (0.10, 0.10, 0.10), (0.85, 0.75, 0.30)
    boxes = [((-4.445, -1.715, 0.1, 4.445, 1.715, 2.51), body),
             ((-2.54, -1.715, 2.51, 2.54, 1.715, 5.71), body)]
    for x, y in _ftsh_pins().values():
        y = -y
        boxes.append(((x - 0.2, y - 0.2, 2.51, x + 0.2, y + 0.2, 5.56), metal))
        y0, y1 = (0.635 + 0.3, 3.3) if y > 0 else (-3.3, -0.935)
        boxes.append(((x - 0.2, y0, 0.0, x + 0.2, y1, 0.2), metal))
    return boxes


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
              (rrk16, rrk16_3d), (hsop8, None), (sg48, None), (vqfn24, None), (usbc, usbc_3d), (microb, microb_3d),
              (wson12, wson12_3d), (arjm11, arjm11_3d), (dp5700, dp5700_3d), (ftsh107, ftsh107_3d)]


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
