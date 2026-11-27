# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Archet probe schematic: draws circuit.py sheet by sheet, then checks ERC and netlist.

Usage: python schematic.py   (KiCad 10 required; writes ../kicad/archet.kicad_sch and its sheets)
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "lib")]
from circuit import c  # noqa: E402
import symbols  # noqa: E402
import footprints  # noqa: E402
from kicadgen.schematic import Project  # noqa: E402
from kicadgen.check import check  # noqa: E402

KICAD = os.path.join(HERE, "..", "kicad")

# ERC kinds tolerated while some sheets are still missing: none since all sheets are drawn.
PENDING_ERC = ()
# VCAP1 and VCAP2 are both LDO outputs ("power output"): ST ties them, each with its 2.2 µF (NUCLEO-H723ZG, AN5419).
# USB_B_Micro declares its GND pin "power output" (KiCad library): it meets the GND PWR_FLAG.
WAIVED_ERC = (("pin_to_pin", "VCAP"), ("pin_to_pin", "Symbol J5 Pin 5"))


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
    s.w("VSYS_OR", (xk, yk), (xk, yr))
    s.w("VSYS_OR", s.P(q, 5), (xbus, yr))
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

    # --- VSYS_OR bus, shunt, VSYS ---
    s.w("VSYS_OR", (xbus, rows[0]), (xbus, rows[2]))
    y = rows[1] - 20.32
    xs, xB = xbus + 48.26, xbus + 58.42
    s.w("VSYS_OR", (xbus, y), (xs - 3.81, y))
    s.power("PWR_FLAG", xbus + 7.62, y, 0)
    for i, ref in enumerate(("C7", "C8")):
        x = xbus + 15.24 + 15.24 * i
        s.w("VSYS_OR", (x, y), (x, y + 2.54))
        vpart(s, ref, x, y + 2.54)
        s.rail("GND", *s.P(ref, 2))
    s.place("R126", xs, y, rot=90, ref_at=(xs - 2.54, y - 3.81), val_at=(xs + 2.54, y - 3.81))
    s.w("VSYS", s.P("R126", 2), (xbus + 93.98, y))
    s.glabel("VSYS", xbus + 93.98, y, 0, "output")
    s.power("PWR_FLAG", xbus + 63.5, y, 0)
    sense(s, "R7", "R8", "C12", "VSYS", "VSYS_SENSE", xbus + 71.12, y)
    ina_monitor(s, "U43", "C126", "VSYS_OR", "VSYS", xB + 20.32, y + 63.5, xB, y,
                "Address 0x41 (A1 = GND, A0 = VS)")
    s.text("VSYS: 4.5-24 V, to the +5V buck (LMR33630) and the VIN_BUS boost (LM5155).\n"
           "U43 reads everything drawn from the active source.", xbus + 2.54, y - 15.24)
    s.text("ADC dividers 100k / 10k: 24 V -> 2.18 V; the TVS clamp (38.9 V) gives 3.54 V\n"
           "through 100 kΩ, 35 µA into the pin protection. Inputs: PF12, PF13, PF14, PA6.",
           xbus + 2.54, rows[2] + 25.4)


def usbc(prj):
    s = prj.sheet("USB-C", "usbc.kicad_sch", "USB-C sink: STUSB4500 PD controller, VBUS switch, ESD")
    s.text("USB-C SINK", 20.32, 17.78, 2.54, True)
    s.text("The STUSB4500 negotiates the highest PDO stored in its NVM, then closes Q4 (VBUS_EN_SNK low).\n"
           "Dead battery mode: with the probe unpowered, CCxDB presents Rd so that the source turns VBUS on.",
           20.32, 25.4)
    yp = 50.8                     # VBUS power row
    ux, uy = 139.7, 106.68        # STUSB4500
    jx, jy = 40.64, uy + 12.7     # connector
    fx = 203.2                    # sink switch

    # --- connector: shield and ground at the bottom ---
    s.place("J2", jx, jy, ref_at=(jx - 7.62, jy - 26.67), val_at=(jx - 7.62, jy - 24.13))
    s.rail("GND", *s.P("J2", "A1"))
    s.rail("GND", *s.P("J2", "SH"))

    # --- VBUS row: connector -> TVS, bulk, VDD, sense resistor -> P-MOS -> VBUS_USB ---
    xv = jx + 17.78
    vx, vy = s.P("J2", "A4")
    s.w("VBUS_CONN", (vx, vy), (xv, vy), (xv, yp))
    s.place("Q4", fx, yp + 2.54, rot=270, mirror="x", ref_at=(fx + 2.54, yp - 6.35), val_at=(fx + 2.54, yp - 3.81))
    s.w("VBUS_CONN", (xv, yp), s.P("Q4", 1))
    s.power("PWR_FLAG", xv + 7.62, yp, 0)
    s.w("VBUS_CONN", (xv, yp), (xv, yp - 7.62))
    s.glabel("VBUS_CONN", xv, yp - 7.62, 90, "output")
    xt = 76.2
    s.w("VBUS_CONN", (xt, yp), (xt, yp + 2.54))
    s.place("D2", xt, yp + 6.35, rot=90, ref_at=(xt - 2.54, yp + 5.08), val_at=(xt - 2.54, yp + 7.62))
    s.rail("GND", *s.P("D2", 1))
    xc = 116.84
    s.w("VBUS_CONN", (xc, yp), (xc, yp + 2.54))
    vpart(s, "C13", xc, yp + 2.54)
    s.rail("GND", *s.P("C13", 2))
    s.place("U4", ux, uy, ref_at=(ux + 5.08, uy + 25.4), val_at=(ux + 5.08, uy + 27.94))
    s.w("VBUS_CONN", s.P("U4", 24), (s.P("U4", 24)[0], yp))
    xq, yq = s.P("Q4", 5)
    s.w("VBUS_USB", (xq, yq), (fx + 30.48, yp))
    s.glabel("VBUS_USB", fx + 30.48, yp, 0, "output")
    s.text("To the Sources sheet\n(ideal diode 2)", fx + 15.24, yp - 10.16)

    # gate: 100k to the source, 10k to VBUS_EN_SNK
    gx, gy = s.P("Q4", 4)
    yg = gy + 5.08
    xr = fx - 12.7
    s.w("VBUS_CONN", (xr, yp), (xr, yp + 2.54))
    vpart(s, "R10", xr, yp + 2.54, label_dx=-7.62)
    s.w("VBUS_GATE", s.P("R10", 2), (xr, yg), (gx, yg), (gx, gy))
    s.w("VBUS_GATE", (gx, yg), (gx, yg + 2.54))
    vpart(s, "R11", gx, yg + 2.54)
    ex, ey = s.P("U4", 16)
    s.w("VBUS_EN_N", s.P("R11", 2), (gx, ey), (ex, ey))

    # --- STUSB4500 supplies, top ---
    x22, y22 = s.P("U4", 22)
    s.w("+3V3", (x22, y22), (x22, uy - 35.56), (ux + 43.18, uy - 35.56))
    s.rail("+3V3", ux + 43.18, uy - 35.56)
    vpart(s, "C16", ux + 43.18, uy - 35.56)
    s.rail("GND", *s.P("C16", 2))
    for pin, net, ref, yh, xcap in ((21, "PD_1V2", "C14", uy - 30.48, ux + 30.48),
                                    (23, "PD_2V7", "C15", uy - 25.4, ux + 17.78)):
        px, py = s.P("U4", pin)
        s.w(net, (px, py), (px, yh), (xcap, yh))
        vpart(s, ref, xcap, yh)
        s.rail("GND", *s.P(ref, 2))
    s.rail("GND", *s.P("U4", 10))

    # --- CC lines: CC1 rises, CC2 runs low; the ESD pair sits between them ---
    px = ux - 15.24
    c1x, c1y = s.P("J2", "A5")
    xcc = jx + 22.86
    ycc1 = uy - 10.16
    s.w("CC1", (c1x, c1y), (xcc, c1y), (xcc, ycc1), s.P("U4", 1))
    s.w("CC1", (px - 5.08, ycc1), (px - 5.08, uy - 12.7), s.P("U4", 2))
    c2x, c2y = s.P("J2", "B5")
    xb = px - 33.02
    s.w("CC2", (c2x, c2y), (xb, c2y), (xb, uy - 5.08), s.P("U4", 4))
    s.w("CC2", (xb, uy - 2.54), s.P("U4", 5))
    s.label("CC2", c2x + 5.08, c2y, 0)
    xe = 76.2
    s.place("D3", xe, (ycc1 + c2y) / 2, rot=90, ref_at=(xe - 2.54, uy - 3.81), val_at=(xe - 2.54, uy - 1.27))
    ax, ay = s.P("D3", 3)
    s.w("GND", (ax, ay), (ax + 2.54, ay))
    s.rail("GND", ax + 2.54, ay)

    # --- STUSB4500 left side: RESET and address to ground, discharge resistor, I2C ---
    rx, ry = s.P("U4", 6)
    s.w("GND", (rx, ry), (px - 12.7, ry))
    s.rail("GND", px - 12.7, ry)
    xr9 = px - 13.97
    s.place("R9", xr9, uy + 2.54, rot=90, ref_at=(xr9 - 2.54, uy), val_at=(xr9 + 2.54, uy))
    s.w("PD_DISCH", s.P("R9", 2), s.P("U4", 18))
    s.label("PD_DISCH", s.P("R9", 2)[0] + 1.27, s.P("R9", 2)[1], 0)
    s.glabel("VBUS_CONN", *s.P("R9", 1), 180, "input")
    for pin, net, shape in ((7, "SYS_SCL", "input"), (8, "SYS_SDA", "bidirectional"), (19, "PD_ALERT", "output")):
        lx, ly = s.P("U4", pin)
        s.w(net, (lx, ly), (lx - 2.54, ly))
        s.glabel(net, lx - 2.54, ly, 180, shape)
    a0x, a0y = s.P("U4", 12)
    a1x, a1y = s.P("U4", 13)
    s.w("GND", (a0x, a0y), (px - 5.08, a0y), (px - 5.08, a1y))
    s.w("GND", (a1x, a1y), (px - 5.08, a1y))
    s.rail("GND", px - 5.08, a1y)

    # --- D+ / D-: down under the controller, through the ESD array, to the ULPI sheet ---
    yl = uy + 33.02
    xu = 101.6
    s.place("U5", xu, yl, ref_at=(xu + 2.54, yl - 7.62), val_at=(xu + 2.54, yl + 10.16))
    m1, m2 = s.P("J2", "A7"), s.P("J2", "B7")
    s.w("USB_C_DM", m1, (xv, m1[1]), (xv, m2[1]))
    s.w("USB_C_DM", m2, (xv, m2[1]), (jx + 25.4, m2[1]), (jx + 25.4, yl), s.P("U5", 1))
    p1, p2 = s.P("J2", "A6"), s.P("J2", "B6")
    s.w("USB_C_DP", p1, (xv, p1[1]), (xv, yl + 2.54), s.P("U5", 3))
    s.w("USB_C_DP", p2, (xv, p2[1]))
    s.rail("+3V3", *s.P("U5", 5))
    s.rail("GND", *s.P("U5", 2))
    for pin, net in ((6, "USB_DM"), (4, "USB_DP")):
        ox, oy = s.P("U5", pin)
        s.w(net, (ox, oy), (ux + 30.48, oy))
        s.glabel(net, ux + 30.48, oy, 0, "bidirectional")
    s.text("To the USB3320C\n(ULPI sheet)", ux + 30.48, yl - 7.62)
    s.text("SYS_SCL / SYS_SDA: I2C5, pull-ups R63/R64 on the\ntarget supply sheet. PD_ALERT: PG0, MCU pull-up.",
           20.32, uy + 50.8)


def poe(prj):
    s = prj.sheet("PoE", "poe.kicad_sch", "PoE+ input: RJ45 magnetics, polarity bridges, isolated 12 V PD module")
    s.text("POE+ INPUT", 20.32, 17.78, 2.54, True)
    s.text("Modes A and B: one bridge on the data pair centre taps, one on the spare pairs.\n"
           "The DP5700 signs as a class 4 PD and delivers an isolated 12 V; the primary side (POE_VP / POE_VN)\n"
           "never touches GND. TYP2-DET crosses the barrier through an opto: POE_AT_N low = 25.5 W budget.",
           20.32, 25.4)
    yp, yn, yb = 53.34, 93.98, 66.04          # POE_VP bus, POE_VN bus, bridge AC row
    s.place("J3", 38.1, 101.6, ref_at=(30.48, 72.39), val_at=(30.48, 74.93))
    s.rail("GND", *s.P("J3", "SH"))

    # --- bridges: AC left / right, + up to POE_VP, - down to POE_VN; the lower J3 pin feeds the right AC pin ---
    for ref, x, top, low in (("D4", 76.2, 9, 10), ("D5", 114.3, 7, 8)):
        s.place(ref, x, yb, rot=90, ref_at=(x - 5.08, yb - 8.89), val_at=(x - 5.08, yb - 6.35))
        tx, ty = s.P("J3", top)
        lx, ly = s.P(ref, 2)
        net2 = s.prj.parts[ref]["pins"]["2"]
        s.w(net2, (tx, ty), (lx - 5.08, ty), (lx - 5.08, ly), (lx, ly))
        bx, by = s.P("J3", low)
        rx, ry = s.P(ref, 1)
        net1 = s.prj.parts[ref]["pins"]["1"]
        s.w(net1, (bx, by), (rx + 5.08, by), (rx + 5.08, ry), (rx, ry))
        # named at the jack: the automatic label would land on a crossing and short the nets
        s.label(net2, tx + 2.54, ty, 0)
        s.label(net1, bx + 2.54, by, 0)
        px, py = s.P(ref, 3)
        s.w("POE_VP", (px, py), (px, yp))
        nx, ny = s.P(ref, 4)
        s.w("POE_VN", (nx, ny), (nx, yn))

    # --- TVS across the primary, then the module ---
    ux, uy = 177.8, 68.58
    s.place("U6", ux, uy, ref_at=(ux - 5.08, uy - 12.7), val_at=(ux - 5.08, uy - 10.16))
    xv = 152.4
    vx, vy = s.P("U6", 4)
    s.w("POE_VP", (76.2, yp), (xv, yp), (xv, vy), (vx, vy))
    s.label("POE_VP", 81.28, yp, 0)
    nx, ny = s.P("U6", 6)
    s.w("POE_VN", (76.2, yn), (xv, yn), (xv, ny), (nx, ny))
    s.label("POE_VN", 81.28, yn, 0)
    xt = 139.7
    s.place("D6", xt, 74.93, rot=270, ref_at=(xt + 2.54, 73.66), val_at=(xt + 2.54, 76.2))
    s.w("POE_VP", (xt, yp), s.P("D6", 1))
    s.w("POE_VN", s.P("D6", 2), (xt, yn))
    tx, ty = s.P("U6", 5)
    s.w("POE_TYP2", (tx, ty), (tx - 2.54, ty))
    s.label("POE_TYP2", tx - 2.54, ty, 180)

    # --- isolated 12 V output: bulk, ceramic, minimum load ---
    ox, oy = s.P("U6", 1)
    xo = ox + 50.8
    s.w("POE_12V", (ox, oy), (xo, oy))
    s.glabel("POE_12V", xo, oy, 0, "output")
    s.text("To the Sources sheet\n(ideal diode 3)", xo - 15.24, oy - 10.16)
    for i, ref in enumerate(("C17", "C18", "R14")):
        x = ox + 15.24 * (i + 1)
        s.w("POE_12V", (x, oy), (x, oy + 2.54))
        vpart(s, ref, x, oy + 2.54)
        s.rail("GND", *s.P(ref, 2))
    s.rail("GND", *s.P("U6", 2))

    # --- Type 2 detection across the barrier ---
    ox7, oy7 = 177.8, 116.84
    s.place("U7", ox7, oy7, ref_at=(ox7 - 2.54, oy7 - 7.62), val_at=(ox7, oy7 + 12.7))
    ax, ay = s.P("U7", 1)
    s.place("R12", ax - 20.32, ay, rot=90, ref_at=(ax - 20.32, ay - 6.35), val_at=(ax - 20.32, ay - 3.81))
    s.w("POE_OPTO_A", s.P("R12", 2), (ax, ay))
    s.label("POE_OPTO_A", s.P("R12", 2)[0] + 1.27, ay, 0)
    r1x, r1y = s.P("R12", 1)
    s.w("POE_VP", (r1x, r1y), (r1x - 7.62, r1y))
    s.label("POE_VP", r1x - 7.62, r1y, 180, tag="opto")
    kx, ky = s.P("U7", 2)
    s.w("POE_TYP2", (kx, ky), (kx - 20.32, ky))
    s.label("POE_TYP2", kx - 20.32, ky, 180, tag="opto")
    cx, cy = s.P("U7", 4)
    xa = cx + 30.48
    s.w("POE_AT_N", (cx, cy), (xa, cy))
    s.glabel("POE_AT_N", xa, cy, 0, "output")
    vpart(s, "R13", cx + 12.7, cy - 7.62)
    s.rail("+3V3", *s.P("R13", 1))
    s.rail("GND", *s.P("U7", 3))
    s.text("To PC15 (MCU)", xa - 10.16, cy - 5.08)

    # --- Ethernet side of the magnetics, to the PHY sheet ---
    for pin, net in ((1, "ETH_TXP"), (2, "ETH_TXN"), (5, "ETH_CT"), (3, "ETH_RXP"), (4, "ETH_RXN"),
                     (13, "ETH_LEDL_A"), (14, "GND"), (11, "ETH_LEDR_A"), (12, "GND")):
        ex, ey = s.P("J3", pin)
        if net == "GND":    # LED cathodes, joined right of the anode labels
            s.w(net, (ex, ey), (ex + 20.32, ey))
            continue
        s.w(net, (ex, ey), (ex + 5.08, ey))
        s.glabel(net, ex + 5.08, ey, 0, "passive")
    kx = s.P("J3", 14)[0] + 20.32
    s.w("GND", (kx, s.P("J3", 14)[1]), (kx, s.P("J3", 12)[1]))
    s.rail("GND", kx, s.P("J3", 12)[1])
    s.text("To the LAN8742A (PHY sheet).\nLEDs: left green, right yellow;\nanodes driven by the PHY.", 20.32, 139.7)


