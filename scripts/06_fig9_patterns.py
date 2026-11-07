#!/usr/bin/env python3
"""06 - Fig 9 radiation patterns: peak levels, and a shape test with a mismatched-frequency null.

Part A (levels): the paper's Fig 9 peak levels (calibrated earlier) vs the paper's text gains vs our cut maxima.
Part B (shapes): which angle convention, if any, makes OUR simulated gain cut match the SHAPE of each paper curve?
  1. Re-computes all 352 correlations stored in fig9_convention_scan.csv from the raw inputs and compares them.
  2. Adds the null test that file lacks: for every paper curve, the best-of-16-conventions correlation with our cut
     at the SAME frequency (matched) is compared with the same quantity for our cuts at the other 6 resonance
     frequencies (mismatched). If the matched value is not systematically higher, the shape test shows nothing.

Inputs : paper_fig9_patterns_raw_pixels.csv, sim_gain_cuts_adaptive_freqs.csv, sim_gain_cuts_discrete_freqs.csv,
         fig9_peak_levels_paper_vs_sim.csv, fig9_convention_scan.csv (old names also accepted)
Outputs: figures/06_fig9_patterns.png, results/06_fig9_null_test.csv, results/06_fig9_levels.csv

Convention (reproduces the stored scan to 1e-12): for a simulated plane (XZ = phi 0/180, YZ = phi 90/270) the signed
polar angle psi = -180..180 deg is theta on the first phi and -theta on the second; the plotted angle is
(offset + sign*psi) mod 360, with offset in {0, 90, 180, 270}, sign in {+1, -1}: 16 conventions. 0 deg = right,
counter-clockwise. 'z-consistent' = offset 90 or 270 (broadside at top/bottom, as the paper's curves imply).
Correlations use the paper curve's radius in pixels: the radius-to-dB scale is linear, and Pearson/Spearman are
unchanged by a linear rescaling, so no calibration is needed for shapes.
Limits: only 4 phi planes were exported; non-principal planes cannot be tested. When levels differ by 20 dB, shape
agreement is not expected anyway. 16 conventions per curve give a strong max-selection effect, hence the null.
"""
import numpy as np
import pandas as pd
from scipy.stats import binom, spearmanr

import _common as C
import matplotlib.pyplot as plt

CONVS = [(c, s, o) for c in ("XZ", "YZ") for s in (1, -1) for o in (0, 90, 180, 270)]
PLANE = {"XZ": (0, 180), "YZ": (90, 270)}


def build_cuts(cuts):
    out = {}
    for (f, phi), g in cuts.groupby([cuts["f"].round(2), "phi"]):
        out[(float(f), int(phi))] = g.sort_values("theta").set_index("theta")["g"]
    return out


def mapped(cuts, f, plane, sg, off):
    p0, p1 = PLANE[plane]
    a, b = cuts[(round(f, 2), p0)], cuts[(round(f, 2), p1)]
    psi = np.arange(-180, 181)
    g = np.array([a[p] if p >= 0 else b[-p] for p in psi])
    return dict(zip((off + sg * psi) % 360, g))


def corr(sub, cuts, f, conv, method="pearson"):
    d = mapped(cuts, f, *conv)
    s = sub.dropna(subset=["r_px"])
    x = s["r_px"].to_numpy()
    y = np.array([d[a] for a in s["ang"].to_numpy()])
    return float(np.corrcoef(x, y)[0, 1]) if method == "pearson" else float(spearmanr(x, y)[0])


def best(sub, cuts, f, zonly=False):
    res = [(corr(sub, cuts, f, c), c) for c in CONVS if not zonly or c[2] in (90, 270)]
    return max(res, key=lambda t: t[0])


