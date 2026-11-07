#!/usr/bin/env python3
"""02 - Fig 4: S11 of design iterations 0-3, our HFSS model vs the paper's digitized Fig 4.

Question: does the geometry sequence of the paper's Fig 2 (Iter0 single triangle ... Iter3 final design) give the
paper's Fig 4 curves? (The paper's text describes the iterations differently from Fig 2; see geometry/make_geometry.py.)
Inputs : sim_s11_iter0-3_and_koch_only.csv, paper_fig4_s11_iter0-3_digitized.csv (old names also accepted)
Outputs: figures/02_fig4_iterations.png, results/02_fig4_dips.csv, results/02_fig4_summary.csv

Method
  - Window 1-10 GHz (our model starts at 1 GHz; the paper's plot axis ends at 10 GHz). Dip counts apply to this window only.
  - Dips: local minima with >= 1 dB prominence and S11 <= -10 dB, on a 0.01 GHz grid (paper curves resampled to that grid).
  - RMSE / correlation: 1.5-10 GHz, both curves clipped at -30 dB, evaluated only where both curves exist
    (the paper's Iter0 curve starts at 2.07 GHz; its dotted line is hidden under later curves below that).
  - RMSE_flat_extension_dB repeats the RMSE with the paper curve held constant beyond its first/last point (np.interp
    default over the full 1.5-10 GHz grid). This is the method behind the RMSE values quoted in earlier notes.
  - Digitization uncertainty of the paper curves is about +-1 dB, larger at narrow notches.
"""
import numpy as np
import pandas as pd

import _common as C
import matplotlib.pyplot as plt

ITERS = ["Iter0", "Iter1", "Iter2", "Iter3"]
OURS = {"Iter0": "Iter0", "Iter1": "Iter1", "Iter2": "Iter2", "Iter3": "Iter3_hybrid_baseline"}
THR = -10.0


def main():
    args = C.make_parser(__doc__).parse_args()
    C.prepare(args)
    sim = C.load(args.data_dir, "sim_iters")
    pap = C.load(args.data_dir, "paper_fig4")
    print("  designs in our file:", sorted(sim["Design"].unique()))
    print("  curves in paper file:", sorted(pap["Iter"].unique()))

    drows, srows = [], []
    curves = {}
    for it in ITERS:
        so = sim[sim["Design"] == OURS[it]].sort_values("Freq_GHz")
        sp = pap[pap["Iter"] == it]
        fo, yo = so["Freq_GHz"].to_numpy(), so["S11_dB"].to_numpy()
        fg, yg = C.regrid(sp["Freq_GHz"], sp["S11_dB_paper_Fig4"], 0.01)
        curves[it] = (fo, yo, fg, yg)
        do = [d for d in C.find_dips(fo, yo, 1.0, 1.0, 10.0) if d[1] <= THR]
        dp = [d for d in C.find_dips(fg, yg, 1.0, 1.0, 10.0) if d[1] <= THR]
        for who, dl in (("paper", dp), ("ours", do)):
            for fd, sd in dl:
                drows.append({"iteration": it, "source": who, "dip_f_GHz": round(fd, 2), "dip_dB": round(sd, 1)})
        rm, co, n = C.score(fo, yo, sp["Freq_GHz"], sp["S11_dB_paper_Fig4"])
        rm_flat, _, n_flat = C.score(fo, yo, sp["Freq_GHz"], sp["S11_dB_paper_Fig4"], overlap_only=False)
        srows.append({"iteration": it, "paper_curve_starts_GHz": round(float(sp["Freq_GHz"].min()), 2),
                      "RMSE_dB": round(rm, 2), "corr": round(co, 2), "n_grid_points": n,
                      "RMSE_flat_extension_dB": round(rm_flat, 2),
                      "paper_dips_le_-10": len(dp), "ours_dips_le_-10": len(do),
                      "paper_dips_le_-15": sum(d[1] <= -15 for d in dp), "ours_dips_le_-15": sum(d[1] <= -15 for d in do)})
    dt = pd.DataFrame(drows)
    st = pd.DataFrame(srows)
    for it in ITERS:
        print(f"\n{it}: dips <= {THR:.0f} dB in 1-10 GHz (GHz / dB)")
        for who in ("paper", "ours"):
            sub = dt[(dt.iteration == it) & (dt.source == who)]
            print(f"  {who:5s}: " + ", ".join(f"{a:.2f}/{b:.1f}" for a, b in zip(sub.dip_f_GHz, sub.dip_dB)))
    print("\nSummary (counts of dips <= -10 dB; the paper's text claims 2, 3, 5, 7 for iterations 0-3)")
    C.show(st)
    C.save_table(dt, args.results, "02_fig4_dips.csv")
    C.save_table(st, args.results, "02_fig4_summary.csv")

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
    for ax, it in zip(axes.ravel(), ITERS):
        fo, yo, fg, yg = curves[it]
        ax.plot(fo, yo, color="C0", lw=1.5, label="Ours (HFSS, assumed setup)")
        ax.plot(fg, yg, color="C1", lw=1.4, ls="--", label="Paper Fig 4 (digitized)")
        ax.axhline(THR, color="0.5", lw=0.8)
        r = st[st.iteration == it].iloc[0]
        ax.set_title(f"{it}: RMSE {r.RMSE_dB:.1f} dB, dips <= -10 dB: paper {r['paper_dips_le_-10']}, ours {r['ours_dips_le_-10']}", fontsize=10)
        ax.set_xlim(1, 10); ax.set_ylim(-42, 2); ax.grid(alpha=0.25)
    for ax in axes[1]:
        ax.set_xlabel("Frequency (GHz)")
    for ax in axes[:, 0]:
        ax.set_ylabel("S11 (dB)")
    axes[0, 0].legend(loc="lower left", fontsize=9)
    fig.suptitle("Design iterations: Iter0-2 follow the paper's Fig 4 in dip frequency, the final geometry (Iter3) differs in depth")
    fig.tight_layout()
    C.save_fig(fig, args.figures, "02_fig4_iterations.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
