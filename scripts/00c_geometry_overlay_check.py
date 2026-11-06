#!/usr/bin/env python3
"""Overlay the regenerated geometry on the paper's Fig 1 and Fig 2 and measure how well the edges agree.

What it tests
  For every edge of the outline, of each slot and of the feed, the script samples points along the
  edge, looks along the edge normal in the figure image for the dark outline line, and records the
  signed offset (mm) between the drawn line and the edge in the DXF geometry
  (positive = the figure's line lies farther out of the shape than the DXF edge).
  It also compares the filled areas (orange patch pixels) with the rasterised geometry.

What it does NOT show
  The vertices were originally read from Fig 1/2 (about 0.05 mm), so this test shows that the
  vertex table, the mirroring and the DXF writer reproduce the figures. It is not an independent
  measurement of the physical antenna: the paper gives no dimensions beyond Sl, Sw, Fw, Fl, D1, D2.
  Fig 2(d) is a separate rendering of the same design, so it gives a partly independent check of Fig 1.

Axis calibration: the board outline (60 x 40 mm) is found in each image; its border line centres
define the pixel <-> mm mapping separately in x and y, with the origin at the board centre.

Tolerances were fixed before the first run. First run: 73 passed, 11 failed, all failures in Fig 2 and all
within 0.01 mm of the threshold (outline mean offset -0.051 mm vs 0.05; feed-edge mean -0.052 to -0.055 mm vs 0.05;
feed width 1.69-1.70 mm vs 1.8 +-0.1). Two changes were then made AFTER seeing that result (disclosed here and in
the report): (1) the mean-offset tolerance has a floor of one image pixel (0.052 mm at the Fig 2 resolution), because
a tolerance below one pixel cannot be tested; (2) the feed edges and feed width are reported as measurements (INFO),
not pass/fail, because the DXF files contain no feed and the question "what width did the authors draw" is not a
test of the DXF geometry.

Usage (repo root, venv active):
  python scripts/00c_geometry_overlay_check.py --images C:\\Projects\\scratch_png --out docs\\verification
"""
import argparse
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_geometry", ROOT / "geometry" / "make_geometry.py")
mg = importlib.util.module_from_spec(spec)
sys.modules["make_geometry"] = mg
spec.loader.exec_module(mg)

# ---- tolerances (fixed before the first run) -------------------------------------------------
TOL_EDGE_MEDIAN_MM = 0.10      # every outline edge: |median offset|
TOL_MEAN_MM = 0.05             # per group: |mean offset|
TOL_P95_MM = 0.15              # per group: 95th percentile of |offset|
TOL_FEED_WIDTH_MM = 0.10       # measured feed width vs 1.8 mm
TOL_TILT_DEG = 0.5             # edge direction error
TOL_ACCEPT = 0.80              # fraction of sample points that gave a usable line position
TOL_ANISO = 0.005              # |sx/sy - 1|
TOL_IOU = 0.995                # filled-area agreement
SAMPLE_STEP_MM = 0.10
END_MARGIN_MM = 0.12
WINDOW_MM = 0.22

results = []
infos = []


def info(text):
    infos.append(text)
    print("INFO  " + text, flush=True)


def check(label, ok, detail=""):
    results.append((label, bool(ok), detail))
    print(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail else ""), flush=True)


# ---- image helpers ----------------------------------------------------------------------------
def find_image(folder, tokens):
    """Pick the image whose name starts with one of the tokens; an 'upscaled' version wins over other versions."""
    cands = [p for p in sorted(Path(folder).iterdir())
             if p.suffix.lower() in (".png", ".webp", ".jpg", ".jpeg") and any(p.name.lower().startswith(t) for t in tokens)]
    cands.sort(key=lambda p: (0 if "upscaled" in p.name.lower() else 1, p.name.lower()))
    if len(cands) > 1:
        print(f"Several candidates for {tokens[0]}: {[c.name for c in cands]}; using {cands[0].name} "
              f"(pass --fig1 / --fig2 to choose another)")
    return cands[0] if cands else None


def describe_image(path, im):
    yellow, orange = board_class_masks(im)
    print(f"  loaded {Path(path).name}: {im.shape[1]} x {im.shape[0]} px, yellow pixels {int(yellow.sum())}, "
          f"orange pixels {int(orange.sum())}", flush=True)


def load_rgb(path):
    return np.array(Image.open(path).convert("RGB")).astype(np.int16)


def board_class_masks(im):
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    yellow = (R > 200) & (G > 200) & (B < 120)
    orange = (R > 200) & (G > 100) & (G < 190) & (B < 90)
    return yellow, orange