def buck5(prj):
    s = prj.sheet("+5V", "buck5.kicad_sch", "+5V rail: LMR33630 synchronous buck from VSYS")
    s.text("+5V BUCK", 20.32, 17.78, 2.54, True)
    s.text("VSYS 4.5-24 V -> +5V 3 A (15 W). On a 5 V USB port the converter runs in dropout (~98 % duty):\n"
           "+5V ~ 4.8 V, enough for the TLV62569 bucks; the firmware keeps 5V_OUT off.\n"
           "Layout: C21 and C19/C20 against VIN and the PGND pad, short SW node, FB divider away from L1.",
           20.32, 25.4)
    ux, uy = 127.0, 66.04
    yi, yo = uy - 5.08, uy - 2.54             # VSYS input row (VIN pin), +5V output row (SW pin level)
    s.place("U8", ux, uy, ref_at=(ux - 5.08, uy - 13.97), val_at=(ux - 5.08, uy - 11.43))
    x0 = 40.64
    s.glabel("VSYS", x0, yi, 180, "input")
    s.text("From the Sources sheet", x0 - 12.7, yi - 7.62)
    s.w("VSYS", (x0, yi), s.P("U8", 2))
    for i, ref in enumerate(("C19", "C20", "C21")):
        x = ux - 76.2 + 15.24 * i
        s.w("VSYS", (x, yi), (x, yi + 2.54))
        vpart(s, ref, x, yi + 2.54)
        s.rail("GND", *s.P(ref, 2))
    ex, ey = s.P("U8", 3)
    s.w("VSYS", (ex, ey), (ex - 5.08, ey), (ex - 5.08, yi))
    vx, vy = s.P("U8", 6)
    xc = ux - 30.48
    s.w("BUCK5_VCC", (vx, vy), (xc, vy), (xc, vy + 2.54))
    vpart(s, "C22", xc, vy + 2.54)
    s.rail("GND", *s.P("C22", 2))
    s.rail("GND", *s.P("U8", 1))

    # --- bootstrap and switch node ---
    bx, by = s.P("U8", 7)
    xb = ux + 38.1
    s.w("BUCK5_BOOT", (bx, by), (bx + 5.08, by), (bx + 5.08, uy - 17.78), (xb, uy - 17.78))
    vpart(s, "C23", xb, uy - 17.78)
    sx, sy = s.P("U8", 8)
    s.w("BUCK5_SW", (sx, sy), (xb, sy), s.P("C23", 2))
    s.place("L1", xb + 10.16, yo, rot=90, ref_at=(xb + 10.16, yo - 5.08), val_at=(xb + 10.16, yo - 2.54))
    s.w("BUCK5_SW", (xb, yo), s.P("L1", 1))

    # --- output: ceramics, feedback divider, rail ---
    lx, ly = s.P("L1", 2)
    xe = ux + 121.92
    s.w("+5V", (lx, ly), (xe, yo))
    s.rail("+5V", xe, yo)
    s.power("PWR_FLAG", xe - 5.08, yo, 0)
    xf = lx + 5.08
    s.w("+5V", (xf, yo), (xf, yo + 2.54))
    vpart(s, "R15", xf, yo + 2.54)
    vpart(s, "R16", xf, yo + 10.16)
    s.rail("GND", *s.P("R16", 2))
    fx, fy = s.P("U8", 5)
    s.w("BUCK5_FB", (fx, fy), (fx + 5.08, fy), (fx + 5.08, yo + 10.16), s.P("R15", 2))
    for i, ref in enumerate(("C24", "C25", "C26")):
        x = xf + 17.78 + 17.78 * i
        s.w("+5V", (x, yo), (x, yo + 2.54))
        vpart(s, ref, x, yo + 2.54)
        s.rail("GND", *s.P(ref, 2))
    s.text("To the TLV62569 bucks, the 5V_OUT eFuse,\nthe ULPI PHY and the target supply", xe - 25.4, yo - 15.24)


def boost(prj):
    s = prj.sheet("VIN_BUS", "boost.kicad_sch", "VIN_BUS: LM5155 24.5 V boost from VSYS, or VIN_EXT")
    s.text("VIN_BUS BOOST", 20.32, 17.78, 2.54, True)
    s.text("VIN_BUS = the higher of the boost (24.5 V) and VIN_EXT through D18. With VIN_EXT present, Q9 holds UVLO\n"
           "low: a 12 V VIN_EXT is passed through, never boosted. On USB or PoE the firmware enables the boost\n"
           "(BOOST_EN) within the source budget. Values simulated in hardware/sim/boost.py.\n"
           "Layout: C119/C120, Q8, R116 and D17 in one tight loop on the PGND side; CS and FB tracks away from SW.",
           20.32, 25.4)
    yp = 63.5                                  # power row
    ux, uy = 147.32, 127.0                     # LM5155
    s.place("U42", ux, uy, ref_at=(ux + 5.08, uy - 17.78), val_at=(ux + 5.08, uy - 15.24))

    # --- VSYS input row: ceramics, BIAS, inductor ---
    s.glabel("VSYS", 30.48, yp, 180, "input")
    s.text("From the Sources sheet", 17.78, yp - 7.62)
    xl = ux + 30.48
    s.place("L5", xl, yp, rot=90, ref_at=(xl, yp - 5.08), val_at=(xl, yp - 2.54))
    s.w("VSYS", (30.48, yp), s.P("L5", 1))
    for ref, x in (("C119", 45.72), ("C120", 58.42), ("C118", ux - 25.4)):
        s.w("VSYS", (x, yp), (x, yp + 2.54))
        vpart(s, ref, x, yp + 2.54)
        s.rail("GND", *s.P(ref, 2))
    bx, by = s.P("U42", 1)
    s.w("VSYS", (bx, by), (ux - 15.24, by), (ux - 15.24, yp))

    # --- switch node: Q8 drain, D17 anode ---
    xq = ux + 66.04
    cx, cy = s.P("U42", 5)
    s.place("Q8", xq, cy - 15.24, ref_at=(xq + 5.08, cy - 17.78), val_at=(xq + 5.08, cy - 15.24))
    dx, dy = s.P("Q8", 5)
    xd = dx + 15.24
    s.place("D17", xd, yp, rot=180, ref_at=(xd, yp - 5.08), val_at=(xd, yp - 2.54))
    s.w("BOOST_SW", s.P("L5", 2), (dx, yp), s.P("D17", 2))
    s.w("BOOST_SW", (dx, yp), (dx, dy))
    s.label("BOOST_SW", dx - 10.16, yp, 0)
    gx, gy = s.P("U42", 3)
    qx, qy = s.P("Q8", 4)
    xm = ux + 25.4
    s.w("BOOST_GATE", (gx, gy), (xm, gy), (xm, qy), (qx, qy))
    s.label("BOOST_GATE", gx + 2.54, gy, 0)

    # --- current sense: R116 under the source, slope resistor and filter back to CS ---
    sx, sy = s.P("Q8", 1)
    s.w("BOOST_ISNS", (sx, sy), (sx, cy))
    vpart(s, "R116", sx, cy)
    s.rail("GND", *s.P("R116", 2))
    s.place("R117", sx - 10.16, cy, rot=270, ref_at=(sx - 10.16, cy - 5.08), val_at=(sx - 10.16, cy - 2.54))
    s.place("R118", sx - 30.48, cy, rot=270, ref_at=(sx - 30.48, cy - 5.08), val_at=(sx - 30.48, cy - 2.54))
    s.w("BOOST_ISNS", (sx, cy), s.P("R117", 1))
    s.w("BOOST_CSF", s.P("R117", 2), s.P("R118", 1))
    s.w("BOOST_CS", s.P("R118", 2), (cx, cy))
    vpart(s, "C113", cx + 12.7, cy)
    s.rail("GND", *s.P("C113", 2))
    fx, fy = s.P("U42", 8)
    s.w("BOOST_FB", (fx, fy), (fx + 5.08, fy), (fx + 5.08, uy + 20.32))
    s.label("BOOST_FB", fx + 5.08, uy + 20.32, 0)
    s.rail("GND", *s.P("U42", 4))
    s.rail("GND", *s.P("U42", 7))
    s.rail("GND", *s.P("U42", 13))

    # --- VCC regulator capacitor, on top ---
    vx, vy = s.P("U42", 2)
    yv = uy - 27.94
    s.w("BOOST_VCC", (vx, vy), (vx, yv), (ux - 7.62, yv))
    vpart(s, "C117", ux - 7.62, yv)
    s.rail("GND", *s.P("C117", 2))
    s.label("BOOST_VCC", vx, yv, 0)

    # --- left pins: the lowest pin takes the nearest column, so no wire crosses a hanging part ---
    px, py = s.P("U42", 6)
    s.w("BOOST_COMP", (px, py), (ux - 33.02, py))
    vpart(s, "C115", ux - 20.32, py)
    s.rail("GND", *s.P("C115", 2))
    vpart(s, "R119", ux - 33.02, py)
    s.w("BOOST_CZ", s.P("R119", 2), (ux - 33.02, py + 10.16))
    vpart(s, "C114", ux - 33.02, py + 10.16)
    s.rail("GND", *s.P("C114", 2))
    for pin, net, ref, x in ((10, "BOOST_RT", "R113", ux - 45.72), (9, "BOOST_SS", "C116", ux - 58.42)):
        px, py = s.P("U42", pin)
        s.w(net, (px, py), (x, py))
        vpart(s, ref, x, py)
        s.rail("GND", *s.P(ref, 2))

    # --- enable: BOOST_EN divider, overridden by Q9 when VIN_EXT is present ---
    px, py = s.P("U42", 12)
    xu = ux - 71.12
    s.w("BOOST_UVLO", (px, py), (xu - 21.59, py))
    s.label("BOOST_UVLO", xu + 2.54, py, 0)
    vpart(s, "R121", xu, py)
    s.rail("GND", *s.P("R121", 2))
    xr = xu - 25.4
    s.place("R120", xr, py, rot=90, ref_at=(xr, py - 5.08), val_at=(xr, py - 2.54))
    s.w("BOOST_EN", s.P("R120", 1), (xr - 12.7, py))
    s.glabel("BOOST_EN", xr - 12.7, py, 180, "input")
    s.text("From PD15", xr - 22.86, py - 5.08)
    yq9 = py + 22.86
    s.place("Q9", xu - 12.7, yq9, ref_at=(xu - 8.89, yq9 + 6.35), val_at=(xu - 8.89, yq9 + 8.89))
    ddx, ddy = s.P("Q9", 3)
    s.w("BOOST_UVLO", (ddx, ddy), (ddx, py))
    s.rail("GND", *s.P("Q9", 2))
    ggx, ggy = s.P("Q9", 1)
    xg = ggx - 12.7
    s.w("BOOST_INH", (ggx, ggy), (xg, ggy), (xg, ggy + 2.54))
    vpart(s, "R123", xg, ggy + 2.54)
    s.rail("GND", *s.P("R123", 2))
    s.place("R122", xg - 10.16, ggy, rot=90, ref_at=(xg - 10.16, ggy - 5.08), val_at=(xg - 10.16, ggy - 2.54))
    s.w("BOOST_INH", s.P("R122", 2), (xg, ggy))
    s.w("VIN_EXT_P", s.P("R122", 1), (xg - 22.86, ggy))
    s.glabel("VIN_EXT_P", xg - 22.86, ggy, 180, "input")
    s.text("BOOST_EN low or high-Z: off.\nVIN_EXT >= 10.8 V: gate >= 3.4 V, off.", xr - 22.86, yq9 + 17.78)

    # --- VIN_BUS row: output ceramics, VIN_EXT path, feedback, ADC divider ---
    kx, ky = s.P("D17", 1)
    xe = kx + 149.86
    s.w("VIN_BUS", (kx, yp), (xe, yp))
    s.glabel("VIN_BUS", xe, yp, 0, "output")
    s.text("To the local bus switches\n(TPS27S100B x 2)", xe - 20.32, yp - 12.7)
    s.power("PWR_FLAG", kx + 5.08, yp, 0)
    for i, ref in enumerate(("C121", "C122", "C123", "C124")):
        x = kx + 12.7 + 12.7 * i
        s.w("VIN_BUS", (x, yp), (x, yp + 2.54))
        vpart(s, ref, x, yp + 2.54)
        s.rail("GND", *s.P(ref, 2))
    x18 = kx + 66.04
    s.place("D18", x18, yp - 3.81, rot=90, ref_at=(x18 + 5.08, yp - 6.35), val_at=(x18 + 5.08, yp - 3.81))
    ax, ay = s.P("D18", 2)
    s.w("VIN_EXT_P", (ax, ay), (ax, ay - 5.08))
    s.glabel("VIN_EXT_P", ax, ay - 5.08, 90, "input")
    xf = kx + 81.28
    s.w("VIN_BUS", (xf, yp), (xf, yp + 2.54))
    vpart(s, "R114", xf, yp + 2.54)
    vpart(s, "R115", xf, yp + 15.24)
    s.rail("GND", *s.P("R115", 2))
    s.w("BOOST_FB", s.P("R114", 2), s.P("R115", 1))
    s.w("BOOST_FB", (xf, yp + 12.7), (xf + 7.62, yp + 12.7))
    s.label("BOOST_FB", xf + 7.62, yp + 12.7, 0)
    sense(s, "R124", "R125", "C125", "VIN_BUS", "VIN_BUS_SENSE", kx + 109.22, yp)
    s.text("VIN_BUS_SENSE to PF5.", kx + 109.22, yp + 33.02)


def buck3v3(prj):
    s = prj.sheet("+3V3", "buck3v3.kicad_sch", "+3V3 and +3V3_AUX rails: two TLV62569 bucks from +5V")
    s.text("+3V3 / +3V3_AUX BUCKS", 20.32, 17.78, 2.54, True)
    s.text("Two identical 2 A converters: +3V3 feeds the probe (520 mA max), +3V3_AUX feeds the 3V3_OUT eFuse\n"
           "(1 A ceiling), so a shield or target short never pulls the probe rail down.\n"
           "Layout: input capacitor against VIN and GND, short SW node, FB divider away from the inductor.",
           20.32, 25.4)
    rows = (("U9", "L2", "C27", "C28", "R17", "R18", "+3V3", "B3V3", 68.58,
             "To the MCU, FPGA LDO, PHYs and logic"),
            ("U10", "L3", "C29", "C30", "R19", "R20", "+3V3_AUX", "B3V3A", 124.46,
             "To the 3V3_OUT eFuse (shield)"))
    for u, l, cin, cout, rt, rb, out, tag, uy, dest in rows:
        ux = 101.6
        yi = uy - 2.54                        # VIN pin row, also the SW pin row on the right
        s.place(u, ux, uy, ref_at=(ux - 5.08, uy - 10.16), val_at=(ux - 5.08, uy - 7.62))
        x0 = 50.8
        s.rail("+5V", x0, yi)
        s.w("+5V", (x0, yi), s.P(u, 4))
        xc = ux - 30.48
        s.w("+5V", (xc, yi), (xc, yi + 2.54))
        vpart(s, cin, xc, yi + 2.54)
        s.rail("GND", *s.P(cin, 2))
        ex, ey = s.P(u, 1)
        s.w("+5V", (ex, ey), (ex - 5.08, ey), (ex - 5.08, yi))
        s.rail("GND", *s.P(u, 2))
        sx, sy = s.P(u, 3)
        xl = ux + 30.48
        s.place(l, xl, sy, rot=90, ref_at=(xl, sy - 7.62), val_at=(xl, sy - 5.08))
        s.w(f"{tag}_SW", (sx, sy), s.P(l, 1))
        lx, ly = s.P(l, 2)
        xf = lx + 7.62
        xe = xf + 38.1
        s.w(out, (lx, ly), (xe, ly))
        s.rail(out, xe, ly)
        s.power("PWR_FLAG", xe - 5.08, ly, 0)
        s.w(out, (xf, ly), (xf, ly + 2.54))
        vpart(s, rt, xf, ly + 2.54)
        vpart(s, rb, xf, ly + 10.16)
        s.rail("GND", *s.P(rb, 2))
        fx, fy = s.P(u, 5)
        s.w(f"{tag}_FB", (fx, fy), (fx + 5.08, fy), (fx + 5.08, ly + 10.16), s.P(rt, 2))
        xo = xf + 20.32
        s.w(out, (xo, ly), (xo, ly + 2.54))
        vpart(s, cout, xo, ly + 2.54)
        s.rail("GND", *s.P(cout, 2))
        s.text(dest, xe - 12.7, ly - 12.7)


