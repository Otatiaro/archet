# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""VIN_BUS boost: LM5155 peak current mode, VSYS 4.5-20 V to 24.5 V.

Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -I boost.py
Values: hardware/gen/circuit.py, block "VIN_BUS boost". Datasheet SNVSB75E.

1. Design equations at the corners (duty cycle, ripple, peak current, current limit, slope).
2. Small-signal loop gain (current mode, Ridley sampling model): crossover and phase margin.
3. Cycle-by-cycle switching simulation (ngspice): soft start, load steps up and down.

The controller is modelled by what the datasheet describes (figures 9-17 to 9-19):
PWM reset when  RS.IL + (40 mV + ISLOPE.RSL).t/T + 0.17 V  >=  0.142 . COMP     (GCOMP = 0.142)
current limit   RS.IL + ISLOPE.RSL.t/T >= VCLTH (100 mV)
error amplifier gm 2 mA/V, Ro 10 MΩ, COMP clamped 1.0-2.8 V; maximum duty 1 - 100 ns . fsw.
"""
import cmath
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngs import run  # noqa: E402

# --- design values (circuit.py) ---
RT = 51e3
FSW = 2.21e10 / (RT + 955)            # eq. 5
L, DCR = 10e-6, 30e-3                  # FXL1040-100-M
RS = 15e-3                             # WSL1206R0150FEA
RSL, RF, CF = 470.0, 100.0, 100e-12    # slope resistor, CS filter
RSL_EFF = RSL + RF                     # ISLOPE flows through both
RFBT, RFBB = 47e3, 2e3
VREF = 1.0
VOUT = VREF * (1 + RFBT / RFBB)
RCOMP, CCOMP, CHF = 3.3e3, 100e-9, 470e-12
CSS = 22e-9
COUT = 4 * 3.0e-6                      # 4 x 10 µF 50 V 1206 X7R, ~3 µF each left at 24 V DC bias
ESR = 3e-3
CIN = 2 * 3.5e-6 + 47e-6               # boost input ceramics + the VSYS bulk (C7)
VF = 0.45                              # SS54 at ~1-3 A
RDS = 11e-3                            # CSD18543Q3A at VGS 4.5 V
GM, RO, GCOMP = 2e-3, 10e6, 0.142
ISLOPE, VSLOPE = 30e-6, 0.040
VCLTH = (0.093, 0.100, 0.107)

CORNERS = (  # VSYS, light load, full load (A at VIN_BUS)
    (4.5, 0.05, 0.5),      # 5 V USB after the ideal diode: the source budget caps VIN_BUS near 0.5 A
    (12.0, 0.1, 1.0),      # PoE: 2 x 480 mA
    (20.0, 0.1, 1.0),      # USB PD 20 V
)


def duty(vin):
    return 1 - vin / (VOUT + VF)                                      # eq. 11


def design():
    t = 1 / FSW
    print(f"## Design: fsw {FSW / 1e3:.0f} kHz (RT {RT / 1e3:.0f} k), VOUT {VOUT:.2f} V, "
          f"OVP {1.10 * VOUT:.1f} V (1.07-1.13: {1.07 * VOUT:.1f}-{1.13 * VOUT:.1f} V)")
    dmax = 1 - 100e-9 * FSW
    print(f"  maximum duty {dmax:.3f} (eq. 17), minimum on-time at 20 V: {duty(20) * t * 1e9:.0f} ns")
    ok = True
    for vin, _, iout in CORNERS:
        d = duty(vin)
        iin = VOUT * iout / (0.88 * vin)
        ripple = vin * d * t / L
        ipk = iin + ripple / 2
        se = VSLOPE * FSW + ISLOPE * RSL_EFF * FSW                     # V/s at the comparator
        sf = (VOUT + VF - vin) / L * RS                                # sensed falling slope
        icl = [(v - ISLOPE * RSL_EFF * d) / RS for v in VCLTH]         # eq. 10
        print(f"  VSYS {vin:4.1f} V, {iout:.1f} A: D {d:.3f}, IIN {iin:.2f} A, ripple {ripple:.2f} A, "
              f"peak {ipk:.2f} A; limit {icl[0]:.2f}/{icl[1]:.2f}/{icl[2]:.2f} A; "
              f"slope {se / sf * 100:.0f} % of the falling slope (>= 60 % eq. 8, 82 % optimal)")
        ok &= ipk < icl[0] and se >= 0.6 * sf and d < dmax
    print(f"  VCC load: QG 7.2 nC x fsw = {7.2e-9 * FSW * 1e3:.1f} mA (< 35 mA, eq. 18)")
    print(f"  soft start {CSS * VREF / 10e-6 * 1e3:.1f} ms; FB divider {VOUT / (RFBT + RFBB) * 1e3:.2f} mA")
    return ok


def loop(vin, iout, f):
    """Loop gain at f (Hz): Ridley current-mode boost model x Type 2 compensator."""
    s = 2j * math.pi * f
    t = 1 / FSW
    d = duty(vin)
    dp = 1 - d
    r = VOUT / iout
    ri = RS / GCOMP
    sn = vin / L * RS
    se = VSLOPE * FSW + ISLOPE * RSL_EFF * FSW
    mc = 1 + se / sn
    wn = math.pi / t
    qp = 1 / (math.pi * (mc * dp - 0.5))
    he = 1 + s / (wn * qp) + s * s / wn ** 2
    gvc = (r * dp / (2 * ri)) * (1 - s * L / (r * dp ** 2)) * (1 + s * COUT * ESR) / (1 + s * r * COUT / 2) / he
    hfb = RFBB / (RFBT + RFBB)
    zc = RCOMP + 1 / (s * CCOMP)
    z = 1 / (1 / zc + s * CHF + 1 / RO)
    return gvc * hfb * GM * z


def margins(vin, iout):
    f, fc = 10.0, None
    while f < FSW / 2:
        if abs(loop(vin, iout, f)) < 1:
            fc = f
            break
        f *= 1.01
    if fc is None:
        return None, None, None
    pm = 180 + math.degrees(cmath.phase(loop(vin, iout, fc)))
    f, gm = fc, None
    while f < FSW / 2:
        if math.degrees(cmath.phase(loop(vin, iout, f))) <= -180:
            gm = -20 * math.log10(abs(loop(vin, iout, f)))
            break
        f *= 1.01
    return fc, pm, gm


NET = """* LM5155 boost, cycle-by-cycle model
Vsup vs0 0 {vin}
Rsrc vs0 vsys 20m
Cin vsys 0 {cin}
Rdcr vsys lx {dcr}
L1 lx sw {l} ic=0
S1 sw csp gate 0 swm
Rs csp 0 {rs}
D1 sw out dss54
Cout out ce {cout}
Resr ce 0 {esr}
Rfbt out fb {rfbt}
Rfbb fb 0 {rfbb}
Iload out 0 PWL(0 {i0} {t1} {i0} {t1r} {i1} {t2} {i1} {t2r} {i0})
* soft start (ISS / CSS) and error amplifier
Bss vss 0 V = min(time * 10u / {css}, {vref})
Gea 0 comp vss fb {gm}
Rea comp 0 {ro}
Rcomp comp cz {rcomp}
Ccomp cz 0 {ccomp}
Chf comp 0 {chf}
Dhi comp vhi dclamp
Vhi vhi 0 2.8
Dlo vlo comp dclamp
Vlo vlo 0 1.0
* clock ramp 0 -> 1 over each period
Vramp ramp 0 PULSE(0 1 0 {tr} 1n 0 {t})
* CS pin: RS.IL through RF / CF (slope current ignored in the filter)
Rf csp csf {rf}
Cf csf 0 {cf}
* PWM and current limit comparators, maximum duty, set pulse
Brst rst 0 V = ((v(csf) + ({vsl} + {isl}) * v(ramp) + 0.17 >= {gc} * v(comp)) || (v(csf) + {isl} * v(ramp) >= {vclth}) || (v(ramp) > {dmax})) ? 1 : 0
Bset set 0 V = v(ramp) < 0.02 ? 1 : 0
* SR latch, reset dominant: q = !rst & (set | q delayed by 1 ns)
Bq qn 0 V = v(rst) > 0.5 ? 0 : ((v(set) > 0.5 || v(qd) > 0.5) ? 1 : 0)
Rqd qn qd 1
Cqd qd 0 1n
Bgate gate 0 V = v(qd) > 0.5 ? 1 : 0
.model swm sw(vt=0.5 vh=0.1 ron={rds} roff=10Meg)
.model dss54 d(is=50u n=1.1 rs=30m cjo=300p bv=45)
.model dclamp d(is=1e-14 n=0.5)
.ic v(out)={vin} v(comp)=1.0 v(vsys)={vin}
.options reltol=1e-3 itl4=50
.save v(out) v(comp) i(l1)
"""


def switching(vin, i0, i1):
    t = 1 / FSW
    t1, t2, tend = 4.0e-3, 5.5e-3, 7.0e-3
    net = NET.format(vin=vin, cin=CIN, dcr=DCR, l=L, rs=RS, cout=COUT, esr=ESR, rfbt=RFBT, rfbb=RFBB,
                     i0=i0, i1=i1, t1=t1, t1r=t1 + 1e-6, t2=t2, t2r=t2 + 1e-6, css=CSS, vref=VREF, gm=GM,
                     ro=RO, rcomp=RCOMP, ccomp=CCOMP, chf=CHF, tr=t - 1e-9, t=t, rf=RF, cf=CF,
                     vsl=VSLOPE, isl=ISLOPE * RSL_EFF, gc=GCOMP, vclth=VCLTH[1], dmax=1 - 100e-9 * FSW,
                     rds=RDS)
    v = run(net, f"tran 20n {tend} 0 10n uic")
    tt, vo, il = v["time"], v["out"], v["l1#branch"]

    def window(a, b):
        return [k for k, x in enumerate(tt) if a <= x < b]

    def stats(a, b):
        ks = window(a, b)
        return min(vo[k] for k in ks), max(vo[k] for k in ks)

    settle = sum(vo[k] for k in window(t1 - 0.3e-3, t1)) / len(window(t1 - 0.3e-3, t1))
    lo1, hi1 = stats(t1, t2)
    lo2, hi2 = stats(t2, tend)
    ipk = max(il[k] for k in window(t2 - 0.5e-3, t2))
    rise = next(tt[k] for k in range(len(tt)) if vo[k] > 0.9 * VOUT)
    end = sum(vo[k] for k in window(tend - 0.3e-3, tend)) / len(window(tend - 0.3e-3, tend))
    loaded = sum(vo[k] for k in window(t2 - 0.3e-3, t2)) / len(window(t2 - 0.3e-3, t2))
    print(f"  VSYS {vin:4.1f} V: 90 % at {rise * 1e3:.2f} ms; {i0:.2f} A {settle:.2f} V; step to {i1:.2f} A: "
          f"min {lo1:.2f} V, then {loaded:.2f} V, IL peak {ipk:.2f} A; step back: max {hi2:.2f} V, "
          f"then {end:.2f} V")
    return lo1, hi2, ipk


def main():
    ok = design()
    print("## Loop gain (Ridley model)")
    for vin, i0, i1 in CORNERS:
        for iout in (i0, i1):
            fc, pm, gm = margins(vin, iout)
            print(f"  VSYS {vin:4.1f} V, {iout:.2f} A: crossover {fc / 1e3:.1f} kHz, phase margin {pm:.0f}°, "
                  f"gain margin {gm if gm is None else round(gm)} dB")
            ok &= pm > 45
    print("## Switching simulation: soft start, load step at 4 ms, back at 5.5 ms")
    for vin, i0, i1 in CORNERS:
        lo, hi, ipk = switching(vin, i0, i1)
        ok &= lo > 0.9 * VOUT and hi < 1.07 * VOUT
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
