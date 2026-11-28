// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 Thomas Legrand
//
// Archet probe enclosure, first iteration: three printed shells and a button plunger (README.md).
//   bottom: one piece, M3 button-head screws from below, the board resting on a ledge and six bosses;
//   host:   host-end lid, 17.3 mm over the board (light pipes, plungers, PoE vents), Ruthex inserts;
//   target: target-end lid, 9.2 mm over the board, under the shield, which sits on its corner columns.
// Each lid prints top face down with no support. Select with -D 'PART="host"' (bottom, host, target, plunger,
// assembly).
//
// Frame: the board frame of hardware/gen/board.py (x from the host edge, y down) drawn as [x, -y], z = 0 on the
// board's underside. All part positions come from board.scad (geom.py).

include <board.scad>

PART = "assembly";
CHK = "";      // check: one part only
$fn = 40;

// --- Board and stack ---------------------------------------------------------------------------------------
BW = 150; BH = 100; TOP = 1.6;      // board outline, board top
HX = -1.04;                          // host connector faces = host wall outer face (board.py HOST_FACE)
GAP = 0.3;                           // board edge to wall
WALL = 2.0;
R_OUT = 5;                           // outer vertical edges
XJ = 62;                             // host lid end wall outer face = target lid start (board.py JOINT + 4)

// Bottom shell: floor, air under the board (THT tails reach 1.82 mm), ledge under the board edge.
FLOOR = 2.0; UNDER = 3.0; LEDGE = 1.2;
ZB = -(FLOOR + UNDER);

// Host lid (architecture.md, Enclosure heights): inner ceiling 15.3 over the board, 2 mm lid.
ZH_IN = TOP + 15.3; ZH_OUT = ZH_IN + 2.0;
// Target lid: the shield's underside is 11 mm over the board (standoff height); its through-hole tails need
// 1.8 mm, so the lid's top face is 9.2 mm over the board.
SHIELD_Z = TOP + 11.0; TAILS = 1.8;
ZT_OUT = SHIELD_Z - TAILS; ZT_IN = ZT_OUT - 1.8;

// Fasteners. ISO 7380 M3 button head: head 5.7 x 1.65.
SCREW = 3.4; HEAD_D = 6.2; HEAD_H = 2.0;
// Ruthex inserts: M3 x 5.7 (hole 4.0, 6.7 deep) in the host lid; M3 x 4.0 (hole 4.0, 5.0 deep) twice in the
// target columns (enclosure screw from below, shield screw from above). Check against the stock.
INS_D = 4.0; INS_LONG = 6.7; INS_SHORT = 5.0;
COL_D = 7.6;
TAB = 2.0;                           // target lid tabs clamped under the host lid at the joint screws

// Light pipes: Bivar PLP2-625, 2.92 mm press-fit hole (panel 1.2-2.4).
PIPE_HOLE = 2.92;
// Plungers over the TS-1187A buttons (top 1.5 mm over the board).
PL_D = 3.8; PL_HOLE = 4.1; PL_GUIDE = 9.0; PL_GUIDE_OD = 7.0; PL_PROUD = 1.0;
PL_FLANGE = 6.6; PL_FLANGE_H = 1.2;

ENGRAVE = 0.6; FONT = "Arial Black:style=Regular"; FONT_NARROW = "Arial:style=Bold";

// --- Helpers -----------------------------------------------------------------------------------------------
function part(ref) = PARTS[search([ref], PARTS)[0]];
function hole(ref) = HOLES[search([ref], HOLES)[0]];
function cx(p) = (p[1] + p[3]) / 2;
function cy(p) = (p[2] + p[4]) / 2;
function ox(p) = p[7];                     // footprint origin: actuator, light pipe and buzzer axes
function oy(p) = p[8];

// Box in board coordinates: x0..x1, y0..y1 (y down), z0..z1.
module bbox(x0, y0, x1, y1, z0, z1) { translate([x0, -y1, z0]) cube([x1 - x0, y1 - y0, z1 - z0]); }
// Rounded box, all four vertical edges at radius r.
module rbox(x0, y0, x1, y1, z0, z1, r) {
    hull() for (x = [x0 + r, x1 - r], y = [y0 + r, y1 - r]) translate([x, -y, z0]) cylinder(r = r, h = z1 - z0);
}
// Rounded on one end only (x0 if end < 0, x1 otherwise): the lid ends that meet at the joint stay square.
module rbox_end(x0, y0, x1, y1, z0, z1, r, end) {
    hull() {
        if (end < 0) bbox(x1 - r, y0, x1, y1, z0, z1); else bbox(x0, y0, x0 + r, y1, z0, z1);
        for (y = [y0 + r, y1 - r]) translate([end < 0 ? x0 + r : x1 - r, -y, z0]) cylinder(r = r, h = z1 - z0);
    }
}
module at(ref) { h = hole(ref); translate([h[1], -h[2], 0]) children(); }
module label(t, size = 3.5, font = FONT) { text(t, size = size, font = font, halign = "center", valign = "center"); }
// Engraving on the top face at z, reading along +x.
module engrave_top(x, y, z, t, size = 3.5, font = FONT) { translate([x, -y, z - ENGRAVE]) linear_extrude(2) label(t, size, font); }
// Engraving on the host face (x = HX), read from outside.
module engrave_host(y, z, t) { translate([HX + ENGRAVE, -y, z]) rotate([90, 0, -90]) linear_extrude(2) label(t); }
// Engraving on the target face, read from outside.
module engrave_target(x, y, z, t) { translate([x - ENGRAVE, -y, z]) rotate([90, 0, 90]) linear_extrude(2) label(t); }

