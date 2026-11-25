# Archet

Open-source debug and production-test probe, and hardware-in-the-loop (HIL) platform.

- SWD and JTAG with **reliable simultaneous SWO**, on separate hardware paths;
- ARM, RISC-V and ESP32 (Xtensa) targets;
- USB HS (USB-C, PD) and 100 Mbit/s Ethernet with PoE+, IEEE 1588 clock synchronisation;
- HIL platform: real-time rules on raw IOs (≤ 1 µs), edge timestamping, safe state; each project only adds a simple shield, or [Bornier](https://github.com/bornier-dev/bornier) modules;
- host side: probe-rs, CMSIS-DAP v2 compatibility, Rust/Python library and MCP server.

Built around an STM32H723 and a Lattice iCE40UP5K, manufacturable at JLCPCB with no BGA.

**Status:** architecture draft, no hardware yet.

## Documentation

- [Architecture](docs/architecture.md): goals, decisions, block diagram, MCU ↔ FPGA link, power, pinout constraints, sourcing and cost.

## Related projects

- [OpSy](https://github.com/Otatiaro/OpSy): firmware runtime (C++26);
- [SvdGenerator](https://github.com/Otatiaro/SvdGenerator): register headers;
- [Bornier](https://github.com/bornier-dev/bornier): DIN-rail IO modules, shared local bus.

## Contributing

All content in this repository is in English: code, comments, documentation, commit messages and pull requests.

## License

[MIT](LICENSE), hardware, gateware, firmware and software alike.