DEBUG_NETS = ("MCU_SWDIO", "MCU_SWCLK", "MCU_SWO", "USB_FS_DM", "USB_FS_DP", "CONSOLE_TX", "CONSOLE_RX")


def mcu(prj):
    s = prj.sheet("MCU", "mcu.kicad_sch", "MCU: STM32H723ZGT6, decoupling, HSE, debug connector", paper="A2")
    s.text("MCU", 20.32, 17.78, 2.54, True)
    s.text("STM32H723ZGT6, LQFP-144. Pin assignment: hardware/mcu-pins.csv (checked by pincheck.py); unlisted\n"
           "pins carry a no-connect flag. Layout: one 100 nF per VDD pin against the pin, VCAP capacitors\n"
           "against pins 71 and 106, crystal and load capacitors next to PH0/PH1 with a ground guard.",
           20.32, 25.4)
    x0, y0 = 304.8, 203.2
    s.place("U11", x0, y0, ref_at=(x0 + 25.4, y0 + 99.06), val_at=(x0 + 25.4, y0 + 101.6))
    nets = prj.parts["U11"]["pins"]
    local = {"+3V3", "GND", "VDDA", "VCAP", "BOOT0", "NRST", "HSE_IN", "HSE_OUT"}
    for (ref, num), (px, py) in list(s.pins.items()):
        net = nets.get(num)
        if ref != "U11" or net is None or net in local:
            continue
        rot = 180 if px < x0 else 0
        if net in DEBUG_NETS:
            s.label(net, px, py, rot)
        else:
            s.glabel(net, px, py, rot, "bidirectional")

    # supplies, top: VBAT, VDD x 11 and VDD33USB on one +3V3 bus with the decoupling row on its left
    yb = 101.6
    tops = sorted(s.P("U11", n) for n, net in nets.items() if net == "+3V3" and s.P("U11", n)[1] < y0 - 90)
    for px, py in tops:
        s.w("+3V3", (px, py), (px, yb))
    xr = 137.16
    s.w("+3V3", (xr, yb), (tops[-1][0], yb))
    s.rail("+3V3", xr, yb)
    for i, ref in enumerate([f"C{n}" for n in range(31, 43)] + ["C47"]):
        x = 147.32 + 10.16 * i
        vpart(s, ref, x, yb)
        s.rail("GND", *s.P(ref, 2))
    s.text("11 x 100 nF: one per VDD pin. C47: VDD33USB. C42: bulk", 147.32, 88.9)

    # VDDA / VREF+: ferrite from +3V3, 1 µF + 100 nF
    ax, ay = s.P("U11", "33")
    yv = 93.98
    s.w("VDDA", (ax, ay), (ax, yv), (ax + 35.56, yv))
    s.label("VDDA", ax + 2.54, yv, 0, tag="top")
    xf = ax + 10.16
    s.place("FB1", xf, yv - 2.54, ref_at=(xf + 2.54, yv - 5.08), val_at=(xf + 2.54, yv - 2.54))
    s.rail("+3V3", *s.P("FB1", "1"))
    for ref, x in (("C45", ax + 25.4), ("C46", ax + 35.56)):
        vpart(s, ref, x, yv)
        s.rail("GND", *s.P(ref, 2))
    s.power("PWR_FLAG", ax + 30.48, yv, 0)

    # PPS loopback: PG8 (ETH_PPS_OUT) to PA0 (TIM2_ETR)
    lx, ly = 431.8, 279.4
    s.text("PPS loopback", lx, ly - 10.16, 1.8, True)
    s.place("R175", lx + 12.7, ly, rot=90, ref_at=(lx + 12.7, ly - 4.57), val_at=(lx + 12.7, ly - 2.54))
    s.w("PPS", (lx, ly), s.P("R175", 1))
    s.glabel("PPS", lx, ly, 180, "bidirectional", "loop")
    s.w("PPS_IN", s.P("R175", 2), (lx + 25.4, ly))
    s.glabel("PPS_IN", lx + 25.4, ly, 0, "bidirectional", "loop")
    s.text("PG8 (ETH_PPS_OUT) to PA0 (TIM2_ETR): TIM2 restarts on the PTP second,\n"
           "LATCH follows it. R175 not fitted if TIM2 has an internal ETH PPS trigger.", lx, ly + 7.62)

    # left column: NRST, BOOT0, VREF+, PDR_ON
    nx, ny = s.P("U11", "25")
    s.w("NRST", (nx, ny), (nx - 63.5, ny))
    vpart(s, "C48", nx - 63.5, ny)
    s.rail("GND", *s.P("C48", 2))
    s.label("NRST", nx - 58.42, ny, 0)
    bx, by = s.P("U11", "138")
    s.w("BOOT0", (bx, by), (bx - 50.8, by))
    vpart(s, "R21", bx - 50.8, by)
    s.rail("GND", *s.P("R21", 2))
    s.label("BOOT0", bx - 45.72, by, 0)
    rx, ry = s.P("U11", "32")
    s.w("VDDA", (rx, ry), (rx - 12.7, ry))
    s.label("VDDA", rx - 12.7, ry, 180)
    px, py = s.P("U11", "143")
    s.w("+3V3", (px, py), (px - 22.86, py))
    s.rail("+3V3", px - 22.86, py)

    # HSE crystal below, load capacitors outside the crystal pins
    hx, hy = s.P("U11", "23")
    ox, oy = s.P("U11", "24")
    xc, yc = 227.33, 165.1
    s.place("Y1", xc, yc, ref_at=(xc - 2.54, yc - 7.62), val_at=(xc - 2.54, yc - 5.08))
    (ix, iy), (qx, qy) = s.P("Y1", 1), s.P("Y1", 3)
    s.w("HSE_IN", (ix - 15.24, iy), (ix, iy), (ix, hy), (hx, hy))      # first segment carries the label
    s.w("HSE_OUT", (qx + 15.24, qy), (qx, qy), (qx, oy), (ox, oy))
    s.rail("GND", *s.P("Y1", 2))
    for ref, x in (("C49", ix - 15.24), ("C50", qx + 15.24)):
        vpart(s, ref, x, iy)
        s.rail("GND", *s.P(ref, 2))

    # VCAP
    v1x, v1y = s.P("U11", "71")
    v2x, v2y = s.P("U11", "106")
    s.w("VCAP", (v1x, v1y), (v1x - 38.1, v1y))
    s.w("VCAP", (v2x, v2y), (v2x - 12.7, v2y), (v2x - 12.7, v1y))
    for ref, x in (("C43", v1x - 27.94), ("C44", v1x - 38.1)):
        vpart(s, ref, x, v1y)
        s.rail("GND", *s.P(ref, 2))

    # ground: the VSS pins share one point, VSSA joins it
    gx, gy = s.P("U11", "16")
    s.rail("GND", gx, gy, drop=5.08)
    ax2, ay2 = s.P("U11", "31")
    s.w("GND", (ax2, ay2), (ax2, gy + 2.54), (gx, gy + 2.54))

    # Tag-Connect TC2030 debug footprint (as on Bornier), right of the SWD pins
    jx, jy = 419.1, 165.1
    s.place("J4", jx, jy, ref_at=(jx + 5.08, jy - 15.24), val_at=(jx + 5.08, jy - 12.7))
    s.rail("+3V3", *s.P("J4", 1))
    s.rail("GND", *s.P("J4", 5))
    jn = prj.parts["J4"]["pins"]
    for n in (2, 3, 4, 6):
        s.label(jn[str(n)], *s.P("J4", n), 0, tag="j4")
    s.text("TC2030 footprint, nothing to fit: J-Link through the\nSEGGER 6-pin Needle Adapter or a TC2030-CTX cable.",
           jx - 7.62, jy + 20.32)

    # J5 micro-B: ROM DFU on the internal FS PHY. VBUS powers the board and raises BOOT0
    s.text("Programming with no probe: ROM bootloader (AN2606)", 444.5, 96.52, 1.8, True)
    x5, y5 = 449.58, 129.54
    s.place("J5", x5, y5, ref_at=(x5 - 10.16, y5 - 15.24), val_at=(x5 - 10.16, y5 - 12.7))
    s.w("GND", s.P("J5", "SH"), (x5 - 2.54, y5 + 12.7), (x5, y5 + 12.7))
    s.rail("GND", *s.P("J5", 5))
    yv = 109.22
    s.place("D7", 480.06, yv, rot=180, ref_at=(477.52, yv - 5.08), val_at=(477.52, yv - 2.54))
    s.w("USB_FS_VBUS", s.P("J5", 1), (457.2, yv), s.P("D7", 2))
    s.label("USB_FS_VBUS", 457.2 + 1.27, yv, 0)
    vpart(s, "R24", 467.36, yv)
    s.label("BOOT0", *s.P("R24", 2), 270, tag="j5")
    s.w("VSYS", s.P("D7", 1), (497.84, yv))
    s.glabel("VSYS", 497.84, yv, 0, "bidirectional", tag="j5")
    s.place("U12", 474.98, y5, ref_at=(459.74, y5 + 7.62), val_at=(459.74, y5 + 10.16))
    s.w("J5_DP", s.P("J5", 3), s.P("U12", 1))
    s.w("J5_DM", s.P("J5", 2), s.P("U12", 3))
    s.rail("+3V3", *s.P("U12", 5))
    s.rail("GND", *s.P("U12", 2))
    s.w("USB_FS_DP", s.P("U12", 6), (510.54, y5))
    s.label("USB_FS_DP", 510.54, y5, 0)
    vpart(s, "R23", 500.38, y5)
    s.rail("GND", *s.P("R23", 2))
    ym = 147.32
    s.w("USB_FS_DM", s.P("U12", 4), (482.6, y5 + 2.54), (482.6, ym), (510.54, ym))
    s.label("USB_FS_DM", 510.54, ym, 0)
    vpart(s, "R22", 495.3, ym)
    s.rail("GND", *s.P("R22", 2))
    s.text("J5: prototypes, may be left off. R24 out: J5 is a plain USB FS port.\n"
           "R22/R23: D+/D- at a known level while the ROM polls the other interfaces.", 444.5, 162.56)

    # J6: FTDI cable pads (USART3 console and ROM bootloader). Cable on the left, flow to the right
    x6, y6 = 447.04, 205.74
    s.place("J6", x6, y6, mirror="y", ref_at=(x6 - 7.62, y6 - 10.16), val_at=(x6 - 7.62, y6 + 12.7))
    px = s.P("J6", 1)[0]
    gy = s.P("J6", 1)[1]
    s.w("GND", (px, gy), (px + 2.54, gy))
    s.power("GND", px + 2.54, gy, 90, show=False)
    yb = 190.5
    s.w("BOOT0", s.P("J6", 2), (px + 7.62, s.P("J6", 2)[1]), (px + 7.62, yb), (510.54, yb))
    s.label("BOOT0", 510.54, yb, 0, tag="j6")
    sx = 500.38
    s.place("SW1", sx, yb - 5.08, rot=270, ref_at=(sx + 2.54, yb - 7.62), val_at=(sx + 2.54, yb - 5.08))
    s.rail("+3V3", *s.P("SW1", 1))
    yc = s.P("J6", 3)[1]
    vpart(s, "R25", 474.98, yb)
    s.place("D8", 490.22, yc, rot=180, ref_at=(487.68, yc - 5.08), val_at=(487.68, yc - 2.54))
    s.w("J6_VCC", s.P("J6", 3), s.P("D8", 2))
    s.label("J6_VCC", s.P("J6", 3)[0] + 3.81, yc, 0)
    s.w("J6_VCC", s.P("R25", 2), (474.98, yc))
    s.w("VSYS", s.P("D8", 1), (497.84, yc))
    s.glabel("VSYS", 497.84, yc, 0, "bidirectional", tag="j6")
    for n, net in ((4, "CONSOLE_RX"), (5, "CONSOLE_TX")):
        ex, ey = s.P("J6", n)
        s.w(net, (ex, ey), (510.54, ey))
        s.label(net, 510.54, ey, 0)
    ry = s.P("J6", 6)[1]
    s.place("D9", 482.6, ry + 5.08, ref_at=(480.06, ry + 1.27), val_at=(480.06, ry + 10.16))
    s.w("J6_RST", s.P("J6", 6), (467.36, ry), (467.36, ry + 5.08), s.P("D9", 1))
    s.w("NRST", s.P("D9", 2), (510.54, ry + 5.08))
    s.label("NRST", 510.54, ry + 5.08, 0, tag="j6")
    s.text("J6: pads only, FTDI cable pinout (TTL-232R-5V or adapter with 5 V on VCC).\n"
           "VCC powers the board (D8) and raises BOOT0 (R25). RTS resets through D9: NRST is not\n"
           "5 V tolerant. stm32flash -i / stm32loader drive RTS/DTR. SW1: BOOT0 by hand.", 444.5, 228.6)


FPGA_SHAPE = {"in": "input", "out": "output", "io": "bidirectional"}
FPGA_UNITS = {1: "23 25 26 27 28 31 32 34 35 36 37 38 42 43", 2: "6 9 10 11 12 13 14 15 16 17 18 19 20 21",
              3: "2 3 4 44 45 46 47 48"}   # signal pins per symbol unit (bank 0, 1, 2); RGB0 (39) drawn apart


def fpga_dirs():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fpga-pins.csv"), encoding="utf-8") as f:
        d = {row["pin"]: row["dir"] for row in csv.DictReader(f)}
    return {u: {n: d[n] for n in pins.split() if n in d} for u, pins in FPGA_UNITS.items()}


def fpga_bank(s, prj, unit, x, y, mirror, vccio, cap, xc, dy_ref=27.94):
    """One iCE40 IO bank: a global label per signal pin, VCCIO up to +3V3 with its 100 nF at xc."""
    s.place("U13", x, y, mirror=mirror, unit=unit, show_value=unit == 2,
            ref_at=(x - 5.08, y + dy_ref), val_at=(x - 5.08, y + dy_ref + 2.54))
    nets = prj.parts["U13"]["pins"]
    FPGA_DIR = fpga_dirs()
    for (ref, num), (px, py) in list(s.pins.items()):
        net = nets.get(num)
        if ref != "U13" or num not in FPGA_DIR.get(unit, ()) or net is None:
            continue
        s.glabel(net, px, py, 180 if px < x else 0, FPGA_SHAPE[FPGA_DIR[unit][num]])
    vx, vy = s.P("U13", vccio)
    s.w("+3V3", (vx, vy), (vx, vy - 15.24))
    s.power("+3V3", vx, vy - 15.24)
    s.w("+3V3", (vx, vy - 12.7), (xc, vy - 12.7))
    vpart(s, cap, xc, vy - 12.7)
    s.rail("GND", *s.P(cap, 2))


