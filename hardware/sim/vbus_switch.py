# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Q4 (AO4407A) USB-C sink switch: turn-on inrush into the VSYS capacitors, hot plug, PD 5 -> 20 V step.

Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -I vbus_switch.py
Values: hardware/gen/circuit.py, blocks "USB-C" and "Source OR-ing".
MOSFET: ngspice VDMOS fitted to the UMW AO4407A datasheet (Nov. 2024): transfer curve (fig. 2,
-ID = 20 A at VGS = -3.2 V, 60 A at -4 V), RDS(on) 9.5 mOhm at -10 V, Ciss 2050 pF, Crss 300 pF at -15 V,
Qgd ~10 nC (fig. 7, checked below). SOA: fig. 10, single-pulse power vs pulse width.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngs import run  # noqa: E402

MODEL = (".model AO4407A VDMOS pchan vto=-2.2 kp=40 rd=5m rs=1m rg=3.2 "
         "cgdmax=1.4n cgdmin=0.25n a=0.6 cgs=2.4n cjo=0.25n is=1e-12 n=1.2 rb=5m")
# Fig. 10, single-pulse power rating junction-to-ambient (1 in2 FR-4), read at decade points.
SOA = ((1e-5, 5000), (1e-4, 1200), (1e-3, 150), (1e-2, 60), (1e-1, 15))


def soa_limit(width):
    """Log-log interpolation of fig. 10."""
    pts = [(math.log10(w), math.log10(p)) for w, p in SOA]
    x = math.log10(min(max(width, SOA[0][0]), SOA[-1][0]))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return 10 ** (y0 + (y1 - y0) * (x - x0) / (x1 - x0))
    return SOA[-1][1]


def caps(vbus):
    """VSYS side capacitance at the bias it sees (X7R 1206 50 V: ~90 % at 5 V, ~55 % at 20 V)."""
    k = 0.9 if vbus < 10 else 0.55
    return 10e-6 * k


NET = """* Q4 sink switch, USB-C source to VSYS
Vsrc src 0 {vsrc}
Rcab src l1 0.1
Lcab l1 conn 0.5u
* Q4: drain VBUS_USB, gate VBUS_GATE, source VBUS_CONN
M4 usb gate conn AO4407A
R10 conn gate 100k
C134 conn gate {c134}
* C141 + R181: gate-drain (Miller) soft start, the ramp dV/dt = Ig / C141 on the gate plateau
C141 usb gd {cgd}
R181 gd gate 1k
R11 gate en 10k
Sen en 0 ctl 0 SWEN
Vctl ctl 0 {vctl}
Ren en 0 1G
* VBUS_USB: C4; ideal diode Q2 still on its body diode (charge pump not up)
C4 usb 0 1u
D2 usb vor DBODY
C7 vor e7 47u
Re7 e7 0 0.5
C8 vor 0 1u
R126 vor vsys 15m
Cvs vsys 0 {cvs}
Rload vsys 0 50
.model SWEN SW vt=0.5 ron=30 roff=1e9
.model DBODY D is=1e-11 n=1.3 rs=5m
{model}
.ic v(gate)={vic} v(conn)={vic} v(src)={vic} v(usb)=0 v(vor)=0 v(vsys)=0
"""


def net(vsrc, vctl, vbus, c134=1e-6, cgd=100e-9, vic=None):
    return NET.format(vsrc=vsrc, vctl=vctl, c134=c134, cgd=max(cgd, 1e-15), cvs=4 * caps(vbus), model=MODEL,
                      vic=vbus if vic is None else vic)


def trace(v, name):
    return v[name]


def turn_on(vbus, c134=1e-6, cgd=100e-9):
    """Attach: VBUS_EN_N pulled low at t = 0.1 ms, VBUS already present."""
    v = run(net(f"DC {vbus}", "PWL(0 0 100u 0 100.1u 1)", vbus, c134, cgd), "tran 1u 30m 0 1u uic")
    t, i = v["time"], [-x for x in v["vsrc#branch"]]
    vds = [a - b for a, b in zip(v["conn"], v["usb"])]
    p = [a * b for a, b in zip(i, vds)]
    e = sum(0.5 * (p[k] + p[k + 1]) * (t[k + 1] - t[k]) for k in range(len(t) - 1))
    pk = max(p)
    width = e / pk
    vs = v["vsys"]
    v10 = next(t[k] for k, x in enumerate(vs) if x > 0.1 * (vbus - 0.8))
    v90 = next(t[k] for k, x in enumerate(vs) if x > 0.9 * (vbus - 0.8))
    vgs = min(a - b for a, b in zip(v["gate"], v["conn"]))
    return dict(ipk=max(i), ppk=pk, e=e, width=width, soa=soa_limit(width), rise=v90 - v10, t10=v10, vgs=vgs)


def hot_plug(vbus, trise):
    """Cable plugged into a live source: VBUS_CONN steps from 0, STUSB4500 unpowered (VBUS_EN_N open)."""
    v = run(net(f"PWL(0 0 {trise} {vbus})", "0", vbus, vic=0), f"tran {trise / 50} {trise * 20 + 2e-3} 0 {trise / 50} uic")
    vgs = min(a - b for a, b in zip(v["gate"], v["conn"]))
    return dict(vgs=vgs, iq=max(-x for x in v["vsrc#branch"]), vsys=max(v["vsys"]))


