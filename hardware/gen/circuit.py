# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Archet probe: reference circuit (parts, values, footprints, LCSC codes, connections).

Single source of the schematic: schematic.py draws it, kicadgen.check proves the drawing matches.
Design rationale: docs/architecture.md. Pin assignments: hardware/*.csv.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from kicadgen.circuit import Circuit, C0402, C0603, C0805, R0402  # noqa: E402,F401

C1210 = "Capacitor_SMD:C_1210_3225Metric"
SMB = "Diode_SMD:D_SMB"

# Passive palette: every resistor and capacitor of the board is one of these lines (one feeder each
# on the pick-and-place). JLCPCB basic parts; 0402 by default.
PALETTE = {
    ("R", "10k", R0402): "C25744",
    ("R", "100k", R0402): "C25741",
    ("C", "100nF", C0402): "C307331",      # 50 V X7R
    ("C", "1µF 50V", C0603): "C15849",
}

c = Circuit(PALETTE, r_fp=R0402, c_fp=C0402)

# One 60 V logic-level N-MOS for the three ideal diodes and the VIN_BUS boost: one extended part.
NMOS = ("Transistor_FET:CSD18543Q3A", "CSD18543Q3A", "Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET", "C840100")
IDEAL = ("Power_Management:LM74700", "LM74700QDBVRQ1", "Package_TO_SOT_SMD:SOT-23-6", "C2941042")


def ideal_diode(n, src, ctl, fet, cap, cin, note):
    """LM74700 + N-MOS from `src` to VSYS: source = anode (input), drain = cathode (VSYS).
    EN tied to the anode (always on); charge pump capacitor between VCAP and ANODE (datasheet §9.2)."""
    c.part(fet, NMOS[0], NMOS[1], NMOS[2], NMOS[3], {1: src, 2: src, 3: src, 4: f"GATE{n}", 5: "VSYS"},
           f"Ideal diode {n} switch; 60 V, 8.1 mΩ at 10 V: 73 mW at 3 A")
    c.part(ctl, IDEAL[0], IDEAL[1], IDEAL[2], IDEAL[3],
           {1: f"VCAP{n}", 2: "GND", 3: src, 4: "VSYS", 5: f"GATE{n}", 6: src}, note)
    c.C(cap, "100nF", src, f"VCAP{n}", note="Charge pump, 0.1 µF minimum between VCAP and ANODE")
    c.C(cin, "1µF 50V", src, "GND", note="Local decoupling of the source cable")


def sense(rt, rb, cf, net, out):
    """ADC divider 100k / 10k: 24 V -> 2.18 V, 38.9 V (TVS clamp) -> 3.54 V through 100 k (35 µA)."""
    c.R(rt, "100k", net, out)
    c.R(rb, "10k", out, "GND")
    c.C(cf, "100nF", out, "GND", note="ADC sampling reservoir, 1.1 ms time constant")


# --------------------------------------------------------------------------------------------
c.block("Source OR-ing: VIN_EXT, USB-C VBUS, PoE 12 V into VSYS")
c.part("J1", "Connector:Screw_Terminal_01x02", "VIN_EXT",
       "Connector_Phoenix_MC:PhoenixContact_MC_1,5_2-G-3.81_1x02_P3.81mm_Horizontal", "C441182",
       {1: "VIN_EXT", 2: "GND"}, "KF2EDGR-3.81-2P pluggable header, 8 A (plug KF2EDGK-3.81-2P, C440858); "
       "pole 1 +10.8-24 V, pole 2 0 V")
c.part("F1", "Device:Fuse", "5A 63V", "Fuse:Fuse_1206_3216Metric", "C2980745", {1: "VIN_EXT", 2: "VIN_EXT_P"},
       "12H1500C fast acting, 50 A breaking; worst case ~3 A at 10.8 V (probe, target, 11.5 W shield, VIN_BUS)")
c.part("D1", "Device:D_TVS", "SMBJ24CA", SMB, "C78416", {1: "GND", 2: "VIN_EXT_P"},
       "Bidirectional: 24 V standoff, 26.7 V breakdown, 38.9 V clamp; a reversed supply only meets the "
       "LM74700 (-65 V) and the VIN_BUS Schottky")
ideal_diode(1, "VIN_EXT_P", "U1", "Q1", "C1", "C2", "Ideal diode, VIN_EXT")
ideal_diode(2, "VBUS_USB", "U2", "Q2", "C3", "C4", "Ideal diode, USB-C VBUS after the PD sink switch")
ideal_diode(3, "POE_12V", "U3", "Q3", "C5", "C6", "Ideal diode, PoE module 12 V output")
c.part("C7", "Device:C_Polarized", "47µF 63V", "Capacitor_SMD:CP_Elec_6.3x7.7", "C46550423",
       {1: "VSYS", 2: "GND"}, "Damps the hot-plug ringing of the cables and the ceramics")
c.C("C8", "1µF 50V", "VSYS", "GND")
sense("R1", "R2", "C9", "VIN_EXT_P", "VIN_EXT_SENSE")
sense("R3", "R4", "C10", "VBUS_USB", "VBUS_USB_SENSE")
sense("R5", "R6", "C11", "POE_12V", "POE_12V_SENSE")
sense("R7", "R8", "C12", "VSYS", "VSYS_SENSE")
