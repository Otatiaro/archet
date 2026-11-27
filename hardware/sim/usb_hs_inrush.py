# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""USB-C HS port (J5, 5 V only): self-biased soft start Q11 (AO4407A) ahead of the ideal diode U53/Q12.

Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -I usb_hs_inrush.py
USB 2.0 §7.2.4.1 limits a device to 10 uF / 50 uC at attach; VSYS holds ~90 uF. Q11 has no driver:
R179 (gate-source) and R180 (gate to GND) set Vgs = -4.1 V once on, C136 (gate-source) holds Vgs near 0
on a hot plug, C137 (gate-drain) sets the ramp dV/dt = Ig / C137 while the gate sits on its plateau. D21 (gate to GND)
empties C136 when VBUS falls, so a short dropout finds Q11 off again.
Values: hardware/gen/circuit.py, block "USB-C HS port (J5)". MOSFET model: vbus_switch.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngs import run  # noqa: E402
from vbus_switch import MODEL  # noqa: E402

NET = """* J5 VBUS -> Q11 soft start -> ideal diode 5 (body diode while the charge pump starts) -> VSYS_OR
Vsrc src 0 PWL(0 0 {trise} 5)
Rcab src l1 {rcab}
Lcab l1 conn 0.5u
C138 conn 0 1u
M11 hs gate conn AO4407A
R179 conn gate 100k
C136 conn gate 1u
R180 gate 0 22k
D21 0 gate DSCH
C137 gate hs 100n
C140 hs 0 1u
D12 hs vor DBODY
C7 vor e7 47u
Re7 e7 0 0.5
C8 vor 0 1u
R126 vor vsys 15m
Cvs vsys 0 36u
Rload vsys 0 {rload}
.model DBODY D is=1e-11 n=1.3 rs=5m
* 1N5819WS (D21)
.model DSCH D is=3e-6 n=1.1 rs=0.05 cjo=100p
{model}
"""


def attach(trise=1e-6, rcab=0.2, rload=1e6):
    v = run(NET.format(trise=trise, rcab=rcab, rload=rload, model=MODEL), "tran 2u 60m 0 2u uic")
    t, i = v["time"], [-x for x in v["vsrc#branch"]]
    vgs = [a - b for a, b in zip(v["gate"], v["conn"])]
    # Charge drawn in the first 1 ms: the cable charges C138 (1 uF) at once, Q11 must still be off.
    q1 = sum(0.5 * (i[k] + i[k + 1]) * (t[k + 1] - t[k]) for k in range(len(t) - 1) if t[k + 1] < 1e-3)
    late = [(tt, x) for tt, x in zip(t, i) if tt > 1e-3]
    vs = v["vsys"]
    t10 = next(t[k] for k, x in enumerate(vs) if x > 0.42)
    t90 = next(t[k] for k, x in enumerate(vs) if x > 3.8)
    return dict(vgs0=min(x for tt, x in zip(t, vgs) if tt < 1e-3), vgs=vgs[-1], q1=q1,
                ipk=max(x for _, x in late), t10=t10, rise=t90 - t10, vsys=vs[-1])


def dropout(off, rload=12.0, t0=40e-3, unplug=False):
    """VBUS present 40 ms, then gone for `off`, then back: is Q11 re-armed? Hub port cycled (source pulled to
    0 V) or quick replug (`unplug`: the cable opens, J5 VBUS discharges into VSYS through the ideal diode)."""
    netl = NET.format(trise=1e-6, rcab=0.2, rload=rload, model=MODEL)
    if unplug:
        netl = netl.replace("Rcab src l1 0.2", "Rcab src s1 0.2\nSsw s1 l1 sc 0 SWC\n.model SWC SW vt=0.5 ron=1m roff=1e9\n"
                            f"Vsc sc 0 PWL(0 1 {t0} 1 {t0 + 1e-6} 0 {t0 + off} 0 {t0 + off + 1e-6} 1)")
    else:
        netl = netl.replace("PWL(0 0 1e-06 5)", f"PWL(0 0 1u 5 {t0} 5 {t0 + 1e-6} 0 {t0 + off} 0 {t0 + off + 1e-6} 5)")
    v = run(netl, f"tran 2u {t0 + off + 30e-3} 0 2u uic")
    t, i = v["time"], [-x for x in v["vsrc#branch"]]
    back = t0 + off
    # As attach(): charge drawn in the first ms back (C138 alone takes 5 uC), then the peak once Q11 conducts.
    q1 = sum(0.5 * (i[k] + i[k + 1]) * (t[k + 1] - t[k]) for k in range(len(t) - 1) if back <= t[k] and t[k + 1] < back + 1e-3)
    return dict(q1=q1, ipk=max(x for tt, x in zip(t, i) if tt > back))


def main():
    ok = True
    for trise, rcab, rload, what in ((1e-6, 0.2, 1e6, "1 us edge, no load"), (50e-6, 0.2, 1e6, "50 us edge"),
                                     (1e-6, 0.2, 12.0, "1 us edge, 12 Ohm load (0.35 A)")):
        r = attach(trise, rcab, rload)
        print(f"{what:34s}: Vgs at attach {r['vgs0']:5.2f} V (VGS(th) -1.3 V min), {r['q1'] * 1e6:4.1f} uC in the "
              f"first ms, Q11 on after {r['t10'] * 1e3:4.1f} ms, VSYS 10-90 % in {r['rise'] * 1e3:4.1f} ms, peak "
              f"{r['ipk'] * 1e3:4.0f} mA, final Vgs {r['vgs']:.2f} V, VSYS {r['vsys']:.2f} V")
        ok &= r["vgs0"] > -1.0 and r["q1"] < 50e-6 and r["ipk"] < 0.5 and r["vgs"] < -3.8
    # D21 re-arms the soft start. A replug faster than ~10 ms is not physical; a hub cycling its port is.
    for off, unplug, what in ((1e-3, False, "hub port off 1 ms"), (10e-3, False, "hub port off 10 ms"),
                              (10e-3, True, "cable out 10 ms")):
        for rload in (12.0, 50.0):
            d = dropout(off, rload, unplug=unplug)
            print(f"{what:20s}, {rload:2.0f} Ohm load: {d['q1'] * 1e6:5.1f} uC in the first ms back")
            ok &= d["q1"] < 50e-6
    assert ok, "attach inrush above the USB 2.0 limits"


if __name__ == "__main__":
    main()
