# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Archet probe: printed circuit board, fixed parts.

Builds ../kicad/archet.kicad_pcb from a fresh netlist of the schematic (docs/architecture.md, Board):
- 4 layers, JLC04161H-3313 stack-up, 1.6 mm;
- outline 150 x 100 mm, rounded corners, M3 standoff holes on the corner radius centres (shared with the shield);
- host connectors on the left short edge, faces on the enclosure wall plane (USB-C overhang per the HRO drawing);
  the PoE module behind the magjack, inward; target connectors grouped at the middle of the right short edge,
  cable entries outward; the local bus on the bottom long edge at the host end (it takes a ribbon); the shield
  headers J10/J11 on both long edges at the target end, on a common 2.54 mm grid so that a perfboard shield fits;
- a GND plane on In1.Cu over the whole board.
These parts are locked. Every other part is parked below the board, grouped by schematic sheet, for the placer.

Run with KiCad's Python, cwd = gen. The board is overwritten: refuses to run on an existing board unless --force,
since placement and routing live in that file.
Checks: DRC with schematic parity (errors other than unrouted nets fail the run), and proof that the custom rule
"Barrier parts, own pads" is active (its removal must raise clearance errors on the magjack's own pads).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import circuit as c  # noqa: E402
from kicadgen import sexpr  # noqa: E402

KICAD = os.path.join(HERE, "..", "kicad")
PCB = os.path.join(KICAD, "archet.kicad_pcb")
SCH = os.path.join(KICAD, "archet.kicad_sch")
DRU = os.path.join(KICAD, "archet.kicad_dru")
PRO = os.path.join(KICAD, "archet.kicad_pro")
KICAD_BIN = os.path.dirname(sys.executable)
CLI = os.path.join(KICAD_BIN, "kicad-cli.exe")
SYS_FP = os.path.join(KICAD_BIN, "..", "share", "kicad", "footprints")
LOC_FP = os.path.join(KICAD, "archet.pretty")

# --------------------------------------------------------------------------------------------
# Outline. Board frame: origin at the top-left corner, x along the 150 mm side, y down; drawn at (X0, Y0) on the sheet.
W, H = 150.0, 100.0
X0, Y0 = 50.0, 50.0
CORNER_R = 4.0
HOLE = 4.0              # standoff centres, 4.0 from both edges (corner radius centres)
HOLE_FP = "MountingHole:MountingHole_3.2mm_M3"   # NPTH 3.2, courtyard Ø 6.95: M3 hex standoff 5.5 AF (6.35 AC)
CORNER_KEEP = 8.0       # edge parts start this far from a corner: standoff courtyard (7.48) + margin

# Stack-up JLC04161H-3313 (JLCPCB impedance page): outer 1 oz, inner 0.5 oz, prepreg 3313 0.0994 mm (er 4.1),
# core 1.265 mm. To confirm with the JLCPCB impedance calculator before ordering (netclasses.py, same values).
STACKUP = [("F.Cu", "copper", 0.035, None, None), ("dielectric 1", "prepreg", 0.0994, "3313", 4.1),
           ("In1.Cu", "copper", 0.0152, None, None), ("dielectric 2", "core", 1.265, "FR4", 4.6),
           ("In2.Cu", "copper", 0.0152, None, None), ("dielectric 3", "prepreg", 0.0994, "3313", 4.1),
           ("B.Cu", "copper", 0.035, None, None)]

# --------------------------------------------------------------------------------------------
# Edge parts, in order along the edge: (ref, rotation, inset, reference box). Rotation turns the mating face
# (footprint +y for the connectors) outward. Inset: distance from the edge inward to the reference box, "body"
# (F.Fab: the mating face) or "court" (courtyard: vertical headers, whose cable comes from above and whose pads
# reach past the body). A negative inset puts the face beyond the edge.
#
# Host edge (x = 0), from the top corner. All faces on one plane, the enclosure wall: the USB-C receptacle's
# drawing (HRO TYPE-C-31-M-12, C165948) puts the PCB edge 5.79 mm behind the front shell-oval centre line, i.e.
# at y = +2.66 in the footprint, whose shell front is at +3.70: the shell overhangs the edge by 1.04 mm. The
# ARJM11 drawing (p. 10) gives no edge or panel position: the magjack and the terminal block take the same plane.
HOST_FACE = -(3.70 - 2.66)
HOST = [("J3", 270, HOST_FACE, "body"), ("J1", 270, HOST_FACE, "body"),
        ("J2", 270, HOST_FACE, "body"), ("J5", 270, HOST_FACE, "body")]
# PoE module behind the magjack, inward, rotation 90: the primary row (pins 4-6, VIN+, TYP2-DET, VIN-) faces J3,
# the secondary row (12 V out, GND) faces the board. Its 3 mm primary/secondary keep-out (datasheet p. 7, 10.87 mm
# past both ends of the module) then runs along y, from y ~ 5 to y ~ 58, between J3 and the rest:
# it walls nothing in. Courtyard top level with J3's, POE_GAP (above the 2 mm barrier) from J3's courtyard.
POE = ("U6", 90)
POE_GAP = 2.5
# Target edge (x = W), from the top: field bus terminal, then the two vertical probe headers, grouped at the middle
# with TARGET_GAP between courtyards. Their long axes run along the edge, so the ribbon (it leaves the socket
# across the long axis) folds outward. Odd row on the outside, pin 1 toward the bottom: STDC14 J7 as CN1 of the
# STLINK-V3SET (UM2448 fig. 8, rotated 180 degrees: CN1 sits at the left edge of MB1441, odd row outside, pin 1
# up), so the STLINK cables lie the same way; the ESP-Prog header J8 likewise.
TARGET = [("J9", 90, 0.0, "body"), ("J7", 90, 0.5, "court"), ("J8", 180, 0.5, "court")]
TARGET_GAP = 4.0
# Local bus J12 on the bottom long edge from the host corner keep: it takes a ribbon to the Bornier.
J12 = ("J12", 90, 1.0, "body")
# Shield headers on both long edges at the target end, courtyards SHIELD_INSET from the edge and ending at the
# target corner keep. Same rotation and pin-1 column, rows a whole number of 2.54 mm steps apart: a perfboard
# shield takes both.
PITCH = 2.54
SHIELD = ("J10", "J11")
SHIELD_ROT = 90
SHIELD_INSET = 0.5

PARK_GAP = 2.5          # between parked parts: above the 2 mm PoE barrier
PARK_Y = H + 15.0       # first row of parked parts, below the board

mm = pcbnew.FromMM


def pt(x, y):
    return pcbnew.VECTOR2I(mm(X0 + x), mm(Y0 + y))


# --------------------------------------------------------------------------------------------
def netlist():
    """Components (ref -> dict) and pad nets ((ref, pin) -> net) from a fresh netlist export."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "archet.net")
        subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out, SCH],
                       check=True, capture_output=True)
        with open(out, encoding="utf-8") as f:
            root = sexpr.parse(f.read())
    comps = {}
    for comp in sexpr.find(sexpr.first(root, "components"), "comp"):
        ref = sexpr.first(comp, "ref")[1]
        fields = {f_[1][1]: (f_[2] if len(f_) > 2 else "")
                  for f_ in sexpr.find(sexpr.first(comp, "fields") or [], "field")}
        props = {sexpr.first(p, "name")[1]: (sexpr.first(p, "value") or [None, ""])[1]
                 for p in sexpr.find(comp, "property")}
        sheet = sexpr.first(comp, "sheetpath")
        comps[ref] = dict(value=sexpr.first(comp, "value")[1], fp=sexpr.first(comp, "footprint")[1],
                          fields=fields, props=props,
                          path=sexpr.first(sheet, "tstamps")[1] + sexpr.first(comp, "tstamps")[1])
    pads = {}
    for net in sexpr.find(sexpr.first(root, "nets"), "net"):
        name = sexpr.first(net, "name")[1]
        for node in sexpr.find(net, "node"):
            pads[(sexpr.first(node, "ref")[1], sexpr.first(node, "pin")[1])] = name
    return comps, pads


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    fp = pcbnew.FootprintLoad(LOC_FP if lib == "Archet" else os.path.join(SYS_FP, lib + ".pretty"), name)
    if fp is None:
        sys.exit(f"footprint {fpid} not found")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def bbox(fp, layer):
    """Bounding box (x0, y0, x1, y1) of a footprint's drawings on a layer, in the board frame, or None."""
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() == layer:
            b = g.GetBoundingBox()
            xs += [pcbnew.ToMM(b.GetLeft()) - X0, pcbnew.ToMM(b.GetRight()) - X0]
            ys += [pcbnew.ToMM(b.GetTop()) - Y0, pcbnew.ToMM(b.GetBottom()) - Y0]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def courtyard(fp):
    b = bbox(fp, pcbnew.F_CrtYd)
    if b is None:
        r = fp.GetBoundingBox(False)
        b = (pcbnew.ToMM(r.GetLeft()) - X0, pcbnew.ToMM(r.GetTop()) - Y0,
             pcbnew.ToMM(r.GetRight()) - X0, pcbnew.ToMM(r.GetBottom()) - Y0)
    return b


def body(fp):
    return bbox(fp, pcbnew.F_Fab) or courtyard(fp)


def shift(fp, dx, dy):
    fp.Move(pcbnew.VECTOR2I(mm(dx), mm(dy)))


def build_footprints(board, comps, pads):
    nets = {}
    for name in sorted(set(pads.values())):
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    dnp = {p["ref"] for p in c.c.parts if p.get("dnp")}
    fps = {}
    for ref in sorted(comps, key=lambda r: (re.sub(r"\d+", "", r), int(re.sub(r"\D", "", r) or 0))):
        cp = comps[ref]
        fp = load_fp(cp["fp"])
        fp.SetReference(ref)
        fp.SetValue(cp["value"])
        for k, v in cp["fields"].items():
            if k != "Footprint":
                fp.SetField(k, v)
        for f_ in fp.GetFields():
            if not (f_.IsReference() or f_.IsValue()):
                f_.SetVisible(False)
        fp.SetPath(pcbnew.KIID_PATH(cp["path"]))
        fp.SetSheetname(cp["props"].get("Sheetname", ""))
        fp.SetSheetfile(cp["props"].get("Sheetfile", ""))
        fp.SetDNP(ref in dnp)
        fp.SetExcludedFromBOM("exclude_from_bom" in cp["props"])
        for pad in fp.Pads():
            net = pads.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(nets[net])
        board.Add(fp)
        fps[ref] = fp
    missing = sorted({r for r, _ in pads} - set(fps))
    if missing:
        sys.exit(f"netlist nodes on unknown parts: {missing}")
    return fps


# --------------------------------------------------------------------------------------------
def outline(board):
    r = CORNER_R

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(*a)); s.SetEnd(pt(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)

    def arc(cx, cy, a0, a1):
        import math
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        p = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in (a0, (a0 + a1) / 2, a1)]
        s.SetArcGeometry(pt(*p[0]), pt(*p[1]), pt(*p[2]))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)

    seg((r, 0), (W - r, 0)); seg((W, r), (W, H - r)); seg((W - r, H), (r, H)); seg((0, H - r), (0, r))
    arc(W - r, r, 270, 360); arc(W - r, H - r, 0, 90); arc(r, H - r, 90, 180); arc(r, r, 180, 270)