def fpga(prj):
    s = prj.sheet("FPGA", "fpga.kicad_sch", "FPGA: iCE40UP5K-SG48, 1.2 V core, PLL filter, configuration")
    s.text("FPGA", 20.32, 17.78, 2.54, True)
    s.text("iCE40UP5K-SG48I, SPI slave configuration by the MCU over the QSPI pins. Pin assignment:\n"
           "hardware/fpga-pins.csv (checked by fpgacheck.py and nextpnr). Bank 1 (MCU, configuration) on the left,\n"
           "banks 0 and 2 (target translators, shield IOs) on the right. One 100 nF per supply pin, against the pin.",
           20.32, 25.4)
    # bank 1: MCU side, configuration pins
    x2, y2 = 101.6, 154.94
    fpga_bank(s, prj, 2, x2, y2, None, "22", "C58", 116.84)
    cx, cy = s.P("U13", "8")
    s.w("FPGA_CRESET_B", (cx, cy), (cx - 5.08, cy), (cx - 5.08, cy - 15.24), (cx - 33.02, cy - 15.24))
    s.glabel("FPGA_CRESET_B", cx - 33.02, cy - 15.24, 180, "input")
    vpart(s, "R27", cx - 22.86, cy - 15.24)
    s.rail("GND", *s.P("R27", 2))
    dx, dy = s.P("U13", "7")
    s.w("FPGA_CDONE", (dx, dy), (dx + 25.4, dy))
    s.glabel("FPGA_CDONE", dx + 25.4, dy, 0, "output")
    vpart(s, "R28", dx + 12.7, dy - 12.7)
    s.w("FPGA_CDONE", s.P("R28", 2), (dx + 12.7, dy))
    s.rail("+3V3", *s.P("R28", 1))
    s.text("R27: FPGA held in reset (IOs high-Z) until the MCU\nreleases CRESET_B, also in the ROM bootloader.",
           38.1, 187.96)
    # banks 0 and 2: target and shield, pins mirrored to the right
    fpga_bank(s, prj, 1, 304.8, 147.32, "y", "33", "C60", 320.04, 31.75)
    fpga_bank(s, prj, 3, 304.8, 223.52, "y", "1", "C57", 320.04, 19.05)
    ox, oy = s.P("U13", "39")
    s.w("SHIELD_OE_N", (ox, oy), (ox + 40.64, oy))
    s.glabel("SHIELD_OE_N", ox + 40.64, oy, 0, "output")
    vpart(s, "R29", ox + 35.56, oy - 7.62)
    s.rail("+3V3", *s.P("R29", 1))
    for num in ("40", "41"):                          # RGB1, RGB2: LED current sinks, LEDs on the UI sheet
        px, py = s.P("U13", num)
        s.glabel(prj.parts["U13"]["pins"][num], px, py, 0, "output")
    s.text("SHIELD_OE_N on RGB0 (open drain): R29 keeps the\nshield drivers off until the bitstream pulls it low.\n"
           "RGB1, RGB2: constant-current LED sinks (LINK, spare).", ox + 2.54, oy + 12.7)

    # power: +3V3 -> ME6211 -> +1V2 bus -> VCC; VCCPLL through 100 Ω; VPP_2V5 on +3V3
    yb = 50.8
    s.place("U14", 78.74, yb + 2.54, ref_at=(73.66, yb - 10.16), val_at=(73.66, yb - 7.62))
    ix, iy = s.P("U14", 1)
    s.w("+3V3", (45.72, iy), (ix, iy))
    s.power("+3V3", 45.72, iy, 90)
    vpart(s, "C51", 55.88, iy)
    s.rail("GND", *s.P("C51", 2))
    ex, ey = s.P("U14", 3)
    s.w("+3V3", (ex, ey), (ex - 5.08, ey), (ex - 5.08, iy))
    s.rail("GND", *s.P("U14", 2))
    px, py = 215.9, yb + 27.94
    s.place("U13", px, py, unit=4, show_value=False, ref_at=(px + 8.89, py + 5.08))
    vx, vy = s.P("U13", "5")
    ox, oy = s.P("U14", 5)
    s.w("+1V2", (ox, oy), (vx, oy))
    s.w("+1V2", (vx, oy), (vx, vy))
    for ref, x in (("C52", 96.52), ("C53", 154.94), ("C54", 165.1)):
        vpart(s, ref, x, oy)
        s.rail("GND", *s.P(ref, 2))
    s.text("C53, C54: VCC pins 5 and 30", 149.86, oy + 15.24)
    ax, ay = s.P("U13", "24")
    s.w("+3V3", (ax, ay), (ax, ay - 7.62), (ax - 15.24, ay - 7.62))
    s.power("+3V3", ax - 15.24, ay - 7.62, 90)
    vpart(s, "C59", ax - 7.62, ay - 7.62)
    s.rail("GND", *s.P("C59", 2))
    lx, ly = s.P("U13", "29")
    yl = ly - 5.08
    s.w("VCCPLL", (lx, ly), (lx, yl), (lx + 35.56, yl))
    s.w("+1V2", (vx, oy), (lx + 35.56, oy))
    vpart(s, "R26", lx + 35.56, oy)
    s.w("VCCPLL", s.P("R26", 2), (lx + 35.56, yl))
    for ref, x in (("C55", lx + 7.62), ("C56", lx + 25.4)):
        vpart(s, ref, x, yl)
        s.rail("GND", *s.P(ref, 2))
    s.rail("GND", *s.P("U13", "49"))
    s.text("VCCPLL filter (Lattice UltraPlus development platform):\n100 Ω, 10 µF, 100 nF against pin 29, "
           "even with the PLL unused.\nVPP_2V5 on +3V3: NVCM unused, SPI slave configuration.",
           lx + 43.18, oy - 2.54)


ULPI_SHAPE = {"1": "output", "31": "output", "2": "output", "29": "input", "27": "input"}


def ulpi(prj):
    s = prj.sheet("USB HS", "ulpi.kicad_sch", "USB HS: USB3320C ULPI PHY, 24 MHz crystal, 1.8 V LDO")
    s.text("USB HS PHY", 20.32, 17.78, 2.54, True)
    s.text("USB3320C ULPI transceiver for the OTG_HS controller (480 Mbit/s); D+/D- come from the USB-C connector "
           "after the ESD array.\nR33 holds RESETB low: PHY suspended, ULPI outputs high-Z, so CLKOUT stays off PA5 "
           "(SPI1_SCK of the ROM bootloader)\nuntil the firmware drives ULPI_RST (PD10) high. "
           "REFSEL[2:0] = 111: 24 MHz crystal.", 20.32, 25.4)
    ux, uy = 190.5, 127
    s.place("U15", ux, uy, ref_at=(ux - 20.32, uy + 27.94), val_at=(ux - 20.32, uy + 30.48))
    nets = prj.parts["U15"]["pins"]

    # --- cable side: VBUS through RVBUS, D+ / D- ---
    xg = 127
    vx, vy = s.P("U15", "22")
    s.place("R30", 147.32, vy, rot=90, ref_at=(147.32, vy - 2.54), val_at=(147.32, vy + 2.54))
    s.w("PHY_VBUS", s.P("R30", 2), (vx, vy))
    s.label("PHY_VBUS", s.P("R30", 2)[0] + 1.27, vy, 0)
    s.w("VBUS_CONN", s.P("R30", 1), (xg, vy))
    s.glabel("VBUS_CONN", xg, vy, 180, "input")
    for pin in ("18", "19"):
        px, py = s.P("U15", pin)
        s.w(nets[pin], (px, py), (xg, py))
        s.glabel(nets[pin], xg, py, 180, "bidirectional")
    # ID and REFSEL[2:0] to +3V3
    xs = 160.02
    for pin in ("23", "8", "11", "14"):
        px, py = s.P("U15", pin)
        s.w("+3V3", (px, py), (xs, py))
    iy, ry = s.P("U15", "23")[1], s.P("U15", "14")[1]
    s.w("+3V3", (xs, iy), (xs, ry))
    s.w("+3V3", (xs, iy), (xs - 7.62, iy))
    s.power("+3V3", xs - 7.62, iy, 90)
    s.text("ID unused (device only).\nREFSEL[2:0] = 111: 24 MHz.", xs - 38.1, iy + 7.62)

    # --- 24 MHz crystal, 1 MΩ across it, load capacitors outside its pins ---
    rx, ry = s.P("U15", "26")
    ox, oy = s.P("U15", "25")
    xc, yc = 139.7, 165.1
    s.place("Y2", xc, yc, ref_at=(xc + 5.08, yc + 5.08), val_at=(xc + 5.08, yc + 7.62))
    (ix, _), (qx, _) = s.P("Y2", 1), s.P("Y2", 3)
    yr = 152.4
    s.place("R32", xc, yr, rot=90, ref_at=(xc, yr - 2.54), val_at=(xc, yr + 2.54))
    s.w("PHY_REFCLK", (ix - 15.24, yc), (ix, yc), (ix, yr), (ix, ry), (rx, ry))
    s.w("PHY_XO", (qx + 15.24, yc), (qx, yc), (qx, yr), (qx, oy), (ox, oy))
    s.label("PHY_REFCLK", ix + 2.54, ry, 0)
    s.label("PHY_XO", qx + 2.54, oy, 0)
    s.rail("GND", *s.P("Y2", 2))                 # pins 2 and 4 share the same point in the library symbol
    for ref, x in (("C68", ix - 15.24), ("C69", qx + 15.24)):
        vpart(s, ref, x, yc)
        s.rail("GND", *s.P(ref, 2))
    bx, by = s.P("U15", "24")
    s.w("PHY_RBIAS", (bx, by), (bx - 15.24, by))
    s.label("PHY_RBIAS", bx - 13.97, by, 0)
    vpart(s, "R31", bx - 15.24, by)
    s.rail("GND", *s.P("R31", 2))

    # --- ULPI to the MCU, RESETB pull-down ---
    xl = 238.76
    for pin, net in nets.items():
        if not net.startswith("ULPI_"):
            continue
        px, py = s.P("U15", pin)
        s.w(net, (px, py), (xl, py))
        s.glabel(net, xl, py, 0, ULPI_SHAPE.get(pin, "bidirectional"))
    px, py = s.P("U15", "27")
    vpart(s, "R33", xl - 10.16, py)
    s.rail("GND", *s.P("R33", 2))
    s.rail("GND", *s.P("U15", "33"))

    # --- 3.3 V supplies: one capacitor per pin, on the left of the rail ---
    y3 = 81.28
    xa = s.P("U15", "21")[0]
    for pin in ("21", "20", "32"):
        px, py = s.P("U15", pin)
        s.w("+3V3", (px, py), (px, y3))
    s.w("+3V3", (s.P("U15", "32")[0], y3), (127, y3))
    s.power("+3V3", 127, y3, 90)
    for ref, x in (("C66", xa - 38.1), ("C65", xa - 25.4), ("C67", xa - 12.7)):
        vpart(s, ref, x, y3)
        s.rail("GND", *s.P(ref, 2))
    s.text("C66 VBAT, C65 VDD33 (COUT of the internal\n3.3 V regulator), C67 VDDIO: against their pins.",
           139.7, y3 - 5.08)

    # --- 1.8 V: ME6211 from +5V, so VDD18 is up before VDDIO (+3V3, buck from +5V) ---
    yb = 63.5
    s.place("U16", 78.74, yb + 2.54, ref_at=(73.66, yb - 10.16), val_at=(73.66, yb - 7.62))
    lx, ly = s.P("U16", 1)
    s.w("+5V", (45.72, ly), (lx, ly))
    s.power("+5V", 45.72, ly, 90)
    vpart(s, "C61", 55.88, ly)
    s.rail("GND", *s.P("C61", 2))
    ex, ey = s.P("U16", 3)
    s.w("+5V", (ex, ey), (ex - 5.08, ey), (ex - 5.08, ly))
    s.rail("GND", *s.P("U16", 2))
    tx, ty = s.P("U16", 5)
    x18 = s.P("U15", "30")[0] + 20.32
    s.w("+1V8", (tx, ty), (x18, ty))
    s.label("+1V8", tx + 5.08, ty, 0)
    for pin in ("28", "30"):
        px, py = s.P("U15", pin)
        s.w("+1V8", (px, py), (px, ty))
    for ref, x in (("C62", 96.52), ("C63", x18 - 10.16), ("C64", x18)):
        vpart(s, ref, x, ty)
        s.rail("GND", *s.P(ref, 2))
    s.text("C63, C64: VDD18 pins 28 and 30", x18 - 12.7, ty + 15.24)
    s.text("U16 runs from +5V: 1.8 V is up before +3V3, as the absolute\n"
           "maximum ratings require (VDDIO 0.7 V max while VDD18 is off).", 40.64, yb + 25.4)


RMII_SHAPE = {"7": "output", "8": "output", "11": "output", "12": "bidirectional", "13": "input",
              "14": "output", "15": "input", "16": "input", "17": "input", "18": "input"}


def rmii(prj):
    s = prj.sheet("Ethernet", "rmii.kicad_sch",
                  "Ethernet: LAN8742A RMII PHY, 25 MHz crystal, line termination, RJ45 LEDs")
    s.text("Ethernet PHY", 20.32, 17.78, 2.54, True)
    s.text("LAN8742A 10/100 PHY on the RMII of the MCU. REF_CLK Out mode: the PHY makes the 50 MHz REF_CLK from its "
           "own 25 MHz crystal\nand drives PA1 (nINTSEL low through R41); its nINT output is then lost, the link is "
           "polled over MDIO.\nR42 holds the PHY in reset until the firmware drives ETH_PHY_RST (PG6) high; the "
           "straps are latched at that edge:\nMODE[2:0] = 111 (all capable, auto-negotiation) and PHYAD = 0, both by "
           "the internal pulls. Internal 1.2 V regulator (REGOFF low).", 20.32, 25.4)
    ux, uy = 152.4, 116.84
    s.place("U17", ux, uy, ref_at=(ux + 5.08, uy + 30.48), val_at=(ux + 5.08, uy + 33.02))
    nets = prj.parts["U17"]["pins"]

    # --- RMII and management to the MCU; pulls on MDIO and nRST further left ---
    xd, xm = 121.92, 88.9
    for pin, net in nets.items():
        if net.startswith("RMII_") or net == "ETH_PHY_RST":
            px, py = s.P("U17", pin)
            xl = xm if pin in ("12", "13", "15") else xd
            s.w(net, (px, py), (xl, py))
            s.glabel(net, xl, py, 180, RMII_SHAPE[pin])
    xp = 99.06
    my = s.P("U17", "12")[1]
    vpart(s, "R43", xp, my - 7.62)
    s.rail("+3V3", *s.P("R43", 1))
    vpart(s, "R42", xp, s.P("U17", "15")[1])
    s.rail("GND", *s.P("R42", 2))
    s.text("To the MCU", xm - 12.7, 93.98)

    # --- 25 MHz crystal, load capacitors outside its pins ---
    xc, yc = 114.3, 152.4
    s.place("Y3", xc, yc, ref_at=(xc + 5.08, yc + 5.08), val_at=(xc + 5.08, yc + 7.62))
    (ix, _), (qx, _) = s.P("Y3", 1), s.P("Y3", 3)
    (_, y1), (_, y2) = s.P("U17", "5"), s.P("U17", "4")
    s.w("ETH_XTAL1", (ix - 10.16, yc), (ix, yc), (ix, y1), (s.P("U17", "5")[0], y1))
    s.w("ETH_XTAL2", (qx + 10.16, yc), (qx, yc), (qx, y2), (s.P("U17", "4")[0], y2))
    s.label("ETH_XTAL1", ix + 2.54, y1, 0)
    s.label("ETH_XTAL2", qx + 2.54, y2, 0)
    s.rail("GND", *s.P("Y3", 2))
    for ref, x in (("C70", ix - 10.16), ("C71", qx + 10.16)):
        vpart(s, ref, x, yc)
        s.rail("GND", *s.P(ref, 2))

    # --- supplies: VDDIO on the left rail, VDD1A/VDD2A on the right one, VDDCR up between them ---
    y3, ycr = 68.58, 50.8
    vx = s.P("U17", "9")[0]
    s.w("+3V3", s.P("U17", "9"), (vx, y3), (116.84, y3))
    s.power("+3V3", 116.84, y3, 90)
    for ref, x in (("C77", 129.54), ("C74", 139.7)):
        vpart(s, ref, x, y3)
        s.rail("GND", *s.P(ref, 2))
    ax, bx = s.P("U17", "19")[0], s.P("U17", "1")[0]
    for pin in ("19", "1"):
        px, py = s.P("U17", pin)
        s.w("+3V3", (px, py), (px, y3))
    s.w("+3V3", (ax, y3), (170.18, y3))
    s.rail("+3V3", 170.18, y3)
    for ref, x in (("C75", 160.02), ("C76", 170.18)):
        vpart(s, ref, x, y3)
        s.rail("GND", *s.P(ref, 2))
    cx, cy = s.P("U17", "6")
    s.w("ETH_VDDCR", (cx, cy), (cx, ycr), (129.54, ycr))
    s.label("ETH_VDDCR", 141.0, ycr, 0)
    s.power("PWR_FLAG", 134.62, ycr, 0)
    for ref, x in (("C73", 129.54), ("C72", 139.7)):
        vpart(s, ref, x, ycr)
        s.rail("GND", *s.P(ref, 2))
    s.text("C74 VDDIO, C75 VDD1A, C76 VDD2A, C72/C73 VDDCR\n(1.2 V regulator output): against their pins.",
           20.32, 55.88)
    s.rail("GND", *s.P("U17", "25"))

    # --- line side: pairs fanned out, 49.9 ohm terminations in series across each pair, middle = centre tap ---
    xj, xr, xg = 180.34, 203.2, 226.06
    fan = (("21", 66.04, 0), ("20", 83.82, 2.54), ("23", 93.98, 5.08), ("22", 111.76, None))
    for pin, yt, dx in fan:
        px, py = s.P("U17", pin)
        net = nets[pin]
        if dx is None:
            s.w(net, (px, py), (xg, py))
        else:
            s.w(net, (px, py), (xj + dx, py), (xj + dx, yt), (xg, yt))
        s.glabel(net, xg, yt, 0, "passive")
    for top, bot, ya, tag in (("R35", "R36", 66.04, "tx"), ("R37", "R38", 93.98, "rx")):
        vpart(s, top, xr, ya)
        vpart(s, bot, xr, ya + 10.16)
        my = s.P(top, 2)[1]
        s.w("ETH_CT", (xr, my), (xr, my + 2.54))
        s.w("ETH_CT", (xr, my), (xr + 10.16, my))
        s.glabel("ETH_CT", xr + 10.16, my, 0, "passive", tag)
    s.text("To J3 (PoE sheet)", xg - 2.54, 58.42)
    # centre-tap supply: +3V3 through FB2
    fx, fy = 177.8, 38.1
    s.place("FB2", fx, fy, ref_at=(fx + 2.54, fy - 1.27), val_at=(fx + 2.54, fy + 1.27))
    s.rail("+3V3", *s.P("FB2", 1))
    tx, ty = s.P("FB2", 2)
    s.w("ETH_CT", (tx, ty), (tx, ty + 5.08), (xr + 2.54, ty + 5.08))
    s.glabel("ETH_CT", xr + 2.54, ty + 5.08, 0, "passive", "fb")
    vpart(s, "C78", 190.5, ty + 5.08)
    s.rail("GND", *s.P("C78", 2))

    # --- RBIAS, LEDs (anodes in J3, cathodes to GND on the PoE sheet) ---
    rx, ry = s.P("U17", "24")
    s.w("ETH_RBIAS", (rx, ry), (187.96, ry))
    s.label("ETH_RBIAS", rx + 2.54, ry, 0)
    vpart(s, "R34", 187.96, ry)
    s.rail("GND", *s.P("R34", 2))
    for pin, yt, dx, r, net in (("3", 139.7, 5.08, "R39", "ETH_LEDL_A"), ("2", 147.32, 2.54, "R40", "ETH_LEDR_A")):
        px, py = s.P("U17", pin)
        s.place(r, 195.58, yt, rot=90, ref_at=(195.58, yt - 4.57), val_at=(195.58, yt - 2.54))
        s.w(nets[pin], (px, py), (170.18 + dx, py), (170.18 + dx, yt), s.P(r, 1))
        s.label(nets[pin], 170.18 + dx + 2.54, yt, 0)
        s.w(net, s.P(r, 2), (xg, yt))
        s.glabel(net, xg, yt, 0, "passive")
    vpart(s, "R41", 185.42, 147.32)
    s.rail("GND", *s.P("R41", 2))
    s.text("LED1 green (link/activity), LED2 yellow (speed).\nR41 pulls LED2/nINTSEL low: REF_CLK Out.",
           172.72, 165.1)


