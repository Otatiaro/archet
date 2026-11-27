# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Source OR-ing: MX74700T + CSD18543Q3A ideal diodes into VSYS_OR (U1 VIN_EXT, U2 USB-C PD, U3 PoE;
U53 USB-C HS, 5 V only, see usb_hs_inrush.py) and VIN_EXT into VIN_BUS (U52/Q10). Source handover,
reverse current on a shorted input.

Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -I oring.py
The MX74700T (same pinout and thresholds as the TI LM74700) is modelled by its reverse-blocking
comparator, with the LM74700 figures (datasheet SNOSD17G, 6.5/6.6; MX74700T datasheet identical):
V(AK REV) -17 mV worst case, tReverse delay 0.75 us max (applied as a delay on V(AK), also on turn-on,
where the datasheet gives 2.6 us max), on again above +30 mV, then a 2.37 A gate sink (switch-off in a few ns
for the 11 nC of the CSD18543Q3A, neglected). Forward: the MOSFET (8.1 mOhm at 10 V) or its body diode.
The regulation of V(AK) to 20 mV at light load is not modelled (it only matters below ~2.5 A).
Values: hardware/gen/circuit.py, blocks "Source OR-ing" and "VIN_BUS". Parasitics are estimates:
10 nH between the VSYS capacitors and each MOSFET, 0.1 Ohm + 0.5-1 uH per cable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngs import run  # noqa: E402

VREV, TREV = -0.017, 0.75e-6           # worst-case reverse threshold and turn-off delay
VON = 0.03                             # back on once the body diode conducts (V(AK) above the 20 mV regulation)
RDS = 8.1e-3
IDM, EAS = 156.0, 55e-3                # CSD18543Q3A: pulsed drain current, single-pulse avalanche energy

SUBCKT = f""".subckt IDEAL a k
Bc c0 0 V = max(-1, min(1, v(a)-v(k)))
T1 c0 0 c1 0 Z0=50 TD={TREV}
Rt c1 0 50
S1 a k c1 0 SWF
D1 a k DB
.model SWF SW vt={(VREV + VON) / 2} vh={(VON - VREV) / 2} ron={RDS} roff=1e5
.model DB D is=1e-11 n=1.3 rs=5m bv=65 ibv=1m cjo=300p
.ends
"""

BASE = """* OR-ing
{sources}
* U1 / Q1: VIN_EXT. Cq1 = C8 (1 uF) placed at the Q1 drain (layout rule: without it the 10 nH loop kicks the drain to 83 V)
C2 vext 0 1u
D1tvs 0 vext DTVS
X1 vext q1 IDEAL
Cq1 q1 0 1u
L1 q1 vor 10n
* U2 / Q2: USB-C after Q4
C4 vusb 0 1u
X2 vusb q2 IDEAL
Cq2 q2 0 1n
L2 q2 vor 10n
* U3 / Q3: PoE 12 V
C6 vpoe 0 1u
X3 vpoe q3 IDEAL
Cq3 q3 0 1n
L3 q3 vor 10n
* VSYS_OR: C7 (ESR 0.5 Ohm), C8 at Q1 (above); R126; VSYS ceramics 4 x 10 uF 50 V (~5 uF each at 20-24 V)
C7 vor e7 47u
Re7 e7 0 0.5
R126 vor vsys 15m
Cvs vsys 0 20u
Rload vsys 0 {rload}
* U52 / Q10: VIN_EXT into VIN_BUS, C121-C124 (~3 uF each at 24 V); Cq10 = one of them at the Q10 drain (layout rule)
X52 vext q10 IDEAL
Cq10 q10 0 1u
L10 q10 vbus 10n
Cvb vbus 0 9u
Rvb vbus 0 {rvbus}
.options method=gear reltol=1e-3 abstol=1e-9 itl4=50
.model DTVS D is=1e-12 n=1.5 bv=26.7 ibv=1m rs=0.1
{subckt}
"""


def sim(sources, rload, rvbus, tstop, ics, step="20n"):
    netl = BASE.format(sources=sources, rload=rload, rvbus=rvbus, subckt=SUBCKT) + f".ic {ics}\n"
    return run(netl, f"tran {step} {tstop} 0 {step} uic")