def holes(board):
    for i, (x, y) in enumerate(((HOLE, HOLE), (W - HOLE, HOLE), (W - HOLE, H - HOLE), (HOLE, H - HOLE)), 1):
        fp = load_fp(HOLE_FP)
        fp.SetReference(f"H{i}")
        fp.SetValue("M3 standoff 11 mm")
        fp.Reference().SetVisible(False)
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        fp.SetPosition(pt(x, y))
        fp.SetLocked(True)
        board.Add(fp)


def edge_row(fps, parts, edge, lo, hi, gap=None):
    """Lays parts along an edge between lo and hi (along-edge coordinates). Without `gap`, equal gaps between
    courtyards and the range ends; with it, that gap between courtyards and the group centred in the range.
    edge: 'left' (x = 0), 'right' (x = W), 'top' (y = 0), 'bottom' (y = H)."""
    vertical = edge in ("left", "right")
    sizes = []
    for ref, rot, _, _ in parts:
        fp = fps[ref]
        fp.SetOrientationDegrees(rot)
        b = courtyard(fp)
        sizes.append(b[3] - b[1] if vertical else b[2] - b[0])
    if gap is None:
        gap = (hi - lo - sum(sizes)) / (len(parts) + 1)
        pos = lo + gap
    else:
        pos = (lo + hi - sum(sizes) - gap * (len(parts) - 1)) / 2
    if gap < (0.5 if len(parts) > 1 else -0.01) or pos < lo - 0.01:
        sys.exit(f"{edge} edge: {sum(sizes):.1f} mm of parts in {hi - lo:.1f} mm")
    for (ref, _, inset, ref_box), size in zip(parts, sizes):
        fp = fps[ref]
        cy = courtyard(fp)
        b = cy if ref_box == "court" else body(fp)
        if edge == "left":
            shift(fp, inset - b[0], pos - cy[1])
        elif edge == "right":
            shift(fp, W - inset - b[2], pos - cy[1])
        elif edge == "top":
            shift(fp, pos - cy[0], inset - b[1])
        else:
            shift(fp, pos - cy[0], H - inset - b[3])
        fp.SetLocked(True)
        pos += size + gap