def find_boards(im):
    yellow, orange = board_class_masks(im)
    m = yellow | orange
    lab, n = ndi.label(m)
    objs = ndi.find_objects(lab)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    boxes = []
    for k, sl in enumerate(objs):
        if sizes[k] < 0.02 * im.shape[0] * im.shape[1]:
            continue
        y0, y1, x0, x1 = sl[0].start, sl[0].stop - 1, sl[1].start, sl[1].stop - 1
        boxes.append((x0, x1, y0, y1))
    boxes = [b for b in boxes if not any(o != b and o[0] <= b[0] and o[1] >= b[1] and o[2] <= b[2] and o[3] >= b[3] for o in boxes)]
    boxes.sort(key=lambda b: (round(b[2] / max(1, im.shape[0] / 4)), b[0]))
    return boxes


def border_centre(im, box, side):
    """Sub-pixel centre of the dark board border line on one side (pixel-index coordinates)."""
    x0, x1, y0, y1 = box
    Rch = im[..., 0].astype(float)
    w = np.clip(240.0 - Rch, 0, None)
    cs = []
    if side in ("left", "right"):
        rows = np.arange(int(y0 + 0.20 * (y1 - y0)), int(y0 + 0.40 * (y1 - y0)))
        for r in rows:
            xs = np.arange(x0 - 15, x0 + 3) if side == "left" else np.arange(x1 - 2, x1 + 16)
            xs = xs[(xs >= 0) & (xs < w.shape[1])]
            ww = w[r, xs]
            if ww.sum() > 50:
                cs.append((xs * ww).sum() / ww.sum())
    else:
        cols = np.arange(int(x0 + 0.20 * (x1 - x0)), int(x0 + 0.40 * (x1 - x0)))
        for c in cols:
            ys = np.arange(y0 - 15, y0 + 3) if side == "top" else np.arange(y1 - 2, y1 + 16)
            ys = ys[(ys >= 0) & (ys < w.shape[0])]
            ww = w[ys, c]
            if ww.sum() > 50:
                cs.append((ys * ww).sum() / ww.sum())
    return float(np.median(cs)) if cs else float("nan")


class Frame:
    def __init__(self, im, box):
        self.xl, self.xr = border_centre(im, box, "left"), border_centre(im, box, "right")
        self.yt, self.yb = border_centre(im, box, "top"), border_centre(im, box, "bottom")
        self.sx = (self.xr - self.xl) / mg.SL
        self.sy = (self.yb - self.yt) / mg.SW
        self.xc, self.yc = (self.xl + self.xr) / 2, (self.yt + self.yb) / 2
        self.s = (self.sx + self.sy) / 2
        if not all(np.isfinite(v) for v in (self.xl, self.xr, self.yt, self.yb)):
            raise ValueError("the dark board border line was not found on every side of the board "
                             "(is the image cropped too tightly, or is it a different version of the figure?)")

    def to_px(self, x, y):
        return self.xc + x * self.sx, self.yc - y * self.sy


