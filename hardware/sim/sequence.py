# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Power-up order of the iCE40 UltraPlus (U13) and the USB3320 (U15) as +5V comes up.

Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -I sequence.py
Values: hardware/gen/circuit.py, blocks "+5V", "+3V3 and +3V3_AUX", "FPGA", "USB HS".
Behavioural time model, swept over the datasheet corners:
- +5V: LMR33630 soft start 2.9 / 4 / 6 ms (SNVSAN3F tSS), a linear ramp to 5.03 V; VSYS is already up.
- +1V2 (ME6211C12, U14) and +1V8 (ME6211C18, U16), CE tied to VIN: off until VIN reaches the CE threshold
  (0.5-1.0 V, VCEL max / VCEH min), then VIN minus ~50 mV (dropout at a few mA) up to the set voltage.
  The datasheet gives no turn-on waveform: the output is assumed to track its input, which a 300 mA LDO
  driving 1.2 uF does.
- VCCPLL: R26 100 Ohm into C55 10 uF + C56 100 nF (PLL unused, no load).
- +3V3 (TLV62569, U9), EN tied to VIN: starts when +5V crosses the UVLO rising threshold (2.4-2.55 V,
  VUVLO falling 2.3-2.45 V plus 100 mV hysteresis, SLVSDG3), then soft start 0.9 ms, taken as a linear ramp.
  +3V3 feeds SPI_VCCIO1, VPP_2V5 (tied together, iCE40 fig. 4.2), VCCIO0/2, and the USB3320 VDD33/VDDIO.
Requirements: iCE40 UltraPlus FPGA-DS-02008 §4.5 (VCC and VCCPLL at 0.5 V or more before SPI_VCCIO1;
SPI_VCCIO1 before VPP_2V5; VCCIO after VCC), table 4.3 (0.6-10 V/ms monotonic ramps); USB3320 absolute
maximum ratings (VDDIO 0.7 V max while VDD18 is not up).
"""
import math

V5 = 5.03
DT = 1e-6


def ldo(vin, vce, vset):
    return 0.0 if vin < vce else max(0.0, min(vset, vin - 0.05))


def run(tss, vce, uvlo, tss33=0.9e-3):
    """Returns the time traces and the checks for one corner."""
    t, vpll = 0.0, 0.0
    tau = 100 * 10.1e-6
    t33 = None
    out = []
    while t < tss + 3e-3:
        v5 = min(V5, V5 * t / tss)
        v12, v18 = ldo(v5, vce, 1.2), ldo(v5, vce, 1.8)
        vpll += (v12 - vpll) * DT / tau
        if t33 is None and v5 >= uvlo:
            t33 = t
        v33 = 0.0 if t33 is None else min(3.33, 3.33 * (t - t33) / tss33)
        out.append((t, v5, v12, vpll, v18, v33))
        t += DT
    return out, t33


def at(trace, k, t0):
    return next(r for r in trace if r[0] >= t0)[k]


def ramp(trace, k, vmax):
    """Average slope between 10 % and 90 % of the final value, V/ms."""
    t10 = next(r[0] for r in trace if r[k] >= 0.1 * vmax)
    t90 = next(r[0] for r in trace if r[k] >= 0.9 * vmax)
    return 0.8 * vmax / (t90 - t10) / 1e3


def main():
    ok = True
    print("corner (+5V tSS, LDO CE, TLV UVLO rising): VCC / VCCPLL / +1V8 when +3V3 starts; ramps 10-90 %")
    worst = None
    for tss in (2.9e-3, 4e-3, 6e-3):
        for vce in (0.5, 1.0):
            for uvlo in (2.4, 2.55):
                tr, t33 = run(tss, vce, uvlo)
                vcc, vpll, v18 = at(tr, 2, t33), at(tr, 3, t33), at(tr, 4, t33)
                r12, rpll, r33 = ramp(tr, 2, 1.2), ramp(tr, 3, 1.2), ramp(tr, 5, 3.33)
                print(f"  {tss * 1e3:.1f} ms  CE {vce:.1f} V  UVLO {uvlo:.2f} V: VCC {vcc:.2f} V, VCCPLL {vpll:.2f} V, "
                      f"+1V8 {v18:.2f} V; ramps +1V2 {r12:.1f}, VCCPLL {rpll:.2f}, +3V3 {r33:.1f} V/ms")
                ok &= vcc >= 0.5 and vpll >= 0.5 and v18 >= 1.7 and r12 >= 0.6 and r33 <= 10
                if worst is None or vpll < worst[0]:
                    worst = (vpll, tss, vce, uvlo)
    print(f"tightest: VCCPLL {worst[0]:.2f} V when +3V3 starts (+5V in {worst[1] * 1e3:.1f} ms, CE {worst[2]} V, "
          f"UVLO {worst[3]} V); 0.5 V required")
    print("VCCPLL ramps slower than 0.6 V/ms over 10-90 % (RC 1 ms): the filter is the one Lattice recommends "
          "(hardware checklist FPGA-TN-02006, development board); VCCPLL is not monitored by the POR")
    print("+1V2 above 10 V/ms when the LDO wakes at CE 1.0 V: the output then steps to VIN - dropout (~0.95 V). "
          "The ME6211 datasheet gives no turn-on waveform, so the 10 V/ms ceiling is not guaranteed by design")
    # +1V8 is at 1.8 V before +3V3 leaves 0, so VDDIO never exceeds 0.7 V with VDD18 down.
    assert ok, "a sequencing corner fails"


if __name__ == "__main__":
    main()