def pin1(fp):
    p = next((p for p in fp.Pads() if p.GetNumber() in ("1", "A1")), None)
    if p is None:
        return float("nan"), float("nan")
    p = p.GetPosition()
    return pcbnew.ToMM(p.x) - X0, pcbnew.ToMM(p.y) - Y0


def fixed(fps):
    edge_row(fps, HOST, "left", CORNER_KEEP, H - CORNER_KEEP)
    edge_row(fps, TARGET, "right", CORNER_KEEP, H - CORNER_KEEP, gap=TARGET_GAP)
    # PoE module behind J3.
    ref, rot = POE
    fp = fps[ref]
    fp.SetOrientationDegrees(rot)
    j3, cy = courtyard(fps["J3"]), courtyard(fp)
    shift(fp, j3[2] + POE_GAP - cy[0], j3[1] - cy[1])
    fp.SetLocked(True)
    # J12 alone, from the host corner keep.
    fp = fps[J12[0]]
    fp.SetOrientationDegrees(J12[1])
    cy = courtyard(fp)
    edge_row(fps, [J12], "bottom", CORNER_KEEP, CORNER_KEEP + cy[2] - cy[0])
    # Shield headers: J10 against the top edge, J11 on the lowest grid row that keeps its courtyard on the board.
    top, bot = (fps[r] for r in SHIELD)
    for fp in (top, bot):
        fp.SetOrientationDegrees(SHIELD_ROT)
    cy = courtyard(top)
    edge_row(fps, [(SHIELD[0], SHIELD_ROT, SHIELD_INSET, "court")], "top", W - CORNER_KEEP - (cy[2] - cy[0]),
             W - CORNER_KEEP)
    x1, y1 = pin1(top)
    bx, by = pin1(bot)
    shift(bot, x1 - bx, y1 - by)
    cy = courtyard(bot)
    steps = int((H - SHIELD_INSET - cy[3]) / PITCH + 1e-6)
    shift(bot, 0, steps * PITCH)
    bot.SetLocked(True)


