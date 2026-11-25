# iCE40 pin assignment check

Test design, not the probe gateware: it drives every pin of
[`hardware/fpga-pins.csv`](../../hardware/fpga-pins.csv) with the IO type it will have
(QSPI DDR registers, tristate SWDIO and shield IOs, open-drain emulation on RGB0), so that
nextpnr validates the placement on the iCE40UP5K-SG48 and reports the clock paths.

Requires the [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build) (yosys,
nextpnr-ice40) in the PATH.

```
make                      # top.pcf from the CSV, synthesis, place and route
nextpnr-ice40 ... --post-route clkpath.py   # clock routing delays, pad to IO registers
```

## Results (OSS CAD Suite 2026-11-25)

- All 37 pins placed, RGB0 (pin 39) included as a plain SB_IO: tristate with output 0
  gives an open drain whatever the pad can do when driven high. `SB_IO_OD` is not
  supported by nextpnr.
- QSPI clock on SPI_SCK (pin 15, not a GBIN): routed through the fabric to a global
  buffer, 3.1 ns, then 0.9 ns to the DDR registers of the IO cells, i.e. ~4 ns plus
  the buffer delays after the data. The capture window is shifted by a static
  ~5 ns of the 10 ns DTR half-period at 50 MHz: the MCU must launch data on the clock
  edge (no quarter-cycle hold, DHQC = 0), to be confirmed on the prototype. The read
  direction is compensated in the MCU by DLYB.
- Logic: 125 MHz on the QSPI clock domain for this test design.
- Real gateware: use `SB_GB_IO` on the GBIN pins (20 reference clock, 23 SYNC_IN) to
  take the dedicated clock path instead of the fabric.
