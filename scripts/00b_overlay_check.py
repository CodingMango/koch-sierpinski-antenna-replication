"""
00b_overlay_check.py - overlay test for the digitized paper figures (Figs 4, 5, 9, 11).

WHY
---
00_verify_data.py shows that the CSV files agree with each other and with the numbers
printed in the paper. It cannot show that the digitized curves lie on the curves of the
ORIGINAL figure images. This script does that: it puts the digitized points back onto
the original PNG and measures how well they sit on the drawn curves.

WHAT IT DOES
------------
Line plots (Fig 4 = S11 of 4 iterations, Fig 5 = simulated S11, Fig 11 = gain vs frequency)
  1. Finds the black plot frame and the axis tick marks in the image.
  2. Builds the pixel<->data calibration from the TICK MARKS (checks they are evenly
     spaced; for Fig 4 it also compares with the frame constants used when digitizing).
  3. Test A "points sit on the curve": every digitized (GHz, value) point is converted
     to a pixel; that pixel must have the colour of its own curve.
  4. Test B "no curve piece is missed": every pixel of the curve colour must lie close
     to the digitized polyline (legend sample lines are ignored).
Polar plots (Fig 9, 7 panels, E and H curves)
  1. Finds the outer black circle of each panel (RANSAC circle fit) -> centre, radius.
  2. Converts each (angle, radius in pixels) to a pixel (0 deg = right, counter-clockwise)
     and runs tests A and B. Only raw pixel radii are tested; the radius->dB scale is not
     in the CSV and is covered by the text-anchor check in 00_verify_data.py.

OUTPUT
------
PASS/FAIL table, overlay images (digitized points drawn on the original figure) and
overlay_report.txt in --out. Exit code 0 if everything passes.

LIMITS
------
Test A is partly circular (the points were extracted from the same colours), so it
confirms that the CSV and the image use the same pixel mapping. The independent parts are
the tick calibration, the circle fit and test B (completeness). Always look at the overlay
images too. The measured (blue) curve of Fig 5 was never digitized, so it is not tested.

USAGE
-----
Run from the REPOSITORY ROOT (the folder that contains README.md, scripts/ and data/):
    python scripts/00b_overlay_check.py --images C:\\Projects\\scratch_png --data-dir C:\\Projects\\scratch_csv
Needs Figure_4.png, Figure_5.png, Figure_9.png, Figure_9_Cont.png, Figure_11.png in --images
(any upper/lower case, spaces or "(1)" suffixes are tolerated; .png/.jpg accepted).
Do not end the folder path with a backslash inside quotes in PowerShell.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, label, find_objects

CSV_NAMES = {
    "fig4": ["paper_fig4_s11_iter0-3_digitized.csv", "paper_Fig4_digitized_all.csv"],
    "fig5": ["paper_s11_final_simulated_digitized.csv", "paper_S11_digitized.csv"],
    "fig9": ["paper_fig9_patterns_raw_pixels.csv", "paper_Fig9_digitized_pixels.csv"],
    "fig11": ["paper_fig11_gain_vs_freq_digitized.csv", "paper_Fig11_gain_digitized_v2.csv"],
}
IMAGE_STEMS = {  # key -> (expected file name, accepted normalised stems)
    "fig4": ("Figure_4.png", {"figure4", "fig4"}),
    "fig5": ("Figure_5.png", {"figure5", "fig5"}),
    "fig9": ("Figure_9.png", {"figure9", "fig9"}),
    "cont": ("Figure_9_Cont.png", {"figure9cont", "fig9cont", "figure9continued"}),
    "fig11": ("Figure_11.png", {"figure11", "fig11"}),
}
FIG4_COLOURS = {"Iter0": (31, 119, 180), "Iter1": (255, 127, 14), "Iter2": (44, 160, 44), "Iter3": (214, 39, 40)}
FIG4_FRAME_REF = (285.5, 2065.5, 50.5, 1179.5, 0.5, 10.0, 0.0, -30.0)  # px x_left,x_right,y_top,y_bottom ; data f_left,f_right,s_top,s_bottom
FIG4_LEGEND = (640, 830)  # legend box covers x < 640 and y > 830 (excluded from test B)
RED = (255, 0, 0)

results = []
rng = np.random.default_rng(0)


def record(group, name, ok, detail=""):
    results.append((group, name, bool(ok), detail))


# ------------------------------------------------------------------ file finding
def norm_stem(path):
    stem = re.sub(r"\s*\(\d+\)$", "", path.stem)          # "Figure_4 (1)" -> "Figure_4"
    return re.sub(r"[^a-z0-9]", "", stem.lower())          # "Figure_4" -> "figure4"


def find_images(folder):
    """Return ({key: path or None}, [image files seen])."""
    folder = Path(folder)
    seen = sorted(p for p in folder.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg")) if folder.is_dir() else []
    found = {}
    for key, (_, stems) in IMAGE_STEMS.items():
        found[key] = next((p for p in seen if norm_stem(p) in stems), None)
    return found, seen


def find_csv(folder, names):
    for n in names:
        hits = list(Path(folder).rglob(n)) if Path(folder).is_dir() else []
        if hits:
            return hits[0]
    return None


def cluster(idx, gap=2):
    idx = list(idx)
    if not idx:
        return []
    groups, cur = [], [idx[0]]
    for v in idx[1:]:
        if v - cur[-1] <= gap:
            cur.append(v)
        else:
            groups.append(float(np.mean(cur))); cur = [v]
    groups.append(float(np.mean(cur)))
    return groups


def dist_to(mask):
    return distance_transform_edt(~mask)


def remove_legend_lines(mask):
    """Drop short thick horizontal components (legend sample lines)."""
    lab, n = label(mask)
    keep = np.ones(n + 1, bool); keep[0] = False
    for i, o in enumerate(find_objects(lab), 1):
        h = o[0].stop - o[0].start; w = o[1].stop - o[1].start
        if w >= 50 and h <= 14 and (lab[o] == i).sum() < 2000:
            keep[i] = False
    return keep[lab]


# ------------------------------------------------------------------ line plots
def check_xy_figure(g, png, series, xvals, yvals, out, tag, frame_ref=None, legend_rect=None,
                    auto_legend=False, extremes=False, zoom_from=None):
    """series: list of (label, (r,g,b), x data array, y data array)."""
    im = np.array(Image.open(png).convert("RGB")).astype(int)
    H, W, _ = im.shape
    dark = im.sum(axis=2) < 150
    vx = cluster(np.nonzero(dark.sum(axis=0) > 0.5 * H)[0])
    hy = cluster(np.nonzero(dark.sum(axis=1) > 0.4 * W)[0])
    record(g, "plot frame found (2 vertical + 2 horizontal lines)", len(vx) == 2 and len(hy) == 2, f"v={vx}, h={hy}")
    if len(vx) != 2 or len(hy) != 2:
        return
    xl, xr, yt, yb = vx[0], vx[1], hy[0], hy[1]
    xt = cluster([i for i, c in enumerate(dark[int(yb) + 5:int(yb) + 17, :].sum(axis=0)) if c >= 8 and xl - 5 < i < xr + 5])
    yk = cluster([i for i, c in enumerate(dark[:, int(xl) - 18:int(xl) - 4].sum(axis=1)) if c >= 8 and yt - 5 < i < yb + 5])
    record(g, f"{len(xvals)} x-ticks and {len(yvals)} y-ticks found", len(xt) == len(xvals) and len(yk) == len(yvals),
           f"{len(xt)} x-ticks, {len(yk)} y-ticks")
    if len(xt) != len(xvals) or len(yk) != len(yvals):
        return
    ax, bx = np.polyfit(xvals, xt, 1)
    ay, by = np.polyfit(yvals, yk, 1)
    resx = np.abs(np.polyval([ax, bx], xvals) - xt).max()
    resy = np.abs(np.polyval([ay, by], yvals) - yk).max()
    record(g, "ticks are evenly spaced (residual <= 1 px)", max(resx, resy) <= 1.0, f"x {resx:.2f} px, y {resy:.2f} px")
    x_left, x_right = (xl - bx) / ax, (xr - bx) / ax
    record(g, "INFO axis span read from the ticks", True,
           f"x {x_left:.2f} to {x_right:.2f}; y {(yt - by) / ay:.1f} (top) to {(yb - by) / ay:.1f} (bottom); "
           f"1 px = {1/abs(ax):.4f} x-units = {1/abs(ay):.3f} y-units")
    if frame_ref:
        fx = lambda f: frame_ref[0] + (f - frame_ref[4]) / (frame_ref[5] - frame_ref[4]) * (frame_ref[1] - frame_ref[0])
        fy = lambda s: frame_ref[2] + (s - frame_ref[6]) / (frame_ref[7] - frame_ref[6]) * (frame_ref[3] - frame_ref[2])
        dfr = max(abs(xl - frame_ref[0]), abs(xr - frame_ref[1]), abs(yt - frame_ref[2]), abs(yb - frame_ref[3]))
        record(g, "frame matches the digitizing calibration (<= 1 px)", dfr <= 1.0, f"max difference {dfr:.2f} px")
        dd = max([abs(ax * f + bx - fx(f)) for f in (frame_ref[4], 2, frame_ref[5])] +
                 [abs(ay * s + by - fy(s)) for s in (frame_ref[6], -15, frame_ref[7])])
        record(g, "tick calibration = frame calibration (<= 1.5 px)", dd <= 1.5, f"max difference {dd:.2f} px")

    out_img = Image.fromarray(im.astype(np.uint8)); draw = ImageDraw.Draw(out_img)
    for label_, col, xs, ys in series:
        order = np.argsort(xs); xs, ys = np.asarray(xs)[order], np.asarray(ys)[order]
        mk = np.abs(im - np.array(col)).sum(axis=2) < 60
        x = ax * xs + bx; y = ay * ys + by
        xi = np.clip(np.round(x).astype(int), 0, W - 1); yi = np.clip(np.round(y).astype(int), 0, H - 1)
        # drawn stroke thickness and the position of each digitized point inside the stroke
        offs, thick = [], []
        for xc, yc in zip(xi[::5], yi[::5]):
            colm = mk[:, xc]
            if not colm[yc]:
                continue
            a = yc
            while a > 0 and colm[a - 1]: a -= 1
            b = yc
            while b < H - 1 and colm[b + 1]: b += 1
            if b - a <= 40:
                offs.append(yc - (a + b) / 2.0); thick.append(b - a + 1)
        med_thick = float(np.median(thick)) if thick else 8.0
        # Test A: a point may lie up to 5 px outside the visible stroke (stroke edges are anti-aliased,
        # and 5 px = 0.14 dB on the S11 plots). The stricter 3 px figure is reported as INFO.
        dA = dist_to(mk)[yi, xi]
        fa = float((dA <= 5).mean())
        record(g, f"{label_}: digitized points on the curve (<= 5 px)", fa >= 0.995,
               f"{100*fa:.1f}% of {len(xs)} points ({100*(dA <= 3).mean():.1f}% within 3 px; farthest {dA.max():.1f} px)")
        # Test B: every curve pixel must be near the digitized line. At sharp peaks the thick stroke sticks out
        # past the vertex, so the tolerance is max(12 px, 1.5 x the measured stroke thickness).
        tol_b = max(12.0, 1.5 * med_thick)
        mkb = mk.copy()
        mkb[:, :int(xl)] = False; mkb[:, int(xr) + 2:] = False; mkb[:int(yt) - 1] = False; mkb[int(yb) + 2:] = False
        if legend_rect:
            mkb[legend_rect[1]:, :legend_rect[0]] = False
        if auto_legend:
            mkb &= remove_legend_lines(mkb)
        poly = Image.new("L", (W, H), 0); ImageDraw.Draw(poly).line(list(zip(x, y)), fill=255, width=1)
        yy, xx = np.nonzero(mkb)
        db_ = dist_to(np.array(poly) > 0)[yy, xx]
        fb = float((db_ <= tol_b).mean())
        record(g, f"{label_}: no curve piece missed (<= {tol_b:.0f} px)", fb >= 0.995,
               f"{100*fb:.2f}% of {len(xx)} curve pixels; farthest {db_.max():.0f} px = {db_.max()/abs(ay):.2f} y-units; "
               f"stroke is {med_thick:.0f} px thick")
        if offs:
            record(g, f"{label_}: INFO digitized value vs centre of the drawn line", True,
                   f"{np.median(offs)/ay:+.2f} y-units (stroke = {med_thick/abs(ay):.2f} y-units thick)")
        if extremes:
            ysel, _ = np.nonzero(mkb)
            top_v, bot_v = (ysel.min() - by) / ay, (ysel.max() - by) / ay
            record(g, f"{label_}: INFO digitized max/min vs outer edge of the drawn stroke", True,
                   f"digitized max {np.max(ys):.2f}, top edge {top_v:.2f}; digitized min {np.min(ys):.2f}, bottom edge {bot_v:.2f} "
                   f"(the stroke edge lies beyond the true vertex at sharp tips)")
        for xp, yp in zip(x, y):
            draw.ellipse([xp - 2, yp - 2, xp + 2, yp + 2], fill=(0, 0, 0))
    out_img.save(out / f"overlay_{tag}_full.png")
    if zoom_from is not None:
        x6 = int(ax * zoom_from + bx)
        out_img.crop((x6, int(yt) - 20, int(xr) + 40, int(yb) + 20)).resize(
            (int((xr + 40 - x6) * 1.6), int((yb - yt + 40) * 1.6)), Image.LANCZOS).save(out / f"overlay_{tag}_zoom.png")


# ------------------------------------------------------------------ Fig 9 (polar)
def fit3(p):
    (x1, y1), (x2, y2), (x3, y3) = p
    A = np.array([[x2 - x1, y2 - y1], [x3 - x1, y3 - y1]]) * 2.0
    b = np.array([x2**2 - x1**2 + y2**2 - y1**2, x3**2 - x1**2 + y3**2 - y1**2])
    try:
        c = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        return None
    return c, float(np.hypot(x1 - c[0], y1 - c[1]))


def fit_circle(pts, rmin=300, rmax=460, iters=4000):
    best = None
    for _ in range(iters):
        r = fit3(pts[rng.choice(len(pts), 3, replace=False)])
        if r is None or not (rmin < r[1] < rmax):
            continue
        c, rad = r
        n = (np.abs(np.hypot(pts[:, 0] - c[0], pts[:, 1] - c[1]) - rad) < 2).sum()
        if best is None or n > best[0]:
            best = (n, c, rad)
    _, c, rad = best
    m = np.abs(np.hypot(pts[:, 0] - c[0], pts[:, 1] - c[1]) - rad) < 3
    x, y = pts[m, 0], pts[m, 1]
    sol = np.linalg.lstsq(np.c_[2 * x, 2 * y, np.ones(len(x))], x**2 + y**2, rcond=None)[0]
    return sol[0], sol[1], float(np.sqrt(sol[2] + sol[0]**2 + sol[1]**2))


def curve_mask(im, curve, pale=True):
    r, g_, b = im[..., 0], im[..., 1], im[..., 2]
    if curve == "E":
        m = (b > 180) & (r < 90) & (g_ < 90)
        if pale: m |= (b > 235) & (r < 225) & (g_ < 225) & (b - r > 25) & (b - g_ > 25)
    else:
        m = (r > 180) & (g_ < 90) & (b < 90)
        if pale: m |= (r > 235) & (g_ < 225) & (b < 225) & (r - g_ > 25) & (r - b > 25)
    return m


PANELS = {"a": ("fig9", (0, 1/3), None), "b": ("fig9", (1/3, 2/3), None), "c": ("fig9", (2/3, 1), None),
          "d": ("cont", (0, 1/3), "top"), "e": ("cont", (1/3, 2/3), "top"), "f": ("cont", (2/3, 1), "top"),
          "g": ("cont", (1/3, 2/3), "bottom")}


def check_fig9(pngs, csv, out):
    g = "Fig 9"
    d = pd.read_csv(csv)
    imgs = {k: np.array(Image.open(p).convert("RGB")).astype(int) for k, p in pngs.items()}
    draws = {k: Image.fromarray(v.astype(np.uint8)) for k, v in imgs.items()}
    dr = {k: ImageDraw.Draw(v) for k, v in draws.items()}
    cache = {}
    for panel, (key, (xa, xb), part) in PANELS.items():
        im = imgs[key]; H, W, _ = im.shape
        y0, y1 = (0, H) if part is None else ((0, 1100) if part == "top" else (1100, H))
        ys, xs = np.nonzero((im.sum(axis=2) < 120)[y0:y1, int(xa * W):int(xb * W)])
        pts = np.c_[xs + int(xa * W), ys + y0].astype(float)
        if len(pts) > 60000:
            pts = pts[rng.choice(len(pts), 60000, replace=False)]
        cx, cy, rad = fit_circle(pts)
        record(g, f"panel {panel}: outer circle found (radius 385-395 px)", 385 <= rad <= 395, f"centre ({cx:.1f}, {cy:.1f}), radius {rad:.1f}")
        dr[key].ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(0, 160, 0), width=2)
        dr[key].line([cx - 15, cy, cx + 15, cy], fill=(0, 160, 0), width=2); dr[key].line([cx, cy - 15, cx, cy + 15], fill=(0, 160, 0), width=2)
        for cv in ("E", "H"):
            s = d[(d.panel == panel) & (d.curve == cv)].dropna(subset=["r_px"]).sort_values("ang")
            th = np.deg2rad(s.ang.values)
            x = cx + s.r_px.values * np.cos(th); y = cy - s.r_px.values * np.sin(th)
            xi = np.clip(np.round(x).astype(int), 0, W - 1); yi = np.clip(np.round(y).astype(int), 0, H - 1)
            ck = (key, cv)
            if ck not in cache:
                cache[ck] = dist_to(curve_mask(im, cv))
            fa = float((cache[ck][yi, xi] <= 3).mean())
            record(g, f"panel {panel} {cv}: digitized points on the curve (<= 3 px)", fa >= 0.98, f"{100*fa:.1f}% of {len(s)} points")
            mks = curve_mask(im, cv, pale=False) & True
            keep = remove_legend_lines(mks)
            pts_ = list(zip(x, y)); pts_.append(pts_[0])
            poly = Image.new("L", (W, H), 0); ImageDraw.Draw(poly).line(pts_, fill=255, width=1)
            yy, xx = np.nonzero(mks)
            ok = (np.hypot(xx - cx, yy - cy) <= rad + 5) & keep[yy, xx]
            dd = dist_to(np.array(poly) > 0)[yy[ok], xx[ok]]
            fb = float((dd <= 20).mean())
            record(g, f"panel {panel} {cv}: no curve piece missed (<= 20 px)", fb >= 0.99,
                   f"{100*fb:.2f}% within 20 px, {100*(dd <= 10).mean():.1f}% within 10 px, farthest {dd.max():.0f} px of {ok.sum()}")
            for xp, yp in zip(x, y):
                dr[key].ellipse([xp - 3, yp - 3, xp + 3, yp + 3], fill=(0, 0, 0))
    draws["fig9"].save(out / "overlay_fig9.png")
    draws["cont"].save(out / "overlay_fig9_cont.png")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="Overlay test of digitized figures on the original PNGs")
    ap.add_argument("--images", required=True, help="folder with Figure_4.png, Figure_5.png, Figure_9.png, Figure_9_Cont.png, Figure_11.png")
    ap.add_argument("--data-dir", default="data", help="folder with the digitized CSV files (searched recursively)")
    ap.add_argument("--out", default="docs/verification", help="where overlay images and the report are written")
    a = ap.parse_args()

    # ---- find all inputs first and report EVERYTHING that is missing
    imgs, seen = find_images(a.images)
    csvs = {k: find_csv(a.data_dir, v) for k, v in CSV_NAMES.items()}
    problems = []
    if not Path(a.images).is_dir():
        problems.append(f"The --images folder does not exist: {Path(a.images).resolve()}")
    for key, p in imgs.items():
        if p is None:
            problems.append(f"Image not found: {IMAGE_STEMS[key][0]}")
    for key, p in csvs.items():
        if p is None:
            problems.append(f"CSV not found: {CSV_NAMES[key][0]}  (or old name {CSV_NAMES[key][1]})")
    if problems:
        print("\n".join(["Cannot start:"] + ["  - " + p for p in problems]))
        print(f"\nImages folder searched : {Path(a.images).resolve()}")
        print("Image files found there: " + (", ".join(p.name for p in seen) if seen else "none"))
        print(f"CSV folder searched    : {Path(a.data_dir).resolve()}")
        print(f"Current folder         : {Path.cwd()}")
        print("\nHints: check the spelling of the folder path; do not end it with a backslash when it is in quotes;"
              "\n       copy the 5 PNG files into that folder; run 'dir <folder>' to see what is really there.")
        sys.exit(2)

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    d4 = pd.read_csv(csvs["fig4"])
    check_xy_figure("Fig 4", imgs["fig4"],
                    [(it, col, d4[d4.Iter == it].Freq_GHz.values, d4[d4.Iter == it].S11_dB_paper_Fig4.values) for it, col in FIG4_COLOURS.items()],
                    [2, 4, 6, 8, 10], [0, -5, -10, -15, -20, -25, -30], out, "fig4",
                    frame_ref=FIG4_FRAME_REF, legend_rect=FIG4_LEGEND, zoom_from=6)
    d5 = pd.read_csv(csvs["fig5"])
    check_xy_figure("Fig 5 (simulated S11, red)", imgs["fig5"], [("simulated", RED, d5.iloc[:, 0].values, d5.iloc[:, 1].values)],
                    [2, 4, 6, 8, 10], [0, -5, -10, -15, -20, -25, -30], out, "fig5", auto_legend=True)
    record("Fig 5 (simulated S11, red)", "INFO measured (blue) curve is not digitized", True, "not tested")
    d11 = pd.read_csv(csvs["fig11"])
    check_xy_figure("Fig 11 (gain)", imgs["fig11"], [("gain", RED, d11.iloc[:, 0].values, d11.iloc[:, 1].values)],
                    [2, 4, 6, 8, 10], [20, 10, 0, -10, -20], out, "fig11", auto_legend=True, extremes=True)
    check_fig9({"fig9": imgs["fig9"], "cont": imgs["cont"]}, csvs["fig9"], out)

    lines, last, bad = [], None, 0
    for grp, name, ok, detail in results:
        if grp != last:
            lines.append(f"\n=== {grp} ==="); last = grp
        lines.append(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")
        bad += (not ok)
    lines.append(f"\n{len(results) - bad} passed, {bad} failed, {len(results)} checks")
    text = "\n".join(lines)
    print(text)
    (out / "overlay_report.txt").write_text(text, encoding="utf-8")
    print(f"\nImages and report written to {out.resolve()}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