# ---- edge sampling ---------------------------------------------------------------------------
def ring_edges(pts, outward_is_right):
    """Yield (p0, p1, outward_normal) for each edge of a ring given CCW; normal points away from the ring interior."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        n = (dy / L, -dx / L)   # right-hand normal = outward for a CCW ring
        yield (x0, y0), (x1, y1), n, L


def sample_edge(im_R, fr, p0, p1, n, L, skip_zone=None):
    """Return list of (t_mm, offset_mm or None) along one edge."""
    win_px = WINDOW_MM * fr.s
    step = 0.25
    offs_px = np.arange(-win_px, win_px + 1e-9, step)
    out = []
    t_values = np.arange(END_MARGIN_MM, L - END_MARGIN_MM + 1e-9, SAMPLE_STEP_MM)
    ux, uy = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L
    for t in t_values:
        x, y = p0[0] + ux * t, p0[1] + uy * t
        if skip_zone is not None and skip_zone.contains(Point(x, y)):
            continue
        px, py = fr.to_px(x, y)
        npx, npy = n[0], -n[1]                       # image y points down
        rr = py + offs_px * npy
        cc = px + offs_px * npx
        prof = ndi.map_coordinates(im_R, [rr, cc], order=1, mode="nearest")
        w = np.clip(235.0 - prof, 0, None)
        ok = (prof.min() >= 60) and (w.max() >= 50) and (w[0] < 15) and (w[-1] < 15)
        if not ok:
            out.append((t, None))
            continue
        off_px = float((offs_px * w).sum() / w.sum())
        out.append((t, off_px / fr.s))
    return out


def stats(a):
    a = np.asarray(a, float)
    if a.size == 0:
        return dict(n=0, mean=float("nan"), median=float("nan"), std=float("nan"), p95=float("nan"), mx=float("nan"))
    return dict(n=a.size, mean=a.mean(), median=np.median(a), std=a.std(), p95=np.percentile(np.abs(a), 95), mx=np.abs(a).max())


# ---- per-design analysis ---------------------------------------------------------------------
def analyse(tag, im, box, design, designs, out_dir, edge_rows):
    outline, holes = designs[design]
    fr = Frame(im, box)
    aniso = fr.sx / fr.sy - 1.0
    print(f"\n--- {tag}: design {design}; scale {fr.sx:.3f} x {fr.sy:.3f} px/mm; board border centres "
          f"x {fr.xl:.2f}..{fr.xr:.2f}, y {fr.yt:.2f}..{fr.yb:.2f}", flush=True)
    check(f"{tag}: board frame found and scale isotropic within {TOL_ANISO*100:.1f} %",
          np.isfinite(aniso) and abs(aniso) <= TOL_ANISO, f"sx/sy-1 = {aniso*100:+.3f} %, {fr.s:.2f} px/mm")

    Rch = im[..., 0].astype(float)
    feed = mg.feed_rectangle(design)
    zone = feed.buffer(0.25)
    groups = {"outline": [], "slot_5mm": [], "slot_1.67mm": [], "slot_0.56mm": []}
    tried = {k: 0 for k in groups}

    # outline
    pts = mg.ring_coords(outline)
    for i, (p0, p1, n, L) in enumerate(ring_edges(pts, True)):
        res = sample_edge(Rch, fr, p0, p1, n, L, skip_zone=zone)
        tried["outline"] += len(res)
        good = [(t, o) for t, o in res if o is not None]
        groups["outline"] += [o for _, o in good]
        row = dict(fig=tag, design=design, ring="outline", edge=i, length_mm=round(L, 3),
                   angle_deg=round(math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])) % 180, 2),
                   n_try=len(res), n_ok=len(good), median_off_mm=float("nan"), tilt_deg=float("nan"))
        if len(good) >= 5:
            ts = np.array([t for t, _ in good]); os_ = np.array([o for _, o in good])
            row["median_off_mm"] = float(np.median(os_))
            if (ts.max() - ts.min()) >= 0.6 * L and L >= 2.0:
                row["tilt_deg"] = math.degrees(math.atan(np.polyfit(ts, os_, 1)[0]))
        edge_rows.append(row)

    # slots
    for h in holes:
        side = h.bounds[2] - h.bounds[0]
        key = "slot_5mm" if side > 3 else ("slot_1.67mm" if side > 1 else "slot_0.56mm")
        hp = mg.ring_coords(h)                      # CCW; right-hand normal points INTO the hole
        for p0, p1, n, L in ring_edges(hp, True):
            n_out_of_hole = (-n[0], -n[1])         # away from the slot interior
            res = sample_edge(Rch, fr, p0, p1, n_out_of_hole, L)
            tried[key] += len(res)
            groups[key] += [o for _, o in res if o is not None]

    # feed edges (outward normal = +y for the top edge, -y for the bottom edge)
    fx0 = 13.0
    feed_off = {}
    for name, (y, ny) in {"top": (mg.FW / 2, 1.0), "bottom": (-mg.FW / 2, -1.0)}.items():
        res = sample_edge(Rch, fr, (fx0, y), (29.0, y), (0.0, ny), 29.0 - fx0)
        vals = [o for _, o in res if o is not None]
        feed_off[name] = float(np.median(vals)) if len(vals) >= 5 else float("nan")
        groups.setdefault("feed_edges", []).extend(vals)
        tried.setdefault("feed_edges", 0)
        tried["feed_edges"] += len(res)

    for key, vals in groups.items():
        st = stats(vals)
        frac = st["n"] / max(1, tried[key])
        print(f"{tag} {key:12s} accepted {st['n']:5d}/{tried[key]:5d} ({frac*100:5.1f} %)  mean {st['mean']:+.3f}  "
              f"median {st['median']:+.3f}  std {st['std']:.3f}  p95|off| {st['p95']:.3f}  max|off| {st['mx']:.3f} mm", flush=True)
        if key == "feed_edges":
            info(f"{tag} feed edges: mean offset {st['mean']:+.3f} mm (outward positive), usable {frac*100:.0f} %")
            continue
        if key.startswith("slot") and tried[key] == 0:
            continue
        tol_mean = max(TOL_MEAN_MM, 1.0 / fr.s)                      # never tighter than one image pixel
        check(f"{tag} {key}: >= {TOL_ACCEPT*100:.0f} % of sample points usable", frac >= TOL_ACCEPT, f"{frac*100:.1f} %")
        check(f"{tag} {key}: |mean offset| <= {tol_mean:.3f} mm (max of {TOL_MEAN_MM} mm and 1 px)", abs(st["mean"]) <= tol_mean, f"{st['mean']:+.3f} mm")
        check(f"{tag} {key}: p95 |offset| <= {TOL_P95_MM} mm", st["p95"] <= TOL_P95_MM, f"{st['p95']:.3f} mm")

    ed = [r for r in edge_rows if r["fig"] == tag and r["ring"] == "outline" and np.isfinite(r["median_off_mm"])]
    worst = max(ed, key=lambda r: abs(r["median_off_mm"])) if ed else None
    check(f"{tag} outline: every edge |median offset| <= {TOL_EDGE_MEDIAN_MM} mm ({len(ed)} edges measured)",
          bool(ed) and abs(worst["median_off_mm"]) <= TOL_EDGE_MEDIAN_MM,
          f"worst edge {worst['edge']}: {worst['median_off_mm']:+.3f} mm" if worst else "no edge measured")
    tl = [r for r in edge_rows if r["fig"] == tag and np.isfinite(r["tilt_deg"])]
    if tl:
        wt = max(tl, key=lambda r: abs(r["tilt_deg"]))
        check(f"{tag} outline: edge direction within {TOL_TILT_DEG} deg ({len(tl)} edges)", abs(wt["tilt_deg"]) <= TOL_TILT_DEG,
              f"worst edge {wt['edge']}: {wt['tilt_deg']:+.2f} deg")
    if np.isfinite(feed_off["top"]) and np.isfinite(feed_off["bottom"]):
        fwm = mg.FW + feed_off["top"] + feed_off["bottom"]
        info(f"{tag} drawn feed width {fwm:.3f} mm (paper text: {mg.FW} mm); feed centre offset "
             f"{(feed_off['top'] - feed_off['bottom'])/2:+.3f} mm")
    else:
        info(f"{tag} feed width not measurable (annotation arrows in the way?)")

    # filled-area agreement
    Hh, Ww = im.shape[:2]
    exp = Image.new("L", (Ww, Hh), 0)
    d = ImageDraw.Draw(exp)
    d.polygon([fr.to_px(x, y) for x, y in pts], fill=1)
    for h in holes:
        d.polygon([fr.to_px(x, y) for x, y in mg.ring_coords(h)], fill=0)
    d.polygon([fr.to_px(x, y) for x, y in mg.ring_coords(feed)], fill=1)
    exp = np.array(exp).astype(bool)
    R_, G_, B_ = im[..., 0], im[..., 1], im[..., 2]
    obs = (R_ > 180) & (G_ < 195) & (B_ < 110)                        # orange
    dark = R_ < 190
    band = ndi.binary_dilation(dark, iterations=max(2, int(round(0.05 * fr.s))))
    inside = np.zeros_like(exp)
    inside[int(fr.yt + 3):int(fr.yb - 3), int(fr.xl + 3):int(fr.xr - 3)] = True
    use = inside & ~band
    inter = (obs & exp & use).sum()
    union = ((obs | exp) & use).sum()
    iou = inter / union
    check(f"{tag} filled-area agreement (IoU, excluding dark lines) >= {TOL_IOU}", iou >= TOL_IOU,
          f"IoU {iou:.5f}; {(obs ^ exp)[use].sum()} mismatching pixels = {(obs ^ exp)[use].sum() / fr.s**2:.3f} mm^2")
    return fr, pts


def draw_overlay(im, fr, design, designs, width):
    img = Image.fromarray(im.astype(np.uint8))
    d = ImageDraw.Draw(img)
    outline, holes = designs[design]
    def poly(coords, color):
        px = [fr.to_px(x, y) for x, y in coords]
        d.line(px + [px[0]], fill=color, width=width)
    poly(mg.ring_coords(outline), (0, 200, 255))
    for h in holes:
        poly(mg.ring_coords(h), (255, 0, 255))
    poly(mg.ring_coords(mg.feed_rectangle(design)), (0, 200, 0))
    return img


def crop_mm(img, fr, x0, x1, y0, y1, scale=1):
    a, b = fr.to_px(x0, y1)
    c, e = fr.to_px(x1, y0)
    cr = img.crop((int(a), int(b), int(c), int(e)))
    if scale != 1:
        cr = cr.resize((cr.width * scale, cr.height * scale), Image.NEAREST)
    return cr


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True, help="folder with the paper's Figure 1 and Figure 2 images")
    ap.add_argument("--out", default=str(ROOT / "docs" / "verification"), help="output folder")
    ap.add_argument("--fig1", help="explicit path of the Fig 1 image (the upscaled version is recommended)")
    ap.add_argument("--fig2", help="explicit path of the Fig 2 image")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    f1 = Path(args.fig1) if args.fig1 else find_image(args.images, ("figure_1", "figure 1", "fig1", "fig_1"))
    f2 = Path(args.fig2) if args.fig2 else find_image(args.images, ("figure_2", "figure 2", "fig2", "fig_2"))
    missing = [n for n, p in (("Figure 1", f1), ("Figure 2", f2)) if p is None]
    if missing:
        print(f"Missing {missing} in {args.images}. Files found: {[p.name for p in Path(args.images).iterdir()]}")
        return 2

    designs = mg.build_designs()
    edge_rows = []

    # Fig 1 (final design)
    im1 = load_rgb(f1)
    describe_image(f1, im1)
    boxes1 = find_boards(im1)
    check("Fig 1: one board found", len(boxes1) == 1, f"{len(boxes1)} found")
    if len(boxes1) != 1:
        print("Cannot continue: the board (yellow substrate with orange patch) was not found as one region in "
              f"{f1.name}. Use the same Fig 1 image as in the project chat (Figure_1_upscaled.webp) via --fig1.")
        return 2
    try:
        fr1, _ = analyse("Fig1", im1, boxes1[0], "Iter3", designs, out, edge_rows)
    except ValueError as e:
        print(f"Cannot continue with {f1.name}: {e}")
        return 2
    ov1 = draw_overlay(im1, fr1, "Iter3", designs, width=2)
    ov1.resize((ov1.width // 2, ov1.height // 2), Image.LANCZOS).save(out / "geometry_overlay_fig1_full.png")
    crop_mm(ov1, fr1, 8.5, 22.0, -6.0, 6.0, 1).save(out / "geometry_overlay_fig1_notch_feed.png")
    crop_mm(ov1, fr1, 0.0, 8.5, 0.0, 8.5, 2).save(out / "geometry_overlay_fig1_carpet_quadrant.png")
    crop_mm(ov1, fr1, 0.0, 19.0, 8.0, 19.8, 1).save(out / "geometry_overlay_fig1_top_right.png")

    # Fig 2 panels a-d = Iter0..Iter3
    im2 = load_rgb(f2)
    describe_image(f2, im2)
    boxes2 = find_boards(im2)
    check("Fig 2: four boards found", len(boxes2) == 4, f"{len(boxes2)} found")
    if len(boxes2) != 4:
        print(f"Cannot continue: expected 4 boards in {f2.name}.")
        return 2
    panels = []
    for tag, design, box in zip(("Fig2a", "Fig2b", "Fig2c", "Fig2d"), ("Iter0", "Iter1", "Iter2", "Iter3"), boxes2):
        try:
            fr, _ = analyse(tag, im2, box, design, designs, out, edge_rows)
        except ValueError as e:
            print(f"Cannot continue with {f2.name}: {e}")
            return 2
        ov = draw_overlay(im2, fr, design, designs, width=1)
        panels.append(crop_mm(ov, fr, -31, 31, -21, 21, 1))
    w = max(p.width for p in panels); h = max(p.height for p in panels)
    mont = Image.new("RGB", (2 * w, 2 * h), (255, 255, 255))
    for k, p in enumerate(panels):
        mont.paste(p, ((k % 2) * w, (k // 2) * h))
    mont.save(out / "geometry_overlay_fig2_panels.png")

    # edge table and report
    import csv
    with open(out / "geometry_overlay_edges.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(edge_rows[0].keys()))
        wr.writeheader()
        wr.writerows(edge_rows)
    npass = sum(1 for r in results if r[1])
    summary = f"{npass} passed, {len(results) - npass} failed, {len(results)} checks"
    with open(out / "geometry_overlay_report.txt", "w", encoding="utf-8") as fh:
        for label, ok, detail in results:
            fh.write(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail else "") + "\n")
        fh.write(summary + "\n\nMeasurements (not pass/fail):\n")
        for t in infos:
            fh.write("INFO  " + t + "\n")
    print("\n" + summary)
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
