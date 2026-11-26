# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Minimal STEP (AP214) writer for package models made of coloured boxes; pure Python, no CAD kernel.

    write("part.step", "part", [((x0, y0, z0, x1, y1, z1), (r, g, b)), ...])

Coordinates in mm, KiCad 3D frame: X right, Y up (opposite of the footprint Y), Z up from the board.
"""

# Faces of a unit box: vertex bits (x, y, z), listed counter-clockwise seen from outside.
FACES = (((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
         ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
         ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)))


class _Data:
    def __init__(self):
        self.lines = []

    def add(self, text):
        self.lines.append(text)
        return f"#{len(self.lines)}"

    def point(self, p):
        return self.add("CARTESIAN_POINT('',(%s));" % ",".join(f"{v:.4f}" for v in p))

    def direction(self, d):
        return self.add("DIRECTION('',(%s));" % ",".join(f"{v:.4f}" for v in d))

    def axis(self, origin, z, x):
        return self.add(f"AXIS2_PLACEMENT_3D('',{self.point(origin)},{self.direction(z)},{self.direction(x)});")


def _sub(a, b):
    return tuple(p - q for p, q in zip(a, b))


def _unit(v):
    n = sum(c * c for c in v) ** 0.5
    return tuple(c / n for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _box(d, box):
    x0, y0, z0, x1, y1, z1 = box
    assert x1 > x0 and y1 > y0 and z1 > z0, box
    coord = {b: (x1 if b[0] else x0, y1 if b[1] else y0, z1 if b[2] else z0)
             for b in [(i, j, k) for i in (0, 1) for j in (0, 1) for k in (0, 1)]}
    vtx = {b: d.add(f"VERTEX_POINT('',{d.point(p)});") for b, p in coord.items()}
    edges = {}

    def edge(a, b):
        key = tuple(sorted((a, b)))
        if key not in edges:
            pa, pb = coord[key[0]], coord[key[1]]
            v = _sub(pb, pa)
            length = sum(c * c for c in v) ** 0.5
            vec = d.add(f"VECTOR('',{d.direction(_unit(v))},{length:.4f});")
            line = d.add(f"LINE('',{d.point(pa)},{vec});")
            edges[key] = d.add(f"EDGE_CURVE('',{vtx[key[0]]},{vtx[key[1]]},{line},.T.);")
        return edges[key], ".T." if (a, b) == key else ".F."

    faces = []
    for loop in FACES:
        oriented = []
        for a, b in zip(loop, loop[1:] + loop[:1]):
            e, sense = edge(a, b)
            oriented.append(d.add(f"ORIENTED_EDGE('',*,*,{e},{sense});"))
        p = [coord[b] for b in loop]
        u, w = _sub(p[1], p[0]), _sub(p[2], p[1])
        plane = d.add(f"PLANE('',{d.axis(p[0], _unit(_cross(u, w)), _unit(u))});")
        el = d.add(f"EDGE_LOOP('',({','.join(oriented)}));")
        bound = d.add(f"FACE_OUTER_BOUND('',{el},.T.);")
        faces.append(d.add(f"ADVANCED_FACE('',({bound}),{plane},.T.);"))
    shell = d.add(f"CLOSED_SHELL('',({','.join(faces)}));")
    return d.add(f"MANIFOLD_SOLID_BREP('',{shell});")


def write(path, name, boxes):
    d = _Data()
    app = d.add("APPLICATION_CONTEXT('core data for automotive mechanical design processes');")
    d.add(f"APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,{app});")
    pctx = d.add(f"PRODUCT_CONTEXT('',{app},'mechanical');")
    prod = d.add(f"PRODUCT('{name}','{name}','',({pctx}));")
    d.add(f"PRODUCT_RELATED_PRODUCT_CATEGORY('part',$,({prod}));")
    form = d.add(f"PRODUCT_DEFINITION_FORMATION('','',{prod});")
    dctx = d.add(f"PRODUCT_DEFINITION_CONTEXT('part definition',{app},'design');")
    pdef = d.add(f"PRODUCT_DEFINITION('design','',{form},{dctx});")
    pds = d.add(f"PRODUCT_DEFINITION_SHAPE('','',{pdef});")
    mm = d.add("(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.));")
    rad = d.add("(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.));")
    sr = d.add("(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT());")
    unc = d.add(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),{mm},'distance_accuracy_value',"
                "'confusion accuracy');")
    ctx = d.add(f"(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT(({unc}))"
                f"GLOBAL_UNIT_ASSIGNED_CONTEXT(({mm},{rad},{sr}))REPRESENTATION_CONTEXT('',''));")
    origin = d.axis((0, 0, 0), (0, 0, 1), (1, 0, 0))
    solids, styled = [], []
    for box, rgb in boxes:
        s = _box(d, box)
        solids.append(s)
        col = d.add("COLOUR_RGB('',%.3f,%.3f,%.3f);" % rgb)
        fac = d.add(f"FILL_AREA_STYLE_COLOUR('',{col});")      # Part 21: no inline entity instances
        fill = d.add(f"FILL_AREA_STYLE('',({fac}));")
        ssfa = d.add(f"SURFACE_STYLE_FILL_AREA({fill});")
        side = d.add(f"SURFACE_SIDE_STYLE('',({ssfa}));")
        usage = d.add(f"SURFACE_STYLE_USAGE(.BOTH.,{side});")
        psa = d.add(f"PRESENTATION_STYLE_ASSIGNMENT(({usage}));")
        styled.append(d.add(f"STYLED_ITEM('',({psa}),{s});"))
    rep = d.add(f"ADVANCED_BREP_SHAPE_REPRESENTATION('{name}',({','.join([origin] + solids)}),{ctx});")
    d.add(f"SHAPE_DEFINITION_REPRESENTATION({pds},{rep});")
    d.add(f"MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',({','.join(styled)}),{ctx});")
    head = ["ISO-10303-21;", "HEADER;", "FILE_DESCRIPTION(('Archet package model'),'2;1');",
            f"FILE_NAME('{name}.step','2026-11-26T00:00:00',(''),(''),'archet step3d.py','','');",
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));", "ENDSEC;", "DATA;"]
    body = [f"#{i}={t}" for i, t in enumerate(d.lines, 1)]
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(head + body + ["ENDSEC;", "END-ISO-10303-21;"]) + "\n")
