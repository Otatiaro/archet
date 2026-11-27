# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Archet probe: board rules, net classes and custom DRC rules.

Writes the net classes and board minimums into ../kicad/archet.kicad_pro, and ../kicad/archet.kicad_dru.
Run with KiCad's Python, cwd = gen. Every value is justified below against the real voltages and currents
(docs/architecture.md, Power) and the JLCPCB 4-layer process (JLC04161H-7628, docs/architecture.md, Board).

The router (Cordeau) reads the classes from the .kicad_pro and, from the .kicad_dru, clearance,
hole_clearance, via_diameter, hole_size and track_width rules on NetName / Type / Reference / memberOfFootprint.
It refuses NetClass, inDiffPair, fromTo and Layer conditions, and a net in two classes: each net gets one
class here, by its exact name, and the PoE barrier is written on net names.

Report: the pads narrower than the track width of their class. The router lays every track of a net at the
class width and does not neck down at a pad: such a net needs a copper zone, or a narrower class.
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import circuit as c  # noqa: E402

KICAD = os.path.join(HERE, "..", "kicad")
PRO = os.path.join(KICAD, "archet.kicad_pro")
DRU = os.path.join(KICAD, "archet.kicad_dru")
SCH = os.path.join(KICAD, "archet.kicad_sch")
KICAD_BIN = os.path.dirname(sys.executable)
SYS_FP = os.path.join(KICAD_BIN, "..", "share", "kicad", "footprints")
LOC_FP = os.path.join(KICAD, "archet.pretty")


# --------------------------------------------------------------------------------------------
# Process and stack-up
#
# JLC04161H-3313: 1.6 mm, outer 1 oz (35 µm + plating), inner 0.5 oz, L1-L2 prepreg 3313 0.0994 mm, er 4.1.
# Chosen over 7628 (0.2104 mm), where 50 Ω takes 0.35 mm: wider than the ULPI, QSPI and RMII pads (0.25-0.30 mm),
# and the router does not neck down at a pad.
# Impedance: Hammerstad-Jensen microstrip with thickness correction, edge-coupled approximation
# Zdiff = 2 Z0 (1 - 0.48 exp(-0.96 s / h)). To confirm with the JLCPCB impedance calculator before ordering.
#   50 Ω single:        w 0.16 mm
#   90 Ω differential:  w 0.155 mm, s 0.15 mm (USB 2.0 HS and FS)
#   100 Ω differential: w 0.125 mm, s 0.15 mm (Ethernet 100BASE-TX, PHY to magjack)
#
# Current: IPC-2221 external conductor, I = 0.048 ΔT^0.44 A^0.725 (A in mil²), 1 oz, ΔT 20 °C:
#   1 A 0.20 mm, 3 A 0.90 mm. Inner layers are 0.5 oz: twice the width; power stays on L1/L4 or in zones.
#
# Voltage: IPC-2221B table 6-1. Secondary side 24 V nominal, 38.9 V only during a TVS clamp:
#   B4 (under solder mask) 0.13 mm up to 100 V; B2 (bare, pads) 0.1 mm up to 30 V, 0.6 mm 31-100 V.
#   PoE primary 57 V continuous (93.6 V SMAJ58A clamp) and the field bus (THVD2450 ±70 V fault) take B2 0.6 mm.
#   PoE isolation barrier: 1500 Vrms (IEEE 802.3 clause 33.4.1, DP5700 rating), 2121 V peak; 2.0 mm, about
#   three times the breakdown distance of air, above the IEC 62368-1 creepage for 57 V working voltage.


def ipc2221_width(amps, dt=20.0, oz=1.0):
    """External conductor width (mm) for a current, IPC-2221 curve."""
    area_mil2 = (amps / (0.048 * dt ** 0.44)) ** (1 / 0.725)
    return area_mil2 / (1.378 * oz) * 0.0254


