#!/usr/bin/env python3
"""04 - Fig 8: VSWR of the final design, ours vs the values printed in the paper's text.

Inputs : sim_s11_vswr_final_design.csv, paper_s11_final_simulated_digitized.csv (old names also accepted)
Outputs: figures/04_fig8_vswr.png, results/04_vswr_at_paper_frequencies.csv

Method
  - VSWR = (1 + |G|) / (1 - |G|), |G| = 10^(S11_dB/20); checked against the VSWR(1) column exported by HFSS.
  - Compared at the paper's seven resonance frequencies (interpolated) and at our matched dips.
  - 'Agrees' = within 0.1 in VSWR (tolerance fixed here; the paper prints two decimals).
  - The plotted 'paper-implied' curve is the paper's digitized S11 converted to VSWR. It is NOT a digitization of the
    paper's Fig 8 and assumes Fig 8 is consistent with Figs 4/5.
"""
import numpy as np
import pandas as pd

import _common as C
import matplotlib.pyplot as plt

TOL = 0.1


def main():
    args = C.make_parser(__doc__).parse_args()
    C.prepare(args)
    sim = C.load(args.data_dir, "sim_s11")
    pap = C.load(args.data_dir, "paper_s11")
    f = sim["Freq [GHz]"].to_numpy()
    s = sim["dB(S(1,1)) []"].to_numpy()
    v_hfss = sim["VSWR(1) []"].to_numpy()
    v_calc = C.vswr_from_s11(s)
    print(f"Max |VSWR from S11 - HFSS VSWR column| = {np.max(np.abs(v_calc - v_hfss)):.2e} (relative {np.max(np.abs(v_calc / v_hfss - 1)):.2e})")
    fp, sp = C.clean_curve(pap["Freq_GHz"], pap["S11_dB_paper_simulated"])

    dips = C.find_dips(f, s, 1.0, 1.0, 12.0)
    rows = []
    for k, (f0, vp) in enumerate(zip(C.PAPER["f"], C.PAPER["vswr"]), start=1):
        vo = float(np.interp(f0, f, v_calc))
        d = C.nearest_dip(dips, f0, 0.03)
        vd = float(C.vswr_from_s11(d[1])) if d else np.nan
        rows.append({"band": k, "paper_f_GHz": f0, "paper_VSWR_text": vp, "ours_VSWR_at_paper_f": round(vo, 2),
                     "diff": round(vo - vp, 2), "agrees_within_0.1": abs(vo - vp) <= TOL,
                     "ours_dip_f_GHz": d[0] if d else np.nan, "ours_VSWR_at_own_dip": round(vd, 2) if d else np.nan,
                     "paper_claim_le_1.8_met_at_paper_f": vo <= 1.8})
    tab = pd.DataFrame(rows)
    C.show(tab)
    C.save_table(tab, args.results, "04_vswr_at_paper_frequencies.csv")
    print(f"\nAgreement within {TOL}: bands {tab.loc[tab['agrees_within_0.1'], 'band'].tolist()} of 7.")
    print(f"Bands where our VSWR exceeds the paper's stated maximum of 1.8 at the paper's frequency: {tab.loc[~tab['paper_claim_le_1.8_met_at_paper_f'], 'band'].tolist()}")

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(f, v_calc, color="C0", lw=1.6, label="Our HFSS model")
    ax.plot(fp, C.vswr_from_s11(sp), color="C1", lw=1.3, ls="--", label="Paper-implied (digitized S11 converted; not Fig 8 itself)")
    ax.scatter(C.PAPER["f"], C.PAPER["vswr"], marker="D", color="C1", zorder=5, label="Paper, VSWR printed in text")
    ax.axhline(2, color="0.5", lw=0.8); ax.axhline(1.8, color="C1", lw=0.8, ls=":")
    ax.set_yscale("log"); ax.set_ylim(1, 20); ax.set_xlim(1, 10)
    ax.set_yticks([1, 1.5, 2, 3, 5, 10, 20]); ax.set_yticklabels(["1", "1.5", "2", "3", "5", "10", "20"])
    ax.set_xlabel("Frequency (GHz)"); ax.set_ylabel("VSWR (50 ohm)")
    ax.set_title(f"VSWR: {int(tab['agrees_within_0.1'].sum())} of the 7 values printed in the paper agree with our model within {TOL}")
    ax.legend(loc="upper right", fontsize=9); ax.grid(alpha=0.25, which="both")
    C.save_fig(fig, args.figures, "04_fig8_vswr.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
