#!/usr/bin/env python3
"""07 - Hero / social-preview figure (1280 x 640 px): resonances line up, gain does not.

Left : S11 of the paper's simulated final design (digitized) vs ours, 1-10 GHz, paper's 7 resonances marked.
Right: peak gain at those 7 frequencies, paper text vs ours (max of 4 phi cuts, a lower bound; true peak up to 2.5 dB higher).
Inputs : sim_s11_vswr_final_design.csv, paper_s11_final_simulated_digitized.csv, sim_gain_cuts_*.csv
Outputs: figures/07_hero_figure.png (exactly 1280 x 640 px, no tight cropping)
"""
import numpy as np
import pandas as pd

import _common as C
import matplotlib.pyplot as plt

PAIRED = {2.11: 2.11, 3.06: 3.04, 5.78: 5.78, 6.94: 6.92, 8.48: 8.45, 9.23: 9.18, 9.56: 9.56}


def main():
    args = C.make_parser(__doc__).parse_args()
    C.prepare(args)
    sim = C.load(args.data_dir, "sim_s11")
    pap = C.load(args.data_dir, "paper_s11")
    ca = C.load(args.data_dir, "cuts_adapt")
    cd = C.load(args.data_dir, "cuts_disc")
    cuts = pd.concat([ca, cd], ignore_index=True)
    cuts.columns = ["f", "phi", "theta", "g"]
    fp, sp = C.clean_curve(pap["Freq_GHz"], pap["S11_dB_paper_simulated"])

    ours = []
    for f0 in C.PAPER["f"]:
        s = cuts[np.isclose(cuts["f"], f0)]
        if s.empty:
            s = cuts[np.isclose(cuts["f"], PAIRED[f0])]
        ours.append(float(s["g"].max()))

    plt.rcParams.update({"font.size": 13})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.8, 6.4), dpi=100, gridspec_kw={"width_ratios": [1.15, 1]})
    a1.plot(fp, sp, color="C1", lw=2.2, label="Paper (simulated)")
    a1.plot(sim["Freq [GHz]"], sim["dB(S(1,1)) []"], color="C0", lw=2.2, label="Our HFSS model")
    for f0 in C.PAPER["f"]:
        a1.axvline(f0, color="0.75", lw=1, ls=":")
    a1.set_xlim(1, 10); a1.set_ylim(-42, 2)
    a1.set_xlabel("Frequency (GHz)"); a1.set_ylabel("S11 (dB)")
    a1.set_title("Resonances line up (7 of 7 within 1 %)", fontsize=15); a1.legend(loc="lower left", fontsize=12); a1.grid(alpha=0.25)
    x = np.arange(7)
    a2.bar(x - 0.2, C.PAPER["gain"], 0.4, color="C1", label="Paper (text)")
    a2.bar(x + 0.2, ours, 0.4, color="C0", label="Ours (max of 4 cuts)")
    a2.axhline(0, color="0.4", lw=0.8)
    a2.set_xticks(x); a2.set_xticklabels([f"{f:g}" for f in C.PAPER["f"]], fontsize=11)
    a2.set_xlabel("Resonance (GHz)"); a2.set_ylabel("Peak gain (dBi)")
    a2.set_title("Gain does not (6-23 dB lower)", fontsize=15); a2.legend(loc="upper left", fontsize=12); a2.grid(alpha=0.25, axis="y")
    fig.suptitle("Koch-Sierpinski antenna replication: resonances reproduced,\ngain not reproduced under the assumed setup", fontsize=17, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.98, top=0.80, bottom=0.12, wspace=0.22)
    C.save_fig(fig, args.figures, "07_hero_figure.png", dpi=100)
    from PIL import Image
    im = Image.open(f"{args.figures}/07_hero_figure.png")
    print(f"size {im.size[0]} x {im.size[1]} px (target 1280 x 640)")


if __name__ == "__main__":
    main()
