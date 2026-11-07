#!/usr/bin/env python3
"""05 - Gain, directivity and radiation efficiency: our HFSS far field vs the paper's text, Fig 9 and Fig 11.

Question: can a peak gain of 3.9-19.4 dBi at the seven resonances (paper text, Fig 10) be reproduced?
Inputs : sim_farfield_summary_1-10GHz.csv, sim_gain_cuts_adaptive_freqs.csv, sim_gain_cuts_discrete_freqs.csv,
         paper_fig11_gain_vs_freq_digitized.csv, fig9_peak_levels_paper_vs_sim.csv (old names also accepted)
Outputs: figures/05_gain_and_efficiency.png, results/05_gain_at_paper_frequencies.csv, results/05_farfield_summary_stats.csv

What the data can and cannot show
  - The gain-cut files hold only four phi planes (0/90/180/270) at 11 frequencies, so 'cut max' is a LOWER BOUND on the
    peak gain (the true peak was 0.4-2.5 dB higher at 9.18-9.56 GHz).
  - The sweep file (0.1 GHz step) gives peak directivity and efficiency, but not at the paper's exact frequencies:
    the table uses the nearest grid point and says which one. Narrow resonances can change efficiency between grid points.
  - Aperture heuristic 4*pi*A/lambda^2 with A = 40 x 60 mm is NOT a strict bound (a resonant patch can exceed it);
    it is only a plausibility yardstick.
  - Results depend on the assumed setup (full ground plane, Perfect-E, 50 ohm wave port, 37.5 mm box).
"""
import numpy as np
import pandas as pd

import _common as C
import matplotlib.pyplot as plt

PAIRED = {2.11: 2.11, 3.06: 3.04, 5.78: 5.78, 6.94: 6.92, 8.48: 8.45, 9.23: 9.18, 9.56: 9.56}


def cut_max(cuts, f):
    s = cuts[np.isclose(cuts["f"], f)]
    if s.empty:
        return np.nan, np.nan, np.nan
    r = s.loc[s["g"].idxmax()]
    return float(r["g"]), float(r["phi"]), float(r["theta"])


def runs(freqs):
    """Contiguous runs of a sorted 0.1 GHz grid, as 'a-b' strings."""
    out, start, prev = [], None, None
    for x in freqs:
        if start is None:
            start = prev = x
        elif abs(x - prev - 0.1) < 1e-6:
            prev = x
        else:
            out.append(f"{start:.1f}-{prev:.1f}"); start = prev = x
    if start is not None:
        out.append(f"{start:.1f}-{prev:.1f}")
    return out