def xlate_power(s, u, ca, cb, top):
    """Translator supplies: VCCA up and left to +3V3, VCCB up and right to TGT_VCC, a 100 nF on each."""
    yt = top - 7.62
    (ax, ay), (bx, by) = s.P(u, "1"), s.P(u, "6" if s.prj.parts[u]["sym"].endswith("1T45DBV") else "8")
    s.w("+3V3", (ax, ay), (ax, yt), (ax - 15.24, yt))
    s.power("+3V3", ax - 15.24, yt, 90)
    s.w("TGT_VCC", (bx, by), (bx, yt), (bx + 15.24, yt))
    s.glabel("TGT_VCC", bx + 15.24, yt, 0, "passive", u)
    for ref, x in ((ca, ax - 10.16), (cb, bx + 10.16)):
        vpart(s, ref, x, yt)
        s.rail("GND", *s.P(ref, 2))


def target(prj):
    s = prj.sheet("Target", "target.kicad_sch",
                  "Target: STDC14 and ESP-Prog connectors, translators, ESD")
    s.text("Target interface", 20.32, 17.78, 2.54, True)
    s.text("iCE40 signals (3.3 V) on the left, translated to TGT_VCC, the logic rail the target returns on T_VCC.\n"
           "With TGT_VCC at 0 V the translators are high-Z on both sides. SWDIO direction from the iCE40, pulled to "
           "input (R44)\nwhile the FPGA is unconfigured. nRST and IO0 open drain, as on the ESP-Prog.", 20.32, 25.4)
    xg, xu, xe = 63.5, 101.6, 154.94
    s.quiet.update({"TGT_SWDIO_B", "TGT_SWCLK_B", "TGT_TDI_B", "TGT_UART_TX_B", "TGT_DIR_BUF"})

    def line(net, pin, u, xe_net=None, r=None):
        """FPGA glabel to translator A, or translator B through the series R to a connector label."""
        px, py = s.P(u, pin)
        if px < xu:
            s.w(net, (xg, py), (px, py))
            s.glabel(net, xg, py, 180, "input" if net.startswith(("TGT_SWO", "TGT_UART_RX")) else
                     "bidirectional" if net == "TGT_SWDIO_3V3" else "output")
            return py
        if r:
            s.place(r, px + 12.7, py, rot=90, ref_at=(px + 10.16, py - 2.54), val_at=(px + 15.24, py - 2.54))
            s.w(prj.parts[r]["pins"]["1"], (px, py), s.P(r, 1))
            s.w(xe_net, s.P(r, 2), (xe, py))
        else:
            s.w(xe_net, (px, py), (xe, py))
        s.label(xe_net, xe, py, 0)
        return py

    def pullup(r, x, y_line, below=False):
        """100k between TGT_VCC and the line at y_line, above it (pin 2 on the line) or below (pin 1)."""
        vpart(s, r, x, y_line if below else y_line - 7.62)
        ex, ey = s.P(r, 2 if below else 1)
        s.w("TGT_VCC", (ex, ey), (ex, ey + 2.54 if below else ey - 2.54))
        s.glabel("TGT_VCC", ex, ey + 2.54 if below else ey - 2.54, 270 if below else 90, "passive", r)

    # --- SWDIO: U18, direction from the iCE40 ---
    s.place("U18", xu, 66.04, ref_at=(xu + 3.81, 78.74), val_at=(xu + 3.81, 81.28))
    xlate_power(s, "U18", "C79", "C80", 55.88)
    s.power("PWR_FLAG", s.P("U18", "6")[0] + 5.08, 55.88 - 7.62, 0)   # TGT_VCC: the target's rail, J7 pin 3
    line("TGT_SWDIO_3V3", "3", "U18")
    y = line(None, "4", "U18", "TGT_SWDIO", "R45")
    pullup("R49", 142.24, y)
    dy = s.P("U18", "5")[1]
    s.w("TGT_SWDIO_DIR", (xg, dy), s.P("U18", "5"))
    s.glabel("TGT_SWDIO_DIR", xg, dy, 180, "input")
    vpart(s, "R44", 78.74, dy)
    s.rail("GND", *s.P("R44", 2))
    s.rail("GND", *s.P("U18", "2"))

    # --- SWCLK and TDI: U19, A to B ---
    s.place("U19", xu, 114.3, ref_at=(xu + 3.81, 129.54), val_at=(xu + 3.81, 132.08))
    xlate_power(s, "U19", "C81", "C82", 101.6)
    for a, b, net, r in (("2", "7", "TGT_SWCLK", "R46"), ("3", "6", "TGT_TDI", "R47")):
        line(net + "_3V3", a, "U19")
        line(None, b, "U19", net, r)
    s.w("+3V3", s.P("U19", "5"), (86.36, s.P("U19", "5")[1]))
    s.power("+3V3", 86.36, s.P("U19", "5")[1], 90)
    s.rail("GND", *s.P("U19", "4"))

    # --- SWO and UART RX: U20, B to A ---
    s.place("U20", xu, 165.1, ref_at=(xu + 3.81, 180.34), val_at=(xu + 3.81, 182.88))
    xlate_power(s, "U20", "C83", "C84", 152.4)
    for a, b, net in (("2", "7", "TGT_SWO"), ("3", "6", "TGT_UART_RX")):
        line(net + "_3V3", a, "U20")
        line(None, b, "U20", net)
    pullup("R50", 137.16, s.P("U20", "7")[1])
    pullup("R51", 147.32, s.P("U20", "6")[1], below=True)
    s.w("GND", s.P("U20", "5"), (86.36, s.P("U20", "5")[1]))
    s.rail("GND", 86.36, s.P("U20", "5")[1])
    s.rail("GND", *s.P("U20", "4"))

    # --- UART TX: U21, A to B ---
    s.place("U21", xu, 213.36, ref_at=(xu + 3.81, 226.06), val_at=(xu + 3.81, 228.6))
    xlate_power(s, "U21", "C85", "C86", 203.2)
    line("TGT_UART_TX_3V3", "3", "U21")
    line(None, "4", "U21", "TGT_UART_TX", "R48")
    s.w("+3V3", s.P("U21", "5"), (86.36, s.P("U21", "5")[1]))
    s.power("+3V3", 86.36, s.P("U21", "5")[1], 90)
    s.rail("GND", *s.P("U21", "2"))

    # --- nRST and IO0: open drain ---
    for q, r, net, yq in (("Q5", "R53", "TGT_NRST", 246.38), ("Q6", "R54", "TGT_IO0", 271.78)):
        s.place(q, xu, yq, ref_at=(xu + 6.35, yq - 1.27), val_at=(xu + 6.35, yq + 1.27))
        gx, gy = s.P(q, 1)
        s.w(net + "_3V3", (xg, gy), (gx, gy))
        s.glabel(net + "_3V3", xg, gy, 180, "output")
        vpart(s, r, 78.74, gy)
        s.rail("GND", *s.P(r, 2))
        dx, dyy = s.P(q, 3)
        s.w(net, (dx, dyy), (dx, dyy - 2.54), (xe, dyy - 2.54))
        s.label(net, xe, dyy - 2.54, 0)
        s.rail("GND", *s.P(q, 2))
    s.text("Gate high: line pulled low.\nR53/R54 keep the lines released\nwhile the iCE40 is unconfigured.",
           119.38, 254.0)
    ny = s.P("Q5", 3)[1] - 2.54
    s.label("TGT_NRST", 180.34, ny, 0, tag="sense")
    s.place("R174", 193.04, ny, rot=90, ref_at=(193.04, ny - 4.57), val_at=(193.04, ny - 2.54))
    s.w("TGT_NRST", (180.34, ny), s.P("R174", 1))
    s.w("TGT_NRST_SENSE", s.P("R174", 2), (205.74, ny))
    s.glabel("TGT_NRST_SENSE", 205.74, ny, 0, "output")
    s.text("nRST readback on PB4 (5 V tolerant).", 180.34, ny + 5.08)

    # --- STDC14 pin 2: copy of the SWDIO direction ---
    bx, by = 215.9, 66.04
    s.place("U22", bx, by, ref_at=(bx + 3.81, by + 12.7), val_at=(bx + 3.81, by + 15.24))
    ix, iy = s.P("U22", 2)
    s.w("TGT_SWDIO_DIR", (ix - 12.7, iy), (ix, iy))
    s.glabel("TGT_SWDIO_DIR", ix - 12.7, iy, 180, "input", "buf")
    ox, oy = s.P("U22", 1)
    s.w("GND", (ox, oy), (ox, oy - 5.08), (ox + 7.62, oy - 5.08))
    s.rail("GND", ox + 7.62, oy - 5.08)
    vx, vy = s.P("U22", 5)
    s.w("+3V3", (vx, vy), (vx, vy - 7.62), (vx - 12.7, vy - 7.62))
    s.power("+3V3", vx - 12.7, vy - 7.62, 90)
    vpart(s, "C87", vx - 7.62, vy - 7.62)
    s.rail("GND", *s.P("C87", 2))
    s.rail("GND", *s.P("U22", 3))
    yx, yy = s.P("U22", 4)
    s.place("R52", yx + 7.62, yy, rot=90, ref_at=(yx + 5.08, yy - 2.54), val_at=(yx + 10.16, yy - 2.54))
    s.w("TGT_DIR_BUF", (yx, yy), s.P("R52", 1))
    s.w("TGT_DIR_OUT", s.P("R52", 2), (yx + 20.32, yy))
    s.label("TGT_DIR_OUT", yx + 20.32, yy, 0)
    s.text("STDC14 pin 2, as on the STLINK-V3SET:\nhigh when the probe drives SWDIO.", 190.5, 86.36)

    # --- target VCC sense ---
    rx, ry = 203.2, 111.76
    s.w("TGT_VCC", (rx, ry), (rx, ry - 2.54))
    s.glabel("TGT_VCC", rx, ry - 2.54, 90, "passive", "sense")
    vpart(s, "R55", rx, ry)
    vpart(s, "R56", rx, ry + 7.62)
    s.rail("GND", *s.P("R56", 2))
    s.w("VTREF_SENSE", (rx, ry + 7.62), (rx + 22.86, ry + 7.62))
    s.glabel("VTREF_SENSE", rx + 22.86, ry + 7.62, 0, "output")
    vpart(s, "C88", rx + 10.16, ry + 7.62)
    s.rail("GND", *s.P("C88", 2))
    s.text("T_VCC sense, ADC PF11 (5.5 V -> 2.75 V).\nAlso discharges TGT_VCC with no target.", 190.5, 139.7)

    # --- ESD at the connectors ---
    for u, y in (("U23", 165.1), ("U24", 205.74)):
        s.place(u, 215.9, y, ref_at=(222.25, y + 12.7), val_at=(222.25, y + 15.24))
        for pin in ("1", "2", "4", "5"):
            px, py = s.P(u, pin)
            ex = px - 5.08 if px < 215.9 else px + 5.08
            net = prj.parts[u]["pins"][pin]
            s.w(net, (px, py), (ex, py))
            s.label(net, ex, py, 180 if ex < px else 0)
        s.rail("GND", *s.P(u, "3"))

    # --- connectors ---
    jx, jy = 317.5, 127.0
    s.place("J7", jx, jy, ref_at=(jx, jy - 12.7), val_at=(jx, jy - 10.16))
    nets = prj.parts["J7"]["pins"]
    for pin in ("2", "4", "6", "8", "10", "12", "14"):
        px, py = s.P("J7", pin)
        s.w(nets[pin], (px, py), (px + 5.08, py))
        s.label(nets[pin], px + 5.08, py, 0)
    for pin, shape in (("1", "input"), ("3", "passive")):
        px, py = s.P("J7", pin)
        s.w(nets[pin], (px, py), (px - 15.24, py))
        s.glabel(nets[pin], px - 15.24, py, 180, shape, "J7")
    px, py = s.P("J7", "13")
    s.w(nets["13"], (px, py), (px - 15.24, py))
    s.label(nets["13"], px - 15.24, py, 180)
    gx = s.P("J7", "5")[0] - 5.08
    for pin in ("5", "7", "11"):
        px, py = s.P("J7", pin)
        s.w("GND", (px, py), (gx, py))
    s.w("GND", (gx, s.P("J7", "5")[1]), (gx, s.P("J7", "11")[1]))
    s.w("GND", (gx, jy), (gx - 7.62, jy))
    s.rail("GND", gx - 7.62, jy)
    s.text("J7 STDC14 (STLINK-V3). A 10-pin Cortex\ntarget plugs on pins 3-12. Pin 9 (RTCK) unused.",
           294.64, 99.06)

    kx, ky = 317.5, 180.34
    s.place("J8", kx, ky, ref_at=(kx, ky - 7.62), val_at=(kx, ky - 5.08))
    nets = prj.parts["J8"]["pins"]
    for pin in ("1", "3", "5"):
        px, py = s.P("J8", pin)
        s.w(nets[pin], (px, py), (px - 10.16, py))
        s.label(nets[pin], px - 10.16, py, 180)
    px, py = s.P("J8", "2")
    s.w("TGT_VCC", (px, py), (px + 15.24, py))
    s.glabel("TGT_VCC", px + 15.24, py, 0, "passive", "J8")
    px, py = s.P("J8", "6")
    s.w("TGT_IO0", (px, py), (px + 5.08, py))
    s.label("TGT_IO0", px + 5.08, py, 0)
    px, py = s.P("J8", "4")
    s.w("GND", (px, py), (px + 20.32, py))
    s.rail("GND", px + 20.32, py)
    s.text("J8 ESP-Prog PROG: EN, VDD, ESP_TXD,\nGND, ESP_RXD, IO0. Same lines as J7:\none connector at a time.",
           294.64, 195.58)
    s.text("TGT_VSUP: target supply sheet.", 294.64, 147.32)


