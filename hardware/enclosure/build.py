# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Archet enclosure: print files, renders and interference check from enclosure.scad.

    python build.py [--check] [--no-render]

Writes out/<part>.3mf (bottom, host, target, plunger) and out/*.png. --check intersects every shell with the
part bodies listed in board.scad and fails if anything is left. Run geom.py first after a board change.
OPENSCAD overrides the OpenSCAD executable.
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SCAD = os.path.join(HERE, "enclosure.scad")
EXE = os.environ.get("OPENSCAD") or shutil.which("openscad") or r"C:\Program Files\OpenSCAD\openscad.com"

PARTS = ["bottom", "host", "target", "plunger"]
# name: (PART, camera translate x,y,z, rotate x,y,z, distance)
VIEWS = {
    "assembly": ("assembly", "75,-50,5,60,0,35,330"),
    "assembly-target": ("assembly", "75,-50,5,60,0,215,330"),
    "assembly-top": ("assembly", "75,-50,5,0,0,0,300"),
    "bottom": ("bottom", "75,-50,0,55,0,25,330"),
    "host-top": ("host", "30,-50,10,0,0,0,260"),
    "target-top": ("target", "105,-50,5,0,0,0,280"),
    "host-inside": ("host", "30,-50,10,130,0,20,230"),
    "target-inside": ("target", "105,-50,5,130,0,20,260"),
}
CHECK = ["J1", "J2", "J3", "J5", "U6", "J7", "J8", "J9", "J10", "J11", "J12", "SW2", "SW3", "BZ1",
         "D10", "D11", "D12", "D13", "D14", "D19"]


def scad(out, *defs, extra=()):
    args = [EXE, "-o", out, *extra]
    for d in defs:
        args += ["-D", d]
    r = subprocess.run(args + [SCAD], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=HERE)
    if r.returncode and "top level object is empty" not in r.stdout:
        sys.exit(f"{os.path.basename(out)}: {r.stdout}")
    return r.stdout


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = [(os.path.join(OUT, p + ".3mf"), f'PART="{p}"', ()) for p in PARTS]
    if "--no-render" not in sys.argv:
        jobs += [(os.path.join(OUT, n + ".png"), f'PART="{p}"',
                  ("--camera", cam, "--imgsize", "1600,1000", "--colorscheme", "Tomorrow", "--projection", "p"))
                 for n, (p, cam) in VIEWS.items()]
    checks = [(os.path.join(OUT, f"check_{r}.stl"), r) for r in CHECK] if "--check" in sys.argv else []
    # CGAL is memory-hungry: a few renders at a time.
    with ThreadPoolExecutor(4) as ex:
        for f in [ex.submit(scad, o, d, extra=e) for o, d, e in jobs]:
            f.result()
        logs = [(r, ex.submit(scad, o, 'PART="check"', f'CHK="{r}"')) for o, r in checks]
        hits = [r for r, f in logs if "Current top level object is empty" not in f.result()]
    for o, _ in checks:
        if os.path.exists(o):
            os.remove(o)
    print("written:", ", ".join(sorted(os.listdir(OUT))))
    if hits:
        sys.exit("interference: " + ", ".join(hits))
    if checks:
        print("check: no interference")


if __name__ == "__main__":
    main()
