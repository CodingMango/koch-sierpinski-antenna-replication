#!/usr/bin/env python3
"""08 - Setup sensitivity: do feed width, radiation-box size or port type close the S11 depth gap?

Cases (all final design, 1-12 GHz, 0.01 GHz grid):
  baseline   wave port, Fw 1.8 (static DXF feed), box padding 37.5 mm (+X side 0)   [sim_s11_vswr_final_design.csv]
  Fw 1.5 / 1.73 / 1.8   parametric feed width, otherwise as baseline                [sim_s11_feed_width_sweep.csv]
  pad 20     radiation-box padding 20 mm instead of 37.5 mm                          [sim_s11_radiation_box_pad20mm.csv]
  copper     finite-conductivity copper instead of Perfect E (conductor details: see hfss/hfss_setup_notes.md) [sim_s11_copper_loss.csv]
  port 7x4   wave port 7 x 4 mm instead of 10 x 6 mm (Wp x Hp)                       [sim_s11_port_7x4mm.csv]
  lumped     lumped port (Fw x h, integration line ground to feed), padding added on the +X side [sim_s11_lumped_port.csv]
CONFOUNDING: the lumped case differs from the baseline in two ways (port type and +X padding; the lumped port could
not be solved with the +X side unpadded). Their effects cannot be separated from these data.
Each case changes one setup item from the baseline (the lumped case changes two).

Inputs : files above (old names also accepted)
Outputs: figures/08_sensitivity_sweeps.png, results/08_sensitivity_dips.csv, results/08_sensitivity_summary.csv
         The summary also gives, per case, the largest dip-frequency difference to the paper's 7 resonances (the 1 % agreement
         of the baseline is NOT independent of port size: see the 'port 7x4' row).
Method : for each case and each of the paper's 7 resonances, the nearest dip (>= 1 dB prominence) within +-3 % and the
         S11 at the paper's frequency; RMSE vs the paper's digitized S11 (1.5-10 GHz, clipped -30 dB).
"""
import numpy as np
import pandas as pd

import _common as C
import matplotlib.pyplot as plt