def main():
    args = C.make_parser(__doc__).parse_args()
    C.prepare(args)
    px = C.load(args.data_dir, "paper_fig9")
    ca = C.load(args.data_dir, "cuts_adapt")
    cd = C.load(args.data_dir, "cuts_disc")
    lev = C.load(args.data_dir, "fig9_levels")
    scan = C.load(args.data_dir, "fig9_scan")
    cuts_df = pd.concat([ca, cd], ignore_index=True)
    cuts_df.columns = ["f", "phi", "theta", "g"]
    cuts = build_cuts(cuts_df)
    pf = dict(zip(C.PANELS, C.PAPER["f"]))

    # ---- Part A: levels --------------------------------------------------------------------------
    lv = lev.copy()
    print("\nPart A - peak levels (dBi): paper Fig 9 vs paper text vs ours (max of 4 phi cuts, a lower bound)")
    C.show(lv[["panel", "f_GHz", "paper_Fig9_E_peak", "paper_Fig9_H_peak", "paper_text_gain", "paper_cutmax", "ours_max_4cuts",
               "diff_Fig9_vs_text", "diff_ours_vs_Fig9"]])
    print(f"Fig 9 cut maximum vs text gain: largest |difference| {lv['diff_Fig9_vs_text'].abs().max():.1f} dB (calibration uncertainty ~ +-1 dB)")
    print(f"Ours below the Fig 9 cut maximum by {-lv['diff_ours_vs_Fig9'].max():.1f} to {-lv['diff_ours_vs_Fig9'].min():.1f} dB")
    C.save_table(lv, args.results, "06_fig9_levels.csv")

    # ---- Part B1: reproduce the stored scan -------------------------------------------------------
    maxd = 0.0
    for _, r in scan.iterrows():
        sub = px[(px["panel"] == r["panel"]) & (px["curve"] == r["curve"])]
        conv = (r["cut"], int(r["s"]), int(r["off"]))
        maxd = max(maxd, abs(corr(sub, cuts, float(r["f"]), conv) - r["pearson"]),
                   abs(corr(sub, cuts, float(r["f"]), conv, "spearman") - r["spearman"]))
    print(f"\nPart B1 - recomputed all {len(scan)} stored correlations; largest difference to fig9_convention_scan.csv: {maxd:.1e}"
          f" -> {'REPRODUCED' if maxd < 1e-6 else 'MISMATCH (check conventions)'}")

    # ---- Part B2: null test ----------------------------------------------------------------------
    out = {}
    for label, zonly in (("all 16 conventions", False), ("z-consistent (offset 90/270)", True)):
        rows = []
        for p, f in pf.items():
            for cv in ("E", "H"):
                sub = px[(px["panel"] == p) & (px["curve"] == cv)]
                m, conv = best(sub, cuts, f, zonly)
                nul = [best(sub, cuts, g, zonly)[0] for q, g in pf.items() if q != p]
                rows.append({"panel": p, "curve": cv, "f_GHz": f, "matched_best_pearson": round(m, 3),
                             "matched_convention": f"{conv[0]} s={conv[1]:+d} off={conv[2]}",
                             "null_max": round(max(nul), 3), "null_median": round(float(np.median(nul)), 3),
                             "rank_among_7": 1 + sum(n > m for n in nul)})
        d = pd.DataFrame(rows)
        k = int((d["rank_among_7"] == 1).sum())
        out[label] = d
        print(f"\nPart B2 - null test, {label}: matched correlation vs the 6 mismatched-frequency cuts (14 curves)")
        C.show(d)
        print(f"Matched best is the highest of 7 in {k} of 14 curves (chance expectation 14/7 = 2.0; "
              f"P(X >= {k} | pure chance) = {binom.sf(k - 1, 14, 1 / 7):.2f}); matched below the null median in "
              f"{int((d['matched_best_pearson'] < d['null_median']).sum())} of 14; below the null maximum in "
              f"{int((d['matched_best_pearson'] < d['null_max']).sum())} of 14.")
    allc = out["all 16 conventions"].assign(set="all16")
    zc = out["z-consistent (offset 90/270)"].assign(set="z_only")
    C.save_table(pd.concat([allc, zc]), args.results, "06_fig9_null_test.csv")
    print("\nReading: no single convention reproduces the paper's pattern shapes, and the matched frequency is not "
          "systematically better than mismatched ones, so the shape test cannot support or reject a convention. "
          "With a 20 dB level gap (Part A) this is expected, not informative.")

    # ---- figure -----------------------------------------------------------------------------------
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.5))
    d = out["all 16 conventions"]
    for i, r in d.reset_index(drop=True).iterrows():
        nul_rows = [best(px[(px["panel"] == r["panel"]) & (px["curve"] == r["curve"])], cuts, g)[0] for q, g in pf.items() if q != r["panel"]]
        a1.scatter([i] * len(nul_rows), nul_rows, color="0.6", s=18, label="mismatched frequency (6 nulls)" if i == 0 else None)
        a1.scatter([i], [r["matched_best_pearson"]], color="C3", s=50, zorder=5, label="matched frequency" if i == 0 else None)
    a1.set_xticks(range(14)); a1.set_xticklabels([f"{p}-{c}" for p, c in zip(d["panel"], d["curve"])], fontsize=8)
    a1.set_xlabel("Fig 9 panel - curve"); a1.set_ylabel("best Pearson r over 16 angle conventions")
    a1.set_title("Shape test: matched frequency is not systematically better than mismatched"); a1.legend(fontsize=8); a1.grid(alpha=0.25)
    x = np.arange(7)
    a2.bar(x - 0.27, lv["paper_text_gain"], 0.27, color="C1", label="Paper text")
    a2.bar(x, lv["paper_cutmax"], 0.27, color="C1", alpha=0.5, label="Paper Fig 9 cut max")
    a2.bar(x + 0.27, lv["ours_max_4cuts"], 0.27, color="C0", label="Ours (max of 4 cuts)")
    a2.set_xticks(x); a2.set_xticklabels([f"{p}\n{f:.2f}" for p, f in zip(lv["panel"], lv["f_GHz"])])
    a2.set_xlabel("Panel / frequency (GHz)"); a2.set_ylabel("Peak level (dBi)"); a2.axhline(0, color="0.4", lw=0.8)
    a2.set_title("Peak levels: Fig 9 agrees with the text, ours is 6-23 dB lower"); a2.legend(fontsize=8); a2.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    C.save_fig(fig, args.figures, "06_fig9_patterns.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