def park(board, fps):
    """Unlocked parts below the board, one group per schematic block, largest parts first in each group."""
    blocks = {}
    for p in c.c.parts:
        if not fps[p["ref"]].IsLocked():
            blocks.setdefault(p["block"], []).append(p["ref"])
    y = PARK_Y
    for name, refs in blocks.items():
        t = pcbnew.PCB_TEXT(board)
        t.SetText(name[:90]); t.SetLayer(pcbnew.Cmts_User)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5)))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        t.SetPosition(pt(0, y))
        board.Add(t)
        y += 2.5
        x, row_h = 0.0, 0.0
        refs.sort(key=lambda r: -(lambda b: (b[2] - b[0]) * (b[3] - b[1]))(courtyard(fps[r])))
        for ref in refs:
            fp = fps[ref]
            b = courtyard(fp)
            w, h = b[2] - b[0], b[3] - b[1]
            if x > 0 and x + w > W:
                x, y, row_h = 0.0, y + row_h + PARK_GAP, 0.0
            shift(fp, x - b[0], y - b[1])
            x += w + PARK_GAP
            row_h = max(row_h, h)
        y += row_h + 5.0


def gnd_plane(board):
    z = pcbnew.ZONE(board)
    z.SetLayer(pcbnew.In1_Cu)
    z.SetNet(board.FindNet("GND"))
    z.SetZoneName("GND plane")
    z.SetIsRuleArea(False)
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    poly = z.Outline()
    poly.NewOutline()
    for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
        poly.Append(mm(X0 + x), mm(Y0 + y))
    board.Add(z)


def stackup_text():
    lines = ['(stackup', '(layer "F.SilkS" (type "Top Silk Screen"))', '(layer "F.Paste" (type "Top Solder Paste"))',
             '(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))']
    for name, kind, t, mat, er in STACKUP:
        if kind == "copper":
            lines.append(f'(layer "{name}" (type "copper") (thickness {t}))')
        else:
            n = name.split()[1]
            lines.append(f'(layer "dielectric {n}" (type "{kind}") (thickness {t}) (material "{mat}") '
                         f'(epsilon_r {er}) (loss_tangent 0.02))')
    lines += ['(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))',
              '(layer "B.Paste" (type "Bottom Solder Paste"))', '(layer "B.SilkS" (type "Bottom Silk Screen"))',
              '(copper_finish "None")', '(dielectric_constraints no))']
    return " ".join(lines)


