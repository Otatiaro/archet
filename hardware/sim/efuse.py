# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Output switches: limits, start-up slew and inrush, and what an overload does to the +5V buck.

Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -I efuse.py
Values: hardware/gen/circuit.py, blocks "Shield supply" and "Local bus".
- TPS259531 (U38 5V_OUT, U40 3V3_OUT), SLVSE57C: ILIMIT = 2000 / RILM + 0.04 A (eq. 4), +/-7.5 %;
  tLIM 250 us; slew SR = 42000 pF / CdVdt (eq. 3); RON 53 mOhm max; RthJA 65.6 C/W.
- TPS2553 (U44 +3V3_BUS), SLVS841: IOS = 23950 / R^0.977 (R in kOhm, mA); rise time 0.7-1 ms at 2.5 V,
  1.1-1.5 ms at 6.5 V; tIOS 2 us.
- TPS27S100B (U45/U46 VIN_BUS1/2), SLVSE42B: ILIM = 1.233 x 2000 / R (eq. 4), +/-20 % above 25 C,
  +/-28 % below; slew 0.1-0.5 V/us.
+5V: LMR33630, (ILIMIT + ISC) / 2 = 3.38 A minimum (buck5.py).
"""

BUCK_MIN = 3.38
ETA = 0.9                     # TLV62569 and TPS63020 efficiency


def tps2595(rilm):
    i = 2000 / rilm + 0.04
    return 0.925 * i, i, 1.075 * i


def start(vin, r_load, c_out, cdvdt=100e-9, dt=1e-6):
    """eFuse ramp at SR into C and a resistive load: peak and mean power in the eFuse."""
    sr = 42000e-12 / cdvdt * 1e3        # V/s
    t, v, e, pk = 0.0, 0.0, 0.0, 0.0
    while v < vin:
        i = c_out * sr + v / r_load
        p = (vin - v) * i
        e += p * dt
        pk = max(pk, p)
        v += sr * dt
        t += dt
    return t, c_out * sr, pk, e / t


def main():
    ok = True
    print("TPS259531 current limits (eq. 4, +/-7.5 %):")
    lim = {}
    for name, r, vout in (("5V_OUT", 1e3, 5.0), ("3V3_OUT", 2e3, 3.3)):
        lo, typ, hi = tps2595(r)
        lim[name] = hi
        print(f"  {name:8s} RILM {r / 1e3:.0f} k: {lo:.2f} / {typ:.2f} / {hi:.2f} A; overloads above "
              f"{1.2 * hi:.2f} A pass for up to 250 us (tLIM) before regulation")
    print("\nStart-up at 0.42 V/ms (CdVdt 100 nF), shield 470 uF + C107 10 uF and a resistive load at full current:")
    for name, vin, rl in (("5V_OUT", 5.0, 5.0 / 2.0), ("3V3_OUT", 3.3, 3.3 / 1.0)):
        t, icap, pk, pav = start(vin, rl, 480e-6)
        tj = pav * 65.6
        print(f"  {name:8s}: {t * 1e3:.1f} ms, capacitor current {icap * 1e3:.0f} mA, eFuse peak {pk:.2f} W, "
              f"mean {pav:.2f} W (+{tj:.0f} C if it lasted; the eFuse's own thermal limit backs it)")
        ok &= icap < 0.25
    # +5V budget at the limits. 3V3_OUT comes from +3V3_AUX (U10) on +5V.
    probe = 2.1 * ETA / 5.0                 # probe at VSYS 2.1 W max, ~90 % behind the buck
    target_def, target_max = 0.3 * 5.0 / ETA / 5.0, 1.0 * 5.0 / ETA / 5.0
    i5 = lim["5V_OUT"]
    i33 = lim["3V3_OUT"] * 3.3 / ETA / 5.0
    print("\n+5V load with the shield rails at their maximum limits (buck: 3.38 A minimum):")
    for name, tgt in (("target 300 mA (default)", target_def), ("target 1 A", target_max)):
        one = probe + tgt + i5 + 0.2
        both = probe + tgt + i5 + i33
        print(f"  {name:24s}: 5V_OUT at its limit {one:.2f} A, both rails at their limits {both:.2f} A")
    print("  Both rails at their limits exceed the buck: the 11.5 W shield share is enforced by the firmware, "
          "INA_ALERT (INA226 over-current alert, wired-OR to the MCU) dropping the eFuse EN")
    print("\nTPS2553 +3V3_BUS (R127 47 k):")
    ios = 23950 / 47 ** 0.977 / 1e3
    print(f"  IOS {ios * 1e3:.0f} mA (505-616 mA, table); rise 0.7-1.5 ms: ribbon capacitance charged without "
          f"limiting up to {0.505 * 0.7e-3 / 3.3 * 1e6:.0f} uF (C128 10 uF included); above it charges at the limit")
    print("  +3V3 load: probe 550 mA max + 616 mA = 1.17 A on the 2 A TLV62569 (U9)")
    ok &= 0.55 + 0.616 < 2.0
    print("\nTPS27S100B VIN_BUS1/2 (R 4.7 k):")
    il = 1.233 * 2000 / 4.7e3
    print(f"  ILIM {il * 1e3:.0f} mA: {0.8 * il * 1e3:.0f}-{1.2 * il * 1e3:.0f} mA above 25 C, "
          f"{0.72 * il * 1e3:.0f}-{1.28 * il * 1e3:.0f} mA below; slew 0.1-0.5 V/us: up to "
          f"{0.72 * il / 0.5e6 * 1e6:.2f} uF charged without limiting, larger loads charge at the limit "
          f"(energy 1/2 C V^2: {0.5 * 100e-6 * 24 ** 2 * 1e3:.0f} mJ for 100 uF at 24 V)")
    print(f"  two switches: {2 * 1.28 * il:.2f} A worst case from VIN_BUS (VIN_EXT through U52/Q10)")
    assert ok, "a check fails"


if __name__ == "__main__":
    main()
