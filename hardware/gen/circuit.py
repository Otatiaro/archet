# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Archet probe: reference circuit (parts, values, footprints, LCSC codes, connections).

Single source of the schematic: schematic.py draws it, kicadgen.check proves the drawing matches.
Design rationale: docs/architecture.md. Pin assignments: hardware/*.csv.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from kicadgen.circuit import Circuit, C0402, C0603, C0805, R0402  # noqa: E402,F401
from kicadgen.kicad import Libraries, pin_names  # noqa: E402

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

C1210 = "Capacitor_SMD:C_1210_3225Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"
R0805 = "Resistor_SMD:R_0805_2012Metric"
R1206 = "Resistor_SMD:R_1206_3216Metric"
R0603 = "Resistor_SMD:R_0603_1608Metric"
SMB = "Diode_SMD:D_SMB"

# Passive palette: every resistor and capacitor of the board is one of these lines (one feeder each
# on the pick-and-place). JLCPCB basic parts; 0402 by default. Values are pooled to keep the line count low:
# a new value or size needs a reason (datasheet, simulation, rating).
PALETTE = {
    ("R", "10k", R0402): "C25744",
    ("R", "100k", R0402): "C25741",
    ("R", "1k", R0402): "C11702",
    ("R", "47k", R0805): "C17713",         # 150 V: on the 57 V PoE input
    ("R", "1k", R1206): "C4410",           # 250 mW: PoE module minimum load
    ("C", "100nF", C0402): "C307331",      # 50 V X7R
    ("C", "1µF 50V", C0603): "C15849",
    ("C", "10µF 25V", C0805): "C15850",
    ("C", "10µF 50V", C1206): "C13585",
    ("C", "22µF 25V", C1206): "C12891",
    ("R", "22k", R0402): "C25768",
    ("R", "5.1k", R0402): "C25905",        # 1 %: USB-C Rd (J5)
    ("C", "2.2µF", C0402): "C12530",       # 6.3 V X5R: VCAP (1.2 V)
    ("C", "15pF", C0402): "C1548",         # 50 V C0G
    ("R", "100", R0402): "C25076",         # VCCPLL filter
    ("R", "8.06k", R0402): "C25923",       # ext, 1 %: USB3320 RBIAS (value imposed by the datasheet), LMR33630 FB top
    ("R", "1M", R0402): "C26083",          # USB3320 crystal bias
    ("R", "12.1k", R0402): "C25852",       # ext, 1 %: LAN8742A RBIAS (value imposed by the datasheet)
    ("R", "49.9", R0402): "C25120",        # 1 %: Ethernet line termination
    ("R", "33", R0402): "C25105",          # series termination: target lines, shield IOs
    ("C", "470pF", C0402): "C1537",        # preferred, X7R: LAN8742A VDDCR (datasheet 1 µF // 470 pF)
    ("R", "150k", R0402): "C25755",        # preferred: TPS63020 FB top
    ("R", "18k", R0402): "C25762",         # preferred: TPS63020 FB bottom
    ("R", "120k", R0402): "C25750",        # preferred: TPS63020 DAC injection (hardware/sim/tgt_vsup.py)
    ("R", "50m", R1206): "C844686",        # ext, Vishay WSL1206R0500FEA 75 ppm/°C: INA226 shunts
    ("R", "22", R1206): "C17958",          # 250 mW: buzzer series resistor
    ("R", "120", R0402): "C25079",         # RJ45 LEDs
    ("R", "120", R0603): "C22787",         # 100 mW: field bus termination (75 mW with 3 V differential)
    ("R", "2k", R0402): "C4109",           # TPS2595 ILM: 1.04 A; I2C pull-ups; LMR33630 FB bottom
    ("R", "15m", R1206): "C844483",        # ext, Vishay WSL1206R0150FEA: boost sense, VSYS and 5V_OUT shunts
    ("R", "51k", R0402): "C25794",         # LM5155 RT: 425 kHz
    ("R", "47k", R0402): "C25792",
    ("R", "470", R0402): "C25117",         # LM5155 slope resistor
    ("R", "3.3k", R0402): "C25890",        # LM5155 compensation
    ("C", "22nF", C0402): "C1532",         # 50 V X7R: LM5155 soft start
    ("C", "100pF", C0402): "C1546",        # 50 V C0G: LM5155 CS filter
    ("R", "4.7k", R0402): "C25900",        # TPS27S100 ILIM: 525 mA
}

c = Circuit(PALETTE, r_fp=R0402, c_fp=C0402)

# One 60 V logic-level N-MOS for the five ideal diodes and the VIN_BUS boost: one extended part.
NMOS = ("Transistor_FET:CSD18543Q3A", "CSD18543Q3A", "Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET", "C840100")
# Wuxi Maxin Micro MX74700T: pin-compatible LM74700 (KiCad symbol and SOT-23-6 kept). Datasheet V10 (LCSC):
# ANODE -100/+100 V (-90/+90 V operating), CATHODE-ANODE -5/+75 V, V(AK REV) -17 mV max, tReverse 0.75 µs max,
# 2.37 A gate sink: the LM74700 figures sim/oring.py was built on. 0.41 $ against 2.61 $ (2026-11-27).
IDEAL = ("Power_Management:LM74700", "MX74700T", "Package_TO_SOT_SMD:SOT-23-6", "C22468156")
SCHOTTKY = ("Device:D_Schottky", "1N5819WS", "Diode_SMD:D_SOD-323", "C191023")  # pin 1 = cathode


def ideal_diode(n, src, ctl, fet, cap, cin, note, out="VSYS_OR"):
    """MX74700T + N-MOS from `src` to `out`: source = anode (input), drain = cathode (output).
    EN tied to the anode (always on); charge pump capacitor between VCAP and ANODE (datasheet §9.2)."""
    c.part(fet, NMOS[0], NMOS[1], NMOS[2], NMOS[3], {1: src, 2: src, 3: src, 4: f"GATE{n}", 5: out},
           f"Ideal diode {n} switch; 60 V, 8.1 mΩ at 10 V: 73 mW at 3 A")
    c.part(ctl, IDEAL[0], IDEAL[1], IDEAL[2], IDEAL[3],
           {1: f"VCAP{n}", 2: "GND", 3: src, 4: out, 5: f"GATE{n}", 6: src}, note)
    c.C(cap, "1µF 50V", src, f"VCAP{n}", note="Charge pump, 0.1 µF minimum between VCAP and ANODE. 1 µF: ~0.5 µF left "
        "at the 12-13 V VCAP-ANODE bias (100 nF 0402 keeps ~65 nF); the 300 µA pump reaches its 6.6 V UVLO in ~22 ms, "
        "body diode meanwhile (the sims assume it)")
    if cin:
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
       "MX74700T ideal diodes U1 and U52 (anode -90 V; cathode to anode 75 V, 48.5 V with the boost running)")
ideal_diode(1, "VIN_EXT_P", "U1", "Q1", "C1", "C2", "Ideal diode, VIN_EXT")
ideal_diode(2, "VBUS_USB", "U2", "Q2", "C3", "C4", "Ideal diode, USB-C PD port (J2) VBUS after the sink switch")
ideal_diode(3, "POE_12V", "U3", "Q3", "C5", "C6", "Ideal diode, PoE module 12 V output")
c.part("C7", "Device:C_Polarized", "47µF 63V", "Capacitor_SMD:CP_Elec_6.3x7.7", "C46550423",
       {1: "VSYS_OR", 2: "GND"}, "Damps the hot-plug ringing of the cables and the ceramics")
c.C("C8", "1µF 50V", "VSYS_OR", "GND", note="Layout: at the Q1 drain. A short on VIN_EXT turns Q1 off with ~120 A reverse "
    "(sim/oring.py): 31 V on the drain with it, 83 V without (MX74700T cathode-anode 75 V)")
sense("R1", "R2", "C9", "VIN_EXT_P", "VIN_EXT_SENSE")
sense("R3", "R4", "C10", "VBUS_USB", "VBUS_USB_SENSE")
sense("R5", "R6", "C11", "POE_12V", "POE_12V_SENSE")
# VSYS itself: U43 bus voltage (no ADC divider; PA6 reads the J5 CC lines)
c.R("R126", "15m", "VSYS_OR", "VSYS", fp=R1206,
    note="VSYS shunt: 81.9 mV full scale = 5.46 A; 135 mW at 3 A")
c.part("U43", "Sensor_Energy:INA226", "INA226AIDGSR", "Package_SO:TSSOP-10_3x3mm_P0.5mm", "C49851",
       {10: "VSYS_OR", 9: "VSYS", 8: "VSYS", 6: "+3V3", 7: "GND", 4: "SYS_SDA", 5: "SYS_SCL",
        3: "INA_ALERT", 1: "GND", 2: "+3V3"},
       "VSYS monitor: everything drawn from the active source (probe, target, shield, boost), I2C5 address "
       "0x41. VIN_BUS fed from VIN_EXT through U52/Q10 bypasses it: the TPS27S100 IMON reads that current")
c.C("C126", "100nF", "+3V3", "GND", note="U43")

# --------------------------------------------------------------------------------------------
c.block("USB-C PD port (J2): STUSB4500 sink, VBUS switch, USB FS for the ROM DFU, ESD")
# Two USB-C ports (architecture.md, "USB ports"): J2 takes a PD charger (up to 20 V) and carries the FS
# lines of the internal PHY (ROM DFU only); J5 carries USB HS to the USB3320C at 5 V, from a PC.
# One OTG_HS controller: ULPI or the internal FS PHY, never both at once.
c.part("J2", "Connector:USB_C_Receptacle_USB2.0_16P", "TYPE-C-31-M-12",
       "Archet:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948",
       {"A4": "VBUS_CONN", "A9": "VBUS_CONN", "B4": "VBUS_CONN", "B9": "VBUS_CONN", "A5": "CC1", "B5": "CC2",
        "A6": "USB_C_DP", "B6": "USB_C_DP", "A7": "USB_C_DM", "B7": "USB_C_DM",
        "A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND"},
       "PD and FS port, USB 2.0 receptacle, 5 A contacts; SBU unused")
c.part("D2", "Device:D_TVS", "SMBJ24CA", SMB, "C78416", {1: "GND", 2: "VBUS_CONN"},
       "Same TVS as VIN_EXT: 24 V standoff covers the 20 V PD contract")
c.C("C13", "1µF 50V", "VBUS_CONN", "GND", note="STUSB4500 VDD decoupling and USB cSnkBulk (1-10 µF)")
c.part("U4", "Interface_USB:STUSB4500QTR", "STUSB4500QTR", "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
       "C2678061",
       {1: "CC1", 2: "CC1", 4: "CC2", 5: "CC2", 6: "GND", 7: "SYS_SCL", 8: "SYS_SDA", 10: "GND", 12: "GND",
        13: "GND", 16: "VBUS_EN_N", 18: "PD_DISCH", 19: "PD_ALERT", 21: "PD_1V2", 22: "+3V3", 23: "PD_2V7",
        24: "VBUS_CONN", 25: "GND"},
       "Auto-run sink, NVM holds the PDOs. CCxDB to CCx: dead battery mode, the probe is unpowered when the "
       "cable arrives. VDD from VBUS, VSYS from +3V3: I2C5 (shared with the INA226) is not clamped low "
       "when USB is absent. RESET grounded (soft reset over I2C), address 0x28. ALERT: MCU pull-up on PG0")
c.C("C14", "1µF 50V", "PD_1V2", "GND", note="VREG_1V2, 0.5-10 µF")
c.C("C15", "1µF 50V", "PD_2V7", "GND", note="VREG_2V7, 0.5-10 µF")
c.C("C16", "100nF", "+3V3", "GND", note="VSYS")
c.R("R9", "1k", "VBUS_CONN", "PD_DISCH", note="VBUS sense and discharge path, 20 mA at 20 V (50 mA max)")
c.part("Q4", "Transistor_FET:FDS9435A", "AO4407A", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "C2841482",
       {1: "VBUS_CONN", 2: "VBUS_CONN", 3: "VBUS_CONN", 4: "VBUS_GATE",
        5: "VBUS_USB", 6: "VBUS_USB", 7: "VBUS_USB", 8: "VBUS_USB"},
       "Sink switch, -30 V, 18.5 mΩ max at -4.5 V (5 V VBUS), 11.5 mΩ at -10 V: 0.17-0.22 W at 3 A. Closes at attach (VBUS_EN_SNK) "
       "with a Miller soft start (C141, R181): 0.27 A peak into VSYS; its body diode only conducts toward the connector, the MX74700T blocks VSYS")
c.R("R10", "100k", "VBUS_CONN", "VBUS_GATE", note="Gate off when VBUS_EN_SNK is released")
c.C("C134", "1µF 50V", "VBUS_CONN", "VBUS_GATE", note="Gate-source: Q4 turns on ~6 ms after VBUS_EN_N. Holds Vgs at "
    "-0.42 V on a 5 V hot plug (VGS(th) -1.3 V min)")
c.C("C141", "100nF", "VBUS_USB", "VBUS_MILLER", note="Gate-drain (Miller) soft start with R181: VSYS rises in 1.7 ms, "
    "0.27 A peak at 5 V attach (3 A with C134 alone, sim/vbus_switch.py)")
c.R("R181", "1k", "VBUS_MILLER", "VBUS_GATE", note="Damps the Miller loop: 1.45 A peak without it")
c.R("R11", "10k", "VBUS_GATE", "VBUS_EN_N", note="Vgs = -0.91 VBUS: -18.2 V at 20 V (±25 V max), -4.5 V at 5 V")
c.part("D3", "Device:D_Dual_CommonAnode_KKA", "ESDA25W", "Package_TO_SOT_SMD:SOT-323_SC-70", "C2935152",
       {1: "CC2", 2: "CC1", 3: "GND"}, "CC lines ESD, 25 V breakdown: above the 22 V short-to-VBUS rating")
c.part("U5", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", "C7519",
       {1: "USB_C_DM", 6: "USB_FS_DM", 3: "USB_C_DP", 4: "USB_FS_DP", 2: "GND", 5: "+3V3"},
       "D+/D- ESD, flow-through: 1-6 and 3-4 are joined inside, the tracks pass over the pads; reference on +3V3 since VBUS reaches 20 V (6 V max on pin 5)")
c.R("R22", "100k", "GND", "USB_FS_DM", note="Known level with J2 open (AN2606 §4.4: no floating "
    "D+/D- while the ROM polls the other interfaces)")
c.R("R23", "100k", "USB_FS_DP", "GND", note="Same; against the 1.5 kΩ device pull-up D+ stays at 3.25 V")

# --------------------------------------------------------------------------------------------
c.block("USB-C HS port (J5): 5 V sink, soft start, ideal diode, CC current read-back, ESD")
c.part("J5", "Connector:USB_C_Receptacle_USB2.0_16P", "TYPE-C-31-M-12",
       "Archet:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948",
       {"A4": "VBUS_HS_CONN", "A9": "VBUS_HS_CONN", "B4": "VBUS_HS_CONN", "B9": "VBUS_HS_CONN",
        "A5": "CC1_HS", "B5": "CC2_HS", "A6": "HS_C_DP", "B6": "HS_C_DP", "A7": "HS_C_DM", "B7": "HS_C_DM",
        "A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND"},
       "HS port, same receptacle as J2. 5 V only (no PD): a PC port, Type-A through a cable or Type-C")
c.part("D7", "Device:D_TVS", "SMBJ24CA", SMB, "C78416", {1: "GND", 2: "VBUS_HS_CONN"},
       "Same TVS as J2: survives a 20 V source plugged by mistake (the 5 V Rd sink asks for none)")
c.C("C138", "1µF 50V", "VBUS_HS_CONN", "GND", note="cSnkBulk (1-10 µF), the only capacitance seen at attach")
c.R("R25", "5.1k", "GND", "CC1_HS", note="Rd: the source turns VBUS on. Type-C sink without PD")
c.R("R176", "5.1k", "CC2_HS", "GND", note="Rd, flipped cable")
c.part("D20", "Device:D_Dual_CommonAnode_KKA", "ESDA25W", "Package_TO_SOT_SMD:SOT-323_SC-70", "C2935152",
       {1: "CC2_HS", 2: "CC1_HS", 3: "GND"}, "CC lines ESD, as D3")
c.R("R7", "100k", "CC1_HS", "CC_HS_SENSE", note="CC read-back: the active CC (vRd of the source Rp) averaged with "
    "the open one at 0 V: 0.51 vRd on PA6. Default < 0.34 V, 1.5 A 0.34-0.63 V, 3 A > 0.63 V. Loads Rd to 4.98 kΩ "
    "(4.59-5.61 kΩ allowed)")
c.R("R8", "100k", "CC2_HS", "CC_HS_SENSE", note="Second CC into the average")
c.C("C12", "100nF", "CC_HS_SENSE", "GND", note="ADC sampling reservoir, 5 ms time constant (vRd is static)")
c.part("Q11", "Transistor_FET:FDS9435A", "AO4407A", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "C2841482",
       {1: "VBUS_HS_CONN", 2: "VBUS_HS_CONN", 3: "VBUS_HS_CONN", 4: "HS_GATE",
        5: "VBUS_HS", 6: "VBUS_HS", 7: "VBUS_HS", 8: "VBUS_HS"},
       "Self-biased soft start, as Q4 with no driver: USB 2.0 attach limit (10 µF / 50 µC) against ~90 µF on VSYS. "
       "sim/usb_hs_inrush.py: on 13 ms after attach, VSYS in 4 ms, 90 mA peak; D21 re-arms it on a dropout. Body diode toward the connector")
c.R("R179", "100k", "VBUS_HS_CONN", "HS_GATE", note="Gate-source: Vgs = -4.1 V once on (with R180)")
c.R("R180", "22k", "HS_GATE", "GND", note="Pulls the gate down: 20 ms time constant with C136 + C137")
c.C("C136", "1µF 50V", "VBUS_HS_CONN", "HS_GATE", note="Gate-source: Vgs -0.66 V on a 1 µs hot plug (VGS(th) -1.3 V min)")
c.C("C137", "100nF", "VBUS_HS", "HS_GATE", note="Gate-drain (Miller): ramp ~0.9 V/ms, ~80 mA into VSYS")
c.part("D21", *SCHOTTKY[:3], SCHOTTKY[3], {1: "HS_GATE", 2: "GND"},
       "Re-arms the soft start: VBUS falling drags the gate below GND through C136, D21 empties C136. Without it "
       "a hub port cycled for 1-10 ms finds Q11 on: 400-670 µC, 6-12 A into VSYS (sim/usb_hs_inrush.py)")
ideal_diode(5, "VBUS_HS", "U53", "Q12", "C139", "C140", "Ideal diode, USB-C HS port (J5) VBUS after the soft start")
c.part("U12", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", "C7519",
       {1: "HS_C_DM", 6: "USB_DM", 3: "HS_C_DP", 4: "USB_DP", 2: "GND", 5: "+3V3"},
       "J5 D+/D- ESD to the USB3320C, flow-through as U5")

# --------------------------------------------------------------------------------------------
c.block("PoE+: RJ45 with PoE+ magnetics, bridges, isolated 12 V PD module")
c.part("J3", "Archet:ARJM11D7-104-AB-EW2", "ARJM11D7-104-AB-EW2", "Archet:ARJM11_Layout7_10P_LED", "C5554250",
       {9: "POE_DA", 10: "POE_DB", 7: "POE_SA", 8: "POE_SB", 1: "ETH_TXP", 2: "ETH_TXN", 5: "ETH_CT",
        3: "ETH_RXP", 4: "ETH_RXN", 13: "ETH_LEDL_A", 14: "GND", 11: "ETH_LEDR_A", 12: "GND",
        "SH": "GND"},
       "Schematic 104: 600 mA per pair (the -114 PoE variant only takes 350 mA, short of class 4). "
       "Through-hole, wave solder; 64 in stock: reserve it")
for ref, a, b, what in (("D4", "POE_DA", "POE_DB", "data pair centre taps (mode A)"),
                        ("D5", "POE_SA", "POE_SB", "spare pairs (mode B)")):
    c.part(ref, "Diode_Bridge:MB6S", "MB10S", "Package_TO_SOT_SMD:TO-269AA", "C2488",
           {1: b, 2: a, 3: "POE_VP", 4: "POE_VN"},
           f"Polarity bridge, {what}; 1 kV 1 A. MDD numbers its pins 1 +, 2 -, 3/4 ~ (KiCad: 3 +, 4 -): "
           "check the CPL orientation")
c.part("D6", "Diode:SMAJ58A", "SMAJ58A", "Diode_SMD:D_SMA", "C10762", {1: "POE_VP", 2: "POE_VN"},
       "Input TVS of the DP5700 typical circuit: 58 V standoff, 93.6 V clamp (module surge rating 80 V for 1 ms)")
c.part("U6", "Archet:DP5700-12V2A", "DP5700-12V2A", "Archet:DP5700", "C22358555",
       {4: "POE_VP", 6: "POE_VN", 5: "POE_TYP2", 1: "POE_12V", 2: "GND"},
       "Class 4 PD, 12.07 V with ADJ open, 1500 V isolation. TYP2-DET: switch + 27 kΩ to VIN-, "
       "closed under a Type 2 PSE (copy of the Silvertel Ag5700: its datasheet §2.2.3, figure 4, opto LED from VIN+)")
c.R("R12", "47k", "POE_VP", "POE_OPTO_A", fp=R0805, note="Opto LED, in series with the 27 kΩ inside TYP2-DET: "
    "0.48-0.75 mA at 37-57 V; 26 mW, 150 V rating")
c.part("U7", "Isolator:PC817", "PC817X2CSP9F", "Package_DIP:SMDIP-4_W7.62mm", "C66405",
       {1: "POE_OPTO_A", 2: "POE_TYP2", 4: "POE_AT_N", 3: "GND"},
       "Carries TYP2-DET across the isolation barrier (5 kV); CTR >= 50 % at 5 mA, lower at 0.5 mA: ~0.15 mA available, 33 µA needed")
c.R("R13", "100k", "+3V3", "POE_AT_N", note="POE_AT_N to PC15: low when a Type 2 (at) PSE powers the probe")
c.part("C17", "Device:C_Polarized", "100µF 25V", "Capacitor_SMD:CP_Elec_6.3x7.7", "C970685",
       {1: "POE_12V", 2: "GND"}, "Output capacitor of the DP5700 typical circuit")
c.C("C18", "10µF 25V", "POE_12V", "GND", note="Output capacitor of the DP5700 typical circuit")
c.R("R14", "1k", "POE_12V", "GND", fp=R1206,
    note="Minimum load, 12 mA (10 mA required): the module stays quiet and keeps the PSE MPS when "
         "VIN_EXT or USB PD wins the OR-ing; 144 mW")

# --------------------------------------------------------------------------------------------
c.block("+5V: VSYS (4.5-24 V) to 5 V 3 A synchronous buck, LMR33630A at 400 kHz")
c.part("U8", "Regulator_Switching:LMR33630ADDA", "LMR33630ADDAR",
       "Archet:Texas_HSOP-8-1EP_3.9x4.9mm_P1.27mm_ThermalVias", "C841384",
       {2: "VSYS", 3: "VSYS", 6: "BUCK5_VCC", 7: "BUCK5_BOOT", 8: "BUCK5_SW", 5: "BUCK5_FB", 1: "GND", 9: "GND"},
       "36 V input, 1.5 x the 24 V maximum. EN tied to VIN: the internal VIN UVLO is enough, the rail "
       "powers the MCU and stays on. PG unused: the MCU it would report to sits on this rail")
c.C("C19", "10µF 50V", "VSYS", "GND", fp=C1206, note="Input bulk, X5R: ~3 µF left at 24 V DC bias")
c.C("C20", "10µF 50V", "VSYS", "GND", fp=C1206, note="Input bulk, second half")
c.C("C21", "100nF", "VSYS", "GND", note="Input HF, against the VIN pin and the PGND pad")
c.C("C22", "1µF 50V", "BUCK5_VCC", "GND", note="Internal LDO output (VCC), datasheet 1 µF")
c.C("C23", "100nF", "BUCK5_BOOT", "BUCK5_SW", note="Bootstrap, datasheet 100 nF")
c.part("L1", "Device:L", "10µH", "Inductor_SMD:L_Changjiang_FXL0630", "C167223", {1: "BUCK5_SW", 2: "+5V"},
       "FXL0630-100-M: Isat 5.5 A, Irms 4.5 A, 68 mΩ (0.6 W at 3 A). Ripple 1.0 A p-p at 24 V, 1.1 A at 36 V "
       "(~35 % of 3 A); peak 3.6 A, under the LMR33630 high-side limit and the saturation current")
for ref in ("C24", "C25", "C26"):
    c.C(ref, "22µF 25V", "+5V", "GND", fp=C1206, note="Output, X5R: ~13 µF each at 5 V DC bias")
c.R("R15", "8.06k", "+5V", "BUCK5_FB", note="Feedback top: palette value (datasheet 100 kΩ), divider 0.5 mA")
c.R("R16", "2k", "BUCK5_FB", "GND", note="Feedback bottom: 1.0 V x (1 + 8.06/2) = 5.03 V")

# --------------------------------------------------------------------------------------------
c.block("VIN_BUS: LM5155 24.5 V boost from VSYS, or VIN_EXT through an ideal diode")
# Datasheet SNVSB75E; values simulated in hardware/sim/boost.py (loop and cycle by cycle, VSYS 4.5-20 V).
# VIN_BUS = the higher of the boost (24.5 V) and VIN_EXT. VIN_EXT present: the boost is held off.
c.part("U42", "Archet:LM5155", "LM5155DSSR", "Archet:WSON-12-1EP_3x2mm_P0.5mm_EP1x2.65", "C545416",
       {1: "VSYS", 2: "BOOST_VCC", 3: "BOOST_GATE", 4: "GND", 5: "BOOST_CS", 6: "BOOST_COMP", 7: "GND",
        8: "BOOST_FB", 9: "BOOST_SS", 10: "BOOST_RT", 12: "BOOST_UVLO", 13: "GND"},
       "Peak current mode, 425 kHz. BIAS on VSYS (>= 3.5 V). PGOOD unused: VIN_BUS_SENSE reads the output")
c.part("Q8", NMOS[0], NMOS[1], NMOS[2], NMOS[3],
       {1: "BOOST_ISNS", 2: "BOOST_ISNS", 3: "BOOST_ISNS", 4: "BOOST_GATE", 5: "BOOST_SW"},
       "Boost switch; QG 7.2 nC: 3.1 mA from VCC")
c.part("L5", "Device:L", "10µH", "Inductor_SMD:L_Changjiang_FXL1040", "C475915", {1: "VSYS", 2: "BOOST_SW"},
       "FXL1040-100-M: Isat 8.5 A, 30 mΩ. Peak 3.5 A at 4.5 V / 0.5 A, under the 5.27 A minimum limit")
c.part("D17", "Device:D_Schottky", "SS54", "Diode_SMD:D_SMA", "C22452", {1: "VIN_BUS", 2: "BOOST_SW"},
       "Boost diode, 40 V 5 A")
ideal_diode(4, "VIN_EXT_P", "U52", "Q10", "C135", None,
            "VIN_EXT straight to VIN_BUS, < 10 mW at 1 A. Blocks the boost output: ~2 µA cathode leakage (a "
            "Schottky would lift VIN_EXT_P, turn Q9 on and fake a VIN_EXT); a reversed VIN_EXT with the boost "
            "running puts 48.5 V across Q10 (60 V) and cathode to anode (75 V). Input decoupling: C2",
            out="VIN_BUS")
c.R("R116", "15m", "BOOST_ISNS", "GND", fp=R1206, note="Current sense: 100 mV limit -> 5.3-6.9 A over VSYS")
c.R("R117", "470", "BOOST_ISNS", "BOOST_CSF", note="Slope compensation, with R118: 79 % at 4.5 V")
c.R("R118", "100", "BOOST_CSF", "BOOST_CS", note="CS filter")
c.C("C113", "100pF", "BOOST_CS", "GND", note="CS filter, against the pin")
c.R("R113", "51k", "BOOST_RT", "GND", note="fsw = 2.21e10 / (RT + 955) = 425 kHz")
c.C("C116", "22nF", "BOOST_SS", "GND", note="Soft start 2.2 ms (10 µA)")
c.R("R119", "3.3k", "BOOST_COMP", "BOOST_CZ", note="Compensation: crossover 6-25 kHz, phase margin >= 53°")
c.C("C114", "100nF", "BOOST_CZ", "GND", note="Compensation zero")
c.C("C115", "470pF", "BOOST_COMP", "GND", note="Compensation high-frequency pole")
c.R("R114", "47k", "VIN_BUS", "BOOST_FB", note="1.0 V x (1 + 47/2) = 24.5 V; OVP 27 V")
c.R("R115", "2k", "BOOST_FB", "GND")
c.C("C117", "1µF 50V", "BOOST_VCC", "GND", note="VCC regulator, 1 µF minimum")
c.C("C118", "100nF", "VSYS", "GND", note="BIAS")
for ref in ("C119", "C120"):
    c.C(ref, "10µF 50V", "VSYS", "GND", fp=C1206, note="Boost input, against L5 and R116")
for ref in ("C121", "C122", "C123", "C124"):
    c.C(ref, "10µF 50V", "VIN_BUS", "GND", fp=C1206, note="Boost output: ~3 µF each at 24 V DC bias"
        + ("; layout: at the Q10 drain (VIN_EXT short, sim/oring.py)" if ref == "C121" else ""))
c.R("R120", "10k", "BOOST_EN", "BOOST_UVLO", note="3.3 V x 22/32 = 2.27 V, above the 1.5 V threshold")
c.R("R121", "22k", "BOOST_UVLO", "GND", note="Boost off while the MCU pin is high-Z")
c.part("Q9", "Transistor_FET:2N7002", "2N7002", "Package_TO_SOT_SMD:SOT-23", "C8545",
       {1: "BOOST_INH", 2: "GND", 3: "BOOST_UVLO"},
       "VIN_EXT present: UVLO held low in hardware, whatever BOOST_EN says (a 12 V VIN_EXT must not be "
       "boosted to 24 V)")
c.R("R122", "100k", "VIN_EXT_P", "BOOST_INH", note="Gate 3.45 V at 10.8 V, 12.4 V at the 38.9 V TVS clamp")
c.R("R123", "47k", "BOOST_INH", "GND")
sense("R124", "R125", "C125", "VIN_BUS", "VIN_BUS_SENSE")

# --------------------------------------------------------------------------------------------
c.block("+3V3 and +3V3_AUX: two TLV62569 2 A bucks from +5V, 1.5 MHz")
# Probe rail: 550 mA max (docs/architecture.md, power budget), plus +3V3_BUS through U44 (616 mA limit): 1.17 A. AUX rail: the 3V3_OUT eFuse, 1 A ceiling.
# Ripple 3.3 x (1 - 3.3/5) / (2.2 µH x 1.5 MHz) = 0.34 A p-p; peak 2.2 A at the 2 A rating.
for u, l, cin, cout, rt, rb, out, tag in (("U9", "L2", "C27", "C28", "R17", "R18", "+3V3", "B3V3"),
                                         ("U10", "L3", "C29", "C30", "R19", "R20", "+3V3_AUX", "B3V3A")):
    c.part(u, "Regulator_Switching:TLV62569DBV", "TLV62569DBVR", "Package_TO_SOT_SMD:SOT-23-5", "C141836",
           {4: "+5V", 1: "+5V", 3: f"{tag}_SW", 5: f"{tag}_FB", 2: "GND"},
           "EN tied to VIN: always on (the AUX rail is switched downstream by the 3V3_OUT eFuse). "
           "Runs at 100 % duty when +5V sags to 4.8 V on a USB port")
    c.C(cin, "10µF 25V", "+5V", "GND", fp=C0805, note="Input, datasheet 4.7 µF minimum")
    c.part(l, "Device:L", "2.2µH", "Inductor_SMD:L_Changjiang_FXL0420", "C167206", {1: f"{tag}_SW", 2: out},
           "FXL0420-2R2-M: Isat 5 A, Irms 4.5 A, 58 mΩ. Datasheet standard pair: 2.2 µH with 10-22 µF")
    c.C(cout, "22µF 25V", out, "GND", fp=C1206, note="Output, X5R: ~15 µF at 3.3 V DC bias, within 10-47 µF")
    c.R(rt, "100k", out, f"{tag}_FB", note="Feedback top")
    c.R(rb, "22k", f"{tag}_FB", "GND", note="Feedback bottom: 0.6 V x (1 + 100/22) = 3.33 V; R2 under 200 kΩ")

# --------------------------------------------------------------------------------------------
c.block("MCU: STM32H723ZGT6, decoupling, 25 MHz HSE, debug connector")
MCU_SYM = "MCU_ST_STM32H7:STM32H723ZGTx"


def mcu_pins():
    """{pin number: net} for the MCU: signals from hardware/mcu-pins.csv, supplies here."""
    sym = Libraries().resolve(MCU_SYM)
    by_name = {}
    for num, name in pin_names(sym).items():
        by_name.setdefault(name, []).append(num)
        by_name.setdefault(name.split("(")[0], []).append(num)   # "PA13(JTMS" -> "PA13"
    pins = {}
    with open(os.path.join(HW, "mcu-pins.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            (num,) = set(by_name[row["pin"].split("-")[0]])          # "PH0-OSC_IN" -> "PH0"
            pins[num] = row["net"]
    supplies = {"VDD": "+3V3", "VSS": "GND", "VSSA": "GND", "VDDA": "VDDA", "VREF+": "VDDA",
                "VBAT": "+3V3", "VDD33USB": "+3V3", "PDR_ON": "+3V3", "VCAP": "VCAP",
                "BOOT0": "BOOT0", "NRST": "NRST"}
    for name, net in supplies.items():
        for num in by_name[name]:
            pins[num] = net
    return pins


c.part("U11", MCU_SYM, "STM32H723ZGT6", "Package_QFP:LQFP-144_20x20mm_P0.5mm", "C730146", mcu_pins(),
       "550 MHz Cortex-M7, LQFP-144 (no BGA). Signal pins: hardware/mcu-pins.csv; unlisted pins left "
       "unconnected (analog-capable inputs, reset state). PDR_ON high: internal power-on reset")
for i in range(31, 42):
    c.C(f"C{i}", "100nF", "+3V3", "GND", note="VDD decoupling, one per VDD pin (11), against the pin")
c.C("C42", "10µF 25V", "+3V3", "GND", fp=C0805, note="VDD bulk, datasheet 4.7 µF")
c.C("C43", "2.2µF", "VCAP", "GND", note="VCAP1, datasheet 2.2 µF ESR < 100 mΩ per pin (LDO supply)")
c.C("C44", "2.2µF", "VCAP", "GND", note="VCAP2")
c.part("FB1", "Device:FerriteBead_Small", "600Ω@100MHz", "Inductor_SMD:L_0603_1608Metric", "C1002",
       {1: "+3V3", 2: "VDDA"}, "GZ1608D601TF: 200 mA, 0.45 Ω. Separates VDDA/VREF+ (ADC, DAC) from VDD noise")
c.C("C45", "1µF 50V", "VDDA", "GND", note="VDDA/VREF+ bulk, datasheet 1 µF")
c.C("C46", "100nF", "VDDA", "GND", note="VDDA/VREF+ HF")
c.C("C47", "100nF", "+3V3", "GND", note="VDD33USB decoupling (internal FS PHY: ROM DFU on J2)")
c.R("R175", "33", "PPS", "PPS_IN", note="PPS loopback PG8 -> PA0 (TIM5_CH1, AF2): input capture of the "
    "PPS edge; TIM2_CH1 is BUS_LATCH (PA15). TIM2 reset needs no wire: ETH PPS is TIM2 ITR4 (RM0468 table 355)")
c.R("R21", "22k", "BOOT0", "GND", note="BOOT0 low: boot from flash. GO held through R24 (1k): 3.16 V, "
    "ROM bootloader at reset")
c.R("R24", "1k", "GO_BTN", "BOOT0", note="GO is also BOOT0: held at power-up or reset, it enters the ROM "
    "bootloader (DFU on J2, USART3 on J6); once running, BOOT0 is ignored")

# Programming with no probe (architecture.md, "Programming a board with no debug probe"): the ROM
# bootloader through USB FS DFU (J2) or USART3 (J6, FTDI cable), GO held at reset.
c.part("J6", "Connector_Generic:Conn_01x06", "Console / bootloader (FTDI)",
       "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", "",
       {1: "GND", 2: "BOOT0", 3: "J6_VCC", 4: "CONSOLE_RX", 5: "CONSOLE_TX", 6: "J6_RST"},
       "Pads only, FTDI cable pinout: 1 GND, 2 CTS (BOOT0 test pad), 3 VCC 5 V, 4 TXD, 5 RXD, 6 RTS. "
       "USART3 PD8/PD9 (FT pins: 5 V cables accepted)", bare=True)
c.part("D8", *SCHOTTKY[:3], SCHOTTKY[3], {1: "VSYS", 2: "J6_VCC"},
       "J6 VCC powers the whole board (150-250 mA in the bootloader); blocks VSYS from the cable")
c.R("R177", "1k", "GND", "J6_VCC", note="Sinks the D8 reverse leakage (VSYS up to 24 V, hot) with J6 open: "
    "the VCC pad stays near 0 V")
c.part("D9", *SCHOTTKY[:3], SCHOTTKY[3], {1: "J6_RST", 2: "NRST"},
       "RTS low pulls NRST low; RTS high (5 V on a 5 V cable) is blocked: NRST is not 5 V tolerant")
c.C("C48", "100nF", "NRST", "GND", note="NRST filter, datasheet 100 nF; internal pull-up")
c.part("Y1", "Device:Crystal_GND24", "25MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "C9006",
       {1: "HSE_IN", 3: "HSE_OUT", 2: "GND", 4: "GND"},
       "X322525MOB4SI: ±10 ppm, CL 12 pF, ESR 50 Ω max. MCU HSE only: the RMII PHY has its own crystal (Y3), "
       "PA1 being the REF_CLK input")
c.C("C49", "15pF", "HSE_IN", "GND", note="Load: 2 x (12 pF - ~4.5 pF stray) = 15 pF")
c.C("C50", "15pF", "HSE_OUT", "GND", note="Load, second")
c.part("J4", "Connector:Conn_ARM_SWD_TagConnect_TC2030", "MCU debug (TC2030)",
       "Connector:Tag-Connect_TC2030-IDC-FP_2x03_P1.27mm_Vertical", "",
       {1: "+3V3", 2: "MCU_SWDIO", 3: "NRST", 4: "MCU_SWCLK", 5: "GND", 6: "MCU_SWO"},
       "Footprint only, nothing to buy (as on Bornier): J-Link through the SEGGER 6-pin Needle Adapter or "
       "the Tag-Connect TC2030-CTX cable. SWD, SWO and reset; the console goes over SWO or USB")

# --------------------------------------------------------------------------------------------
c.block("FPGA: iCE40UP5K-SG48, 1.2 V core LDO, PLL filter, configuration pulls")
FPGA_SYM = "FPGA_Lattice:ICE40UP5K-SG48ITR"


def fpga_pins():
    """{pin number: net} for the iCE40: signals from hardware/fpga-pins.csv, supplies and configuration here."""
    with open(os.path.join(HW, "fpga-pins.csv"), encoding="utf-8") as f:
        pins = {row["pin"]: row["net"] for row in csv.DictReader(f)}
    pins.update({"1": "+3V3", "33": "+3V3",          # VCCIO_2, VCCIO_0: 3.3 V banks
                 "22": "+3V3",                       # SPI_VCCIO1 (bank 1)
                 "24": "+3V3",                       # VPP_2V5: NVCM unused, SPI slave configuration
                 "5": "+1V2", "30": "+1V2", "29": "VCCPLL",
                 "7": "FPGA_CDONE", "8": "FPGA_CRESET_B", "49": "GND"})
    return pins                                      # 40, 41 (RGB1, RGB2): LED_LINK, LED_SPARE (current sinks)


c.part("U13", FPGA_SYM, "iCE40UP5K-SG48I", "Archet:QFN-48-1EP_7x7mm_P0.5mm_EP5.3x5.3mm", "C2678152",
       fpga_pins(), "SWD/JTAG/SWO engine, configured by the MCU as SPI slave (SPI_SS low at CRESET_B release). "
       "Signal pins: hardware/fpga-pins.csv. RGB1/RGB2 drive LEDs (current sinks). Exposed pad = only GND")
c.part("U14", "Regulator_Linear:ME6211C12M5", "ME6211C12M5G-N", "Package_TO_SOT_SMD:SOT-23-5", "C236672",
       {1: "+5V", 2: "GND", 3: "+5V", 5: "+1V2"},
       "1.2 V core, 500 mA (UP5K core: a few mA to tens of mA). No basic 1.2 V LDO at JLCPCB. Fed from +5V "
       "(6 V max): VCC and VCCPLL are up before SPI_VCCIO1 and VPP_2V5 (+3V3, buck from +5V), the order the "
       "UltraPlus datasheet requires (§4.5, 0.5 V before the next supply). 0.1 W at 30 mA")
c.C("C51", "1µF 50V", "+5V", "GND", note="LDO input, datasheet 1 µF")
c.C("C52", "1µF 50V", "+1V2", "GND", note="LDO output, datasheet 1 µF ceramic")
c.C("C53", "100nF", "+1V2", "GND", note="VCC pin 5")
c.C("C54", "100nF", "+1V2", "GND", note="VCC pin 30")
c.R("R26", "100", "+1V2", "VCCPLL", note="VCCPLL filter, Lattice UltraPlus development platform: 100 Ω, 10 µF, "
    "100 nF. Required even with the PLL unused")
c.C("C55", "10µF 25V", "VCCPLL", "GND", fp=C0805, note="VCCPLL filter, against pin 29")
c.C("C56", "100nF", "VCCPLL", "GND", note="VCCPLL filter HF")
for i, pin in zip(range(57, 61), ("1 VCCIO_2", "22 SPI_VCCIO1", "24 VPP_2V5", "33 VCCIO_0")):
    c.C(f"C{i}", "100nF", "+3V3", "GND", note=f"Pin {pin}")
c.R("R27", "10k", "FPGA_CRESET_B", "GND", note="FPGA held in reset until the MCU releases it: IOs high-Z while "
    "the MCU is in reset or in the ROM bootloader (QSPI pins shared with I2C2)")
c.R("R28", "10k", "+3V3", "FPGA_CDONE", note="CDONE pull-up, open drain")
c.R("R29", "10k", "+3V3", "SHIELD_OE_N", note="Shield drivers off until the bitstream pulls OE_N low (RGB0, "
    "open drain). On +3V3, not +3V3_OUT: a self-powered shield stays disabled with +3V3_OUT off (0.33 mA "
    "into an unpowered shield at most)")

# --------------------------------------------------------------------------------------------
c.block("USB HS: USB3320C ULPI PHY, 24 MHz crystal, 1.8 V LDO")
# Microchip DS00001792F. Device mode, ULPI output clock mode (figure 8-1), 3.3 V supply on VBAT and VDD33
# (figure 5-7), VDDIO 3.3 V. ~47 mA in HS: 11 mA (3.3 V) + 30 mA (1.8 V) + 6 mA (VDDIO).
c.part("U15", "Archet:USB3320C-EZK", "USB3320C-EZK-TR", "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm",
       "C132156",
       {22: "PHY_VBUS", 18: "USB_DP", 19: "USB_DM", 23: "+3V3",
        26: "PHY_REFCLK", 25: "PHY_XO", 24: "PHY_RBIAS", 8: "+3V3", 11: "+3V3", 14: "+3V3",
        1: "ULPI_CK", 31: "ULPI_DIR", 2: "ULPI_NXT", 29: "ULPI_STP",
        3: "ULPI_D0", 4: "ULPI_D1", 5: "ULPI_D2", 6: "ULPI_D3", 7: "ULPI_D4", 9: "ULPI_D5", 10: "ULPI_D6",
        13: "ULPI_D7", 27: "ULPI_RST",
        21: "+3V3", 20: "+3V3", 32: "+3V3", 28: "+1V8", 30: "+1V8", 33: "GND"},
       "RESETB low: suspended, all ULPI outputs high-Z (CLKOUT included). REFSEL = 111: 24 MHz. ID on VDD33: "
       "no ID detection. CPEN, SPK_L/R unused, pin 12 must stay unconnected. Exposed pad = only GND")
c.part("U16", "Regulator_Linear:ME6211C18M5", "ME6211C18M5G-N", "Package_TO_SOT_SMD:SOT-23-5", "C236671",
       {1: "+5V", 2: "GND", 3: "+5V", 5: "+1V8"},
       "From +5V, not +3V3: 1.8 V is up before VDDIO (3.3 V), as the absolute maximum ratings require "
       "(VDDIO 0.7 V max while VDD18 = 0). 30 mA: 0.1 W")
c.C("C61", "1µF 50V", "+5V", "GND", note="LDO input, datasheet 1 µF")
c.C("C62", "1µF 50V", "+1V8", "GND", note="LDO output, datasheet 1 µF ceramic")
c.C("C63", "100nF", "+1V8", "GND", note="VDD18 pin 28")
c.C("C64", "100nF", "+1V8", "GND", note="VDD18 pin 30")
c.C("C65", "10µF 25V", "+3V3", "GND", fp=C0805, note="COUT: VDD33 pin 20, datasheet 2.2 µF < 1 Ω ESR; 0805 25 V "
    "keeps well above 2.2 µF at 3.3 V DC bias")
c.C("C66", "100nF", "+3V3", "GND", note="CBYP: VBAT pin 21")
c.C("C67", "100nF", "+3V3", "GND", note="CBYP: VDDIO pin 32")
c.R("R30", "10k", "VBUS_HS_CONN", "PHY_VBUS", note="RVBUS, device mode 10 kΩ (table 5-7): J5 VBUS, ahead of "
    "Q11 (session valid as soon as the host turns VBUS on). Internal clamp up to 30 V covers a 20 V source by mistake")
c.R("R31", "8.06k", "PHY_RBIAS", "GND", note="RBIAS 8.06 kΩ 1 %, close to the pin")
c.R("R33", "10k", "ULPI_RST", "GND", note="PHY held in reset (RESETB has no internal pull) until the firmware "
    "drives PD10 high: ULPI_CK quiet on PA5 = SPI1_SCK of the ROM bootloader")
c.part("Y2", "Device:Crystal_GND24", "24MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "C70590",
       {1: "PHY_REFCLK", 3: "PHY_XO", 2: "GND", 4: "GND"},
       "X322524MOB4SI: CL 12 pF, ±10 ppm (USB HS budget ±500 ppm). No basic 24 MHz crystal at JLCPCB")
c.R("R32", "1M", "PHY_REFCLK", "PHY_XO", note="Across the crystal, as in figure 8-3")
c.C("C68", "15pF", "PHY_REFCLK", "GND", note="Load: 2 x (12 pF - ~4.5 pF pin + stray) = 15 pF")
c.C("C69", "15pF", "PHY_XO", "GND", note="Load, second")

# --------------------------------------------------------------------------------------------
c.block("Ethernet: LAN8742A RMII PHY, 25 MHz crystal, line termination, RJ45 LEDs")
# Microchip DS00001989A. REF_CLK Out mode (§3.7.4.2): the PHY makes the 50 MHz REF_CLK from its own 25 MHz
# crystal and drives PA1; nINT is then not available, the link is polled over MDIO. Internal 1.2 V regulator
# (REGOFF low), single 3.3 V supply (figure 3-23). Straps by the internal pulls: MODE = 111 (all capable,
# auto-negotiation), PHYAD = 0.
c.part("U17", "Interface_Ethernet:LAN8742A", "LAN8742A-CZ-TR",
       "Archet:VQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias", "C621424",
       {1: "+3V3", 2: "ETH_LED2", 3: "ETH_LED1", 4: "ETH_XTAL2", 5: "ETH_XTAL1", 6: "ETH_VDDCR",
        7: "RMII_RXD1", 8: "RMII_RXD0", 9: "+3V3", 11: "RMII_CRS_DV", 12: "RMII_MDIO", 13: "RMII_MDC",
        14: "RMII_REF_CLK", 15: "ETH_PHY_RST", 16: "RMII_TX_EN", 17: "RMII_TXD0", 18: "RMII_TXD1", 19: "+3V3",
        20: "ETH_TXN", 21: "ETH_TXP", 22: "ETH_RXN", 23: "ETH_RXP", 24: "ETH_RBIAS", 25: "GND"},
       "nINT/REFCLKO = 50 MHz REF_CLK to PA1 (nINTSEL low). RXER/PHYAD0 unused: internal pull-down, PHY "
       "address 0. Exposed pad = only GND, via array")
c.part("Y3", "Device:Crystal_GND24", "25MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "C9006",
       {1: "ETH_XTAL1", 3: "ETH_XTAL2", 2: "GND", 4: "GND"},
       "X322525MOB4SI, as Y1: ±10 ppm, CL 12 pF (PHY budget ±50 ppm)")
c.C("C70", "15pF", "ETH_XTAL1", "GND", note="Load: 2 x (12 pF - 3 pF pin - ~2 pF stray) = 14 pF")
c.C("C71", "15pF", "ETH_XTAL2", "GND", note="Load, second")
c.C("C72", "1µF 50V", "ETH_VDDCR", "GND", note="VDDCR (internal regulator output), datasheet 1 µF // 470 pF")
c.C("C73", "470pF", "ETH_VDDCR", "GND", note="VDDCR, second")
c.C("C74", "100nF", "+3V3", "GND", note="VDDIO pin 9")
c.C("C75", "100nF", "+3V3", "GND", note="VDD1A pin 19")
c.C("C76", "100nF", "+3V3", "GND", note="VDD2A pin 1 (also feeds the 1.2 V regulator)")
c.C("C77", "10µF 25V", "+3V3", "GND", fp=C0805, note="PHY bulk")
c.R("R34", "12.1k", "ETH_RBIAS", "GND", note="RBIAS 12.1 kΩ 1 %, close to the pin")
c.part("FB2", "Device:FerriteBead_Small", "600Ω@100MHz", "Inductor_SMD:L_0603_1608Metric", "C1002",
       {1: "+3V3", 2: "ETH_CT"}, "GZ1608D601TF, as FB1: 3.3 V to the magnetics centre tap and terminations")
c.C("C78", "100nF", "ETH_CT", "GND", note="Centre tap bypass")
c.R("R35", "49.9", "ETH_TXP", "ETH_CT", note="Line termination 49.9 Ω 1 % to the centre-tap supply")
c.R("R36", "49.9", "ETH_CT", "ETH_TXN", note="Line termination")
c.R("R37", "49.9", "ETH_RXP", "ETH_CT", note="Line termination")
c.R("R38", "49.9", "ETH_CT", "ETH_RXN", note="Line termination")
c.R("R39", "120", "ETH_LED1", "ETH_LEDL_A", note="Green LED (left), cathode to GND: LED1 active high (O12, 12 mA): ~9 mA, 11.7 mA worst case; "
    "also pulls REGOFF low (regulator on)")
c.R("R40", "120", "ETH_LED2", "ETH_LEDR_A", note="Yellow LED (right): LED2 active high once nINTSEL is low")
c.R("R41", "10k", "ETH_LED2", "GND", note="nINTSEL low: REF_CLK Out mode (figure 3-15)")
c.R("R42", "10k", "ETH_PHY_RST", "GND", note="PHY held in reset until the firmware drives PG6 high. Internal "
    "pull-up 50 µA: 0.5 V, below the 1.15 V threshold. Straps are latched at the release")
c.R("R43", "1k", "+3V3", "RMII_MDIO", note="MDIO pull-up (IEEE 802.3 clause 22: 1.5 kΩ ± 5 %; 1 kΩ "
    "palette value, 3.3 mA)")

# --------------------------------------------------------------------------------------------
c.block("Target: STDC14 and ESP-Prog connectors, SN74LVC translators, open-drain nRST and IO0, ESD")
# Pinout: hardware/connectors.csv. A side on +3V3 (iCE40 right bank), B side on TGT_VCC, the logic rail the
# target returns. TI SCES515/SCES516: with either VCC at 0 V both ports are high-Z (Ioff), so an unpowered
# target sees nothing. DIR is referenced to VCCA, high = A to B.
LVC1T45 = ("Logic_LevelTranslator:SN74LVC1T45DBV", "SN74LVC1T45DBVR", "Package_TO_SOT_SMD:SOT-23-6", "C7843")
LVC2T45 = ("Logic_LevelTranslator:SN74LVC2T45DCUR", "SN74LVC2T45DCUR", "Package_SO:VSSOP-8_2.3x2mm_P0.5mm", "C15741")
c.part("J7", "Connector_Generic:Conn_02x07_Odd_Even", "STDC14", "Archet:FTSH-107-01-L-DV-K", "C5307809",
       {1: "TGT_VSUP", 2: "TGT_DIR_OUT", 3: "TGT_VCC", 4: "TGT_SWDIO", 5: "GND", 6: "TGT_SWCLK", 7: "GND",
        8: "TGT_SWO", 10: "TGT_TDI", 11: "GND", 12: "TGT_NRST", 13: "TGT_UART_TX", 14: "TGT_UART_RX"},
       "Samtec FTSH-107-01-L-DV-K, 2 x 7 1.27 mm keyed shroud, as on the STLINK-V3. Pin 9 (RTCK) not connected")
c.part("J8", "Connector_Generic:Conn_02x03_Odd_Even", "ESP-Prog PROG", "Connector_PinHeader_2.54mm:"
       "PinHeader_2x03_P2.54mm_Vertical", "C492420",
       {1: "TGT_NRST", 2: "TGT_VCC", 3: "TGT_UART_RX", 4: "GND", 5: "TGT_UART_TX", 6: "TGT_IO0"},
       "PZ254V-12-6P. ESP-Prog PROG pinout: EN, VDD, ESP_TXD, GND, ESP_RXD, IO0")
c.part("U18", *LVC1T45, {1: "+3V3", 2: "GND", 3: "TGT_SWDIO_3V3", 4: "TGT_SWDIO_B", 5: "TGT_SWDIO_DIR",
                          6: "TGT_VCC"}, "SWDIO / TMS; direction from the iCE40")
c.part("U19", *LVC2T45, {1: "+3V3", 2: "TGT_SWCLK_3V3", 3: "TGT_TDI_3V3", 4: "GND", 5: "+3V3",
                          6: "TGT_TDI_B", 7: "TGT_SWCLK_B", 8: "TGT_VCC"}, "SWCLK / TCK and TDI: A to B")
c.part("U20", *LVC2T45, {1: "+3V3", 2: "TGT_SWO_3V3", 3: "TGT_UART_RX_3V3", 4: "GND", 5: "GND",
                          6: "TGT_UART_RX", 7: "TGT_SWO", 8: "TGT_VCC"}, "SWO / TDO and UART RX: B to A")
c.part("U21", *LVC1T45, {1: "+3V3", 2: "GND", 3: "TGT_UART_TX_3V3", 4: "TGT_UART_TX_B", 5: "+3V3",
                          6: "TGT_VCC"}, "UART TX: A to B")
for ca, cb, u in (("C79", "C80", "U18"), ("C81", "C82", "U19"), ("C83", "C84", "U20"),
                    ("C85", "C86", "U21")):
    c.C(ca, "100nF", "+3V3", "GND", note=f"{u} VCCA")
    c.C(cb, "100nF", "TGT_VCC", "GND", note=f"{u} VCCB")
c.R("R44", "1k", "TGT_SWDIO_DIR", "GND", note="SWDIO in input (B to A) while the iCE40 is unconfigured: "
    "its weak pull-ups (128 µA max at 3.3 V) give 0.13 V, under the 0.8 V VIL of DIR")
c.R("R45", "33", "TGT_SWDIO_B", "TGT_SWDIO", note="Series termination of the ribbon, as R46-R48")
c.R("R46", "33", "TGT_SWCLK_B", "TGT_SWCLK")
c.R("R47", "33", "TGT_TDI_B", "TGT_TDI")
c.R("R48", "33", "TGT_UART_TX_B", "TGT_UART_TX")
c.R("R49", "100k", "TGT_VCC", "TGT_SWDIO", note="SWDIO idle high during turnaround (ADIv5)")
c.R("R50", "100k", "TGT_VCC", "TGT_SWO", note="Defined level with no target driver")
c.R("R51", "100k", "TGT_UART_RX", "TGT_VCC", note="UART idle high with no target connected")
# STDC14 pin 2 copies the SWDIO direction, as on the STLINK-V3SET (3.3 V, high = probe drives)
c.part("U22", "74xGxx:SN74LVC1G125DBV", "SN74LVC1G125DBVR", "Package_TO_SOT_SMD:SOT-23-5", "C23654",
       {1: "GND", 2: "TGT_SWDIO_DIR", 3: "GND", 4: "TGT_DIR_BUF", 5: "+3V3"}, "Always enabled")
c.C("C87", "100nF", "+3V3", "GND", note="U22")
c.R("R52", "1k", "TGT_DIR_BUF", "TGT_DIR_OUT", note="Limits back-feed into an unpowered target to 3 mA")
# nRST (ESP32 EN) and IO0: open drain, as on the ESP-Prog, so the target keeps them free outside programming
for q, r, net in (("Q5", "R53", "TGT_NRST"), ("Q6", "R54", "TGT_IO0")):
    c.part(q, "Transistor_FET:2N7002", "2N7002", "Package_TO_SOT_SMD:SOT-23", "C8545",
           {1: net + "_3V3", 2: "GND", 3: net}, "Gate high = line pulled low")
    c.R(r, "1k", net + "_3V3", "GND", note="Line released while the iCE40 is unconfigured: 0.13 V against "
        "its weak pull-up, under the 2N7002 threshold")
c.R("R174", "10k", "TGT_NRST", "TGT_NRST_SENSE", note="nRST readback on PB4 (FT): limits injection from a "
    "5 V target to 0.2 mA")
# Target VCC sense: PF11 (ADC1_INP2); 200 kΩ also discharges TGT_VCC when no target is connected
c.R("R55", "100k", "TGT_VCC", "VTREF_SENSE", note="5.5 V -> 2.75 V")
c.R("R56", "100k", "VTREF_SENSE", "GND")
c.C("C88", "100nF", "VTREF_SENSE", "GND", note="ADC sampling reservoir")
ESD = ("Power_Protection:TPD4E05U06DQA", "TPD4E05U06DQAR", "Package_SON:USON-10_2.5x1.0mm_P0.5mm", "C138714")
c.part("U23", *ESD, {1: "TGT_SWDIO", 2: "TGT_SWCLK", 4: "TGT_SWO", 5: "TGT_TDI", 3: "GND", 8: "GND"},
       "ESD at the connectors, flow-through")
c.part("U24", *ESD, {1: "TGT_NRST", 2: "TGT_IO0", 4: "TGT_UART_TX", 5: "TGT_UART_RX", 3: "GND", 8: "GND"})

# --------------------------------------------------------------------------------------------
c.block("Target supply: TPS63020 buck-boost 1.4-5.2 V set by DAC, INA226 monitor")
# TI SLVS916I. FB holds 0.5 V, so Vout = 0.5 + R57 (0.5/R58 + (0.5 - VSET)/R59): 5.29 V at DAC 0 V (5.44 V
# worst case, under the 5.5 V rating), 1.17 V at 3.3 V. hardware/sim/tgt_vsup.py. Preferred 0402 values;
# 120 kΩ loads the DAC, ~15 kΩ with its buffer off, so the firmware runs it buffered (0.2-3.1 V: 1.42-5.04 V)
# and drops the buffer at 0 V for the top (5.22 V); the INA226 bus voltage trims the setpoint.
c.part("U25", "Archet:TPS63020", "TPS63020DSJR", "Archet:Texas_DSJ0014A_VSON-14_3x4mm_P0.5mm", "C15483",
       {10: "+5V", 11: "+5V", 1: "+5V", 12: "TGT_VSUP_EN", 13: "GND", 8: "TGSUP_L1", 9: "TGSUP_L1",
        6: "TGSUP_L2", 7: "TGSUP_L2", 4: "TGT_VSUP_REG", 5: "TGT_VSUP_REG", 3: "TGSUP_FB", 2: "GND",
        15: "GND"},
       "Fed from +5V: true 5 V even with +5V in dropout on a USB port. PS/SYNC low: power save, the "
       "converter never sinks current from a target that holds the rail higher. Load disconnected in "
       "shutdown (§7.3.3). PG unused (no MCU pin left): the INA226 reads the output")
c.C("C89", "10µF 25V", "+5V", "GND", fp=C0805, note="Input, datasheet 2 x 10 µF")
c.C("C90", "10µF 25V", "+5V", "GND", fp=C0805)
c.C("C91", "100nF", "+5V", "GND", note="VINA bypass, datasheet 0.1 µF (0.22 µF max)")
c.part("L4", "Device:L", "1.5µH", "Inductor_SMD:L_Changjiang_FXL0420", "C167205",
       {1: "TGSUP_L1", 2: "TGSUP_L2"},
       "FXL0420-1R5-M: Isat 6 A, Irms 5 A, 46 mΩ. Datasheet 1.5 µH; peak 1.9 A at 1 A out (5.3 V from 4.5 V), "
       "switch limit 4.5 A max, under Isat")
for ref in ("C92", "C93", "C94"):
    c.C(ref, "22µF 25V", "TGT_VSUP_REG", "GND", fp=C1206, note="Output, datasheet 3 x 22 µF")
c.R("R57", "150k", "TGT_VSUP_REG", "TGSUP_FB", note="FB top (datasheet example 1 MΩ)")
c.R("R58", "18k", "TGSUP_FB", "GND", note="FB bottom: 4.67 V with the DAC pin in high-Z (reset)")
c.R("R178", "1k", "TGT_VSET", "TGT_VSET_F", note="Isolates the DAC buffer from C95 (50 pF maximum load "
    "buffered); 0.8 % gain error, trimmed through the INA226")
c.R("R59", "120k", "TGT_VSET_F", "TGSUP_FB", note="DAC injection: -1.25 V per DAC volt, 1 mV per 12-bit step")
c.C("C95", "100nF", "TGT_VSET_F", "GND", note="DAC noise filter; output ramps in ~3 ms with the buffer off")
c.R("R60", "100k", "TGT_VSUP_EN", "GND", note="Converter off until the firmware has set the DAC (EN VIH 1.2 V)")
# Monitor: shunt after the output capacitors, bus voltage read on the connector side.
c.R("R61", "50m", "TGT_VSUP_REG", "TGT_VSUP", note="Shunt: 81.9 mV full scale = 1.64 A; 50 mV at the 1 A limit")
c.part("U26", "Sensor_Energy:INA226", "INA226AIDGSR", "Package_SO:TSSOP-10_3x3mm_P0.5mm", "C49851",
       {10: "TGT_VSUP_REG", 9: "TGT_VSUP", 8: "TGT_VSUP", 6: "+3V3", 7: "GND", 4: "SYS_SDA", 5: "SYS_SCL",
        3: "INA_ALERT", 1: "+3V3", 2: "+3V3"},
       "I2C5 address 0x45 (A1 = A0 = VS). Alert: overcurrent or bus over/undervoltage, set by the firmware")
c.C("C96", "100nF", "+3V3", "GND", note="U26")
c.R("R62", "10k", "+3V3", "INA_ALERT", note="Single pull-up of the wired-OR INA226 alert line (PG1)")
# I2C5 (STUSB4500, INA226s): one pair of pull-ups for the bus. 2 kΩ: ~100 ns rise with ~60 pF, inside the
# 300 ns of 400 kHz Fm; 1.65 mA sink, under the 3 mA of the spec.
c.R("R63", "2k", "+3V3", "SYS_SDA", note="I2C5 SDA pull-up")
c.R("R64", "2k", "+3V3", "SYS_SCL", note="I2C5 SCL pull-up")
c.C("C97", "100nF", "TGT_VSUP", "GND", note="At STDC14 pin 1")

# --------------------------------------------------------------------------------------------
c.block("User interface, standalone flash, field bus: LEDs, buttons, buzzer, W25N02KV, CAN FD / RS-485")
# Standalone images and SWD / SWO trace recording: 256 MB QSPI NAND on OCTOSPI1 (internal ECC, read through the
# page buffer, no memory mapping). NCS pulled up (flash deselected while the MCU is in reset or in the ROM, PE11
# being SPI4 NSS there); IO2 / IO3 pulled up too, so /WP and /HOLD stay inactive outside quad mode.
# Symbol: W25Q128JVE, same WSON-8 8 x 6 pinout (W25N02KV datasheet rev. G fig. 1a); the exposed pad is not
# connected inside (section 11.1 note 1), tied to GND.
c.part("U27", "Memory_Flash:W25Q128JVE", "W25N02KVZEIR", "Archet:WSON-8-1EP_8x6mm_P1.27mm_EP3.4x4.3mm",
       "C17626844",
       {1: "FLASH_NCS", 2: "FLASH_IO1", 3: "FLASH_IO2", 4: "GND", 5: "FLASH_IO0", 6: "FLASH_CLK", 7: "FLASH_IO3",
        8: "+3V3", 9: "GND"}, "Winbond W25N02KV, 2 Gbit SPI NAND, WSON-8 8 x 6, 104 MHz")
c.C("C98", "100nF", "+3V3", "GND", note="U27")
c.R("R65", "10k", "+3V3", "FLASH_NCS", note="Flash deselected until OCTOSPI1 runs")
c.R("R66", "10k", "+3V3", "FLASH_IO2", note="/WP inactive outside quad mode")
c.R("R67", "10k", "+3V3", "FLASH_IO3", note="/HOLD inactive outside quad mode")
# Buttons with a 10 kΩ resistor and a 1 ms RC: clean EXTI edges, defined level with the MCU in reset.
# GO is active high (to +3V3, pull-down) since it also raises BOOT0 through R24; STOP is active low.
BUTTON = ("Switch:SW_Push", "Archet:SW_Push_1P1T_XKB_TS-1187A", "C318884")
for sw, r, cf, net, rail, what in (
        ("SW2", "R68", "C99", "GO_BTN", "+3V3", "GO (active high): programs the target with the stored image; "
         "held at reset, ROM bootloader (R24)"),
        ("SW3", "R69", "C100", "STOP_BTN", "GND", "Emergency stop (active low): target supply and outputs off")):
    high = rail == "+3V3"
    c.part(sw, BUTTON[0], net.split("_")[0], BUTTON[1], BUTTON[2], {1: rail, 2: net} if high else {1: net, 2: rail},
           f"TS-1187A-B-A-B, 5.1 x 5.1 mm. {what}")
    c.R(r, "10k", *((net, "GND") if high else ("+3V3", net)))
    c.C(cf, "100nF", net, "GND", note="Debounce, 1 ms")
# LEDs: MCU ones active low through 1 kΩ (~1.3 mA, indicator brightness), iCE40 ones on the RGB current sinks
# (no resistor, current set in the RGB_DRV IP, 2 mA).
LED_Y = ("Device:LED", "KT-0805Y", "LED_SMD:LED_0805_2012Metric", "C2296")
LED_G = ("Device:LED", "KT-0805G", "LED_SMD:LED_0805_2012Metric", "C2297")
LED_R = ("Device:LED", "NCD0805R1", "LED_SMD:LED_0805_2012Metric", "C84256")
for d, r, led, net, what in (("D10", "R70", LED_Y, "LED_STATUS", "STATUS (PB8, TIM4_CH3), yellow"),
                             ("D11", "R71", LED_G, "LED_PASS", "PASS (PE14, TIM1_CH4), green"),
                             ("D12", "R72", LED_R, "LED_FAIL", "FAIL (PA10, TIM1_CH3), red; ROM pull-up keeps it off")):
    c.part(d, *led, {1: net, 2: net + "_A"}, what)
    c.R(r, "1k", "+3V3", net + "_A")
c.part("D13", *LED_G, {1: "LED_LINK", 2: "+3V3"}, "LINK, green: iCE40 RGB1 (pin 40) current sink")
c.part("D14", *LED_Y, {1: "LED_SPARE", 2: "+3V3"}, "Spare, yellow: iCE40 RGB2 (pin 41) current sink")
# Buzzer: MLT-8530 coil 16 Ω, 95 mA max at 5 Vo-p 2.7 kHz (datasheet), so ~53 Ω at resonance. 22 Ω in series
# brings it to ~3.6 Vo-p, its rating. Held on (gate stuck high), 5 V / 40 Ω = 125 mA: 0.34 W in the 1206, above
# its 0.25 W; the firmware never leaves the pin high (TIM17 PWM, reset and ROM: gate pull-down).
c.part("BZ1", "Device:Buzzer", "MLT-8530", "Archet:Buzzer_HNDZ_MLT-8530", "C94599", {1: "BUZ_P", 2: "BUZ_N"},
       "Passive magnetic transducer, 2.7 kHz resonance, 8.5 x 8.5 mm")
c.R("R73", "22", "+5V", "BUZ_P", fp=R1206, note="Coil to ~3.6 Vo-p from +5V")
c.part("D15", *SCHOTTKY[:3], SCHOTTKY[3], {1: "BUZ_P", 2: "BUZ_N"}, "Flyback across the coil")
c.part("Q7", "Transistor_FET:2N7002", "2N7002", "Package_TO_SOT_SMD:SOT-23", "C8545",
       {1: "BUZZER", 2: "GND", 3: "BUZ_N"}, "Low-side switch, TIM17_CH1 (PB9)")
c.R("R74", "10k", "BUZZER", "GND", note="Silent while PB9 is I2C1 SDA in the ROM bootloader")
# Field bus: TCAN3413 (CAN FD) and THVD2450 (RS-485) share J9, the termination and the ESD; FIELD_SEL_485 picks one.
c.part("U28", "Interface_CAN_LIN:TJA1051T-3", "TCAN3413DR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "C22433320",
       {1: "FIELD_TX", 2: "GND", 3: "+3V3", 4: "CAN_RXD", 5: "+3V3", 6: "FIELD_L", 7: "FIELD_H",
        8: "FIELD_SEL_485"}, "CAN FD 5 Mbit/s, 3.3 V supply (ISO 11898-2, mixes with 5 V nodes): independent "
       "of +5V, which sags below 4.5 V on a 5 V USB source. ±58 V bus fault. TJA1051T/3 pinout (symbol); pin 8 "
       "is STB: high (RS-485 mode) = standby, driver off")
c.C("C101", "100nF", "+3V3", "GND", note="U28 VCC")
c.C("C102", "100nF", "+3V3", "GND", note="U28 VIO")
c.part("U29", "Interface_UART:MAX3485", "THVD2450DR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "C2672621",
       {1: "RS485_RO", 2: "GND", 3: "RS485_DE", 4: "FIELD_TX", 5: "GND", 6: "FIELD_H", 7: "FIELD_L", 8: "+3V3"},
       "RS-485 half duplex, 3.3 V, MAX3485 pinout, 50 Mbit/s. ±70 V bus fault (24 V wired to H or L by mistake), "
       "±25 V common mode, fail-safe receiver. Receiver always on (/RE low); A = H, B = L")
c.C("C103", "100nF", "+3V3", "GND", note="U29")
c.R("R75", "10k", "RS485_DE", "GND", note="RS-485 driver off until the firmware drives PG15")
c.part("U30", "Archet:74LVC1G157", "74LVC1G157GW", "Package_TO_SOT_SMD:SOT-363_SC-70-6", "C135822",
       {3: "CAN_RXD", 1: "RS485_RO", 6: "FIELD_SEL_485", 4: "FIELD_RX", 5: "+3V3", 2: "GND"},
       "RX mux to PD0: S low = CAN (I0), S high = RS-485 (I1)")
c.C("C104", "100nF", "+3V3", "GND", note="U30")
c.R("R76", "10k", "FIELD_SEL_485", "GND", note="CAN by default: ROM bootloader and unprogrammed board")
c.R("R77", "120", "FIELD_H", "FIELD_TERM", fp=R0603, note="Bus termination, CAN and RS-485. 0603 (100 mW): "
    "75 mW with a 3 V RS-485 differential held")
c.part("SW4", "Switch:SW_SPDT", "TERM", "Archet:SW_SPDT_Shouhan_MSK12C02", "C431540",
       {1: "FIELD_L", 2: "FIELD_TERM"}, "MSK-12C02 slide switch: termination on in position 1-2")
c.part("D16", "Power_Protection:NUP2105L", "NUP2105LT1G", "Package_TO_SOT_SMD:SOT-23", "C14486",
       {1: "FIELD_H", 2: "FIELD_L", 3: "GND"}, "Bus ESD, 24 V working: covers CAN and RS-485 common mode")
c.part("J9", "Connector:Screw_Terminal_01x03", "FIELD H/L/GND",
       "Connector_Phoenix_MC:PhoenixContact_MC_1,5_3-G-3.81_1x03_P3.81mm_Horizontal", "C441183",
       {1: "FIELD_H", 2: "FIELD_L", 3: "GND"}, "KF2EDGR-3.81-3P, pluggable (plug KF2EDGK-3.81-3P, C440859)")

# --------------------------------------------------------------------------------------------
c.block("Shield connectors: J_SHIELD_IO, J_SHIELD_SVC, 33 Ω series, ESD, pull-ups")
# Pinout: hardware/connectors.csv. Same IDC 2 x 17 as the Bornier bus. 33 Ω at the header on every logic line
# the probe drives or that may be driven both ways (iCE40 IOs, sync, OE, SWD, UART); I²C, reset (open drain)
# and presence go straight. ESD on all 27 signals, flow-through at the headers.
IDC34 = ("Connector_Generic:Conn_02x17_Odd_Even", "Connector_IDC:IDC-Header_2x17_P2.54mm_Vertical", "C20920")
# Nets: fpga-pins.csv / mcu-pins.csv names on the probe side, suffix _J on the header side of the 33 Ω.
SHIELD_IOS = [f"SHIELD_IO{i}" for i in range(16)]
SVC_SERIES = ["SYNC_IN", "SYNC_OUT", "SHIELD_OE_N", "SHIELD_SWCLK", "SHIELD_SWDIO", "SHIELD_UART_TX",
              "SHIELD_UART_RX"]
io_pins = {2 * i + 2: n + "_J" for i, n in enumerate(SHIELD_IOS)}
io_pins.update({p: "GND" for p in list(range(1, 34, 2)) + [34]})
c.part("J10", IDC34[0], "SHIELD IO", IDC34[1], IDC34[2], io_pins,
       "Shrouded IDC 2 x 17, keyed. Every IO on an even pin between two grounds; 33-34 ground")
SVC = {2: "SYNC_IN_J", 4: "SYNC_OUT_J", 6: "SHIELD_OE_N_J", 8: "SHIELD_SCL", 10: "SHIELD_SDA",
       12: "SHIELD_SWCLK_J", 14: "SHIELD_SWDIO_J", 16: "SHIELD_UART_TX_J", 18: "SHIELD_UART_RX_J", 20: "SHIELD_RESET_N",
       22: "SHIELD_PRESENT_N", 23: "+3V3_OUT", 24: "+3V3_OUT", 27: "+5V_OUT", 28: "+5V_OUT", 29: "+5V_OUT",
       30: "+5V_OUT", 33: "VIN_EXT_P", 34: "VIN_EXT_P"}
SVC.update({p: "GND" for p in list(range(1, 22, 2)) + [25, 26, 31, 32]})
c.part("J11", IDC34[0], "SHIELD SVC", IDC34[1], IDC34[2], SVC,
       "Shrouded IDC 2 x 17, keyed. Services, then +3V3_OUT, +5V_OUT and VIN_EXT, rail groups split by grounds. "
       "VIN_EXT pins behind F1 and D1, both ways: a shield feeding the probe meets the TVS, and a shield drawing "
       "from J1 is fused")
for r, n in enumerate(SHIELD_IOS + SVC_SERIES, 78):           # R78-R100
    c.R(f"R{r}", "33", n, n + "_J", note="Series termination at the header" if r == 78 else "")
c.R("R101", "2k", "+3V3_OUT", "SHIELD_SCL", note="I2C4 pull-ups, as I2C5. On +3V3_OUT, as R103: "
    "nothing back-powers a shield whose rail is off")
c.R("R102", "2k", "+3V3_OUT", "SHIELD_SDA")
c.R("R103", "10k", "+3V3_OUT", "SHIELD_RESET_N", note="Shield out of reset unless PG10 (open drain) pulls it low")
c.R("R104", "10k", "+3V3", "SHIELD_PRESENT_N", note="High with no shield; the shield ties it to ground")
ESD_LINES = [n + "_J" for n in SHIELD_IOS + SVC_SERIES] + ["SHIELD_SCL", "SHIELD_SDA", "SHIELD_RESET_N",
                                                          "SHIELD_PRESENT_N"]
for k in range(7):
    lines = ESD_LINES[4 * k:4 * k + 4]
    pins = {p: n for p, n in zip((1, 2, 4, 5), lines)}
    pins.update({3: "GND", 8: "GND"})
    c.part(f"U{31 + k}", *ESD, pins, "ESD at the shield headers, flow-through" if k == 0 else "")

# --------------------------------------------------------------------------------------------
c.block("Shield supply: TPS259531 eFuses (5V_OUT 2 A, 3V3_OUT 1 A), INA226 monitors")
# TPS2595 datasheet SLVSE57C. ILM (eq. 4): R = 2000 / (I - 0.04): 1 k -> 2.04 A, 2 k -> 1.04 A, ±7.5 %.
# dVdt (eq. 3): C = 42000 pF / SR: 100 nF -> 0.42 V/ms, 5 V in 12 ms; 470 µF on the shield draws ~200 mA
# while rising, so the probe's own +5V does not sag. TPS259531 (5.7 V clamp) on both rails: one part.
# Overcurrent only limits (no FLT): the INA226 reads it and the firmware drops EN. FLT = thermal shutdown.
EFUSE = ("Archet:TPS2595x1", "TPS259531DSGR", "Archet:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
         "C2155674")
INA = ("Sensor_Energy:INA226", "INA226AIDGSR", "Package_SO:TSSOP-10_3x3mm_P0.5mm", "C49851")
for (u, ina, src, raw, out, tag, rilm, ilim, shunt, fs, rs, cdv, ren, rflt, cin, cout, cina, a1, a0, addr) in (
        ("U38", "U39", "+5V", "SH5V_RAW", "+5V_OUT", "5V", "R106", "1k", "15m", "5.46 A", "R105",
         "C105", "R107", "R108", "C106", "C107", "C108", "GND", "GND", "0x40"),
        ("U40", "U41", "+3V3_AUX", "SH3V3_RAW", "+3V3_OUT", "3V3", "R110", "2k", "50m", "1.64 A", "R109",
         "C109", "R111", "R112", "C110", "C111", "C112", "+3V3", "GND", "0x44")):
    c.part(u, *EFUSE, {3: src, 4: src, 2: f"EFUSE_{tag}_EN", 1: f"EFUSE_{tag}_DVDT", 5: raw,
                       6: f"EFUSE_{tag}_FLT", 7: f"EFUSE_{tag}_ILM", 8: "GND", 9: "GND"},
           f"{out} eFuse, {'2.04' if tag == '5V' else '1.04'} A ceiling. EN driven by the MCU (VIH 1.2 V)")
    c.C(cin, "1µF 50V", src, "GND", note="Input")
    c.R(rilm, ilim, f"EFUSE_{tag}_ILM", "GND", note="Current limit (eq. 4)")
    c.C(cdv, "100nF", f"EFUSE_{tag}_DVDT", "GND", note="Slew rate 0.42 V/ms (eq. 3)")
    c.R(ren, "100k", f"EFUSE_{tag}_EN", "GND", note="Off while the MCU pin is high-Z (reset, bootloader)")
    c.R(rflt, "10k", "+3V3", f"EFUSE_{tag}_FLT", note="Open-drain fault, active low")
    c.R(rs, shunt, raw, out, fp=R1206, note=f"Shunt: 81.9 mV full scale = {fs}")
    c.C(cout, "10µF 25V", out, "GND", fp=C0805, note="Output, connector side")
    c.part(ina, *INA, {10: raw, 9: out, 8: out, 6: "+3V3", 7: "GND", 4: "SYS_SDA", 5: "SYS_SCL",
                       3: "INA_ALERT", 1: a1, 2: a0},
           f"{out} monitor, I2C5 address {addr}. Alert on the wired-OR INA_ALERT line")
    c.C(cina, "100nF", "+3V3", "GND", note=ina)

# --------------------------------------------------------------------------------------------
c.block("Local bus: IDC 2 x 17 ribbon to the Bornier extension modules, +3V3_BUS and VIN_BUS switches")
# Taken from Bornier hardware/base/gen/circuit.py (same pinout, terminations, pulls and ESD). MCU-side nets carry
# the mcu-pins.csv names (BUS_*), ribbon-side nets the prefix RB_ behind the 49.9 Ω source terminations.
BUS_PINOUT = {k + 1: f"RB_CS{k}" for k in range(12)} | {
    13: "GND", 14: "+3V3_BUS", 15: "GND", 16: "BUS_SDA", 17: "GND", 18: "BUS_SCL", 19: "GND", 20: "RB_SCK",
    21: "GND", 22: "RB_MOSI", 23: "GND", 24: "BUS_MISO", 25: "GND", 26: "RB_LATCH", 27: "GND", 28: "RB_OE",
    29: "GND", 30: "BUS_IRQ", 31: "+3V3_BUS", 32: "GND", 33: "+VIN_BUS1", 34: "+VIN_BUS2"}
c.part("J12", IDC34[0], "LOCAL BUS", IDC34[1], IDC34[2], BUS_PINOUT,
       "Shrouded, keyed IDC 2 x 17, pinout identical to Bornier. VIN_BUS last, its only neighbour a ground")
# VIN_BUS switches. TPS27S100 datasheet SLVSE42B: R(ILIM) = 1.233 x 2000 / I (eq. 4), limit >= 0.5 A
# recommended: 4.7 k -> 525 mA (±28 %). IMON = I(OUT) / 500 (K(IMON)), linear to 4 V, pulled to 4.3-4.9 V on a
# fault. The two IMON join on one 2 k load: 0.96 A total -> 3.84 V; tap at half -> 1.92 V on PF7, a fault
# 2.15-2.45 V. DIAG_EN high: diagnostics and protections always on. EN: internal 500 k pull-down (off in reset).
SWITCH = ("Archet:TPS27S100B", "TPS27S100BRRKR",
          "Archet:Texas_RRK0016A_WQFN-16-1EP_3.5x4mm_P0.5mm_EP2.05x2.55mm", "C1849486")
for u, out, en, rl, cin, cout in (("U45", "+VIN_BUS1", "VIN_BUS1_EN", "R129", "C129", "C130"),
                                  ("U46", "+VIN_BUS2", "VIN_BUS2_EN", "R130", "C131", "C132")):
    pins = {p: "VIN_BUS" for p in (9, 10, 11, 12)} | {p: out for p in (5, 6, 7, 8)}
    pins.update({3: en, 14: "+3V3", 16: "VIN_BUS_IMON_RAW", 15: f"{u}_ILIM", 2: "GND", 17: "GND"})
    c.part(u, *SWITCH, pins, f"{out}: ribbon pin {33 if out.endswith('1') else 34}, 525 mA limit, MCU enable")
    c.R(rl, "4.7k", f"{u}_ILIM", "GND", note="Current limit 525 mA (eq. 4)")
    c.C(cin, "100nF", "VIN_BUS", "GND", note="Input, at the switch (datasheet table 3)")
    c.C(cout, "22nF", out, "GND", note="Output, ESD immunity (datasheet table 3)")
c.R("R131", "1k", "VIN_BUS_IMON_RAW", "VIN_BUS_IMON", note="IMON load, top half: 2 k in all keeps 0.96 A under 4 V")
c.R("R132", "1k", "VIN_BUS_IMON", "GND")
c.C("C133", "22nF", "VIN_BUS_IMON", "GND", note="ADC filter and sample reservoir: 500 Ω x 22 nF = 11 µs")
# +3V3_BUS. TPS2553 datasheet: I(OS) = 23950 / R(kΩ)^0.977: 47 k -> 556 mA (505-616 mA).
c.part("U44", "Archet:TPS2553", "TPS2553DBVR", "Package_TO_SOT_SMD:SOT-23-6", "C55266",
       {1: "+3V3", 3: "BUS_3V3_EN", 5: "U44_ILIM", 6: "+3V3_BUS", 4: "BUS_3V3_FLT", 2: "GND"},
       "+3V3_BUS: 3.3 V of the ribbon, 505-616 mA limit, MCU enable; a short leaves the probe +3V3 up")
c.R("R127", "47k", "U44_ILIM", "GND", note="I(OS) = 556 mA")
c.R("R128", "100k", "BUS_3V3_EN", "GND", note="Off while the MCU pin is high-Z (reset, bootloader)")
c.R("R133", "10k", "+3V3", "BUS_3V3_FLT", note="Open-drain fault, active low (PD7)")
c.R("R134", "1k", "+3V3", "U44_LED")
c.part("D19", *LED_R, {2: "U44_LED", 1: "BUS_3V3_FLT"}, "FAULT: on while +3V3_BUS is in current limit")
c.C("C127", "100nF", "+3V3", "GND", note="U44 input")
c.C("C128", "10µF 25V", "+3V3_BUS", "GND", fp=C0805, note="U44 output (datasheet: 120 µF max)")
r = 135
for sig in [f"CS{i}" for i in range(12)] + ["LATCH", "OE"]:
    c.R(f"R{r}", "10k", f"BUS_{sig}", "+3V3_BUS", note="Inactive (high) while the MCU pin is not configured; "
        "on +3V3_BUS, as the IRQ and I2C1 pulls: nothing back-powers the modules with the ribbon rail off"
        if sig == "CS0" else "")
    r += 1
for sig in [f"CS{i}" for i in range(12)] + ["SCK", "MOSI", "LATCH", "OE"]:
    c.R(f"R{r}", "49.9", f"BUS_{sig}", f"RB_{sig}", note="Series termination at the source" if sig == "CS0" else "")
    r += 1
for sig in ("SCK", "MOSI", "LATCH"):     # multipoint edges: 2 x 49.9 in parallel = 25 Ω
    c.R(f"R{r}", "49.9", f"BUS_{sig}", f"RB_{sig}", note="In parallel with the first: 25 Ω, first step above 2 V")
    r += 1
c.R(f"R{r}", "10k", "BUS_IRQ", "+3V3_BUS", note="IRQ: wired-OR of open-drain outputs (low with the rail off: "
    "the firmware ignores it then)")
c.R(f"R{r + 1}", "100k", "BUS_MISO", "GND", note="MISO is tri-stated when no module is selected")
c.R(f"R{r + 2}", "100k", "BUS_SCK", "GND", note="SCK low while the MCU pin is not configured: mode 0 idle")
c.R(f"R{r + 3}", "100k", "BUS_MOSI", "GND", note="MOSI defined while the MCU pin is not configured")
c.R(f"R{r + 4}", "2k", "BUS_SDA", "+3V3_BUS", note="I2C1 at 100 kHz, ribbon and 12 modules: rise < 1 µs")
c.R(f"R{r + 5}", "2k", "BUS_SCL", "+3V3_BUS")
assert r + 5 == 173, r
# ESD of every ribbon signal, at the header (order of the lines on the channels as on Bornier)
for k, group in enumerate((("RB_CS2", "RB_CS1", "RB_CS3", "RB_CS0"), ("RB_CS7", "RB_CS5", "RB_CS4", "RB_CS6"),
                           ("RB_CS9", "RB_CS8", "RB_CS11", "RB_CS10"), ("BUS_SDA", "BUS_SCL", "RB_SCK", "RB_MOSI"),
                           ("BUS_MISO", "RB_LATCH", "RB_OE", "BUS_IRQ"))):
    pins = {p: n for p, n in zip((1, 2, 4, 5), group)}
    pins.update({3: "GND", 8: "GND"})
    c.part(f"U{47 + k}", *ESD, pins, "ESD of the ribbon lines at the header, flow-through" if k == 0 else "")
