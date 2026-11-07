#!/usr/bin/env python3
"""01 - S11 of the final design: our HFSS result vs the paper's simulated S11 (Figs 4/5, red curve) and text.

Question: do the seven reported resonances appear, how deep are they, and how wide?
Inputs : sim_s11_vswr_final_design.csv, paper_s11_final_simulated_digitized.csv (old names also accepted)
Outputs: figures/01_s11_final_vs_paper.png, results/01_s11_resonances.csv

Method
  - Our dips: local minima of S11 with >= 1 dB prominence, 1-12 GHz.
  - Each paper resonance is matched to the nearest dip of ours within +-3 %.
  - Pre-registered criterion for 'frequency reproduced': |df| / f <= 1.0 %.
  - Bandwidth = width of the contiguous S11 <= -10 dB band that contains our dip (0 if the dip is shallower).
  - RMSE/correlation vs the paper's digitized S11: 1.5-10 GHz, both curves clipped at -30 dB.
The paper's values (RL, BW) are the numbers printed in its text; the digitized curve has about +-1 dB uncertainty.
"""
import numpy as np
import pandas as pd

import _common as C
import matplotlib.pyplot as plt

TOL_F_PCT = 1.0


def main():
    args = C.make_parser(__doc__).parse_args()
    C.prepare(args)
    sim = C.load(args.data_dir, "sim_s11")
    pap = C.load(args.data_dir, "paper_s11")
    f = sim["Freq [GHz]"].to_numpy()
    s = sim["dB(S(1,1)) []"].to_numpy()
    fp, sp = C.clean_curve(pap["Freq_GHz"], pap["S11_dB_paper_simulated"])

    dips = C.find_dips(f, s, 1.0, 1.0, 12.0)
    rows = []
    for k, (f0, rl, bw) in enumerate(zip(C.PAPER["f"], C.PAPER["rl"], C.PAPER["bw"]), start=1):
        d = C.nearest_dip(dips, f0, 0.03)
        row = {"band": k, "paper_f_GHz": f0, "paper_RL_text_dB": rl, "paper_BW_text_MHz": bw,
               "paper_digitized_S11_at_f_dB": round(float(np.interp(f0, fp, sp)), 1),
               "ours_S11_at_paper_f_dB": round(float(np.interp(f0, f, s)), 1)}
        if d is None:
            row.update({"ours_dip_f_GHz": np.nan, "df_MHz": np.nan, "df_pct": np.nan, "ours_dip_dB": np.nan,
                        "ours_BW_MHz": np.nan, "band_lo": np.nan, "band_hi": np.nan})
        else:
            b = C.band_around(f, s, d[0], -10.0)
            row.update({"ours_dip_f_GHz": d[0], "df_MHz": round((d[0] - f0) * 1000), "df_pct": round(100 * (d[0] - f0) / f0, 2),
                        "ours_dip_dB": round(d[1], 1),
                        "ours_BW_MHz": 0 if b is None else round((b[1] - b[0]) * 1000),
                        "band_lo": np.nan if b is None else round(b[0], 3), "band_hi": np.nan if b is None else round(b[1], 3)})
        row["depth_gap_dB"] = round(row["ours_dip_dB"] - rl, 1) if d else np.nan   # positive = ours shallower
        rows.append(row)
    tab = pd.DataFrame(rows)
    print("\nResonances: paper text vs our HFSS model (positive depth_gap = ours shallower than the paper's text value)")
    C.show(tab)
    C.save_table(tab, args.results, "01_s11_resonances.csv")

    n_ok = int((tab["df_pct"].abs() <= TOL_F_PCT).sum())
    print(f"\nFrequency criterion |df|/f <= {TOL_F_PCT} %: {n_ok} of 7 bands (largest {tab['df_pct'].abs().max():.2f} %)")
    shallow = tab.loc[tab["ours_dip_dB"] > -10, "band"].tolist()
    print(f"Bands whose dip is shallower than -10 dB in our model: {shallow}")
    pairs = tab[["band_lo", "band_hi"]].round(3).apply(tuple, axis=1)
    merged = [(int(tab.band[i]), int(tab.band[j])) for i in range(7) for j in range(i + 1, 7)
              if pairs[i] == pairs[j] and not np.isnan(tab.band_lo[i])]
    print(f"Bands that share one contiguous -10 dB band in our model: {merged}")
    rm, co, n = C.score(f, s, fp, sp)
    print(f"RMSE vs paper's digitized S11 (1.5-10 GHz, clipped -30 dB, {n} points): {rm:.2f} dB, correlation {co:.2f}")

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(f, s, color="C0", lw=1.8, label="Our HFSS model (assumed setup)")
    ax.plot(fp, sp, color="C1", lw=1.6, ls="--", label="Paper, simulated S11 (digitized)")
    for f0 in C.PAPER["f"]:
        ax.axvline(f0, color="0.7", lw=0.8, ls=":")
    ax.scatter(C.PAPER["f"], C.PAPER["rl"], marker="D", color="C1", zorder=5, label="Paper, RL printed in text")
    dd = tab.dropna(subset=["ours_dip_f_GHz"])
    ax.scatter(dd["ours_dip_f_GHz"], dd["ours_dip_dB"], marker="o", facecolors="none", edgecolors="C0", s=60, zorder=5,
               label="Our dips matched to the paper's resonances")
    ax.axhline(-10, color="0.4", lw=0.8)
    ax.set_xlim(1, 10); ax.set_ylim(-42, 2)
    ax.set_xlabel("Frequency (GHz)"); ax.set_ylabel("S11 (dB)")
    ax.set_title("Final design: resonance frequencies agree, depths do not (dotted lines = paper's 7 resonances)")
    ax.legend(loc="lower left", fontsize=9); ax.grid(alpha=0.25)
    C.save_fig(fig, args.figures, "01_s11_final_vs_paper.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
