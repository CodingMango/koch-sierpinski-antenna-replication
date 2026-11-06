#!/usr/bin/env python3
"""Regenerate the patch geometry (DXF, millimetres) of the Koch-Sierpinski antenna replication.

Designs (Azzouz et al., Fractal Fract. 2026, 10, 47, Figs 2 and 4):
  Iter0     single downward equilateral triangle
  Iter1     Iter0 + 5 mm central slot
  Iter2     hexagram (two opposed triangles) + 5 mm slot + 8 slots of 5/3 mm
  Iter3     Koch-style outline + 73-slot Sierpinski carpet (final design)
  KochOnly  Iter3 outline without any slot (Fig 7 comparison)

The DXF files contain NO feed line. Layers: PATCH (outer outline), HOLES (slots).
Feed dimensions are written to feed_dimensions.csv and are added in HFSS as a rectangle.

The Iter3 outline comes from vertices_quadrant.csv (one quadrant, mirrored in x and y).
Those vertices were read from the paper's Fig 1/2 to about 0.05 mm; the paper does not give
the base side, the outward shift of the 4th iteration or the carpet ratio.

Usage:  python geometry/make_geometry.py [--out geometry/dxf] [--check-only]
"""
import argparse
import csv
import math
import sys
from pathlib import Path

import ezdxf
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent

# Paper dimensions (mm)
SL, SW = 60.0, 40.0          # board length (x) and width (y)
FW = 1.8                     # feed width
FL = 18.5                    # feed length parameter of the paper
D1 = 5.0                     # central slot side
CELL = D1                    # carpet cell pitch of the 8 medium slots (5 mm)
MED = D1 / 3.0               # medium slot side, 5/3 mm
SMALL = D1 / 9.0             # small slot side, 5/9 mm

# Feed: start x of the feed rectangle (it runs to x = SL/2); y is centred on 0.
FEED_START = {
    "Iter0": SL / 2 - FL - 2.0,
    "Iter1": SL / 2 - FL - 2.0,
    "Iter2": SL / 2 - FL - 0.6,
    "Iter3": SL / 2 - FL - 0.6,
    "KochOnly": SL / 2 - FL - 0.6,
}
FILENAMES = {
    "Iter0": "Iter0_triangle.dxf",
    "Iter1": "Iter1_triangle_slot5.dxf",
    "Iter2": "Iter2_hexagram_carpet2.dxf",
    "Iter3": "KochSierpinski_patch_v3_nofeed.dxf",
    "KochOnly": "KochOnly_noslots.dxf",
}


def read_quadrant(path=None):
    path = Path(path) if path else HERE / "vertices_quadrant.csv"
    with open(path, newline="") as fh:
        rows = sorted(csv.DictReader(fh), key=lambda r: int(r["order"]))
    return [(r["name"], float(r["x_mm"]), float(r["y_mm"])) for r in rows]


def koch_outline(quadrant):
    """Full 48-vertex outline from the upper-right quadrant (T on the y axis ... N on the x axis)."""
    q = [(x, y) for _, x, y in quadrant]
    right = q + [(x, -y) for x, y in reversed(q)][1:]            # T ... N ... T'   (clockwise)
    left = [(-x, y) for x, y in reversed(right)][1:-1]           # mirror in x, drop duplicated tips
    pts = right + left
    return Polygon(pts)


def triangle(R):
    a = R * math.sqrt(3.0)
    return Polygon([(-a / 2, R / 2), (a / 2, R / 2), (0.0, -R)])


def hexagram(R):
    a = R * math.sqrt(3.0)
    up = Polygon([(-a / 2, -R / 2), (a / 2, -R / 2), (0.0, R)])
    return unary_union([triangle(R), up])


def square(cx, cy, side):
    h = side / 2.0
    return box(cx - h, cy - h, cx + h, cy + h)


def medium_centres():
    return [(i * CELL, j * CELL) for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0)]


def slots_iter1():
    return [square(0.0, 0.0, D1)]


def slots_iter2():
    return slots_iter1() + [square(cx, cy, MED) for cx, cy in medium_centres()]


def slots_iter3():
    small = []
    step = MED                                   # 5/3 mm spacing of the small slots
    for cx, cy in medium_centres():
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                if (i, j) != (0, 0):
                    small.append(square(cx + i * step, cy + j * step, SMALL))
    return slots_iter2() + small


def build_designs(quadrant=None):
    quadrant = quadrant or read_quadrant()
    outline = koch_outline(quadrant)
    R = max(y for _, _, y in quadrant)           # tip height of the hexagram = 19.061 mm
    tri, hexa = triangle(R), hexagram(R)
    return {
        "Iter0": (tri, []),
        "Iter1": (tri, slots_iter1()),
        "Iter2": (hexa, slots_iter2()),
        "Iter3": (outline, slots_iter3()),
        "KochOnly": (outline, []),
    }


