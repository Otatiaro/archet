# nextpnr post-route script: routing delay of each clock from its pad to the global
# buffer, then from the buffer to the IO cells it clocks (DDR registers).
for name, net in ctx.nets:
    if not any(c in name for c in ("qspi_clk", "refclk")):
        continue
    for user in net.users:
        cell = user.cell
        if not (cell.type.startswith("SB_IO") or cell.type == "SB_GB"):
            continue
        d = ctx.getNetinfoRouteDelay(net, user)
        print(f"CLKPATH {name} -> {cell.name}.{user.port}: {ctx.getDelayNS(d):.2f} ns")