// Outer extents.
X_OUT = BW + GAP + WALL; Y0_OUT = -GAP - WALL; Y1_OUT = BH + GAP + WALL;
CAV_X0 = HX + WALL;

// --- Wall openings (cut from every shell) ------------------------------------------------------------------
M = 0.3;   // clearance around a connector face
module host_openings() {
    for (r = ["J1", "J3"]) { p = part(r); bbox(HX - 1, p[2] - M, CAV_X0 + 0.5, p[4] + M, TOP, p[6] + M); }
    // USB-C: the shell sits 1 mm into the board edge
    for (r = ["J2", "J5"]) usbc(part(r), M, HX - 1, CAV_X0 - HX + 1.5);
}
// USB-C shell (stadium section) grown by m, from x0 over len along x.
module usbc(p, m, x0, len) {
    translate([x0, -cy(p), (p[5] + p[6]) / 2]) rotate([0, 90, 0])
        hull() for (d = [-1, 1]) translate([0, d * ((p[4] - p[2]) / 2 - (p[6] - p[5]) / 2), 0])
            cylinder(d = p[6] - p[5] + 2 * m, h = len);
}
J9P = part("J9"); SW4P = part("SW4"); J7P = part("J7"); J8P = part("J8");
BAY = [min(J7P[1], J8P[1]) - 1.5, J7P[2] - 1.0, J8P[4] + 1.0];     // x0, y0, y1: J7 and J8 reached from above
SW4_Y = cy(SW4P); SW4_SLOT = 5.5;
module target_openings() {
    // J9: plug enters through the end wall
    bbox(J9P[1] - 1, J9P[2] - M, X_OUT + 1, J9P[4] + M, TOP, J9P[6] + M);
    // J7, J8: open bay, lid and end wall, ribbons leave flat under the shield
    bbox(BAY[0], BAY[1], X_OUT + 1, BAY[2], TOP, 50);
    // SW4: knob slot and a finger recess in the outer face
    bbox(BW, SW4_Y - SW4_SLOT / 2, X_OUT + 1, SW4_Y + SW4_SLOT / 2, SW4P[5] - 0.3, SW4P[6] + 0.4);
    bbox(X_OUT - 1.3, SW4_Y - 4.5, X_OUT + 1, SW4_Y + 4.5, SW4P[5] - 1.0, SW4P[6] + 1.2);
}

// --- Bottom shell ------------------------------------------------------------------------------------------
module bottom() {
    difference() {
        union() {
            difference() {
                rbox(HX, Y0_OUT, X_OUT, Y1_OUT, ZB, TOP, R_OUT);
                rbox(-GAP, -GAP, BW + GAP, BH + GAP, 0, TOP + 1, 4 + GAP);                     // board pocket
                rbox(LEDGE, LEDGE, BW - LEDGE, BH - LEDGE, ZB + FLOOR, 1, 4 - LEDGE + 0.5);    // air under the board
            }
            for (h = HOLES) translate([h[1], -h[2], ZB]) cylinder(d = 8, h = -ZB);
        }
        for (h = HOLES) translate([h[1], -h[2], ZB - 1]) {
            cylinder(d = SCREW, h = 10);
            cylinder(d = HEAD_D, h = HEAD_H + 1);
        }
        host_openings();
        target_openings();
        // Labels under the connectors, read from the cable side.
        zl = (ZB + 0) / 2;
        engrave_host(cy(part("J3")), zl, "PoE");
        engrave_host(cy(part("J1")), zl, "VIN");
        engrave_host(cy(part("J2")), zl, "PD");
        engrave_host(cy(part("J5")), zl, "HS");
        engrave_target(X_OUT, SW4_Y, zl, "TERM");
        engrave_target(X_OUT, cy(J9P), zl, "BUS");
        engrave_target(X_OUT, cy(J7P), zl, "SWD");
        engrave_target(X_OUT, cy(J8P), zl, "ESP");
    }
}