def set_stackup(path):
    """The Python API does not expose the stack-up: written into the file, then reloaded and saved by KiCad."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"\(stackup\b.*?\(dielectric_constraints \w+\)\s*\)", "", text, flags=re.S)
    text = text.replace("(setup", "(setup " + stackup_text(), 1)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    board = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)


# --------------------------------------------------------------------------------------------
def drc(pcb, parity=True):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "drc.json")
        args = [CLI, "pcb", "drc", "--severity-all", "--format", "json", "-o", out]
        if parity:
            args.append("--schematic-parity")
        r = subprocess.run(args + [pcb], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if "netlist" in (r.stdout + r.stderr).lower() and "fail" in (r.stdout + r.stderr).lower() \
                or "chec de la r" in r.stdout + r.stderr:
            sys.exit("DRC could not read the schematic: parity not checked")
        with open(out, encoding="utf-8") as f:
            return json.load(f)


def count(items):
    out = {}
    for v in items:
        out[v["type"]] = out.get(v["type"], 0) + 1
    return out


def prove_barrier():
    """Without the rule "Barrier parts, own pads", the magjack's own pads break the 2 mm PoE barrier."""
    with tempfile.TemporaryDirectory() as tmp:
        for f in (PCB, PRO, DRU):
            shutil.copy(f, tmp)
        dru = os.path.join(tmp, "archet.kicad_dru")
        with open(dru, encoding="utf-8") as f:
            text = f.read()
        cut = re.sub(r'\(rule "Barrier parts, own pads".*?"\)\)\n', "", text, flags=re.S)
        if cut == text:
            sys.exit("rule 'Barrier parts, own pads' not found in the .kicad_dru")
        pcb = os.path.join(tmp, "archet.kicad_pcb")

        def own(rep):
            hits = []
            pat = re.compile(r"Pad.*? \[.*?\] (?:of|de) (\S+)")  # "Pad 5 [net] of J3", "Pad métallisé 5 [net] de J3"
            for v in rep["violations"]:
                refs = {m.group(1) for i in v["items"] for m in [pat.match(i["description"])] if m}
                if v["type"] == "clearance" and len(refs) == 1 and refs & {"J3", "U6"}:
                    hits.append(v)
            return hits
        with_rule = own(drc(pcb, parity=False))
        with open(dru, "w", encoding="utf-8", newline="\n") as f:
            f.write(cut)
        without = own(drc(pcb, parity=False))
    return len(with_rule), len(without)


def main():
    if os.path.exists(PCB) and "--force" not in sys.argv:
        sys.exit(f"{PCB} exists: it holds placement and routing. Run with --force to overwrite it.")
    with open(PRO, "rb") as f:
        pro = f.read()     # KiCad adds its own keys to the project file when it creates a board: kept as generated
    comps, pads = netlist()
    board = pcbnew.NewBoard(PCB)
    board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetBoardThickness(mm(1.6))
    fps = build_footprints(board, comps, pads)
    outline(board)
    holes(board)
    fixed(fps)
    park(board, fps)
    gnd_plane(board)
    pcbnew.SaveBoard(PCB, board)
    set_stackup(PCB)
    with open(PRO, "wb") as f:
        f.write(pro)

    rep = drc(PCB)
    unrouted = len(rep.get("unconnected_items", []))
    viol = count(rep["violations"])
    parity = count(rep.get("schematic_parity", []))
    print(f"{len(fps)} footprints, {sum(1 for f in fps.values() if f.IsLocked())} locked; "
          f"{unrouted} unrouted connections (DRC lists at most 499)")
    print("violations:", viol or 0, " parity:", parity or 0)
    for ref in [p[0] for p in HOST + TARGET] + [POE[0], J12[0], *SHIELD]:
        b, cy = body(fps[ref]), courtyard(fps[ref])
        x1, y1 = pin1(fps[ref])
        print(f"  {ref:4s} body x {b[0]:6.2f}..{b[2]:6.2f}  y {b[1]:6.2f}..{b[3]:6.2f}   "
              f"courtyard x {cy[0]:6.2f}..{cy[2]:6.2f}  y {cy[1]:6.2f}..{cy[3]:6.2f}   pin 1 ({x1:.2f}, {y1:.2f})")
    w, wo = prove_barrier()
    print(f"barrier rule: {w} clearance errors on J3/U6 own pads with it, {wo} without it")
    if wo == 0:
        sys.exit("rule 'Barrier parts, own pads' not proven: no error without it")
    if parity or w:
        sys.exit(1)


if __name__ == "__main__":
    main()