def main():
    args = C.make_parser(__doc__).parse_args()
    C.prepare(args)
    base = C.load(args.data_dir, "sim_s11")
    fw = C.load(args.data_dir, "sim_fw")
    pad = C.load(args.data_dir, "sim_pad")
    cop = C.load(args.data_dir, "sim_copper")
    prt = C.load(args.data_dir, "sim_port")
    lum = C.load(args.data_dir, "sim_lumped")
    pap = C.load(args.data_dir, "paper_s11")
    fp, sp = C.clean_curve(pap["Freq_GHz"], pap["S11_dB_paper_simulated"])

    cases = {"baseline (wave port)": (base["Freq [GHz]"].to_numpy(), base["dB(S(1,1)) []"].to_numpy())}
    for v, g in fw.groupby("Fw [mm]"):
        cases[f"Fw {v:g} mm"] = (g["Freq [GHz]"].to_numpy(), g["dB(S(1,1)) []"].to_numpy())
    cases["radiation box 20 mm"] = (pad["Freq [GHz]"].to_numpy(), pad["dB(S(1,1)) []"].to_numpy())
    cases["copper (finite conductivity)"] = (cop.iloc[:, 0].to_numpy(), cop.iloc[:, 1].to_numpy())
    cases["wave port 7 x 4 mm"] = (prt.iloc[:, 0].to_numpy(), prt.iloc[:, 1].to_numpy())
    cases["lumped port (+X padded)"] = (lum.iloc[:, 0].to_numpy(), lum.iloc[:, 1].to_numpy())
    for k, (f, s) in cases.items():
        print(f"  {k:26s} {len(f)} points, {f.min():.2f}-{f.max():.2f} GHz")

    bf, bs = cases["baseline (wave port)"]
    drows, srows = [], []
    for name, (f, s) in cases.items():
        dips = C.find_dips(f, s, 1.0, 1.0, 12.0)
        for k, f0 in enumerate(C.PAPER["f"], start=1):
            d = C.nearest_dip(dips, f0, 0.03)
            drows.append({"case": name, "band": k, "paper_f_GHz": f0, "dip_f_GHz": d[0] if d else np.nan,
                          "dip_dB": round(d[1], 1) if d else np.nan, "S11_at_paper_f_dB": round(float(np.interp(f0, f, s)), 1)})
        rm_p = C.score(f, s, fp, sp)[0]
        rm_b = C.score(f, s, bf, bs)[0]
        dfp = [abs(100 * (r["dip_f_GHz"] - r["paper_f_GHz"]) / r["paper_f_GHz"]) for r in drows if r["case"] == name]
        srows.append({"case": name, "RMSE_vs_paper_dB": round(rm_p, 2), "RMSE_vs_baseline_dB": round(rm_b, 2),
                      "max_dip_freq_diff_to_paper_pct": round(float(np.nanmax(dfp)), 2)})
    dt = pd.DataFrame(drows)
    st = pd.DataFrame(srows)
    piv = dt.pivot(index="case", columns="band", values="dip_dB").loc[list(cases)]
    pf = dt.pivot(index="case", columns="band", values="dip_f_GHz").loc[list(cases)]
    print("\nDip depth (dB) at the paper's 7 resonances (nearest dip within 3 %); paper text: -14 -12 -16 -10 -30 -16 -17")
    print(piv.to_string())
    print("\nDip frequency (GHz)")
    print(pf.round(2).to_string())
    print("\nLargest dip-frequency difference to the baseline, per case (MHz)")
    for name in cases:
        print(f"  {name:26s} {1000 * np.nanmax(np.abs(pf.loc[name] - pf.loc['baseline (wave port)'])):.0f}")
    print("\nRMSE (dB, 1.5-10 GHz, clipped -30 dB)")
    C.show(st)
    b1 = piv[1]
    print(f"\nBand 1 (2.1 GHz) dip depth over all cases: {b1.min():.1f} to {b1.max():.1f} dB (paper text: -14); "
          f"band 5 (8.4 GHz): {piv[5].min():.1f} to {piv[5].max():.1f} dB (paper text: -30)")
    C.save_table(dt, args.results, "08_sensitivity_dips.csv")
    C.save_table(st, args.results, "08_sensitivity_summary.csv")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 5.8), gridspec_kw={"width_ratios": [1.4, 1]})
    a1.plot(fp, sp, color="C1", lw=1.6, ls="--", label="Paper (simulated, digitized)")
    a1.plot(bf, bs, color="C0", lw=1.5, label="Ours: wave port (baseline)")
    lf, ls_ = cases["lumped port (+X padded)"]
    a1.plot(lf, ls_, color="C2", lw=1.2, label="Ours: lumped port")
    a1.set_xlim(1, 10); a1.set_ylim(-42, 2); a1.set_xlabel("Frequency (GHz)"); a1.set_ylabel("S11 (dB)")
    a1.set_title("Lumped vs wave port: same resonance frequencies, narrow-notch depths change"); a1.legend(fontsize=9, loc="lower left"); a1.grid(alpha=0.25)
    ys = np.arange(len(cases))
    a2.scatter(piv[1], ys, color="C0", label="band 1 (paper text -14 dB)", zorder=5)
    a2.scatter(piv[5], ys, color="C3", marker="s", label="band 5 (paper text -30 dB)", zorder=5)
    a2.axvline(-14, color="C0", ls=":"); a2.axvline(-30, color="C3", ls=":")
    a2.set_yticks(ys); a2.set_yticklabels(list(cases), fontsize=9); a2.invert_yaxis()
    a2.set_xlim(-40, 0); a2.set_xlabel("Dip depth (dB)"); a2.set_title("Setup variants vs the two largest depth gaps"); a2.legend(fontsize=8); a2.grid(alpha=0.25)
    fig.tight_layout()
    C.save_fig(fig, args.figures, "08_sensitivity_sweeps.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