def pd_step(v0=5.0, v1=20.0, slew=0.03e6):
    """PD transition with Q4 on: the source slews at most 30 mV/us (USB PD vSrcSlewPos)."""
    t1 = (v1 - v0) / slew
    vb = net(f"PWL(0 {v0} 1m {v0} {1e-3 + t1} {v1})", "1", v1, vic=v0)
    # Start from steady state at v0: switch closed, gate at its divided level, capacitors charged.
    vb = vb.replace(f".ic v(gate)={v0}", f".ic v(gate)={v0 - 0.91 * v0}").replace(
        "v(usb)=0 v(vor)=0 v(vsys)=0", f"v(usb)={v0} v(vor)={v0 - 0.7} v(vsys)={v0 - 0.7}")
    v = run(vb, f"tran 0.5u {1e-3 + t1 + 1e-3} 0 0.5u uic")
    t, i = v["time"], [-x for x in v["vsrc#branch"]]
    ipk = max(x for tt, x in zip(t, i) if tt > 1.05e-3)
    return dict(ipk=ipk, t=t1)


def gate_charge():
    """Fig. 7 check: constant 1 mA out of the gate, -15 V through 1.07 Ohm (ID = -14 A); Qgd = plateau charge."""
    netl = f"""* gate charge
Vd d 0 -15
Rload x d 1.07
M1 x g 0 AO4407A
Ig g 0 1m
Rleak g 0 1G
{MODEL}
"""
    v = run(netl + ".ic v(g)=0 v(x)=-15\n", "tran 0.05u 60u 0 0.05u uic")
    t, vg, vx = v["time"], v["g"], v["x"]
    q = [1e-3 * x for x in t]
    k0 = next(k for k, x in enumerate(vx) if x > -14.5 and t[k] > 0.5e-6)
    k1 = next(k for k, x in enumerate(vx) if x > -0.5)
    k10 = next(k for k, x in enumerate(vg) if x < -10)
    return dict(qgs=q[k0] * 1e9, qgd=(q[k1] - q[k0]) * 1e9, qg10=q[k10] * 1e9)


def main():
    gc = gate_charge()
    print(f"model check (fig. 7: Qgs 6, Qgd 10, Qg(-10 V) 40 nC): Qgs {gc['qgs']:.1f}, Qgd {gc['qgd']:.1f}, "
          f"Qg(-10 V) {gc['qg10']:.1f} nC")
    ok = True
    print("\nturn-on, VBUS_EN_N low at 0.1 ms (VSYS ~ 47 uF electrolytic + 4 x 10 uF ceramics):")
    for vbus, c134, cgd, tag in ((5.0, 1e-6, 100e-9, "C134 1 uF + C141"), (20.0, 1e-6, 100e-9, "C134 1 uF + C141"),
                                 (5.0, 100e-9, 0.0, "C134 100 nF only"), (5.0, 0.0, 0.0, "bare gate")):
        r = turn_on(vbus, c134, cgd)
        margin = r["soa"] / r["ppk"]
        print(f"  {vbus:4.0f} V {tag:16s}: start {r['t10'] * 1e3:.2f} ms, VSYS 10-90 % in {r['rise'] * 1e6:6.0f} us, "
              f"peak {r['ipk']:5.2f} A, {r['ppk']:5.1f} W, {r['e'] * 1e3:5.2f} mJ "
              f"(equivalent {r['width'] * 1e6:5.0f} us pulse, fig. 10 allows {r['soa']:6.0f} W: x{margin:.1f}), "
              f"Vgs {r['vgs']:.1f} V")
        if cgd and vbus == 5.0:
            # Attach on vSafe5V: stay within the Type-C default current (500 mA from a USB 2.0 port).
            ok &= margin > 3 and r["ipk"] < 0.5
    print("\nhot plug, STUSB4500 unpowered (VBUS_EN_N open):")
    for vbus, tr in ((5.0, 1e-6), (20.0, 1e-6), (5.0, 50e-6)):
        r = hot_plug(vbus, tr)
        print(f"  {vbus:4.0f} V in {tr * 1e6:3.0f} us: Vgs min {r['vgs']:6.2f} V (VGS(th) -1.3 V min), "
              f"VSYS max {r['vsys']:.2f} V, peak current {r['iq']:.2f} A")
        # A compliant source attaches at 5 V. At 20 V (non-compliant) C141 couples -1.8 V onto the gate:
        # Q4 barely conducts, the check is the current.
        ok &= r["vgs"] > -1.0 if vbus < 10 else r["iq"] < 0.2
    r = pd_step()
    print(f"\nPD 5 -> 20 V at 30 mV/us ({r['t'] * 1e3:.2f} ms), Q4 on: peak current {r['ipk']:.2f} A")
    assert ok, "inrush or hot-plug margin not met"


if __name__ == "__main__":
    main()
