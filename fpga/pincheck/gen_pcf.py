"""Generate top.pcf from hardware/fpga-pins.csv (single source of truth).

Usage: python gen_pcf.py ../../hardware/fpga-pins.csv > top.pcf
Port name = net name in lower case, without the FPGA_ prefix and the _3V3 suffix;
numbered buses (QSPI_IOn, SHIELD_IOn) become vectors.
"""
import csv, re, sys

print("# Generated from hardware/fpga-pins.csv by gen_pcf.py: do not edit.")
for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")):
    name = r["net"].lower().removeprefix("fpga_").removesuffix("_3v3")
    name = {"irq": "fpga_irq"}.get(name, name)
    m = re.fullmatch(r"(qspi_io|shield_io)(\d+)", name)
    if m:
        name = f"{m.group(1)}[{m.group(2)}]"
    print(f"set_io {name} {r['pin']}")