// --- Host lid ----------------------------------------------------------------------------------------------
J12P = part("J12");
NOTCH = [J12P[1] - 1.0, J12P[3] + 1.0, J12P[2] - 1.4];   // x0, x1, inner y: J12 reached from above
ZS = J12P[6] + 0.5;                                        // shelf top, just over the J12 shroud
LEDS = [["D11", "PASS", -1], ["D12", "FAIL", -1], ["D10", "STAT", -1],
        ["D13", "LINK", 1], ["D14", "", 1], ["D19", "BUS", 1]];   // label above (-1) or below (+1) the LED
BUTTONS = [["SW2", "GO", -1], ["SW3", "STOP", 1]];              // label left (-1) or right (+1)

module tab(ref, y0, y1) { h = hole(ref); bbox(h[1] - 5, y0, XJ + 4, y1, TOP, TOP + TAB); }
module tabs() { tab("H5", -GAP, hole("H5")[2] + 4.5); tab("H6", hole("H6")[2] - 4.5, J12P[2] - 0.5); }

module host() {
    difference() {
        union() {
            difference() {
                rbox_end(HX, Y0_OUT, XJ, Y1_OUT, TOP, ZH_OUT, R_OUT, -1);
                bbox(CAV_X0, -GAP, XJ - WALL, BH + GAP, TOP - 1, ZH_IN);
                // the end wall stops at the target lid's ceiling: no keep-out band across the board under it
                bbox(XJ - WALL - 1, -GAP, XJ + 1, BH + GAP, TOP - 1, ZT_IN);
            }
            // J12 well: inner walls and a shelf around the shroud
            bbox(NOTCH[0] - 1.6, NOTCH[2] - 1.6, NOTCH[1], NOTCH[2], ZS - 1.6, ZH_OUT);
            bbox(NOTCH[0] - 1.6, NOTCH[2] - 1.6, NOTCH[0], Y1_OUT, ZS - 1.6, ZH_OUT);
            bbox(NOTCH[0], NOTCH[2], NOTCH[1], Y1_OUT, ZS - 1.6, ZS);
            // insert columns
            for (r = ["H1", "H4"]) at(r) translate([0, 0, TOP]) cylinder(d = COL_D, h = ZH_IN - TOP);
            for (r = ["H5", "H6"]) at(r) translate([0, 0, TOP + TAB]) cylinder(d = COL_D, h = ZH_IN - TOP - TAB);
            // plunger guides
            for (b = BUTTONS) { p = part(b[0]); translate([ox(p), -oy(p), ZH_IN - PL_GUIDE])
                cylinder(d = PL_GUIDE_OD, h = PL_GUIDE); }
        }
        bbox(NOTCH[0], NOTCH[2], NOTCH[1], Y1_OUT + 1, ZS, ZH_OUT + 1);                         // J12 well
        bbox(J12P[1] - 0.4, J12P[2] - 0.4, J12P[3] + 0.4, J12P[4] + 0.4, ZS - 2, ZS + 1);       // shroud through the shelf
        for (r = ["H1", "H4"]) at(r) translate([0, 0, TOP - 1]) cylinder(d = INS_D, h = INS_LONG + 1);
        for (r = ["H5", "H6"]) at(r) translate([0, 0, TOP + TAB - 1]) cylinder(d = INS_D, h = INS_LONG + 1);
        // target lid tabs pass under the end wall
        translate([0, 0, -0.01]) minkowski() { tabs(); cube(0.4, center = true); }
        host_openings();
        // vents over the DP5700: lid slots, and intake slots low in the top long wall
        u = part("U6");
        for (x = [u[1] + 2 : 4 : u[3] - 1]) {
            hull() for (y = [u[2] + 3, u[4] - 3]) translate([x, -y, ZH_IN - 1]) cylinder(d = 2, h = 5);
            hull() for (z = [TOP + 3, TOP + 9]) translate([x, -Y0_OUT + 1, z]) rotate([90, 0, 0]) cylinder(d = 2, h = 4);
        }
        // light pipes, plungers, buzzer
        for (l = LEDS) { p = part(l[0]); translate([ox(p), -oy(p), ZH_IN - 1]) cylinder(d = PIPE_HOLE, h = 5); }
        for (b = BUTTONS) { p = part(b[0]); translate([ox(p), -oy(p), ZH_IN - PL_GUIDE - 1])
            cylinder(d = PL_HOLE, h = PL_GUIDE + 5); }
        bz = part("BZ1");
        for (a = [0 : 60 : 300]) translate([ox(bz) + 2.6 * cos(a), -oy(bz) + 2.6 * sin(a), ZH_IN - 1]) cylinder(d = 1.5, h = 5);
        translate([ox(bz), -oy(bz), ZH_IN - 1]) cylinder(d = 1.5, h = 5);
        // markings
        // LED pitch 8 mm: narrower font for these
        for (l = LEDS) { p = part(l[0]); engrave_top(ox(p), oy(p) + l[2] * 3.8, ZH_OUT, l[1], 2.1, FONT_NARROW); }
        for (b = BUTTONS) { p = part(b[0]); engrave_top(ox(p) + b[2] * (b[2] > 0 ? 10 : 9.5), oy(p), ZH_OUT, b[1], 3.2); }
        engrave_top(30, 6, ZH_OUT, "ARCHET", 6);
    }
}