def feed_rectangle(design):
    return box(FEED_START[design], -FW / 2, SL / 2, FW / 2)


def ring_coords(poly):
    pts = list(poly.exterior.coords)[:-1]
    # counter-clockwise, no repeated closing point
    area2 = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return pts if area2 > 0 else pts[::-1]


def write_dxf(path, outline, holes):
    doc = ezdxf.new("R2010")
    doc.units = ezdxf.units.MM
    doc.layers.add("PATCH", color=1)
    doc.layers.add("HOLES", color=5)
    msp = doc.modelspace()
    msp.add_lwpolyline(ring_coords(outline), close=True, dxfattribs={"layer": "PATCH"})
    for h in holes:
        msp.add_lwpolyline(ring_coords(h), close=True, dxfattribs={"layer": "HOLES"})
    doc.saveas(path)


def edge_angle_deviation(poly, allowed=(0.0, 60.0, 120.0)):
    """Largest deviation (degrees) of any outline edge from the allowed directions (mod 180)."""
    pts = ring_coords(poly)
    worst = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180.0
        dev = min(min(abs(ang - a), 180.0 - abs(ang - a)) for a in allowed)
        worst = max(worst, dev)
    return worst


def checks(designs):
    """Return a list of (label, ok, detail)."""
    out = []
    add = lambda label, ok, detail="": out.append((label, bool(ok), detail))
    for name, (outline, holes) in designs.items():
        add(f"{name}: outline valid", outline.is_valid)
        body = outline.difference(unary_union(holes)) if holes else outline
        add(f"{name}: patch valid and one piece", body.is_valid and body.geom_type == "Polygon")
        add(f"{name}: all slots inside the outline, none overlapping",
            all(outline.contains(h) for h in holes) and
            all(not a.intersects(b) for i, a in enumerate(holes) for b in holes[i + 1:]))
        add(f"{name}: feed rectangle touches the patch",
            feed_rectangle(name).intersects(outline),
            f"feed starts at x={FEED_START[name]:.2f} mm")
    kout = designs["Iter3"][0]
    add("Iter3 outline has 48 vertices", len(ring_coords(kout)) == 48, str(len(ring_coords(kout))))
    dev = edge_angle_deviation(kout)
    add("Iter3 edges are at 0/60/120 deg within 0.1 deg", dev < 0.1, f"max deviation {dev:.3f} deg")
    minx, miny, maxx, maxy = kout.bounds
    add("Iter3 outline symmetric about both axes",
        abs(minx + maxx) < 1e-9 and abs(miny + maxy) < 1e-9, f"bounds x {minx:.3f}..{maxx:.3f}, y {miny:.3f}..{maxy:.3f}")
    add("Iter3 has 73 slots", len(designs["Iter3"][1]) == 73, str(len(designs["Iter3"][1])))
    ux = unary_union(designs["Iter3"][1]).bounds
    add("Carpet outer extent equals D2 = 13.88 mm (paper) within 0.02 mm",
        abs((ux[2] - ux[0]) - 13.88) < 0.02, f"{ux[2] - ux[0]:.3f} mm")
    hexa = designs["Iter2"][0]
    inner = sorted({round(abs(x), 3) for x, y in ring_coords(hexa) if abs(y) < 1e-6})
    add("Hexagram inner vertices at x = +-11.005", inner == [11.005], str(inner))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "dxf"), help="output folder for the DXF files")
    ap.add_argument("--check-only", action="store_true", help="run the self-checks, write nothing")
    args = ap.parse_args(argv)

    designs = build_designs()
    results = checks(designs)
    for label, ok, detail in results:
        print(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail else ""))
    failed = [r for r in results if not r[1]]
    print(f"{len(results) - len(failed)} passed, {len(failed)} failed, {len(results)} checks")
    if failed:
        return 1
    if args.check_only:
        return 0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, (outline, holes) in designs.items():
        write_dxf(out / FILENAMES[name], outline, holes)
        body = outline.difference(unary_union(holes)) if holes else outline
        print(f"wrote {FILENAMES[name]:38s} slots={len(holes):3d}  patch area={body.area:8.3f} mm^2")
    with open(HERE / "feed_dimensions.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["design", "x_start_mm", "x_end_mm", "y_centre_mm", "width_mm", "note"])
        for name, x0 in FEED_START.items():
            note = ("starts 2 mm before Sl/2-Fl: the slanted triangle edge meets the feed at x = 10.5-11.5 mm"
                    if name in ("Iter0", "Iter1") else
                    "starts 0.6 mm before Sl/2-Fl; overlaps the patch by about 0.1 mm at the notch apex")
            w.writerow([name, f"{x0:.3f}", f"{SL / 2:.3f}", "0.000", f"{FW:.3f}", note])
    print("wrote feed_dimensions.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
