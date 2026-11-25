# nextpnr pre-pack script: clock constraints in MHz.
ctx.addClock("qspi_clk", 50)  # QSPI DTR, 50 MHz (both edges)
ctx.addClock("refclk", 50)    # MCO2, target and shield logic (test design only)