def tgt_supply(prj):
    s = prj.sheet("Target supply", "tgt_supply.kicad_sch",
                  "Target supply: TPS63020 buck-boost set by DAC, INA226 monitor")
    s.text("TARGET SUPPLY", 20.32, 17.78, 2.54, True)
    s.text("+5V -> TGT_VSUP 1.4-5.2 V (5.44 V worst case), 1 A limit enforced by the firmware from the INA226.\n"
           "TGT_VSET (DAC1_OUT1) injects into the FB node: 0 V -> 5.29 V, 3.3 V -> 1.17 V, ~1 mV per step "
           "(hardware/sim/tgt_vsup.py).\nFirmware: set the DAC before EN, DAC buffer on, ramp the setpoint, stay "
           "above 1.6 V; DAC pin high-Z -> 4.67 V. PS/SYNC low: power save,\nthe converter never sinks current from a "
           "back-driving target. PG unused. INA226 at 0x45 on I2C5.\n"
           "Layout: input capacitors against VIN/PGND, FB divider next to pin 2 (GND), shunt with Kelvin traces.",
           20.32, 25.4)
    ux, uy = 116.84, 91.44
    s.place("U25", ux, uy, ref_at=(ux - 12.7, uy + 15.24), val_at=(ux - 12.7, uy + 17.78))
    x0 = 40.64

    # --- input: +5V row on top, bus down to VIN, VIN, VINA ---
    yt, xb = uy - 33.02, ux - 20.32
    s.rail("+5V", x0, yt)
    s.w("+5V", (x0, yt), (xb, yt), (xb, s.P("U25", 1)[1]))
    for pin in ("10", "11", "1"):
        px, py = s.P("U25", pin)
        s.w("+5V", (px, py), (xb, py))
    for i, ref in enumerate(("C89", "C90", "C91")):
        x = x0 + 12.7 + 15.24 * i
        s.w("+5V", (x, yt), (x, yt + 2.54))
        vpart(s, ref, x, yt + 2.54)
        s.rail("GND", *s.P(ref, 2))
    s.text("C91: VINA bypass, against pin 1", x0 + 30.48, yt - 7.62)

    # --- enable (pulled low), PS/SYNC to ground, ground pins ---
    ex, ey = s.P("U25", 12)
    s.glabel("TGT_VSUP_EN", x0, ey, 180, "input")
    s.w("TGT_VSUP_EN", (x0, ey), (ex, ey))
    s.w("TGT_VSUP_EN", (x0 + 20.32, ey), (x0 + 20.32, ey + 2.54))
    vpart(s, "R60", x0 + 20.32, ey + 2.54)
    s.rail("GND", *s.P("R60", 2))
    px, py = s.P("U25", 13)
    s.w("GND", (px, py), (px - 2.54, py))
    s.rail("GND", px - 2.54, py)
    for pin in ("2", "15"):
        s.rail("GND", *s.P("U25", pin))

    # --- inductor across L1 / L2 ---
    yj, yl = uy - 17.78, uy - 22.86
    s.place("L4", ux, yl, rot=90, ref_at=(ux, yl - 7.62), val_at=(ux, yl - 5.08))
    for a, b, lp in (("8", "9", 1), ("6", "7", 2)):
        (xa, ya), (xb2, _) = s.P("U25", a), s.P("U25", b)
        net = prj.parts["U25"]["pins"][a]
        s.w(net, s.P("U25", b), (xb2, yj), (xa, yj))
        outer = xa if lp == 1 else xb2
        s.w(net, (xa, ya), (xa, yj))
        s.w(net, (outer, yj), (outer, yl), s.P("L4", lp))
        s.label(net, outer, yj, 180 if lp == 1 else 0)

    # --- output: VOUT bus, FB divider, ceramics, shunt ---
    yo = s.P("U25", 4)[1]
    xr, xf, xfb = ux + 20.32, ux + 27.94, ux + 17.78
    s.w("TGT_VSUP_REG", s.P("U25", 5), (xr, s.P("U25", 5)[1]), (xr, yo))
    caps = [ux + 38.1 + 15.24 * i for i in range(3)]
    xs = ux + 83.82
    s.place("R61", xs, yo, rot=90, ref_at=(xs - 2.54, yo + 3.81), val_at=(xs + 2.54, yo + 3.81))
    s.w("TGT_VSUP_REG", s.P("U25", 4), (xr, yo), (xf, yo), *[(x, yo) for x in caps], s.P("R61", 1))
    s.label("TGT_VSUP_REG", caps[-1], yo, 0)
    for x, ref in zip(caps, ("C92", "C93", "C94")):
        s.w("TGT_VSUP_REG", (x, yo), (x, yo + 2.54))
        vpart(s, ref, x, yo + 2.54)
        s.rail("GND", *s.P(ref, 2))
    s.w("TGT_VSUP_REG", (xf, yo), (xf, yo + 2.54))
    vpart(s, "R57", xf, yo + 2.54)
    vpart(s, "R58", xf, yo + 10.16)
    s.rail("GND", *s.P("R58", 2))
    ym = yo + 10.16
    fx, fy = s.P("U25", 3)
    assert abs(fy - ym) < 0.01, (fy, ym)
    s.w("TGSUP_FB", (fx, fy), (xfb, fy), (xf, ym))

    # --- DAC injection, from the left under the converter ---
    yi = uy + 25.4
    xR = ux - 12.7
    s.place("R59", xR, yi, rot=90, ref_at=(xR - 2.54, yi - 2.54), val_at=(xR + 2.54, yi - 2.54))
    s.w("TGSUP_FB", (xfb, ym), (xfb, yi), s.P("R59", 2))
    s.glabel("TGT_VSET", x0, yi, 180, "input")
    s.w("TGT_VSET", (x0, yi), s.P("R59", 1))
    s.w("TGT_VSET", (x0 + 25.4, yi), (x0 + 25.4, yi + 2.54))
    vpart(s, "C95", x0 + 25.4, yi + 2.54)
    s.rail("GND", *s.P("C95", 2))
    s.text("From DAC1_OUT1 (PA4)", x0 - 12.7, yi + 5.08)

    # --- shunt output, INA226 ---
    xe, xB = ux + 152.4, ux + 96.52
    s.w("TGT_VSUP", s.P("R61", 2), (xB, yo), (xB + 10.16, yo), (xe, yo))
    s.glabel("TGT_VSUP", xe, yo, 0, "output")
    s.text("To J7 pin 1 (Target sheet)", xe - 5.08, yo - 7.62)
    s.w("TGT_VSUP", (xB + 10.16, yo), (xB + 10.16, yo + 2.54))
    vpart(s, "C97", xB + 10.16, yo + 2.54)
    s.rail("GND", *s.P("C97", 2))
    xi, yn = ux + 124.46, yo + 30.48
    s.place("U26", xi, yn, ref_at=(xi + 5.08, yn + 15.24), val_at=(xi + 5.08, yn + 17.78))
    bx, by = s.P("U26", 8)
    s.w("TGT_VSUP", (bx, by), (xB, by), (xB, yo))
    for pin, net in (("10", "TGT_VSUP_REG"), ("9", "TGT_VSUP")):   # Kelvin sense, from the shunt pads
        px, py = s.P("U26", pin)
        s.w(net, (px, py), (px - 7.62, py))
        if net == "TGT_VSUP":
            s.glabel(net, px - 7.62, py, 180, "output", "U26")
        else:
            s.label(net, px - 7.62, py, 180)
    vx, vy = s.P("U26", 6)
    yv = vy - 7.62
    s.w("+3V3", (vx, vy), (vx, yv), (vx + 22.86, yv), (vx + 22.86, yv + 2.54))
    s.rail("+3V3", vx, yv)
    vpart(s, "C96", vx + 22.86, yv + 2.54)
    s.rail("GND", *s.P("C96", 2))
    s.rail("GND", *s.P("U26", 7))
    (a1x, a1y), (a0x, a0y) = s.P("U26", 1), s.P("U26", 2)
    s.w("+3V3", (a0x, a0y), (a0x + 2.54, a0y), (a0x + 2.54, a1y))
    s.w("+3V3", (a1x, a1y), (a1x + 2.54, a1y))
    s.rail("+3V3", a1x + 2.54, a1y)
    xg = xi + 35.56
    # I2C5 pull-ups hang from +3V3; the SCL one stands past the SDA label so it crosses no wire.
    for pin, net, shape, ref, xr, xl in (("4", "SYS_SDA", "bidirectional", "R63", xg - 5.08, xg),
                                         ("5", "SYS_SCL", "input", "R64", xg + 15.24, xg + 17.78)):
        px, py = s.P("U26", pin)
        s.w(net, (px, py), (xl, py))
        s.glabel(net, xl, py, 0, shape)
        vpart(s, ref, xr, py - 7.62)
        s.rail("+3V3", *s.P(ref, 1))
    px, py = s.P("U26", 3)
    ya = yn + 20.32
    s.w("INA_ALERT", (px, py), (px + 5.08, py), (px + 5.08, ya), (px + 15.24, ya), (xg, ya))
    s.glabel("INA_ALERT", xg, ya, 0, "output")
    vpart(s, "R62", px + 15.24, ya - 7.62)
    s.rail("+3V3", *s.P("R62", 1))
    s.text("Address 0x45 (A1 = A0 = VS)", xi - 7.62, yn + 22.86)


def ui_field(prj):
    s = prj.sheet("UI and field bus", "ui_field.kicad_sch", "UI, standalone flash, CAN FD / RS-485 field bus")
    s.quiet.update({"LED_STATUS_A", "LED_PASS_A", "LED_FAIL_A", "FIELD_TERM"})
    s.text("USER INTERFACE, STANDALONE FLASH, FIELD BUS", 20.32, 17.78, 2.54, True)
    s.text("Standalone programming: image in U27 (SPI NAND, also records traces), GO starts it, PASS / FAIL / buzzer report it, STOP cuts the target.\n"
           "Field bus on J9: CAN FD (U28) or RS-485 (U29), picked by FIELD_SEL_485 (low = CAN, also the reset state).",
           20.32, 25.4)

    # --- QSPI flash: every signal on the left; IO2 / IO3 step down so their pull-ups cross nothing ---
    ux, uy, xg = 106.68, 78.74, 63.5
    s.text("Standalone image flash (OCTOSPI1)", 40.64, 45.72, 1.524, True)
    s.place("U27", ux, uy, ref_at=(ux + 3.81, uy - 15.24), val_at=(ux + 3.81, uy + 15.24))
    shapes = {"FLASH_NCS": "input", "FLASH_CLK": "input"}
    for pin in ("1", "6", "5", "2"):
        px, py = s.P("U27", pin)
        net = prj.parts["U27"]["pins"][pin]
        s.w(net, (px, py), (xg, py))
        s.glabel(net, xg, py, 180, shapes.get(net, "bidirectional"))
    for pin, xb, yb in (("3", 91.44, 99.06), ("7", 93.98, 116.84)):
        px, py = s.P("U27", pin)
        net = prj.parts["U27"]["pins"][pin]
        s.w(net, (px, py), (xb, py), (xb, yb), (xg, yb))
        s.glabel(net, xg, yb, 180, "bidirectional")
    for ref, x, y in (("R65", 81.28, s.P("U27", 1)[1]), ("R66", 78.74, 99.06), ("R67", 78.74, 116.84)):
        vpart(s, ref, x, y - 7.62)
        s.rail("+3V3", *s.P(ref, 1))
    vx, vy = s.P("U27", 8)
    s.w("+3V3", (vx, vy), (vx, vy - 7.62), (vx + 15.24, vy - 7.62), (vx + 15.24, vy - 5.08))
    s.rail("+3V3", vx, vy - 7.62)
    vpart(s, "C98", vx + 15.24, vy - 5.08)
    s.rail("GND", *s.P("C98", 2))
    s.rail("GND", *s.P("U27", 4))
    s.rail("GND", *s.P("U27", 9))
    s.text("R65: deselected until OCTOSPI1 runs.\nR66 / R67: /WP and /HOLD off in SPI mode.", 40.64, 124.46)

    # --- buttons: switch to GND, 10k pull-up, 100 nF debounce, level out to the MCU on the right ---
    s.text("Buttons", 40.64, 137.16, 1.524, True)
    for sw, r, cf, net, yb in (("SW2", "R68", "C99", "GO_BTN", 147.32), ("SW3", "R69", "C100", "STOP_BTN", 175.26)):
        s.place(sw, 55.88, yb + 5.08, rot=270, ref_at=(59.69, yb + 3.81), val_at=(59.69, yb + 6.35))
        s.rail("GND", *s.P(sw, 2))
        s.w(net, s.P(sw, 1), (106.68, yb))
        s.glabel(net, 106.68, yb, 0, "output")
        vpart(s, r, 71.12, yb - 7.62)
        s.rail("+3V3", *s.P(r, 1))
        vpart(s, cf, 86.36, yb)
        s.rail("GND", *s.P(cf, 2))

    # --- LEDs: driver on the left (sinks), anodes to a +3V3 bus on the right ---
    s.text("Indicators", 40.64, 200.66, 1.524, True)
    xb, rows = 106.68, [210.82 + 11.43 * i for i in range(5)]
    for d, r, y in zip(("D10", "D11", "D12", "D13", "D14"), ("R70", "R71", "R72", None, None), rows):
        s.place(d, 76.2, y, ref_at=(76.2, y - 3.81), val_at=(76.2, y + 3.81))
        kx, ky = s.P(d, 1)
        net = prj.parts[d]["pins"]["1"]
        s.w(net, (kx, ky), (53.34, y))
        s.glabel(net, 53.34, y, 180, "input")
        if r:
            s.place(r, 93.98, y, rot=270, ref_at=(93.98, y - 2.54), val_at=(93.98, y + 2.54))
            s.w(net + "_A", s.P(d, 2), s.P(r, 2))
            s.w("+3V3", s.P(r, 1), (xb, y))
        else:
            s.w("+3V3", s.P(d, 2), (xb, y))
    s.w("+3V3", (xb, rows[0]), (xb, rows[-1]))
    s.rail("+3V3", xb, rows[0])
    s.text("D10-D12: MCU, ~1.3 mA.\nD13 / D14: iCE40 RGB sinks, no resistor.", 40.64, 266.7)

    # --- buzzer: +5V through R73, coil and flyback diode, low-side MOSFET ---
    s.text("Buzzer", 160.02, 45.72, 1.524, True)
    xc = 190.5
    vpart(s, "R73", xc, 50.8)
    s.rail("+5V", *s.P("R73", 1))
    s.place("D15", 177.8, 66.04, rot=270, ref_at=(162.56, 64.77), val_at=(162.56, 67.31))
    s.place("BZ1", xc + 2.54, 66.04, ref_at=(xc + 7.62, 64.77), val_at=(xc + 7.62, 67.31))
    kx, ky = s.P("D15", 1)
    ax, ay = s.P("D15", 2)
    s.w("BUZ_P", s.P("R73", 2), s.P("BZ1", 1))
    s.w("BUZ_P", (kx, ky), (xc, ky))
    s.place("Q7", xc - 2.54, 81.28, ref_at=(xc + 3.81, 80.01), val_at=(xc + 3.81, 82.55))
    s.w("BUZ_N", s.P("BZ1", 2), s.P("Q7", 3))
    s.w("BUZ_N", (ax, ay), (xc, ay))
    s.rail("GND", *s.P("Q7", 2))
    gx, gy = s.P("Q7", 1)
    s.w("BUZZER", (gx, gy), (160.02, gy))
    s.glabel("BUZZER", 160.02, gy, 180, "input")
    vpart(s, "R74", 170.18, gy)
    s.rail("GND", *s.P("R74", 2))
    s.text("TIM17_CH1 (PB9) PWM sets the tone;\nnever left high (R73 sized for the tone).", 160.02, 101.6)

    # --- field bus: CAN FD and RS-485 transceivers on one H / L pair, termination, ESD, J9 ---
    s.text("Field bus", 236.22, 45.72, 1.524, True)
    tx, ty, xl = 299.72, 76.2, 264.16
    s.place("U28", tx, ty, ref_at=(tx + 3.81, ty + 12.7), val_at=(tx + 3.81, ty + 15.24))
    px, py = s.P("U28", 1)
    s.w("FIELD_TX", (px, py), (xl, py))
    s.glabel("FIELD_TX", xl, py, 180, "input")
    px, py = s.P("U28", 4)
    s.w("CAN_RXD", (px, py), (px - 5.08, py))
    s.label("CAN_RXD", px - 5.08, py, 180)
    px, py = s.P("U28", 5)
    s.w("+3V3", (px, py), (px - 15.24, py))
    s.power("+3V3", px - 15.24, py, 90)                 # left of the CAN_RXD label: its text rises past RXD
    px, py = s.P("U28", 8)
    s.w("FIELD_SEL_485", (px, py), (xl, py))
    s.glabel("FIELD_SEL_485", xl, py, 180, "input")
    vpart(s, "R76", xl + 7.62, py)
    s.rail("GND", *s.P("R76", 2))
    vx, vy = s.P("U28", 3)
    s.w("+5V", (vx, vy), (vx, 53.34), (vx + 10.16, 53.34))
    s.rail("+5V", vx, 53.34)
    vpart(s, "C101", vx + 10.16, 53.34)
    s.rail("GND", *s.P("C101", 2))
    vpart(s, "C102", vx - 10.16, 53.34)
    s.rail("+3V3", *s.P("C102", 1))
    s.rail("GND", *s.P("C102", 2))
    s.rail("GND", *s.P("U28", 2))

    yh, xj = 55.88, 393.7
    hx, hy = s.P("U28", 7)
    s.w("FIELD_H", (hx, hy), (hx + 5.08, hy), (hx + 5.08, yh), (xj - 5.08, yh))
    s.label("FIELD_H", hx + 10.16, yh, 0)
    lx, ly = s.P("U28", 6)
    s.w("FIELD_L", (lx, ly), (381.0, ly), (381.0, yh + 2.54), (xj - 5.08, yh + 2.54))
    s.label("FIELD_L", lx + 10.16, ly, 0)
    vpart(s, "R77", 330.2, yh)
    s.place("SW4", 335.28, yh + 10.16, ref_at=(335.28, yh + 15.24), val_at=(335.28, yh + 17.78))
    s.w("FIELD_TERM", s.P("R77", 2), s.P("SW4", 2))
    s1x, s1y = s.P("SW4", 1)
    s.w("FIELD_L", (s1x, s1y), (s1x + 2.54, s1y), (s1x + 2.54, ly))
    s.place("D16", 355.6, yh + 7.62, ref_at=(365.76, yh + 7.62), val_at=(365.76, yh + 10.16))
    s.w("FIELD_H", s.P("D16", 1), (s.P("D16", 1)[0], yh))
    d2x, d2y = s.P("D16", 2)
    s.w("FIELD_L", (d2x, d2y), (d2x + 5.08, d2y), (d2x + 5.08, ly))
    s.rail("GND", *s.P("D16", 3))
    s.place("J9", xj, yh + 2.54, ref_at=(xj + 2.54, yh - 5.08), val_at=(xj + 2.54, yh - 2.54))
    gx, gy = s.P("J9", 3)
    s.w("GND", (gx, gy), (gx - 5.08, gy))
    s.rail("GND", gx - 5.08, gy)
    s.text("SW4 on 1-2: 120 R across H / L\n(set at both ends of the bus only).", 320.04, 88.9)
    s.text("D16: 24 V, H / L to GND.", 345.44, 81.28)

    # RS-485: same pair, reached by label (a second wire pair would cross the first)
    rx, ry = 299.72, 129.54
    s.place("U29", rx, ry, ref_at=(rx + 3.81, ry + 17.78), val_at=(rx + 3.81, ry + 20.32))
    px, py = s.P("U29", 1)
    s.w("RS485_RO", (px, py), (px - 10.16, py))
    s.label("RS485_RO", px - 10.16, py, 180)
    px, py = s.P("U29", 2)
    s.w("GND", (px, py), (px - 2.54, py))
    s.power("GND", px - 2.54, py, 270, show=False)      # /RE low: receiver always on
    px, py = s.P("U29", 3)
    s.w("RS485_DE", (px, py), (236.22, py))
    s.glabel("RS485_DE", 236.22, py, 180, "input")
    vpart(s, "R75", 241.3, py)
    s.rail("GND", *s.P("R75", 2))
    px, py = s.P("U29", 4)
    s.w("FIELD_TX", (px, py), (xl, py))
    s.glabel("FIELD_TX", xl, py, 180, "input", "U29")
    for pin, net in (("6", "FIELD_H"), ("7", "FIELD_L")):
        px, py = s.P("U29", pin)
        s.w(net, (px, py), (px + 7.62, py))
        s.label(net, px + 7.62, py, 0, "U29")
    vx, vy = s.P("U29", 8)
    s.w("+3V3", (vx, vy), (vx, vy - 7.62), (vx - 10.16, vy - 7.62))
    s.rail("+3V3", vx, vy - 7.62)
    vpart(s, "C103", vx - 10.16, vy - 7.62)
    s.rail("GND", *s.P("C103", 2))
    s.rail("GND", *s.P("U29", 5))
    s.text("Receiver always on; DE (PG15) drives the bus.", rx - 12.7, ry + 25.4)

    # RX mux: one MCU input (PD0) for either receiver
    mx, my = 246.38, 172.72
    s.place("U30", mx, my, ref_at=(mx + 3.81, my - 10.16), val_at=(mx + 3.81, my + 10.16))
    for pin, net in (("3", "CAN_RXD"), ("1", "RS485_RO")):
        px, py = s.P("U30", pin)
        s.w(net, (px, py), (px - 10.16, py))
        s.label(net, px - 10.16, py, 180, "U30")
    px, py = s.P("U30", 6)
    s.w("FIELD_SEL_485", (px, py), (px - 17.78, py))
    s.glabel("FIELD_SEL_485", px - 17.78, py, 180, "input", "U30")
    px, py = s.P("U30", 4)
    s.w("FIELD_RX", (px, py), (px + 15.24, py))
    s.glabel("FIELD_RX", px + 15.24, py, 0, "output")
    vx, vy = s.P("U30", 5)
    s.w("+3V3", (vx, vy), (vx, vy - 12.7), (vx + 10.16, vy - 12.7))
    s.rail("+3V3", vx, vy - 12.7)
    vpart(s, "C104", vx + 10.16, vy - 12.7)
    s.rail("GND", *s.P("C104", 2))
    s.rail("GND", *s.P("U30", 2))
    s.text("S low (reset): CAN_RXD; S high: RS485_RO.", mx - 20.32, my + 15.24)


