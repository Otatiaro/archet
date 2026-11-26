# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Archet probe schematic: draws circuit.py sheet by sheet, then checks ERC and netlist.

Usage: python schematic.py   (KiCad 10 required; writes ../kicad/archet.kicad_sch and its sheets)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "lib")]
from circuit import c  # noqa: E402
from kicadgen.schematic import Project  # noqa: E402
from kicadgen.check import check  # noqa: E402

KICAD = os.path.join(HERE, "..", "kicad")

# ERC kinds tolerated while some sheets are still missing: global labels with a single end.
PENDING_ERC = ("global_label_dangling", "isolated_pin_label")
WAIVED_ERC = ()


def vpart(s, ref, x, y_top, label_dx=2.54):
    """Two-pin vertical part (R, C) hanging from (x, y_top): pin 1 there, pin 2 7.62 mm below."""
    y = y_top + 3.81
    s.place(ref, x, y, ref_at=(x + label_dx, y - 1.27), val_at=(x + label_dx, y + 1.27))


def sense(s, rt, rb, cf, net, out, x, yr):
    """100k / 10k divider hanging from the horizontal net at (x, yr), output label to the right."""
    s.w(net, (x, yr), (x, yr + 2.54))
    vpart(s, rt, x, yr + 2.54)
    vpart(s, rb, x, yr + 15.24)
    ym = yr + 12.7
    s.w(out, s.P(rt, 2), s.P(rb, 1))
    s.rail("GND", *s.P(rb, 2))
    s.w(out, (x, ym), (x + 10.16, ym), (x + 17.78, ym))
    vpart(s, cf, x + 10.16, ym)
    s.rail("GND", *s.P(cf, 2))
    s.glabel(out, x + 17.78, ym, 0, "output")


def ideal_diode(s, n, src, q, u, cap, cin, fx, yr, xbus, x0):
    """N-MOS on the row line (source left, drain right, gate down), LM74700 below it."""
    s.place(q, fx, yr + 2.54, rot=270, mirror="x", ref_at=(fx + 2.54, yr - 6.35), val_at=(fx + 2.54, yr - 3.81))
    ly = yr + 25.4
    s.place(u, fx, ly, ref_at=(fx + 10.16, ly + 3.81), val_at=(fx + 10.16, ly + 6.35))
    s.w(f"GATE{n}", s.P(q, 4), s.P(u, 5))
    xa, ya = s.P(u, 6)
    s.w(src, (xa, ya), (xa, yr))
    xk, yk = s.P(u, 4)
    s.w("VSYS", (xk, yk), (xk, yr))
    s.w("VSYS", s.P(q, 5), (xbus, yr))
    s.rail("GND", *s.P(u, 2))
    # charge pump capacitor VCAP-ANODE, EN to ANODE (always on)
    xv, yv = s.P(u, 1)
    xc = fx - 25.4
    s.place(cap, xc, yv - 3.81, ref_at=(xc + 2.54, yv - 5.08), val_at=(xc + 2.54, yv - 2.54))
    s.w(f"VCAP{n}", (xv, yv), s.P(cap, 2))
    s.w(src, s.P(cap, 1), (xc, yr))
    xe, ye = s.P(u, 3)
    s.w(src, (xe, ye), (xc - 7.62, ye), (xc - 7.62, yr))
    # input decoupling, ahead of the controller
    xi = fx - 48.26
    s.w(src, (xi, yr), (xi, yr + 2.54))
    vpart(s, cin, xi, yr + 2.54)
    s.rail("GND", *s.P(cin, 2))
    s.w(src, (x0, yr), s.P(q, 1))


