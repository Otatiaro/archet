# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Archet enclosure: print files, renders and interference check from enclosure.scad.

    python build.py [--check] [--no-render]

Writes out/<part>.3mf (bottom, host, target, plunger), out/*.png and out/kicad/*.wrz (models for KiCad). --check intersects every shell with the
part bodies listed in board.scad and fails if anything is left. Run geom.py first after a board change.
OPENSCAD overrides the OpenSCAD executable.
"""
import gzip
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
# 3D models for KiCad's viewer (board.py hangs them on a board-only footprint at the board origin): name: colour.
KICAD = {"bottom": (0.35, 0.35, 0.37), "host": (0.27, 0.51, 0.71), "target": (0.93, 0.55, 0.15),
         "plungers": (0.95, 0.95, 0.95)}
KICAD_DIR = os.path.join(OUT, "kicad")
TOP = 1.6   # KiCad model origin: board top


def stl_to_wrz(stl, wrz, colour):
    """ASCII STL (enclosure frame, mm) to gzipped VRML 2.0 in KiCad's model frame (0.1 inch units, z = 0 on the
    board top)."""
    index, points, faces, tri = {}, [], [], []
    with open(stl, encoding="ascii") as f:
        for line in f:
            w = line.split()
            if w and w[0] == "vertex":
                v = (round(float(w[1]), 4), round(float(w[2]), 4), round(float(w[3]) - TOP, 4))
                if v not in index:
                    index[v] = len(points)
                    points.append(v)
                tri.append(index[v])
                if len(tri) == 3:
                    faces.append(tri)
                    tri = []
    s = 1 / 2.54
    with gzip.open(wrz, "wt", encoding="ascii", newline="\n") as f:
        f.write("#VRML V2.0 utf8\nShape {\n appearance Appearance { material Material { diffuseColor "
                + " ".join(f"{c:.3f}" for c in colour) + " } }\n geometry IndexedFaceSet {\n  creaseAngle 0.6\n"
                "  coord Coordinate { point [\n")
        f.write(",\n".join(f"{x * s:.5f} {y * s:.5f} {z * s:.5f}" for x, y, z in points))
        f.write("\n  ] }\n  coordIndex [\n")
        f.write(",\n".join(f"{a},{b},{c},-1" for a, b, c in faces))
        f.write("\n  ]\n }\n}\n")


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
    os.makedirs(KICAD_DIR, exist_ok=True)
    jobs = [(os.path.join(OUT, p + ".3mf"), f'PART="{p}"', ()) for p in PARTS]
    jobs += [(os.path.join(KICAD_DIR, p + ".stl"), f'PART="{p}"', ()) for p in KICAD]
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
    for p, colour in KICAD.items():
        stl = os.path.join(KICAD_DIR, p + ".stl")
        stl_to_wrz(stl, os.path.join(KICAD_DIR, p + ".wrz"), colour)
        os.remove(stl)
    print("written:", ", ".join(sorted(os.listdir(OUT))))
    if hits:
        sys.exit("interference: " + ", ".join(hits))
    if checks:
        print("check: no interference")


if __name__ == "__main__":
    main()