SHIELD_SHAPE = {"SYNC_IN": "input", "SYNC_OUT": "output", "SHIELD_OE_N": "output", "SHIELD_SWCLK": "output",
                "SHIELD_UART_TX": "output", "SHIELD_UART_RX": "input", "SHIELD_RESET_N": "output",
                "SHIELD_PRESENT_N": "input"}


def shield(prj):
    s = prj.sheet("Shield", "shield.kicad_sch", "Shield headers: J_SHIELD_IO, J_SHIELD_SVC, series resistors, ESD")
    s.text("Shield headers", 20.32, 17.78, 2.54, True)
    s.text("iCE40 and MCU signals on the left, 33 Ω at the header on every line the probe can drive (_J: header\n"
           "side). I²C4, reset (open drain) and presence go straight, with their pull-ups. ESD on all 27 lines.\n"
           "Pinout: hardware/connectors.csv. +3V3_OUT and +5V_OUT: shield power sheet.", 20.32, 25.4)
    parts = prj.parts
    direct = ("SHIELD_SCL", "SHIELD_SDA", "SHIELD_RESET_N", "SHIELD_PRESENT_N")

    def end(net, x, y, rot, tag):
        """Net leaving a wire end: global label for the direct lines, local label for the _J ones."""
        if net in direct:
            s.glabel(net, x, y, rot, SHIELD_SHAPE.get(net, "bidirectional"), tag)
        else:
            s.label(net, x, y, rot, tag)

    # --- series resistors: glabel, 33 Ω, header-side label ---
    xg, xr, xl = 45.72, 66.04, 86.36
    series = [r for r in parts if parts[r]["value"] == "33" and parts[r]["pins"]["1"].startswith(("SHIELD", "SYNC"))]
    for k, r in enumerate(sorted(series, key=lambda x: int(x[1:]))):
        net = parts[r]["pins"]["1"]
        y = 50.8 + 5.08 * k + (10.16 if k >= 16 else 0)
        s.place(r, xr, y, rot=90, ref_at=(xr - 2.54, y - 2.54), val_at=(xr + 2.54, y - 2.54))
        s.w(net, (xg, y), s.P(r, 1))
        s.glabel(net, xg, y, 180, SHIELD_SHAPE.get(net, "bidirectional"))
        s.w(net + "_J", s.P(r, 2), (xl, y))
        s.label(net + "_J", xl, y, 0)
    s.text("Series 33 Ω at the header (R78-R100).", xg - 20.32, 43.18)

    # --- direct lines with their pull-ups ---
    for k, (net, r) in enumerate(zip(direct, ("R101", "R102", "R103", "R104"))):
        y = 195.58 + 17.78 * k
        s.w(net, (xg, y), (xl, y))
        s.glabel(net, xg, y, 180, SHIELD_SHAPE.get(net, "bidirectional"))
        s.glabel(net, xl, y, 0, SHIELD_SHAPE.get(net, "bidirectional"), "out")
        vpart(s, r, xr, y - 7.62)
        s.rail("+3V3", *s.P(r, 1))
    s.text("I2C4 pull-ups 2 kΩ (as I2C5); reset and presence 10 kΩ.\nThe shield ties PRESENT_N to ground.",
           xg - 20.32, 259.08)

    # --- ESD, flow-through at the headers ---
    esds = sorted((u for u in parts if parts[u]["value"] == "TPD4E05U06DQAR" and 31 <= int(u[1:]) < 47),
                  key=lambda u: int(u[1:]))
    for k, u in enumerate(esds):
        ex, ey = (152.4, 63.5 + 38.1 * k) if k < 4 else (241.3, 63.5 + 38.1 * (k - 4))
        s.place(u, ex, ey, ref_at=(ex + 6.35, ey + 12.7), val_at=(ex + 6.35, ey + 15.24))
        for pin in ("1", "2", "4", "5"):
            net = parts[u]["pins"].get(pin)
            if net is None:
                continue
            px, py = s.P(u, pin)
            qx = px - 5.08 if px < ex else px + 5.08
            s.w(net, (px, py), (qx, py))
            end(net, qx, py, 180 if qx < px else 0, u)
        s.rail("GND", *s.P(u, "3"))
    s.text("ESD at the headers (TPD4E05U06, flow-through).", 129.54, 43.18)

    # --- headers ---
    def header(j, x, y):
        s.place(j, x, y, ref_at=(x, y - 25.4), val_at=(x, y - 22.86))
        nets = parts[j]["pins"]
        px1 = s.P(j, "1")[0]
        gx = px1 - 5.08
        run = []                                             # odd pins grounded from pin 1: one bus
        for p in range(1, 35, 2):
            if nets[str(p)] != "GND":
                break
            run.append(p)
        for p in run:
            s.w("GND", s.P(j, str(p)), (gx, s.P(j, str(p))[1]))
        s.w("GND", (gx, s.P(j, str(run[0]))[1]), (gx, s.P(j, str(run[-1]))[1]))
        ym = s.P(j, "11")[1]
        s.w("GND", (gx, ym), (gx - 2.54, ym))
        s.power("GND", gx - 2.54, ym, 270, show=False)
        for p in range(1, 35):
            net = nets[str(p)]
            px, py = s.P(j, str(p))
            left = px < x
            if p in run:
                continue
            if net == "GND":
                s.w("GND", (px, py), (px - 2.54 if left else px + 2.54, py))
                s.power("GND", px - 2.54 if left else px + 2.54, py, 270 if left else 90, show=False)
            elif net in ("+3V3_OUT", "+5V_OUT", "VIN_EXT"):
                qx = px - 12.7 if left else px + 12.7
                s.w(net, (px, py), (qx, py))
                s.glabel(net, qx, py, 180 if left else 0, "passive", f"{j}-{p}")
            else:                                            # second of two adjacent global labels: further out
                qx = px + (27.94 if net in ("SHIELD_SDA", "SHIELD_PRESENT_N") else 5.08)
                s.w(net, (px, py), (qx, py))
                end(net, qx, py, 0, j)

    header("J10", 330.2, 88.9)
    header("J11", 330.2, 177.8)
    s.text("J10 J_SHIELD_IO: IO n on pin 2n + 2,\nbetween two grounds. 33-34 ground.", 307.34, 116.84)
    s.text("J11 J_SHIELD_SVC: services, then +3V3_OUT,\n+5V_OUT (0.5 A per pin), VIN_EXT into the probe.",
           307.34, 205.74)


def shield_supply(prj):
    s = prj.sheet("Shield supply", "shield_supply.kicad_sch",
                  "Shield supply: eFuses and INA226 monitors")
    s.text("SHIELD SUPPLY", 20.32, 17.78, 2.54, True)
    s.text("Two limits: the eFuse ceiling set by ILM (2.04 A, 1.04 A, ±7.5 %), and the firmware budget from the "
           "INA226 below it (EN dropped on overrun).\nOvercurrent is limited, not flagged: FLT goes low on thermal "
           "shutdown only, then the eFuse retries on its own.\n3V3_OUT comes on with SHIELD_PRESENT_N (ID EEPROM), "
           "5V_OUT after a valid descriptor. Enables pulled low: off in reset and bootloader.",
           20.32, 25.4)
    x0 = 40.64
    rails = (("U38", "U39", "+5V", "SH5V_RAW", "+5V_OUT", "5V", "R106", "R105", "C105", "R107", "R108", "C106",
              "C107", "C108", 81.28, "Address 0x40 (A1 = A0 = GND)"),
             ("U40", "U41", "+3V3_AUX", "SH3V3_RAW", "+3V3_OUT", "3V3", "R110", "R109", "C109", "R111", "R112",
              "C110", "C111", "C112", 182.88, "Address 0x44 (A1 = VS, A0 = GND)"))
    for u, ina, src, raw, out, tag, rilm, rs, cdv, ren, rflt, cin, cout, cina, uy, addr in rails:
        ux = 101.6
        s.place(u, ux, uy, ref_at=(ux - 10.16, uy - 15.24), val_at=(ux - 10.16, uy - 12.7))
        # --- input: source row on top, bus down to the two IN pins ---
        yt, xb = uy - 17.78, ux - 20.32
        s.rail(src, x0, yt)
        s.w(src, (x0, yt), (xb, yt), (xb, uy - 5.08))
        for pin in ("3", "4"):
            px, py = s.P(u, pin)
            s.w(src, (px, py), (xb, py))
        s.w(src, (x0 + 12.7, yt), (x0 + 12.7, yt + 2.54))
        vpart(s, cin, x0 + 12.7, yt + 2.54)
        s.rail("GND", *s.P(cin, 2))
        # --- enable (pulled low), dVdt capacitor, ground pins ---
        en = f"EFUSE_{tag}_EN"
        ex, ey = s.P(u, 2)
        s.glabel(en, x0, ey, 180, "input")
        s.w(en, (x0, ey), (ex, ey))
        s.w(en, (x0 + 7.62, ey), (x0 + 7.62, ey + 2.54))
        vpart(s, ren, x0 + 7.62, ey + 2.54)
        s.rail("GND", *s.P(ren, 2))
        dx, dy = s.P(u, 1)
        s.w(f"EFUSE_{tag}_DVDT", (dx, dy), (dx - 10.16, dy))
        vpart(s, cdv, dx - 10.16, dy)
        s.label(f"EFUSE_{tag}_DVDT", dx - 10.16, dy, 180)
        s.rail("GND", *s.P(cdv, 2))
        for pin in ("8", "9"):
            s.rail("GND", *s.P(u, pin))
        # --- current limit resistor, fault line with its pull-up ---
        lx, ly = s.P(u, 7)
        s.w(f"EFUSE_{tag}_ILM", (lx, ly), (lx + 5.08, ly))
        vpart(s, rilm, lx + 5.08, ly)
        s.rail("GND", *s.P(rilm, 2))
        flt = f"EFUSE_{tag}_FLT"
        fx, fy = s.P(u, 6)
        s.w(flt, (fx, fy), (ux + 40.64, fy))
        s.glabel(flt, ux + 40.64, fy, 0, "output")
        vpart(s, rflt, ux + 25.4, fy - 7.62)
        s.rail("+3V3", *s.P(rflt, 1))
        # --- output: raised row, shunt, output capacitor, global label ---
        ox, oy = s.P(u, 5)
        yo, xs, xe = uy - 17.78, ux + 50.8, ux + 127.0
        s.w(raw, (ox, oy), (ox + 2.54, oy), (ox + 2.54, yo))
        s.place(rs, xs, yo, rot=90, ref_at=(xs - 2.54, yo - 3.81), val_at=(xs + 2.54, yo - 3.81))
        s.w(raw, (ox + 2.54, yo), s.P(rs, 1))
        s.label(raw, ox + 12.7, yo, 0)
        xc, xB = xs + 15.24, xs + 25.4
        s.w(out, s.P(rs, 2), (xc, yo), (xB, yo), (xe, yo))
        s.glabel(out, xe, yo, 0, "output")
        s.w(out, (xc, yo), (xc, yo + 2.54))
        vpart(s, cout, xc, yo + 2.54)
        s.rail("GND", *s.P(cout, 2))
        ina_monitor(s, ina, cina, raw, out, ux + 96.52, uy + 20.32, xB, yo, addr)