def oring(prj):
    s = prj.sheet("Sources", "sources.kicad_sch", "Source OR-ing into VSYS: VIN_EXT, USB-C VBUS, PoE 12 V")
    s.text("SOURCE OR-ING", 20.32, 17.78, 2.54, True)
    s.text("Highest voltage wins, no control logic: VIN_EXT 24 V > PD 15-20 V > PoE 12 V > USB 5 V.\n"
           "Each source enters through an LM74700 ideal diode: no back-feeding of a host, a PoE module or a supply.\n"
           "The firmware identifies the active source from the four ADC inputs and derives the power budget.",
           20.32, 25.4)
    fx, xbus = 203.2, 254.0
    rows = (63.5, 134.62, 205.74)

    # --- row 1: VIN_EXT, terminal block or shield connector, fuse, TVS ---
    yr = rows[0]
    s.place("J1", 30.48, yr, mirror="y", ref_at=(22.86, yr - 3.81), val_at=(22.86, yr + 6.35))
    jx, jy = s.P("J1", 2)
    s.w("GND", (jx, jy), (jx + 2.54, jy))
    s.rail("GND", jx + 2.54, jy, drop=5.08)
    s.w("GND", (jx + 2.54, jy + 5.08), (jx + 7.62, jy + 5.08))
    s.power("PWR_FLAG", jx + 7.62, jy + 5.08, 0)
    s.place("F1", 63.5, yr, rot=90, ref_at=(60.96, yr - 5.08), val_at=(60.96, yr - 2.54))
    s.w("VIN_EXT", s.P("J1", 1), s.P("F1", 1))
    s.w("VIN_EXT", (48.26, yr), (48.26, yr - 7.62))
    s.glabel("VIN_EXT", 48.26, yr - 7.62, 90, "input")
    xt = 76.2
    s.w("VIN_EXT_P", s.P("F1", 2), (xt + 30.48, yr))
    s.w("VIN_EXT_P", (xt, yr), (xt, yr + 2.54))
    # a rotated symbol flips the justification: these texts end at x
    s.place("D1", xt, yr + 6.35, rot=90, ref_at=(xt - 2.54, yr + 5.08), val_at=(xt - 2.54, yr + 7.62))
    s.rail("GND", *s.P("D1", 1))
    s.w("VIN_EXT_P", (88.9, yr), (88.9, yr - 7.62))
    s.glabel("VIN_EXT_P", 88.9, yr - 7.62, 90, "output")
    s.text("From the shield (J_SHIELD_SVC 33-34)\nor the terminal block J1", 20.32, yr + 12.7)
    s.power("PWR_FLAG", 96.52, yr, 0)
    sense(s, "R1", "R2", "C9", "VIN_EXT_P", "VIN_EXT_SENSE", 106.68, yr)
    ideal_diode(s, 1, "VIN_EXT_P", "Q1", "U1", "C1", "C2", fx, yr, xbus, 106.68)

    # --- rows 2 and 3: USB-C VBUS after the PD sink switch, PoE module output ---
    for yr, src, refs, d in ((rows[1], "VBUS_USB", ("R3", "R4", "C10", "Q2", "U2", "C3", "C4"), 2),
                             (rows[2], "POE_12V", ("R5", "R6", "C11", "Q3", "U3", "C5", "C6"), 3)):
        s.glabel(src, 88.9, yr, 180, "input")
        s.w(src, (88.9, yr), (106.68, yr))
        s.power("PWR_FLAG", 96.52, yr, 0)
        rt, rb, cf, q, u, cap, cin = refs
        sense(s, rt, rb, cf, src, f"{src}_SENSE", 106.68, yr)
        ideal_diode(s, d, src, q, u, cap, cin, fx, yr, xbus, 106.68)
    s.text("From the USB-C sheet\n(STUSB4500 sink switch)", 66.04, rows[1] - 10.16)
    s.text("From the PoE module\n(DP5700, isolated 12 V)", 66.04, rows[2] - 10.16)

    # --- VSYS bus ---
    s.w("VSYS", (xbus, rows[0]), (xbus, rows[2]))
    y = rows[1] - 20.32
    s.w("VSYS", (xbus, y), (xbus + 66.04, y))
    s.glabel("VSYS", xbus + 66.04, y, 0, "output")
    s.power("PWR_FLAG", xbus + 7.62, y, 0)
    for i, ref in enumerate(("C7", "C8")):
        x = xbus + 17.78 + 15.24 * i
        s.w("VSYS", (x, y), (x, y + 2.54))
        vpart(s, ref, x, y + 2.54)
        s.rail("GND", *s.P(ref, 2))
    sense(s, "R7", "R8", "C12", "VSYS", "VSYS_SENSE", xbus + 50.8, y)
    s.text("VSYS: 4.5-24 V, to the +5V buck (LMR33630) and the VIN_BUS boost (LM5155).", xbus + 2.54, y - 12.7)
    s.text("ADC dividers 100k / 10k: 24 V -> 2.18 V; the TVS clamp (38.9 V) gives 3.54 V\n"
           "through 100 kΩ, 35 µA into the pin protection. Inputs: PF12, PF13, PF14, PA6.",
           xbus + 2.54, rows[2] + 25.4)


def main():
    os.makedirs(KICAD, exist_ok=True)
    pro = os.path.join(KICAD, "archet.kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w", encoding="utf-8", newline="\n") as f:
            f.write('{"meta": {"filename": "archet.kicad_pro", "version": 3}}\n')
    prj = Project("archet", c, "Archet debug probe", "2026-11-26")
    oring(prj)
    sch, ok = prj.write(KICAD)
    print(f"{len(c.parts)} parts -> {sch}")
    if not ok:
        print("drawing errors: fix them before checking")
        return 1
    return check(c, sch, PENDING_ERC, WAIVED_ERC)


if __name__ == "__main__":
    sys.exit(main())
