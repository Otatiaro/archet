# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Project symbols for the parts that KiCad does not ship; written to ../kicad/archet.kicad_sym.

Pin numbers and names come from the datasheets cited in each symbol.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
from kicadgen.symgen import symbol, write_library  # noqa: E402

LIB = os.path.join(HERE, "..", "kicad", "archet.kicad_sym")
NICK = "Archet"

SYMBOLS = [
    # Abracon ARJM11 datasheet (rev. 01-21-20): schematic 104 (100Base-T PoE+), pin layout 7 (10 pins, LEDs).
    # Line-side centre taps: VC2+/VC2- on the data pairs, VC1+/VC1- on the spare pairs (J4/J5, J7/J8).
    # Pin 6 is not connected inside. LED anodes 13 (left) and 11 (right). SH: the two shield tabs.
    symbol("ARJM11D7-104-AB-EW2", [
        ("9", "VC2+", "passive", "R", 0), ("10", "VC2-", "passive", "R", 1),
        ("7", "VC1+", "passive", "R", 2), ("8", "VC1-", "passive", "R", 3),
        ("1", "TD+", "passive", "R", 5), ("2", "TD-", "passive", "R", 6), ("5", "CT", "passive", "R", 7),
        ("3", "RD+", "passive", "R", 8), ("4", "RD-", "passive", "R", 9),
        ("13", "LED_L+", "passive", "R", 11), ("14", "LED_L-", "passive", "R", 12),
        ("11", "LED_R+", "passive", "R", 13), ("12", "LED_R-", "passive", "R", 14),
        ("SH", "SHIELD", "passive", "B", 1), ("6", "NC", "no_connect", "B", 5),
    ], 8, 18, ref="J", datasheet="https://abracon.com/Magnetics/lan/ARJM11.pdf",
        description="RJ45 jack with 100Base-T PoE+ magnetics (600 mA per pair), green/yellow LEDs, tab up"),
    # SDAPO DP5700 datasheet, table 2. Input side (4, 5, 6) isolated from the output side (1, 2, 3), 1500 V.
    symbol("DP5700-12V2A", [
        ("4", "VIN+", "passive", "L", 0), ("5", "TYP2-DET", "open_collector", "L", 2),
        ("6", "VIN-", "passive", "L", 4),
        ("1", "+VDC", "passive", "R", 0), ("3", "ADJ", "passive", "R", 2), ("2", "-VDC", "passive", "R", 4),
    ], 12, 6, ref="U", datasheet="https://www.sdapo.net",
        description="IEEE 802.3af/at PD module, isolated 12 V 2 A output; TYP2-DET: Type 2 PSE detected"),
    # TI TPS63020 datasheet SLVS916I, 5 (DSJ). Inductor between L1 and L2 on top; 15 = exposed pad (PGND).
    symbol("TPS63020", [
        ("10", "VIN", "power_in", "L", 0), ("11", "VIN", "passive", "L", 1), ("1", "VINA", "power_in", "L", 2),
        ("12", "EN", "input", "L", 5), ("13", "PS/SYNC", "input", "L", 6),
        ("8", "L1", "passive", "T", 1), ("9", "L1", "passive", "T", 2),
        ("6", "L2", "passive", "T", 6), ("7", "L2", "passive", "T", 7),
        ("4", "VOUT", "power_out", "R", 0), ("5", "VOUT", "passive", "R", 1), ("3", "FB", "input", "R", 4),
        ("14", "PG", "open_collector", "R", 5),
        ("2", "GND", "power_in", "B", 5), ("15", "PGND", "power_in", "B", 7),
    ], 10, 9, ref="U", footprint="Archet:Texas_DSJ0014A_VSON-14_3x4mm_P0.5mm",
        datasheet="https://www.ti.com/lit/ds/symlink/tps63020.pdf",
        description="Buck-boost converter, 1.8-5.5 V in, 1.2-5.5 V out, 4 A switches, 2.4 MHz, VSON-14 3x4 mm"),
    # Microchip USB3320 datasheet DS00001792F, table 2-1. Pin 12 must not be connected; flag = GND.
    # Cable side and straps on the left, ULPI (link) side on the right, clock and bias at the bottom left.
    symbol("USB3320C-EZK", [
        ("22", "VBUS", "passive", "L", 0), ("18", "DP", "bidirectional", "L", 2),
        ("19", "DM", "bidirectional", "L", 3), ("23", "ID", "input", "L", 5),
        ("17", "CPEN", "output", "L", 10), ("15", "SPK_L", "passive", "L", 12), ("16", "SPK_R", "passive", "L", 13),
        ("26", "REFCLK", "input", "L", 15), ("25", "XO", "passive", "L", 16), ("24", "RBIAS", "passive", "L", 18),
        ("8", "REFSEL0", "input", "L", 6), ("11", "REFSEL1", "input", "L", 7), ("14", "REFSEL2", "input", "L", 8),
        ("1", "CLKOUT", "output", "R", 0), ("31", "DIR", "output", "R", 1), ("2", "NXT", "output", "R", 2),
        ("29", "STP", "input", "R", 3),
        ("3", "DATA0", "bidirectional", "R", 5), ("4", "DATA1", "bidirectional", "R", 6),
        ("5", "DATA2", "bidirectional", "R", 7), ("6", "DATA3", "bidirectional", "R", 8),
        ("7", "DATA4", "bidirectional", "R", 9), ("9", "DATA5", "bidirectional", "R", 10),
        ("10", "DATA6", "bidirectional", "R", 11), ("13", "DATA7", "bidirectional", "R", 12),
        ("27", "RESETB", "input", "R", 14),
        ("21", "VBAT", "power_in", "T", 2), ("20", "VDD33", "passive", "T", 4), ("32", "VDDIO", "power_in", "T", 7),
        ("28", "VDD18", "power_in", "T", 9), ("30", "VDD18", "power_in", "T", 11),
        ("33", "GND", "power_in", "B", 7), ("12", "NC", "no_connect", "B", 12),
    ], 16, 20, ref="U", footprint="Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm",
        datasheet="https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/"
                  "USB3320-Data-Sheet-DS00001792.pdf",
        description="USB 2.0 HS ULPI transceiver, external 1.8 V; RESETB low: suspended, ULPI outputs high-Z"),
    # Nexperia 74LVC1G157 datasheet (2023), table 3 (SOT363): 1 I1, 2 GND, 3 I0, 4 Y, 5 VCC, 6 S. S low: Y = I0.
    symbol("74LVC1G157", [
        ("3", "I0", "input", "L", 0), ("1", "I1", "input", "L", 1), ("6", "S", "input", "L", 3),
        ("4", "Y", "output", "R", 1),
        ("5", "VCC", "power_in", "T", 2), ("2", "GND", "power_in", "B", 2),
    ], 6, 4, ref="U", footprint="Package_TO_SOT_SMD:SOT-363_SC-70-6",
        datasheet="https://assets.nexperia.com/documents/data-sheet/74LVC1G157.pdf",
        description="Single 2-input multiplexer, 1.65-5.5 V, 5 V tolerant inputs; S low: Y = I0, S high: Y = I1"),
    # TI TPS2595 datasheet SLVSE57C, 6 (DSG): 1 dVdt, 2 EN/UVLO, 3-4 IN, 5 OUT, 6 FLT (x0/x1/x3), 7 ILM,
    # 8 GND, 9 = exposed pad (GND).
    symbol("TPS2595x1", [
        ("3", "IN", "power_in", "L", 0), ("4", "IN", "passive", "L", 1),
        ("2", "EN/UVLO", "input", "L", 3), ("1", "dVdt", "passive", "L", 5),
        ("5", "OUT", "power_out", "R", 0), ("6", "~{FLT}", "open_collector", "R", 3),
        ("7", "ILM", "passive", "R", 5),
        ("8", "GND", "power_in", "B", 2), ("9", "PAD", "passive", "B", 4),
    ], 8, 8, ref="U", footprint="Archet:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
        datasheet="https://www.ti.com/lit/ds/symlink/tps2595.pdf",
        description="eFuse 2.7-18 V, 34 mΩ, 0.5-4 A limit set by ILM resistor, auto-retry; output clamp "
                    "3.8 V (TPS259521), 5.7 V (TPS259531), 13.7 V (TPS259541)"),
    # TI LM5155 datasheet SNVSB75E, 6 (DSS, WSON-12). 13 = exposed pad, tied to AGND.
    symbol("LM5155", [
        ("1", "BIAS", "power_in", "L", 0), ("12", "UVLO/EN/SYNC", "input", "L", 2),
        ("9", "SS", "passive", "L", 4), ("10", "RT", "passive", "L", 6), ("6", "COMP", "passive", "L", 8),
        ("3", "GATE", "output", "R", 0), ("5", "CS", "input", "R", 2), ("11", "PGOOD", "open_collector", "R", 4),
        ("8", "FB", "input", "R", 6),
        ("2", "VCC", "power_out", "T", 4),
        ("4", "PGND", "power_in", "B", 2), ("7", "AGND", "power_in", "B", 4), ("13", "EP", "passive", "B", 6),
    ], 8, 10, ref="U", footprint="Package_SON:WSON-12-1EP_3x2mm_P0.5mm_EP1x2.65",
        datasheet="https://www.ti.com/lit/ds/symlink/lm5155.pdf",
        description="Non-synchronous boost controller, 2.2-45 V input, peak current mode, 100 kHz-2.2 MHz"),
    # TI TPS2553 datasheet SLVS841, DBV pinout: 1 IN, 2 GND, 3 EN (active high), 4 FAULT, 5 ILIM, 6 OUT.
    symbol("TPS2553", [
        ("1", "IN", "power_in", "L", 0), ("3", "EN", "input", "L", 2),
        ("6", "OUT", "power_out", "R", 0), ("4", "~{FAULT}", "open_collector", "R", 2),
        ("5", "ILIM", "passive", "R", 3),
        ("2", "GND", "power_in", "B", 2),
    ], 8, 5, ref="U", footprint="Package_TO_SOT_SMD:SOT-23-6",
        datasheet="https://www.ti.com/lit/ds/symlink/tps2553.pdf",
        description="Power distribution switch, 2.5-6.5 V, 85 mΩ, 75 mA-1.7 A limit set by resistor, active-high EN"),
    # TI TPS27S100 datasheet SLVSE42B, pin functions (B variant, RRK): 2 GND, 3 EN, 5-8 OUT, 9-12 IN,
    # 14 DIAG_EN, 15 ILIM, 16 IMON; 1, 4, 13 not connected; 17 = thermal pad (GND or floating).
    symbol("TPS27S100B", [
        ("9", "IN", "power_in", "L", 0), ("10", "IN", "passive", "L", 1), ("11", "IN", "passive", "L", 2),
        ("12", "IN", "passive", "L", 3), ("3", "EN", "input", "L", 5), ("14", "DIAG_EN", "input", "L", 6),
        ("5", "OUT", "power_out", "R", 0), ("6", "OUT", "passive", "R", 1), ("7", "OUT", "passive", "R", 2),
        ("8", "OUT", "passive", "R", 3), ("16", "IMON", "passive", "R", 5), ("15", "ILIM", "passive", "R", 6),
        ("2", "GND", "power_in", "B", 1), ("17", "PAD", "passive", "B", 3),
        ("1", "NC", "no_connect", "T", 1), ("4", "NC", "no_connect", "T", 2), ("13", "NC", "no_connect", "T", 3),
    ], 8, 8, ref="U", footprint="Archet:Texas_RRK0016A_WQFN-16-1EP_3.5x4mm_P0.5mm_EP2.05x2.55mm",
        datasheet="https://www.ti.com/lit/ds/symlink/tps27s100.pdf",
        description="High-side switch 3.5-40 V, 80 mΩ, adjustable current limit, current monitor IMON (1/500)"),
]


TABLES = {
    "sym-lib-table": f'(sym_lib_table\n  (version 7)\n  (lib (name "{NICK}")(type "KiCad")'
                     f'(uri "${{KIPRJMOD}}/archet.kicad_sym")(options "")(descr "Archet project symbols"))\n)\n',
    "fp-lib-table": f'(fp_lib_table\n  (version 7)\n  (lib (name "{NICK}")(type "KiCad")'
                    f'(uri "${{KIPRJMOD}}/archet.pretty")(options "")(descr "Archet project footprints"))\n)\n',
}


def write():
    """Writes the symbol library and the project library tables; returns {nickname: path} for Project."""
    write_library(LIB, SYMBOLS)
    kicad = os.path.dirname(LIB)
    os.makedirs(os.path.join(kicad, "archet.pretty"), exist_ok=True)
    for name, text in TABLES.items():
        with open(os.path.join(kicad, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return {NICK: LIB}


if __name__ == "__main__":
    print(write())