# Board minimums (KiCad checks them and the router raises every class to them): JLCPCB 4-layer capabilities.
RULES = {
    "min_clearance": 0.1,            # JLCPCB 4-layer 0.09 mm (3.5 mil)
    "min_track_width": 0.1,          # 0.09 mm
    "min_via_diameter": 0.45,        # 0.3 mm drill + 2 × 0.075 mm ring
    "min_via_annular_width": 0.075,
    "min_through_hole_diameter": 0.3,
    "min_hole_clearance": 0.2,       # hole to copper
    "min_hole_to_hole": 0.25,
    "min_copper_edge_clearance": 0.3,
}

# name: clearance, track width, via diameter, via drill, diff pair width, diff pair gap, why
CLASSES = {
    "Default": (0.15, 0.15, 0.5, 0.3, None, None,
                "Logic <= 5.5 V: B4 0.13 mm, fits the 0.5 mm pitch packages (LQFP-144, QFN, USB-C)"),
    "PWR_1A": (0.15, 0.2, 0.6, 0.3, None, None,
               f"Rails <= 1 A: IPC-2221 {ipc2221_width(1):.2f} mm at 1 A"),
    "PWR_3A": (0.2, 0.9, 0.8, 0.4, None, None,
               f"VSYS chain, USB VBUS, 5 V, switch nodes, <= 3 A: IPC-2221 {ipc2221_width(3):.2f} mm at 3 A; "
               "<= 24 V continuous (B2 0.1 mm), 0.2 mm for the 38.9 V clamp under mask"),
    "FIELD": (0.6, 0.25, 0.6, 0.3, None, None,
              "RS-485 / CAN field lines, ±70 V fault on the THVD2450 side: B2 0.6 mm"),
    "POE": (0.6, 0.5, 0.8, 0.4, None, None,
            "PoE primary 57 V (93.6 V clamp): B2 0.6 mm; class 4, 0.6 A per pair: 0.5 mm. Barrier in the .kicad_dru"),
    "USB_90R": (0.15, 0.155, 0.5, 0.3, 0.155, 0.15, "USB 2.0 HS/FS 90 Ω differential"),
    "ETH_100R": (0.15, 0.125, 0.5, 0.3, 0.125, 0.15, "100BASE-TX 100 Ω differential, PHY to magjack"),
    "SE_50R": (0.15, 0.16, 0.5, 0.3, None, None,
               "50 Ω single-ended: ULPI 60 MHz, QSPI to the FPGA and the NAND, RMII and PHY clocks"),
}

PWR_1A = ["+1V2", "+1V8", "+3V3", "+3V3_AUX", "+3V3_BUS", "+3V3_OUT", "SH3V3_RAW", "+VIN_BUS1", "+VIN_BUS2",
          "TGT_VCC", "TGT_VSUP", "TGT_VSUP_REG", "TGSUP_L1", "TGSUP_L2", "VDDA", "VCCPLL", "J6_VCC", "B3V3A_SW"]
PWR_3A = ["VIN_EXT", "VIN_EXT_P", "VSYS_OR", "VSYS", "VBUS_CONN", "VBUS_USB", "VBUS_HS_CONN", "VBUS_HS",
          "POE_12V", "VIN_BUS", "+5V", "+5V_OUT", "SH5V_RAW", "BUCK5_SW", "B3V3_SW", "BOOST_SW", "BOOST_ISNS"]