def unplug():
    """USB-C 20 V feeding 2.5 A, PoE 12 V present; the USB-C cable is pulled at 1 ms."""
    src = """Vu su 0 20
Su su u1 ctl 0 SWU
Vctl ctl 0 PWL(0 1 1m 1 1.0001m 0)
Ru u1 u2 0.1
Lu u2 vusb 0.5u
Vp sp 0 12
Rp sp vpoe 0.05
Vx vext 0 0
.model SWU SW vt=0.5 ron=1m roff=1e6"""
    v = sim(src, 8, 1e6, "3m", "v(vusb)=20 v(vor)=20 v(vsys)=20 v(vpoe)=12 v(vbus)=0 v(q1)=20 v(q2)=20 v(q3)=20", "0.2u")
    t, vs = v["time"], v["vsys"]
    after = [(tt, x) for tt, x in zip(t, vs) if tt > 1e-3]
    vmin = min(x for _, x in after)
    t12 = next(tt for tt, x in after if x < 12.0)
    return dict(vmin=vmin, t12=t12 - 1e-3, irev=max(v["vp#branch"]))


def pd_step():
    """PoE 12 V feeding 2.5 A; the USB-C source goes 5 -> 20 V at 30 mV/us and takes over."""
    src = """Vu su 0 PWL(0 5 0.2m 5 0.7m 20)
Ru su u2 0.1
Lu u2 vusb 0.5u
Vp sp 0 12
Rp sp vpoe 0.05
Vx vext 0 0"""
    v = sim(src, 4.8, 1e6, "1.2m", "v(vusb)=5 v(vor)=12 v(vsys)=12 v(vpoe)=12 v(vbus)=0 v(q1)=12 v(q2)=12 v(q3)=12", "0.1u")
    # Current into the PoE module = positive branch current of Vp (SPICE convention: into the + node).
    return dict(irev=max(v["vp#branch"]), vsys=max(v["vsys"]))


def short_vext():
    """VIN_EXT 24 V feeds VSYS (2.5 A) and VIN_BUS (1 A); USB-C 20 V present; J1 shorted at 50 us."""
    src = """Vs se 0 24
Rs se e1 0.1
Ls e1 vext0 1u
Rf vext0 vext 15m
Sshort vext sh ctl 0 SWS
Lsh sh 0 50n
Vctl ctl 0 PWL(0 0 50u 0 50.01u 1)
Vu su 0 20
Ru su u2 0.1
Lu u2 vusb 0.5u
Vp vpoe 0 0
.model SWS SW vt=0.5 ron=10m roff=1e6"""
    v = sim(src, 9.6, 24, "150u", "v(vext)=24 v(vext0)=24 v(vusb)=20 v(vor)=24 v(vsys)=24 v(vbus)=24 v(q1)=24 v(q2)=24 v(q3)=24 v(q10)=24", "2n")
    t = v["time"]
    i1, i52 = v["l1#branch"], v["l10#branch"]    # positive = forward (MOSFET to output)
    win = [k for k, tt in enumerate(t) if tt > 50e-6]
    irev1, irev52 = -min(i1[k] for k in win), -min(i52[k] for k in win)
    vk = max(v["q1"][k] for k in win)
    vmin = min(v["vsys"][k] for k in win)
    # Reverse charge and energy lost by VSYS before Q1 opens.
    return dict(irev1=irev1, irev52=irev52, vkmax=vk, vmin=vmin, vend=v["vsys"][-1], vbus=v["vbus"][-1])


def main():
    r = unplug()
    print(f"USB-C 20 V pulled (2.5 A load), PoE 12 V takes over: VSYS reaches 12 V after {r['t12'] * 1e6:.0f} us, "
          f"minimum {r['vmin']:.2f} V; current into the PoE module {r['irev']:.2f} A")
    assert r["vmin"] > 11.0
    r = pd_step()
    print(f"PoE 12 V feeding, USB-C 5 -> 20 V at 30 mV/us: reverse current into the PoE module {r['irev']:.2f} A, "
          f"VSYS {r['vsys']:.1f} V")
    assert r["irev"] < 3.0
    r = short_vext()
    print(f"VIN_EXT 24 V feeding, J1 shorted: reverse peak Q1 {r['irev1']:.1f} A, Q10 {r['irev52']:.1f} A "
          f"(IDM {IDM:.0f} A), Q1 drain peak {r['vkmax']:.1f} V (60 V rating), VSYS min {r['vmin']:.1f} V, "
          f"then VSYS {r['vend']:.1f} V from USB-C; reverse pulses < 1 us, IDM rated for 100 us")
    assert r["irev1"] < IDM and r["irev52"] < IDM and r["vkmax"] < 60      # MX74700T CATHODE-ANODE 75 V


if __name__ == "__main__":
    main()
