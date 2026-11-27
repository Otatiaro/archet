# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""+5V buck: LMR33630ADDA, VSYS 4.4-24 V (36 V absolute) to 5.03 V, 3 A, 400 kHz.

Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -I buck5.py
Values: hardware/gen/circuit.py, block "+5V". Datasheet SNVSAN3F (section 7.5 limits, section 9.2 design).
The LMR33630 is internally compensated: no loop model is published, so stability is checked the way the
datasheet frames it, against its recommended L/COUT window (table 9-2: 5 V, 400 kHz, 8 uH, 4 x 22 uF) and
the transient bound of equation 6. The rest is the design equations at the corners:
ripple, peak and valley currents against ISC / ILIMIT and the inductor, minimum on-time, dropout, losses.
"""
import math

FSW = 400e3
L, DCR, ISAT = 10e-6, 68e-3, 5.5           # FXL0630-100-M (L tolerance 20 %)
VREF = (0.985, 1.0, 1.015)
RFBT, RFBB = 8.06e3, 2e3
VOUT = VREF[1] * (1 + RFBT / RFBB)
IOUT = 3.0
ISC = (3.85, 4.5, 5.05)                     # high-side (peak) limit
ILIMIT = (2.9, 3.5, 4.1)                    # low-side (valley) limit
RHS, RLS = (0.095, 0.160), (0.066, 0.110)   # typ, max
TON_MIN, TOFF_MIN, TON_MAX = 108e-9, 85e-9, 9e-6
DMAX = 0.98
RTH_JA = 42.9                               # JEDEC 4-layer; datasheet: comparison only
# +5V effective capacitance at 5 V DC bias (C24-C26 22 uF 25 V 1206, 4 x 10 uF 25 V 0805, 3 x 1 uF)
COUT = 3 * 13e-6 + 4 * 5e-6 + 3 * 0.8e-6
ESR = 3e-3


def ripple(vin, l=L):
    d = VOUT / vin
    return (vin - VOUT) * d / (l * FSW), d


def eq6(di, dv, vin, k):
    """Datasheet equation 6: minimum COUT and maximum ESR for a load step di within dv."""
    d = VOUT / vin
    cmin = di / (FSW * dv * k) * ((1 - d) * (1 + k) + k * k / 12 * (2 - d))
    esr = (2 + k) * dv / (2 * di * (1 + k + k * k / 12 * (1 + 1 / (1 - d))))
    return cmin, esr


def dropout(vsys, iout, rhs, dmax=DMAX):
    """Output in dropout: duty capped at DMAX (frequency folds back to 1 / (tON-MAX + tOFF-MIN))."""
    return vsys * dmax - iout * (rhs * dmax + RLS[0] * (1 - dmax) + DCR)


def main():
    lo, hi = VREF[0] * (1 + RFBT * 0.99 / (RFBB * 1.01)), VREF[2] * (1 + RFBT * 1.01 / (RFBB * 0.99))
    print(f"VOUT {VOUT:.3f} V ({lo:.2f}-{hi:.2f} V with VREF and 1 % resistors)")
    print(f"Max output current, eq. 1 (ILIMIT + ISC) / 2: {(ILIMIT[0] + ISC[0]) / 2:.2f} A minimum")
    lmin = 0.28 * VOUT / FSW
    print(f"L 10 uH vs eq. 5 LMIN {lmin * 1e6:.1f} uH and table 9-2 (8 uH)")
    ok = True
    print("\nVSYS   D     tON    dIL p-p   peak (-20 % L)  valley   ISC min  ILIMIT min  Isat  losses  Tj rise")
    for vin in (12.0, 20.0, 24.0, 36.0):
        di, d = ripple(vin)
        di_lo, _ = ripple(vin, 0.8 * L)
        pk, pk_lo, valley = IOUT + di / 2, IOUT + di_lo / 2, IOUT - di / 2
        ton = d / FSW
        # Conduction at maximum RDS(on), switching from ~10 ns of total edge time, gate drive and IQ.
        pc = IOUT ** 2 * (d * RHS[1] + (1 - d) * RLS[1])
        psw = 0.5 * vin * IOUT * 10e-9 * FSW + 2e-9 * 5 * FSW * 1 + 5e-3 * vin * 0.002
        ploss = pc + psw
        print(f"{vin:4.0f}  {d:.2f}  {ton * 1e9:4.0f} ns  {di:.2f} A    {pk:.2f} ({pk_lo:.2f}) A   {valley:.2f} A  "
              f"{ISC[0]:.2f}     {ILIMIT[0]:.2f}       {ISAT}   {ploss:.2f} W  +{ploss * RTH_JA:.0f} C")
        ok &= pk_lo < ISC[0] and pk_lo < ISAT and ton > TON_MIN and valley < ILIMIT[0]
    print(f"\nMinimum on-time {TON_MIN * 1e9:.0f} ns: frequency foldback above "
          f"{VOUT / (TON_MIN * FSW):.0f} V (eq. 2), beyond the 36 V rating")
    ceff = COUT
    for vin in (12.0, 24.0):
        di, _ = ripple(vin)
        k = di / IOUT
        cmin, esr = eq6(2.0, 0.25, vin, k)
        vr = di * math.sqrt(ESR ** 2 + (1 / (8 * FSW * ceff)) ** 2)
        print(f"COUT at {vin:.0f} V (K {k:.2f}): eq. 6 needs {cmin * 1e6:.0f} uF effective, ESR < {esr * 1e3:.0f} mOhm "
              f"for 2 A / 250 mV; fitted {ceff * 1e6:.0f} uF effective -> ripple {vr * 1e3:.1f} mV p-p (eq. 7)")
        dv = 0.25 * cmin / ceff
        print(f"  -> 2 A step with the fitted COUT: ~{dv * 1e3:.0f} mV ({dv / VOUT * 100:.1f} %)")
        ok &= dv < 0.05 * VOUT * 1.2
    print("Table 9-2 for 5 V / 400 kHz: 8 uH, 4 x 22 uF rated (~52 uF effective): fitted 10 uH (ripple "
          "factor 0.24-0.36, inside the 20-40 % window of 9.2.2.4) and ~61 uF effective. Feedforward capacitor: eq. 9 is only needed for "
          "RFBT > 100 kOhm (FB pole); RFBT is 8.06 kOhm, CFF left open as in the table.")
    # Dropout on a 5 V USB source: vSafe5V 4.75-5.5 V at the source, cable IR drop up to 250 mV each way at 3 A
    # (USB Type-C cable spec), Q4 (14.7 mOhm max at -4.5 V), Q2 at its 20 mV regulation, R126 15 mOhm.
    print("\nDropout on a 5 V USB source (+5V load: probe + target, no 5V_OUT):")
    for name, vbus, rcab, iin, iout, rhs in (("nominal", 5.0, 0.1, 1.0, 0.8, RHS[0]),
                                              ("worst", 4.75, 0.167, 1.5, 1.1, RHS[1])):
        vsys = vbus - iin * (rcab + 0.0147 + 0.015) - 0.02
        vo = min(VOUT, dropout(vsys, iout, rhs))
        print(f"  {name:8s}: VBUS {vbus:.2f} V, VSYS {vsys:.2f} V, +5V {vo:.2f} V at {iout:.1f} A")
        if name == "worst":
            ok &= vo > 2.5 + 0.1        # TLV62569 minimum input with margin
            vwc = vo
    print(f"  worst case still above the TLV62569 2.5 V input minimum ({vwc:.2f} V); TPS63020 boosts TGT_VSUP")
    assert ok, "a corner fails"


if __name__ == "__main__":
    main()