FIELD = ["FIELD_H", "FIELD_L", "FIELD_TERM"]
# Primary side of the DP5700: everything ahead of its isolation (bridges, TVS, TYP2-DET opto LED)
POE = ["POE_DA", "POE_DB", "POE_SA", "POE_SB", "POE_VP", "POE_VN", "POE_TYP2", "POE_OPTO_A"]
USB_90R = ["USB_C_DP", "USB_C_DM", "USB_FS_DP", "USB_FS_DM", "HS_C_DP", "HS_C_DM", "USB_DP", "USB_DM"]
ETH_100R = ["ETH_TXP", "ETH_TXN", "ETH_RXP", "ETH_RXN"]
SE_50R = (["ULPI_CK", "ULPI_DIR", "ULPI_NXT", "ULPI_STP"] + [f"ULPI_D{i}" for i in range(8)]
          + ["FPGA_QSPI_CLK", "FPGA_QSPI_NCS"] + [f"FPGA_QSPI_IO{i}" for i in range(4)]
          + ["FLASH_CLK", "FLASH_NCS"] + [f"FLASH_IO{i}" for i in range(4)]
          + ["RMII_REF_CLK", "RMII_CRS_DV", "RMII_TX_EN", "RMII_TXD0", "RMII_TXD1", "RMII_RXD0", "RMII_RXD1",
             "PHY_REFCLK", "FPGA_REFCLK"])
ASSIGN = {"PWR_1A": PWR_1A, "PWR_3A": PWR_3A, "FIELD": FIELD, "POE": POE, "USB_90R": USB_90R,
          "ETH_100R": ETH_100R, "SE_50R": SE_50R}

# Footprints whose own pads sit closer than the PoE barrier: the manufacturer's geometry (magjack, PD module)
BARRIER_PARTS = ["J3", "U6"]
BARRIER = 2.0


