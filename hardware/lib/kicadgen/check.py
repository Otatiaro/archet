# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Prove that a drawn schematic realises its circuit exactly: ERC plus netlist comparison.

For each expected net, the drawn net holding its pins must hold those pins and no others.
Parts not drawn yet are listed (sheets in progress) and their nets are skipped.
"""
import os
import re
import subprocess
import tempfile

from .kicad import cli, footprint_dir
from .circuit import bare
from .sexpr import parse, find, first


def _drawn(sch):
    with tempfile.TemporaryDirectory() as d:
        net = os.path.join(d, "n.net")
        r = subprocess.run([cli(), "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"netlist export failed: {r.stderr}")
        tree = parse(open(net, encoding="utf-8").read())
    refs = {first(c, "ref")[1] for c in find(first(tree, "components"), "comp")}
    nets = {}
    for n in find(first(tree, "nets"), "net"):
        nodes = {(first(x, "ref")[1], first(x, "pin")[1]) for x in find(n, "node")
                 if not first(x, "ref")[1].startswith("#")}
        if nodes:
            nets[first(n, "name")[1]] = nodes
    return refs, nets


def erc(sch):
    with tempfile.TemporaryDirectory() as t:
        rpt = os.path.join(t, "erc.rpt")
        subprocess.run([cli(), "sch", "erc", "--severity-all", "-o", rpt, sch], capture_output=True)
        text = open(rpt, encoding="utf-8").read()
    blocks = re.split(r"^(?=\[\w+\]:)", text, flags=re.M)
    return text, [(re.match(r"\[(\w+)\]", b).group(1), b) for b in blocks if re.match(r"\[\w+\]:", b)]


def models(circuit, fp_libs=None):
    """Footprints and 3D models: returns one line per footprint that is missing or has no model file.

    fp_libs: project footprint libraries {nickname: path to the .pretty folder}.
    """
    fp_dir = footprint_dir()
    mod_dir = os.path.join(os.path.dirname(fp_dir), "3dmodels").replace("\\", "/")
    by_fp = {}
    for p in circuit.parts:
        if bare(p):
            continue
        by_fp.setdefault(p["fp"], []).append(p["ref"])
    out = []
    for fp, refs in sorted(by_fp.items()):
        lib, name = fp.split(":", 1)
        pretty = (fp_libs or {}).get(lib) or os.path.join(fp_dir, lib + ".pretty")
        path = os.path.join(pretty, name + ".kicad_mod")
        if not os.path.exists(path):
            out.append(f"no footprint {fp} ({', '.join(refs)})")
            continue
        found = re.findall(r'\(model\s+"?([^"\s)]+)', open(path, encoding="utf-8").read())
        files = [re.sub(r"\$\{KICAD\d*_3DMODEL_DIR\}", mod_dir, m).replace("${KIPRJMOD}", os.path.dirname(pretty))
                 for m in found]
        if not any(os.path.exists(f) for f in files):
            out.append(f"no 3D model {fp} ({', '.join(refs)})" + (f": {found[0]} absent" if found else ""))
    return out


def check(circuit, sch, allowed_erc=(), waived=(), fp_libs=None):
    """Print the report; return 0 when ERC (minus allowed kinds) and netlist are clean.

    allowed_erc: violation kinds tolerated while sheets are missing.
    waived: (kind, text) pairs for violations that are understood and accepted, each one
    justified where it is declared; a violation is waived when its report block contains text.
    """
    text, found = erc(sch)
    found = [(k, b) for k, b in found if not any(k == wk and wt in b for wk, wt in waived)]
    kinds = [k for k, _ in found]
    blocking = [k for k in kinds if k not in allowed_erc]
    refs, dnets = _drawn(sch)
    where = {node: name for name, nodes in dnets.items() for node in nodes}
    errors = []
    for name, nodes in sorted(circuit.nets().items()):
        present = {n for n in nodes if n[0] in refs}
        if not present:
            continue
        got = {where.get(n) for n in present}
        if None in got:
            errors.append(f"{name}: pins not connected {sorted(n for n in present if n not in where)}")
            got.discard(None)
        if len(got) > 1:
            errors.append(f"{name}: split into {len(got)} drawn nets {sorted(got)}")
        for d in got:
            extra = sorted(dnets[d] - nodes)
            if extra:
                errors.append(f"{name}: extra pins in '{d}' {extra}")
    missing = sorted({p["ref"] for p in circuit.parts} - refs)
    summary = {k: kinds.count(k) for k in sorted(set(kinds))}
    print(f"ERC: {len(kinds)} violations {summary if kinds else ''}"
          + (f" ({len(kinds) - len(blocking)} allowed while sheets are missing)" if len(blocking) < len(kinds) else ""))
    if blocking:
        print("".join(b for k, b in found if k not in allowed_erc))
    print(f"netlist: {len(errors)} differences")
    for e in errors:
        print("  x", e)
    gaps = models(circuit, fp_libs)
    print(f"footprints and 3D models: {len(gaps)} missing")
    for e in gaps:
        print("  x", e)
    if missing:
        print(f"not drawn yet ({len(missing)}):", " ".join(missing))
    return 1 if errors or blocking else 0