// --- Target lid --------------------------------------------------------------------------------------------
module target() {
    difference() {
        union() {
            difference() {
                rbox_end(XJ, Y0_OUT, X_OUT, Y1_OUT, TOP, ZT_OUT, R_OUT, 1);
                bbox(XJ - 1, -GAP, BW + GAP, BH + GAP, TOP - 1, ZT_IN);
            }
            // corner columns: enclosure screw from below, shield screw from above; the shield sits on them
            for (r = ["H2", "H3"]) at(r) translate([0, 0, TOP]) cylinder(d = COL_D, h = SHIELD_Z - TOP);
            tabs();
            // rib from the bottom tab up to the lid
            bbox(XJ, hole("H6")[2] - 4.5, XJ + 4, J12P[2] - 0.5, TOP, ZT_IN);
        }
        for (r = ["H2", "H3"]) at(r) {
            translate([0, 0, TOP - 1]) cylinder(d = INS_D, h = INS_SHORT + 1);
            translate([0, 0, SHIELD_Z - INS_SHORT]) cylinder(d = INS_D, h = INS_SHORT + 1);
        }
        for (r = ["H5", "H6"]) at(r) translate([0, 0, TOP - 1]) cylinder(d = SCREW, h = TAB + 2);
        // shield headers through the lid
        for (r = ["J10", "J11"]) { p = part(r); bbox(p[1] - 0.4, p[2] - 0.4, p[3] + 0.4, p[4] + 0.4, TOP, 50); }
        // J9 top stands 0.1 over the lid's underside: local relief
        bbox(J9P[1] - 0.4, J9P[2] - 0.4, BW + GAP, J9P[4] + 0.4, ZT_IN - 1, J9P[6] + 0.5);
        target_openings();
    }
}

// --- Plunger (prints standing, flange chamfered underneath) ------------------------------------------------
SW_TOP = part("SW2")[6];
PL_LEN = ZH_OUT + PL_PROUD - SW_TOP - 0.1;
PL_FLANGE_Z = ZH_IN - PL_GUIDE - 0.3 - SW_TOP;   // flange top, from the plunger's bottom end
module plunger() {
    cylinder(d = PL_D, h = PL_LEN - 0.6);
    translate([0, 0, PL_LEN - 0.6]) cylinder(d1 = PL_D, d2 = PL_D - 1.2, h = 0.6);
    translate([0, 0, PL_FLANGE_Z - PL_FLANGE_H]) cylinder(d = PL_FLANGE, h = PL_FLANGE_H);
    translate([0, 0, PL_FLANGE_Z - PL_FLANGE_H - (PL_FLANGE - PL_D) / 2])
        cylinder(d1 = PL_D, d2 = PL_FLANGE, h = (PL_FLANGE - PL_D) / 2);
}

// --- Selection ---------------------------------------------------------------------------------------------
module board_model() { color("darkgreen") import("board.stl"); color("silver") import("parts.stl"); }

if (PART == "bottom") bottom();
else if (PART == "host") host();
else if (PART == "target") target();
else if (PART == "plunger") plunger();
else if (PART == "assembly") {
    board_model();
    color("dimgray") bottom();
    color("steelblue", 0.85) host();
    color("darkorange", 0.85) target();
    for (b = BUTTONS) { p = part(b[0]); color("white") translate([ox(p), -oy(p), SW_TOP + 0.1]) plunger(); }
}
else if (PART == "check") {
    // Interference between each shell and the part bodies (boxes from the 3D models, body part only).
    for (p = PARTS) if (p[0] != "SW4" && (CHK == "" || p[0] == CHK)) intersection() {
        if (p[0] == "J2" || p[0] == "J5") usbc(p, 0, p[1], p[3] - p[1]);
        else bbox(p[1], p[2], p[3], p[4], max(p[5], TOP), p[6]);
        union() { bottom(); host(); target(); }
    }
}