def kicad_names():
    """Circuit net name -> net name in the KiCad netlist (local nets carry their sheet path)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "archet.net")
        subprocess.run([os.path.join(KICAD_BIN, "kicad-cli.exe"), "sch", "export", "netlist",
                        "--format", "kicadsexpr", "-o", out, SCH], check=True, capture_output=True)
        with open(out, encoding="utf-8") as f:
            text = f.read()
    # Map by pin, not by name: a net without a label gets an automatic KiCad name.
    node = {}
    for name, body in re.findall(r'\(net\s+\(code "?\d+"?\)\s+\(name "([^"]*)"\)(.*?)(?=\(net\s+\(code|\Z)', text, re.S):
        for ref, pin in re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', body):
            node[(ref, pin)] = name
    by_base = {}
    for p in c.c.parts:
        for pin, n in p["pins"].items():
            full = node.get((p["ref"], str(pin)))
            if n and full and full not in by_base.setdefault(n, []):
                by_base[n].append(full)
    return by_base


def template():
    """The project file as KiCad writes it: KiCad ignores an incomplete rules block and rewrites it."""
    with open(PRO, encoding="utf-8") as f:
        pro = json.load(f)
    if "board" in pro:
        return pro
    with tempfile.TemporaryDirectory() as tmp:
        pcb = os.path.join(tmp, "archet.kicad_pcb")
        pcbnew.SaveBoard(pcb, pcbnew.NewBoard(pcb))
        with open(os.path.join(tmp, "archet.kicad_pro"), encoding="utf-8") as f:
            full = json.load(f)
    full.update({k: v for k, v in pro.items() if k != "meta"})
    return full


def write_pro(by_base):
    pro = template()
    rules = pro["board"]["design_settings"]["rules"]
    rules.update(RULES)
    ns = pro["net_settings"]
    base = next(k for k in ns["classes"] if k["name"] == "Default")
    classes = []
    for prio, (name, (clr, w, vd, vdr, dpw, dpg, _)) in enumerate(CLASSES.items()):
        k = dict(base)
        k.update(name=name, clearance=clr, track_width=w, via_diameter=vd, via_drill=vdr,
                 priority=2147483647 if name == "Default" else prio)
        if dpw:
            k.update(diff_pair_width=dpw, diff_pair_gap=dpg, diff_pair_via_gap=dpg)
        classes.append(k)
    ns["classes"] = [classes[0]] + sorted(classes[1:], key=lambda k: k["name"])
    patterns = []
    for cls, nets in ASSIGN.items():
        for n in nets:
            for full in by_base[n]:
                patterns.append({"netclass": cls, "pattern": full})
    ns["netclass_patterns"] = sorted(patterns, key=lambda p: p["pattern"])
    with open(PRO, "w", encoding="utf-8", newline="\n") as f:
        json.dump(pro, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    return len(patterns)


def any_of(side, names, op="==", join="||"):
    return "(" + f" {join} ".join(f"{side}.NetName {op} '{n}'" for n in names) + ")"


def write_dru(by_base):
    prim = [full for n in POE for full in by_base[n]]
    own = " || ".join(f"A.memberOfFootprint('{r}') && B.memberOfFootprint('{r}')" for r in BARRIER_PARTS)
    lines = [
        "(version 1)",
        "# Archet custom rules, generated by gen/netclasses.py: do not edit by hand.",
        "# Net classes (clearances, widths, impedances) live in archet.kicad_pro.",
        "",
        "# PoE isolation barrier: 1500 Vrms (IEEE 802.3 clause 33.4.1, DP5700 rating), 2121 V peak.",
        f"# {BARRIER} mm between the primary nets and everything else, zones included.",
        '(rule "PoE barrier"',
        f"  (constraint clearance (min {BARRIER}mm))",
        f'  (condition "{any_of("A", prim)} && {any_of("B", prim, "!=", "&&")}"))',
        "",
        "# The magjack and the PD module carry both sides on their own pads: their geometry is the manufacturer's.",
        "# Pad to pad only (both items in the footprint); tracks keep the barrier.",
        '(rule "Barrier parts, own pads"',
        f"  (constraint clearance (min {RULES['min_clearance']}mm))",
        f'  (condition "{own}"))',
        "",
    ]
    with open(DRU, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def narrow_pads():
    """(net, class width, ref.pad, pad width) where the pad is narrower than the class track."""
    width = {n: CLASSES[cls][1] for cls, nets in ASSIGN.items() for n in nets}
    cache, out = {}, []
    for p in c.c.parts:
        nets = {str(k): n for k, n in p["pins"].items() if n in width}
        if not nets:
            continue
        if p["fp"] not in cache:
            lib, name = p["fp"].split(":", 1)
            path = LOC_FP if lib == "Archet" else os.path.join(SYS_FP, lib + ".pretty")
            cache[p["fp"]] = pcbnew.FootprintLoad(path, name)
        fp = cache[p["fp"]]
        if fp is None:
            continue
        for pad in fp.Pads():
            n = nets.get(pad.GetNumber())
            if n is None:
                continue
            size = pad.GetSize(pcbnew.F_Cu) if hasattr(pad, "GetSize") else pad.GetSize()
            w = min(size.x, size.y) / 1e6
            if w + 1e-6 < width[n]:
                out.append((n, width[n], f"{p['ref']}.{pad.GetNumber()}", w))
    return sorted(set(out))


def main():
    by_base = kicad_names()
    missing = [n for nets in ASSIGN.values() for n in nets if n not in by_base]
    twice = [n for n in by_base if sum(n in nets for nets in ASSIGN.values()) > 1]
    if missing or twice:
        sys.exit(f"unknown nets {missing}, nets in two classes {twice}")
    count = write_pro(by_base)
    write_dru(by_base)
    print(f"{len(CLASSES)} classes, {count} nets assigned, rules written")
    for cls, (clr, w, vd, vdr, dpw, dpg, why) in CLASSES.items():
        print(f"  {cls:9s} clr {clr:<5} w {w:<5} via {vd}/{vdr}  {why}")
    narrow = narrow_pads()
    if narrow:
        print(f"{len(narrow)} pads narrower than their class track (zone or neck-down needed):")
        by_net = {}
        for n, w, pad, pw in narrow:
            by_net.setdefault((n, w), []).append(f"{pad} {pw:.2f}")
        for (n, w), pads in sorted(by_net.items()):
            print(f"  {n} ({w} mm): {', '.join(pads[:8])}{' ...' if len(pads) > 8 else ''}")


if __name__ == "__main__":
    main()