def main():
    args = C.make_parser(__doc__).parse_args()
    C.prepare(args)
    far = C.load(args.data_dir, "sim_far")
    ca = C.load(args.data_dir, "cuts_adapt")
    cd = C.load(args.data_dir, "cuts_disc")
    p11 = C.load(args.data_dir, "paper_fig11")
    lev = C.load(args.data_dir, "fig9_levels")
    cuts = pd.concat([ca, cd], ignore_index=True)
    cuts.columns = ["f", "phi", "theta", "g"]
    print("  frequencies in the cut files:", [float(x) for x in sorted(cuts["f"].round(2).unique())])

    f11, g11 = C.clean_curve(p11["Freq_GHz"], p11["Gain_dBi_paper_Fig11"])
    ff = far["f"].to_numpy()
    A = 0.040 * 0.060
    rows = []
    for k, (f0, gt) in enumerate(zip(C.PAPER["f"], C.PAPER["gain"]), start=1):
        fp = PAIRED[f0]
        g0_, ph0, th0 = cut_max(cuts, f0)
        g1_, ph1, th1 = cut_max(cuts, fp)
        i = int(np.argmin(np.abs(ff - f0)))
        r = far.iloc[i]
        lam = 299.792458 / f0 / 1000.0                                  # metres
        rows.append({"band": k, "paper_f_GHz": f0, "paper_text_gain_dBi": gt,
                     "paper_fig11_dBi": round(float(np.interp(f0, f11, g11)), 1),
                     "paper_fig9_cut_max_dBi": float(lev.loc[lev["panel"] == C.PANELS[k - 1], "paper_cutmax"].iloc[0]),
                     "ours_cut_max_at_paper_f_dBi": round(g0_, 2), "ours_peak_phi_theta": f"{ph0:.0f}/{th0:.0f}" if not np.isnan(ph0) else "",
                     "paired_f_GHz": fp, "ours_cut_max_at_paired_f_dBi": round(g1_, 2),
                     "grid_f_GHz": round(float(r["f"]), 1), "grid_peak_gain_dBi": round(float(r["G_dBi"]), 2),
                     "grid_peak_directivity_dBi": round(float(r["D_dBi"]), 2), "grid_rad_efficiency_pct": round(100 * float(r["Radiation Efficiency"]), 1),
                     "aperture_heuristic_dBi": round(10 * np.log10(4 * np.pi * A / lam ** 2), 1)})
    tab = pd.DataFrame(rows)
    tab["text_minus_ours_cut_max_dB"] = (tab["paper_text_gain_dBi"] - tab["ours_cut_max_at_paper_f_dBi"]).round(1)
    print("\nGain at the paper's seven resonances (dBi)")
    C.show(tab)
    C.save_table(tab, args.results, "05_gain_at_paper_frequencies.csv")

    # ---- 1-10 GHz sweep statistics --------------------------------------------------------------
    G, D, E = far["G_dBi"].to_numpy(), far["D_dBi"].to_numpy(), far["Radiation Efficiency"].to_numpy()
    iG, iD = int(np.argmax(G)), int(np.argmax(D))
    neg = ff[D < 0]
    chk = np.max(np.abs(G - (D + 10 * np.log10(E))))
    m = np.ones(ff.size, bool)                       # all 91 grid points; np.interp holds the Fig 11 end value at 10.0 GHz
    gi = np.interp(ff[m], f11, g11)
    stats = {
        "max_peak_gain_dBi": (round(G[iG], 2), f"at {ff[iG]:.1f} GHz"),
        "max_peak_directivity_dBi": (round(D[iD], 2), f"at {ff[iD]:.1f} GHz"),
        "max_broadside_gain_g0_dBi": (round(far['g0'].max(), 2), f"at {ff[int(far['g0'].idxmax())]:.1f} GHz (g0 inferred = broadside)"),
        "radiation_efficiency_min_pct": (round(100 * E.min(), 1), f"at {ff[int(np.argmin(E))]:.1f} GHz"),
        "radiation_efficiency_max_pct": (round(100 * E.max(), 1), f"at {ff[int(np.argmax(E))]:.1f} GHz"),
        "radiation_efficiency_mean_pct": (round(100 * E.mean(), 1), "mean of 91 grid points"),
        "rows_with_peak_directivity_below_0dBi": (int((D < 0).sum()), "runs (GHz): " + ", ".join(runs(neg)) + " - physically impossible, UNRESOLVED"),
        "max_|G - (D + 10log10 eff)|_dB": (float(f"{chk:.1e}"), "internal consistency"),
        "corr_peakG_vs_paper_Fig11": (round(float(np.corrcoef(G[m], gi)[0, 1]), 2), f"{m.sum()} points; Fig 11 ends at {f11.max():.2f} GHz, its last value is held for the 10.0 GHz point"),
        "corr_broadsideG_vs_paper_Fig11": (round(float(np.corrcoef(far['g0'].to_numpy()[m], gi)[0, 1]), 2), "same points"),
        "mean_paperFig11_minus_ours_peakG_dB": (round(float(np.mean(gi - G[m])), 1), "same points"),
        "RMSE_paperFig11_vs_ours_peakG_dB": (round(float(np.sqrt(np.mean((gi - G[m]) ** 2))), 1), "same points"),
    }
    st = pd.DataFrame([{"quantity": k, "value": str(v[0]), "note": v[1]} for k, v in stats.items()])
    print("\n1-10 GHz sweep statistics (our model)")
    C.show(st)
    C.save_table(st, args.results, "05_farfield_summary_stats.csv")
    print(f"\nAt the 7 resonances the paper's text gain exceeds our peak gain by {tab['text_minus_ours_cut_max_dB'].min():.1f} to "
          f"{tab['text_minus_ours_cut_max_dB'].max():.1f} dB (cut max). Our peak directivity never exceeds {D.max():.1f} dBi in 1-10 GHz.")

    # ---- figure ----------------------------------------------------------------------------------
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [1.6, 1]})
    a1.plot(f11, g11, color="C1", lw=1.3, label="Paper Fig 11 (digitized, +-1 dB)")
    a1.plot(ff, G, color="C0", lw=1.8, label="Ours: peak gain")
    a1.plot(ff, far["g0"], color="C0", lw=1.0, ls=":", label="Ours: broadside gain (g0)")
    a1.plot(ff, D, color="C2", lw=1.2, ls="--", label="Ours: peak directivity")
    a1.scatter(C.PAPER["f"], C.PAPER["gain"], marker="D", color="C1", s=45, zorder=5, label="Paper text / Fig 10 (7 resonances)")
    a1.scatter(tab["paper_f_GHz"], tab["ours_cut_max_at_paper_f_dBi"].fillna(tab["ours_cut_max_at_paired_f_dBi"]), marker="o",
               facecolors="none", edgecolors="C0", s=55, zorder=5, label="Ours: max of 4 phi cuts at those frequencies")
    a1.axhline(0, color="0.5", lw=0.8)
    a1.set_xlim(0.5, 10); a1.set_ylim(-20, 22); a1.set_xlabel("Frequency (GHz)"); a1.set_ylabel("dBi")
    a1.set_title("Gain vs frequency"); a1.legend(fontsize=8, loc="lower right"); a1.grid(alpha=0.25)
    a2.plot(ff, 100 * E, color="C3", lw=1.6)
    a2.scatter(C.PAPER["f"], [np.interp(x, ff, 100 * E) for x in C.PAPER["f"]], color="C3", s=30, zorder=5)
    a2.set_xlim(1, 10); a2.set_ylim(0, 50); a2.set_xlabel("Frequency (GHz)"); a2.set_ylabel("Radiation efficiency (%)")
    a2.set_title("Our radiation efficiency (FR4, tan d = 0.0197)"); a2.grid(alpha=0.25)
    fig.suptitle("Reported peak gains of 3.9-19.4 dBi are not reproduced under our assumed setup (full ground, Perfect-E, 50 ohm port)")
    fig.tight_layout()
    C.save_fig(fig, args.figures, "05_gain_and_efficiency.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
