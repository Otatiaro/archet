# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""TGT_VSUP: TPS63020 output set by DAC1_OUT1 (PA4) injecting into the FB divider.

Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -I tgt_vsup.py
The TPS63020 is modelled by what sets its DC output: a loop that holds FB at VFB (high-gain VCVS).
Switching behaviour is covered by the datasheet design equations (section 8.2.2), evaluated at the corners.
Values: hardware/gen/circuit.py, block "Target supply".
"""
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngs import run  # noqa: E402

R1, R2, R3 = 150e3, 18e3, 120e3       # FB top, FB bottom, DAC injection
CDAC = 100e-9                          # filter on the DAC node
VFB = (0.495, 0.500, 0.505)            # datasheet SLVS916I, 6.5: min, typ, max
VDDA = 3.3
TOL = 0.01                             # 1 % resistors
VOUT_ABS = 5.5                         # recommended maximum output (6.3); OVP 5.5-7 V

NET = """* TGT_VSUP FB injection
Vdac dac0 0 {vdac}
Rdac dac0 vset {rdac}
Cdac vset 0 {cdac}
R3 vset fb {r3}
R1 out fb {r1}
R2 fb 0 {r2}
Eloop out 0 vol = 'min(max(1e5*({vfb} - v(fb)), 0), 7)'
Cout out 0 66u
Rload out 0 5
"""


def net(vdac=0.0, rdac=1.0, r1=R1, r2=R2, r3=R3, vfb=0.5):
    return NET.format(vdac=vdac, rdac=rdac, cdac=CDAC, r1=r1, r2=r2, r3=r3, vfb=vfb)


def vout(vdac, **kw):
    return run(net(vdac, **kw), "op")["out"][0]


def main():
    print("## Nominal transfer, buffered DAC (0 ohm)")
    sweep = run(net(), "dc vdac 0 3.3 0.1")
    v = sweep["out"]
    for k in range(0, len(v), 3):
        print(f"  DAC {k * 0.1:4.2f} V -> {v[k]:.3f} V")
    gain = (v[0] - v[-1]) / 3.3
    print(f"  slope {gain:.4f} V/V, 12-bit step {gain * VDDA / 4096 * 1000:.2f} mV")

    print("## DAC buffer off (output impedance ~15 kohm)")
    for vd in (0.0, 1.65, 3.3):
        print(f"  DAC {vd:4.2f} V -> {vout(vd, rdac=15e3):.3f} V (buffered {vout(vd):.3f} V)")
    print("## DAC buffer on, its range 0.2 V .. VDDA - 0.2 V")
    print(f"  {vout(3.1):.3f} .. {vout(0.2):.3f} V")

    print("## DAC pin high-Z (reset state: analog mode)")
    print(f"  {vout(0.0, rdac=1e12):.3f} V")

    print("## Worst case: 1 % resistors, VFB 495-505 mV (2^4 corners)")
    hi, lo = [], []
    for s1, s2, s3, vfb in itertools.product((-1, 1), (-1, 1), (-1, 1), (VFB[0], VFB[2])):
        kw = dict(r1=R1 * (1 + s1 * TOL), r2=R2 * (1 + s2 * TOL), r3=R3 * (1 + s3 * TOL), vfb=vfb)
        hi.append(vout(0.0, **kw))
        lo.append(vout(VDDA, **kw))
    print(f"  DAC 0 V    : {min(hi):.3f} .. {max(hi):.3f} V (limit {VOUT_ABS} V)")
    print(f"  DAC 3.3 V  : {min(lo):.3f} .. {max(lo):.3f} V (TPS63020 minimum 1.2 V)")
    assert max(hi) < VOUT_ABS, "maximum output above the recommended range"
    assert max(lo) < 1.65, "1.8 V targets out of reach"

    print("## DAC step 3.3 -> 0 V, buffer off: output slew through the 100 nF filter")
    t = run(NET.replace("Vdac dac0 0 {vdac}", "Vdac dac0 0 pulse(3.3 0 1m 1u 1u 1 2)").format(
        rdac=15e3, cdac=CDAC, r1=R1, r2=R2, r3=R3, vfb=0.5), "tran 10u 12m")
    tt, vo = t["time"], t["out"]
    v10 = vo[0] + 0.1 * (vo[-1] - vo[0])
    v90 = vo[0] + 0.9 * (vo[-1] - vo[0])
    t10 = next(x for x, y in zip(tt, vo) if y >= v10)
    t90 = next(x for x, y in zip(tt, vo) if y >= v90)
    print(f"  {vo[0]:.2f} -> {vo[-1]:.2f} V, 10-90 % in {(t90 - t10) * 1e3:.2f} ms")

    print("## Inductor peak current (datasheet 8.2.2.2), L = 1.5 uH -20 %, f = 2.4 MHz -10 %")
    L, f, eta = 1.5e-6 * 0.8, 2.4e6 * 0.9, 0.85
    worst = (0, None)
    for vin, vo_, io in itertools.product((4.5, 5.0, 5.25), (1.25, 1.8, 3.3, 5.0, 5.3), (1.0,)):
        if vo_ > vin:                                     # boost
            d = 1 - vin * eta / vo_
            ip = io / (eta * (1 - d)) + vin * d / (2 * f * L)
        else:                                             # buck
            d = vo_ / (vin * eta)
            ip = io + (vin - vo_) * d / (2 * f * L)
        worst = max(worst, (ip, (vin, vo_)))
    print(f"  at the 1 A firmware limit: {worst[0]:.2f} A (Vin {worst[1][0]} V, Vout {worst[1][1]} V)")
    print("  overload before the firmware acts: switch current limit 4.5 A max, FXL0420-1R5 Isat 6 A")


if __name__ == "__main__":
    main()