def ina_monitor(s, ina, cina, raw, out, xi, yi, xB, yo, addr):
    """INA226 at (xi, yi): Vbus tapped on the output row at xB, Kelvin sense across the shunt, I2C5 out."""
    s.place(ina, xi, yi, ref_at=(xi + 5.08, yi + 15.24), val_at=(xi + 5.08, yi + 17.78))
    bx, by = s.P(ina, 8)
    s.w(out, (bx, by), (xB, by), (xB, yo))
    for pin, net in (("10", raw), ("9", out)):
        px, py = s.P(ina, pin)
        s.w(net, (px, py), (px - 7.62, py))
        if net == out:
            s.glabel(net, px - 7.62, py, 180, "output", ina)
        else:
            s.label(net, px - 7.62, py, 180, ina)
    a1, a0 = s.prj.parts[ina]["pins"]["1"], s.prj.parts[ina]["pins"]["2"]
    vx, vy = s.P(ina, 6)
    yv = vy - 7.62
    xc = vx + (33.02 if a0 == "+3V3" else 22.86)   # clear of the A0 supply arrow
    s.w("+3V3", (vx, vy), (vx, yv), (xc, yv), (xc, yv + 2.54))
    s.rail("+3V3", vx, yv)
    vpart(s, cina, xc, yv + 2.54)
    s.rail("GND", *s.P(cina, 2))
    s.rail("GND", *s.P(ina, 7))
    (a1x, a1y), (a0x, a0y) = s.P(ina, 1), s.P(ina, 2)
    if a1 == "+3V3":
        s.w("+3V3", (a1x, a1y), (a1x + 2.54, a1y))
        s.rail("+3V3", a1x + 2.54, a1y)
    elif a0 == "GND":
        s.w("GND", (a1x, a1y), (a1x + 2.54, a1y), (a1x + 2.54, a0y))
    else:
        s.w("GND", (a1x, a1y), (a1x + 5.08, a1y))
        s.power("GND", a1x + 5.08, a1y, 90, show=False)
    if a0 == "+3V3":
        s.w("+3V3", (a0x, a0y), (a0x + 12.7, a0y))
        s.power("+3V3", a0x + 12.7, a0y, 270)
    else:
        s.w("GND", (a0x, a0y), (a0x + 5.08, a0y))
        s.power("GND", a0x + 5.08, a0y, 90, show=False)
    xg = xi + 35.56
    for pin, net, shape in (("4", "SYS_SDA", "bidirectional"), ("5", "SYS_SCL", "input"),
                            ("3", "INA_ALERT", "output")):
        px, py = s.P(ina, pin)
        s.w(net, (px, py), (xg, py))
        s.glabel(net, xg, py, 0, shape, ina)
    s.text(addr, xi - 7.62, yi + 22.86)


def local_bus(prj):
    s = prj.sheet("Local bus", "local_bus.kicad_sch",
                  "Local bus: IDC 2 x 17 ribbon to the Bornier modules, +3V3_BUS and VIN_BUS switches")
    s.text("LOCAL BUS", 20.32, 17.78, 2.54, True)
    s.text("Ribbon to the Bornier extension modules, pinout and terminations identical to Bornier. SPI2 at 8 MHz, "
           "mode 0; CS0-CS11 shifted by each module;\nLATCH on TIM2_CH1; OE active low. Series 49.9 Ω at the source "
           "(RB_: ribbon side); pulls keep every line defined while the MCU pins are not configured.",
           20.32, 25.4)
    parts = prj.parts

    def on(net, prefix, value=None):
        return sorted((r for r in parts if r.startswith(prefix) and net in parts[r]["pins"].values()
                       and (value is None or parts[r]["value"] == value)), key=lambda r: int(r[1:]))

    # --- signal rows: global label, pull, series 49.9 Ω, ribbon-side label ---
    series = [f"CS{i}" for i in range(12)] + ["LATCH", "OE", "SCK", "MOSI"]
    rows = series + ["IRQ", "SDA", "SCL", "MISO"]
    y0, pitch = 50.8, 5.08
    for k, sig in enumerate(rows):
        y = y0 + pitch * k
        net = f"BUS_{sig}"
        shape = "output" if sig in ("MISO", "IRQ") else "bidirectional" if sig == "SDA" else "input"
        end = 76.2 if sig in series else 50.8
        s.w(net, (40.64, y), (end, y))
        s.glabel(net, 40.64, y, 180, shape)
        pull = next(r for r in on(net, "R") if parts[r]["value"] != "49.9")
        kind = "GND" if "GND" in parts[pull]["pins"].values() else "+3V3"
        s.place(pull, 57.15, y + 2.54, rot=90, show_ref=False, show_value=False)
        s.w(net, (50.8, y), (50.8, y + 2.54), s.P(pull, 1))
        s.power(kind, *s.P(pull, 2), 270 if kind == "+3V3" else 90, show=False)
        if sig in series:
            r1, *r2 = on(net, "R", "49.9")
            s.place(r1, 80.01, y, rot=90, show_ref=False, show_value=False)
            s.w(f"RB_{sig}", s.P(r1, 2), (93.98, y))
            if r2:                                              # SCK, MOSI, LATCH: 2 x 49.9 in parallel
                s.place(r2[0], 80.01, y + 2.54, rot=90, show_ref=False, show_value=False)
                s.w(net, (76.2, y), s.P(r2[0], 1))
                s.w(f"RB_{sig}", s.P(r1, 2), s.P(r2[0], 2))
            s.label(f"RB_{sig}", 93.98, y)
    s.text("Pull-ups 10 kΩ to +3V3 on CS0-CS11, LATCH, OE, IRQ (R135-R148, R168);\n"
           "2 kΩ on SDA, SCL (R172-R173). Pull-downs 100 kΩ on SCK, MOSI, MISO\n"
           "(R169-R171): SPI mode 0 idle; MISO tri-stated with no module selected.\n"
           "Series 49.9 Ω R149-R164; SCK, MOSI, LATCH: second 49.9 Ω in parallel\n"
           "(R165-R167), 25 Ω for the multipoint edges.", 20.32, y0 + pitch * len(rows) + 2.54)

    # --- ESD, flow-through at the header ---
    esds = sorted((u for u in parts if parts[u]["value"] == "TPD4E05U06DQAR" and int(u[1:]) >= 47),
                  key=lambda u: int(u[1:]))
    s.text("ESD of every ribbon line\nat the header (TPD4E05U06).", 134.62, 48.26)
    for k, u in enumerate(esds):
        ex, ey = 147.32, 66.04 + 30.48 * k
        s.place(u, ex, ey, ref_at=(ex + 6.35, ey + 12.7), val_at=(ex + 6.35, ey + 15.24))
        for pin in ("1", "2", "4", "5"):
            px, py = s.P(u, pin)
            net = parts[u]["pins"][pin]
            qx = px - 5.08 if px < ex else px + 5.08
            s.w(net, (px, py), (qx, py))
            rot = 180 if qx < px else 0
            if net.startswith("BUS_"):
                s.glabel(net, qx, py, rot, "bidirectional", u)
            else:
                s.label(net, qx, py, rot, u)
        s.rail("GND", *s.P(u, "3"))

    # --- header ---
    j, jx, jy = "J12", 218.44, 109.22
    s.place(j, jx, jy, ref_at=(jx - 2.54, jy - 29.21), val_at=(jx - 2.54, jy - 26.67))
    for p, net in parts[j]["pins"].items():
        px, py = s.P(j, p)
        left = px < jx
        d = -7.62 if left else 7.62
        if net == "GND":
            s.w(net, (px, py), (px + d / 3, py))
            s.power("GND", px + d / 3, py, 270 if left else 90, show=False)
        elif net.startswith("BUS_"):
            s.w(net, (px, py), (px + d, py))
            s.glabel(net, px + d, py, 180 if left else 0, "bidirectional", j)
        else:
            s.w(net, (px, py), (px + d, py))
            s.label(net, px + d, py, 180 if left else 0, j)
    s.text("Ribbon conductor n = pin n. CS0-CS11 on pins 1-12; every other\nline on an even pin facing a ground; "
           "+VIN_BUS1/2 on pins 33-34,\ntheir only neighbour a ground (pin 32).", jx - 20.32, jy + 27.94)

    # --- +3V3_BUS: TPS2553 ---
    ux, uy, x0 = 294.64, 71.12, 251.46
    s.text("+3V3_BUS: TPS2553, 505-616 mA limit; FAULT low (LED on) while in current limit.\n"
           "EN pulled low: off in reset and bootloader. A short leaves the probe +3V3 up.", x0, 40.64)
    s.place("U44", ux, uy, ref_at=(ux - 10.16, uy - 8.89), val_at=(ux - 10.16, uy + 10.16))
    ix, iy = s.P("U44", 1)
    yr = iy - 10.16
    s.w("+3V3", (ix, iy), (ix - 5.08, iy), (ix - 5.08, yr), (x0 + 12.7, yr))
    s.rail("+3V3", x0 + 12.7, yr)
    s.w("+3V3", (ix - 15.24, yr), (ix - 15.24, yr + 2.54))
    vpart(s, "C127", ix - 15.24, yr + 2.54)
    s.rail("GND", *s.P("C127", 2))
    ex, ey = s.P("U44", 3)
    s.glabel("BUS_3V3_EN", x0, ey, 180, "input")
    s.w("BUS_3V3_EN", (x0, ey), (ex, ey))
    s.w("BUS_3V3_EN", (x0 + 10.16, ey), (x0 + 10.16, ey + 2.54))
    vpart(s, "R128", x0 + 10.16, ey + 2.54)
    s.rail("GND", *s.P("R128", 2))
    s.rail("GND", *s.P("U44", 2))
    lx, ly = s.P("U44", 5)
    s.w("U44_ILIM", (lx, ly), (lx + 5.08, ly), (lx + 5.08, ly + 2.54))
    vpart(s, "R127", lx + 5.08, ly + 2.54)
    s.rail("GND", *s.P("R127", 2))
    fx, fy = s.P("U44", 4)
    s.w("BUS_3V3_FLT", (fx, fy), (fx + 48.26, fy))
    s.glabel("BUS_3V3_FLT", fx + 48.26, fy, 0, "output")
    vpart(s, "R133", fx + 12.7, fy - 7.62)
    s.rail("+3V3", *s.P("R133", 1))
    xl = fx + 30.48
    s.place("D19", xl, fy - 3.81, rot=90, ref_at=(xl + 12.7, fy - 6.35), val_at=(xl + 12.7, fy - 3.81))
    vpart(s, "R134", xl, fy - 17.78)
    s.w("U44_LED", s.P("R134", 2), s.P("D19", 2))
    s.rail("+3V3", *s.P("R134", 1))
    ox, oy = s.P("U44", 6)
    yo = fy - 27.94
    s.w("+3V3_BUS", (ox, oy), (ox + 2.54, oy), (ox + 2.54, yo), (ox + 63.5, yo))
    s.label("+3V3_BUS", ox + 63.5, yo)
    s.w("+3V3_BUS", (ox + 50.8, yo), (ox + 50.8, yo + 2.54))
    vpart(s, "C128", ox + 50.8, yo + 2.54)
    s.rail("GND", *s.P("C128", 2))

    # --- +VIN_BUS1, +VIN_BUS2: TPS27S100B ---
    s.text("+VIN_BUS1, +VIN_BUS2: VIN_BUS on ribbon pins 33 and 34, one TPS27S100B per pin, 525 mA limit\n"
           "(4.7 kΩ, TI minimum 0.5 A), auto-retry. DIAG_EN high: IMON and protections always on.\n"
           "IMON = I/500 from each switch, joined on one 2 kΩ load; half to PF7: 0.96 A -> 1.92 V, fault 2.15-2.45 V.",
           x0, 106.68)
    for u, out, en, rl, cin, cout, uy in (("U45", "+VIN_BUS1", "VIN_BUS1_EN", "R129", "C129", "C130", 142.24),
                                          ("U46", "+VIN_BUS2", "VIN_BUS2_EN", "R130", "C131", "C132", 205.74)):
        s.place(u, ux, uy, ref_at=(ux + 2.54, uy + 15.24), val_at=(ux + 2.54, uy + 17.78))
        yt = uy - 15.24
        xb = s.P(u, 9)[0] - 5.08
        for p in (9, 10, 11, 12):
            s.w("VIN_BUS", s.P(u, p), (xb, s.P(u, p)[1]))
        s.w("VIN_BUS", (xb, s.P(u, 12)[1]), (xb, yt), (x0, yt))
        s.glabel("VIN_BUS", x0, yt, 180, "input", u)
        s.w("VIN_BUS", (xb - 12.7, yt), (xb - 12.7, yt + 2.54))
        vpart(s, cin, xb - 12.7, yt + 2.54)
        s.rail("GND", *s.P(cin, 2))
        ex, ey = s.P(u, 3)
        s.glabel(en, x0, ey, 180, "input")
        s.w(en, (x0, ey), (ex, ey))
        dx, dy = s.P(u, 14)
        s.w("+3V3", (dx, dy), (dx - 7.62, dy))
        s.power("+3V3", dx - 7.62, dy, 90)
        s.rail("GND", *s.P(u, 2))
        s.rail("GND", *s.P(u, 17))
        xo = s.P(u, 5)[0] + 5.08
        for p in (5, 6, 7, 8):
            s.w(out, s.P(u, p), (xo, s.P(u, p)[1]))
        s.w(out, (xo, s.P(u, 8)[1]), (xo, yt), (xo + 45.72, yt))
        s.label(out, xo + 45.72, yt)
        s.w(out, (xo + 15.24, yt), (xo + 15.24, yt + 2.54))
        vpart(s, cout, xo + 15.24, yt + 2.54)
        s.rail("GND", *s.P(cout, 2))
        lx, ly = s.P(u, 15)
        s.w(f"{u}_ILIM", (lx, ly), (lx + 7.62, ly), (lx + 7.62, ly + 2.54))
        vpart(s, rl, lx + 7.62, ly + 2.54)
        s.rail("GND", *s.P(rl, 2))
        mx, my = s.P(u, 16)
        if u == "U45":
            s.w("VIN_BUS_IMON_RAW", (mx, my), (mx + 20.32, my))
            s.label("VIN_BUS_IMON_RAW", mx + 20.32, my, 0)
        else:
            s.w("VIN_BUS_IMON_RAW", (mx, my), (mx + 55.88, my))
            s.label("VIN_BUS_IMON_RAW", mx + 20.32, my, 0, u)
            sense(s, "R131", "R132", "C133", "VIN_BUS_IMON_RAW", "VIN_BUS_IMON", mx + 55.88, my)


def main():
    os.makedirs(KICAD, exist_ok=True)
    pro = os.path.join(KICAD, "archet.kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w", encoding="utf-8", newline="\n") as f:
            f.write('{"meta": {"filename": "archet.kicad_pro", "version": 3}}\n')
    prj = Project("archet", c, "Archet debug probe", "2026-11-26", libs=symbols.write())
    oring(prj)
    usbc(prj)
    poe(prj)
    buck5(prj)
    boost(prj)
    buck3v3(prj)
    mcu(prj)
    fpga(prj)
    ulpi(prj)
    rmii(prj)
    target(prj)
    tgt_supply(prj)
    ui_field(prj)
    shield(prj)
    shield_supply(prj)
    local_bus(prj)
    footprints.write()
    sch, ok = prj.write(KICAD)
    print(f"{len(c.parts)} parts -> {sch}")
    if not ok:
        print("drawing errors: fix them before checking")
        return 1
    return check(c, sch, PENDING_ERC, WAIVED_ERC, fp_libs={"Archet": os.path.join(KICAD, "archet.pretty")})


if __name__ == "__main__":
    sys.exit(main())
