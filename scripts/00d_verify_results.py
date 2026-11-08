#!/usr/bin/env python3
"""00d - Verify (A) the facts stated in data/README.md and (B) the headline numbers of analysis scripts 01-07.

Run AFTER `python scripts/run_all.py` (part B reads results/*.csv written by scripts 01-07).
  python scripts\\00d_verify_results.py [--data-dir data] [--results results]

Complements 00_verify_data.py (which is not modified). It tests that files, README text and results agree with each
other; it does not test that the interpretations are right. Expected values are those stated in the README/notes,
tolerances are written next to each check. Exit code 1 if any check fails.
"""
import sys

import numpy as np
import pandas as pd

import _common as C

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail else ""))


def close(a, b, tol):
    return abs(float(a) - float(b)) <= tol


def main():
    ap = C.make_parser(__doc__)
    args = ap.parse_args()
    D = args.data_dir
    ps, p4, p11, p9 = (C.load(D, k) for k in ("paper_s11", "paper_fig4", "paper_fig11", "paper_fig9"))
    s1, si, fw, pad, cop, prt, lum, far, ca, cd, lev, scan = (C.load(D, k) for k in
        ("sim_s11", "sim_iters", "sim_fw", "sim_pad", "sim_copper", "sim_port", "sim_lumped", "sim_far", "cuts_adapt", "cuts_disc", "fig9_levels", "fig9_scan"))

    print("\n== A. Facts stated in data/README.md ==")
    for name, df, n in [("paper S11", ps, 949), ("paper Fig 4", p4, 4508), ("paper Fig 11", p11, 939), ("paper Fig 9", p9, 1008),
                        ("sim S11 final", s1, 1101), ("sim iterations+Koch", si, 5505), ("sim Fw sweep", fw, 3303),
                        ("sim pad20", pad, 1101), ("sim copper loss", cop, 1101), ("sim port 7x4", prt, 1101), ("sim lumped port", lum, 1101), ("sim far field", far, 91), ("cuts adaptive", ca, 2172),
                        ("cuts discrete", cd, 5792), ("fig9 levels", lev, 7), ("fig9 scan", scan, 352)]:
        check(f"{name}: {n} rows", len(df) == n, str(len(df)))
    check("paper S11 spans 0.51-9.99 GHz", close(ps.iloc[:, 0].min(), 0.51, 1e-6) and close(ps.iloc[:, 0].max(), 9.99, 1e-6))
    check("paper Fig 11 spans 0.57-9.95 GHz", close(p11.iloc[:, 0].min(), 0.57, 1e-6) and close(p11.iloc[:, 0].max(), 9.95, 1e-6))
    g = p4.groupby("Iter")["Freq_GHz"].min()
    check("Fig 4: Iter0 starts at 2.07 GHz, others below 0.55 GHz", close(g["Iter0"], 2.07, 0.005) and (g[["Iter1", "Iter2", "Iter3"]] < 0.55).all(), g.round(2).to_dict().__str__())
    check("Fig 9 file: 7 panels x 2 curves x 72 angles, angles 0-355 step 5",
          p9.groupby(["panel", "curve"]).size().eq(72).all() and p9["panel"].nunique() == 7 and set(p9["ang"]) == set(range(0, 360, 5)))
    check("Fig 9 file: 29 rows without radius", int(p9["r_px"].isna().sum()) == 29, str(int(p9["r_px"].isna().sum())))
    check("sim S11 final: 1-12 GHz, Zo = 50 + j0 everywhere", close(s1["Freq [GHz]"].min(), 1, 1e-9) and close(s1["Freq [GHz]"].max(), 12, 1e-9)
          and (s1["re(Zo(1)) []"] == 50).all() and (s1["im(Zo(1)) []"] == 0).all())
    check("iterations file: designs as documented, 1101 points each",
          set(si["Design"]) == {"Iter0", "Iter1", "Iter2", "Iter3_hybrid_baseline", "Fig7_KochOnly"} and si.groupby("Design").size().eq(1101).all())
    a = si[si["Design"] == "Iter3_hybrid_baseline"].sort_values("Freq_GHz")["S11_dB"].to_numpy()
    d = float(np.max(np.abs(a - s1.sort_values("Freq [GHz]")["dB(S(1,1)) []"].to_numpy())))
    check("Iter3_hybrid_baseline equals the final-design file (max diff <= 0.001 dB)", d <= 1e-3, f"{d:.4f} dB")
    check("Fw sweep: Fw = 1.5, 1.73, 1.8, 1101 points each", set(fw["Fw [mm]"].round(2)) == {1.5, 1.73, 1.8} and fw.groupby("Fw [mm]").size().eq(1101).all())
    check("pad20 file: one case, Fw 1.8 and pad 20", pad["Fw [mm]"].nunique() == 1 and close(pad["Fw [mm]"].iloc[0], 1.8, 1e-9) and pad["pad [mm]"].nunique() == 1 and pad["pad [mm]"].iloc[0] == 20)
    check("lumped, copper and port-size files: 1-12 GHz on the same 0.01 GHz grid as the final-design file, S11 in column 2",
          all(np.allclose(x.iloc[:, 0].to_numpy(), s1["Freq [GHz]"].to_numpy()) and x.iloc[:, 1].max() < 0 and "S(" in x.columns[1] for x in (lum, cop, prt)))
    f = far["f"].to_numpy()
    check("far field: 1.0-10.0 GHz in 0.1 steps", len(f) == 91 and np.allclose(np.diff(f), 0.1, atol=1e-6) and close(f[0], 1.0, 1e-9))
    gd = np.abs(far["G_dBi"] - (far["D_dBi"] + 10 * np.log10(far["Radiation Efficiency"]))).max()
    check("G = D x radiation efficiency within 0.0002 dB", gd <= 2e-4, f"{gd:.1e} dB")
    ee = np.abs(far["Radiation Efficiency"] - far["Prad_W"] / far["Pacc_W"]).max()
    check("radiation efficiency = Prad/Pacc within 1e-6", ee <= 1e-6, f"{ee:.1e}")
    te = np.abs(far["Total Efficiency"] - far["Prad_W"]).max()
    check("total efficiency equals Prad (1 W incident, inference) within 2e-5", te <= 2e-5, f"{te:.1e}")
    over = (far["g0"] - far["G_dBi"])
    check("g0 <= G in 87 of 91 rows; the other 4 exceed it by <= 3e-5 dB", int((over <= 0).sum()) == 87 and over.max() <= 3e-5, f"{int((over <= 0).sum())} rows, max excess {over.max():.1e}")
    neg = f[far["D_dBi"] < 0]
    check("17 rows with peak directivity < 0 dBi: 5 in 1.0-1.4 GHz and 12 in 3.3-4.4 GHz", len(neg) == 17 and int((neg <= 1.45).sum()) == 5 and int(((neg >= 3.25) & (neg <= 4.45)).sum()) == 12, str(len(neg)))
    fa, fd = [float(x) for x in sorted(ca["Freq [GHz]"].round(2).unique())], [float(x) for x in sorted(cd["Freq [GHz]"].round(2).unique())]
    check("adaptive cuts at 2.11, 5.78, 9.56 GHz", fa == [2.11, 5.78, 9.56], str(fa))
    check("discrete cuts at 3.04, 3.06, 6.92, 6.94, 8.45, 8.48, 9.18, 9.23 GHz", fd == [3.04, 3.06, 6.92, 6.94, 8.45, 8.48, 9.18, 9.23], str(fd))
    check("cuts: phi 0/90/180/270, theta 0-180", set(cd["Phi [deg]"]) == {0, 90, 180, 270} and cd["Theta [deg]"].min() == 0 and cd["Theta [deg]"].max() == 180)
    gp = scan.groupby("panel")["f"].nunique()
    check("scan: 22 (panel, f, curve) groups x 16 conventions; panels b,d,e,f at two frequencies, a,c,g at one",
          scan.groupby(["panel", "f", "curve"]).size().eq(16).all() and scan.groupby(["panel", "f", "curve"]).ngroups == 22
          and gp[["b", "d", "e", "f"]].eq(2).all() and gp[["a", "c", "g"]].eq(1).all())
    check("Fig 9 levels: paper cut max within 1.4 dB of text; ours 6.0-23.4 dB below",
          lev["diff_Fig9_vs_text"].abs().max() <= 1.4 and close(lev["diff_ours_vs_Fig9"].max(), -6.0, 0.1) and close(lev["diff_ours_vs_Fig9"].min(), -23.4, 0.1))
    check("Fig 9 levels: paper_Fig9_center is exactly 0.0 for panels d and e (documented as unexplained)",
          (lev.loc[lev["panel"].isin(["d", "e"]), "paper_Fig9_center"] == 0).all())

    print("\n== B. Headline numbers of the analysis scripts (results/*.csv) ==")
    R = args.results
    try:
        r1 = pd.read_csv(f"{R}/01_s11_resonances.csv"); r2 = pd.read_csv(f"{R}/02_fig4_summary.csv")
        r3 = pd.read_csv(f"{R}/03_fig7_dips.csv"); c3 = pd.read_csv(f"{R}/03_fig7_claims.csv")
        r4 = pd.read_csv(f"{R}/04_vswr_at_paper_frequencies.csv"); r5 = pd.read_csv(f"{R}/05_gain_at_paper_frequencies.csv")
        s5 = pd.read_csv(f"{R}/05_farfield_summary_stats.csv").set_index("quantity")["value"]; r6 = pd.read_csv(f"{R}/06_fig9_null_test.csv")
    except FileNotFoundError as e:
        raise SystemExit(f"ERROR: {e}. Run scripts/run_all.py first (or pass --results).")
    check("01: all 7 resonance frequencies within 1.0 % of the paper", r1["df_pct"].abs().max() <= 1.0, f"largest {r1['df_pct'].abs().max():.2f} %")
    check("01: dip depths -5.8, -22.2, -13.3, -13.4, -16.0, -28.6, -37.6 dB (+-0.1)",
          all(close(a, b, 0.1) for a, b in zip(r1["ours_dip_dB"], [-5.8, -22.2, -13.3, -13.4, -16.0, -28.6, -37.6])))
    check("01: bands 6 and 7 share one -10 dB band (9.09-9.66 GHz)", r1.loc[5, "band_lo"] == r1.loc[6, "band_lo"] and close(r1.loc[5, "band_lo"], 9.087, 0.002) and close(r1.loc[5, "band_hi"], 9.662, 0.002))
    check("01: band 1 (2.09 GHz) shallower than -10 dB, bandwidth 0", r1.loc[0, "ours_dip_dB"] > -10 and r1.loc[0, "ours_BW_MHz"] == 0)
    check("02: RMSE (flat-extension method) 1.70 / 2.85 / 2.75 / 2.80 dB (+-0.02)", all(close(a, b, 0.02) for a, b in zip(r2["RMSE_flat_extension_dB"], [1.70, 2.85, 2.75, 2.80])), str(r2["RMSE_flat_extension_dB"].tolist()))
    check("02: dips <= -10 dB, paper 2/3/5/7, ours 2/5/5/6", r2["paper_dips_le_-10"].tolist() == [2, 3, 5, 7] and r2["ours_dips_le_-10"].tolist() == [2, 5, 5, 6])
    dd = pd.read_csv(f"{R}/02_fig4_dips.csv")
    worst = 0.0
    for it in ("Iter0", "Iter1", "Iter2"):
        po, ou = dd[(dd.iteration == it) & (dd.source == "paper")], dd[(dd.iteration == it) & (dd.source == "ours")]
        for fp_ in po["dip_f_GHz"]:
            worst = max(worst, float((ou["dip_f_GHz"] - fp_).abs().min() / fp_))
    check("02: every paper dip <= -10 dB of Iter0-2 has one of ours within 2 % in frequency", worst <= 0.02, f"largest {100 * worst:.1f} %")
    r8 = pd.read_csv(f"{R}/08_sensitivity_dips.csv"); s8 = pd.read_csv(f"{R}/08_sensitivity_summary.csv").set_index("case")
    b1, b5 = r8[r8["band"] == 1]["dip_dB"], r8[r8["band"] == 5]["dip_dB"]
    check("08: band-1 (2.1 GHz) dip depth over the 8 setup cases lies between -7.6 and -5.8 dB (paper text -14)", close(b1.min(), -7.6, 0.05) and close(b1.max(), -5.8, 0.05), f"{b1.min()} to {b1.max()}")
    check("08: band-5 (8.4 GHz) dip depth over the 8 cases lies between -16.5 and -14.7 dB (paper text -30)", close(b5.min(), -16.5, 0.05) and close(b5.max(), -14.7, 0.05), f"{b5.min()} to {b5.max()}")
    lp = r8[r8["case"].str.startswith("lumped")].set_index("band")["dip_f_GHz"]; bp = r8[r8["case"].str.startswith("baseline")].set_index("band")["dip_f_GHz"]
    check("08: lumped-port dip frequencies within 20 MHz of the wave-port baseline in all 7 bands", float((lp - bp).abs().max()) <= 0.0201, f"largest {1000 * float((lp - bp).abs().max()):.0f} MHz")
    mx = s8["max_dip_freq_diff_to_paper_pct"]
    within = sorted(mx.index[mx <= 1.0])
    check("08: cases with all 7 dips within 1.0 % of the paper: baseline, Fw 1.73, Fw 1.8, box 20 mm, copper, lumped (NOT Fw 1.5 mm, NOT wave port 7 x 4 mm)",
          within == sorted(["baseline (wave port)", "Fw 1.73 mm", "Fw 1.8 mm", "radiation box 20 mm", "copper (finite conductivity)", "lumped port (+X padded)"]), str(within))
    check("08: wave port 7 x 4 mm moves dips down by up to 1.6 % vs the paper (largest difference 1.5-1.7 %)", 1.5 <= mx["wave port 7 x 4 mm"] <= 1.7, f"{mx['wave port 7 x 4 mm']} %")
    check("08: RMSE vs paper S11: baseline 2.92 dB, lumped port 2.82 dB (+-0.02)", close(s8.loc["baseline (wave port)", "RMSE_vs_paper_dB"], 2.92, 0.02) and close(s8.loc["lumped port (+X padded)", "RMSE_vs_paper_dB"], 2.82, 0.02))
    exp = [(2.17, -6.5), (3.07, -23.9), (5.93, -16.1), (6.95, -12.7), (7.98, -13.1), (9.21, -22.4), (9.99, -45.3), (10.62, -22.2)]
    kd = r3[r3["design"] == "Koch-only"]
    check("03: Koch-only dips (>= 1 dB prominence): 2.17/-6.5, 3.07/-23.9, 5.93/-16.1, 6.95/-12.7, 7.98/-13.1, 9.21/-22.4, 9.99/-45.3, 10.62/-22.2",
          len(kd) == len(exp) and all(close(a, x, 0.011) and close(b, y, 0.11) for (x, y), a, b in zip(exp, kd["dip_f_GHz"], kd["dip_dB"])))
    k = si[si["Design"] == "Fig7_KochOnly"]
    near72 = k[(k["Freq_GHz"] >= 7.0) & (k["Freq_GHz"] <= 7.4)]["S11_dB"].min()
    check("03: Koch-only S11 never below -20 dB near 7.2 GHz (paper: < -20 dB)", near72 > -20, f"deepest in 7.0-7.4 GHz: {near72:.1f} dB")
    check("03: Koch-only deepest S11 below 9.5 GHz is above -25 dB (paper: better than -25 dB at 5.8-6.2 GHz)", k[k["Freq_GHz"] <= 9.5]["S11_dB"].min() > -25, f"{k[k['Freq_GHz'] <= 9.5]['S11_dB'].min():.1f} dB")
    check("03: all 5 Fig 7 claims come out 'NOT matched' in the claims table", c3["result"].str.startswith("NOT matched").all())
    check("04: VSWR agrees within 0.1 only in bands 2 and 6", r4.loc[r4["agrees_within_0.1"], "band"].tolist() == [2, 6])
    check("04: our VSWR at 2.11 GHz is 3.20 (> the paper's stated 1.8)", close(r4.loc[0, "ours_VSWR_at_paper_f"], 3.20, 0.01) and not r4.loc[0, "paper_claim_le_1.8_met_at_paper_f"])
    check("05: cut maxima at the 7 frequencies -2.32, -14.81, -0.97, 1.61, -2.70, -6.15, -0.06 dBi (+-0.01)",
          all(close(a, b, 0.011) for a, b in zip(r5["ours_cut_max_at_paper_f_dBi"], [-2.32, -14.81, -0.97, 1.61, -2.70, -6.15, -0.06])))
    check("05: paper text gain exceeds our cut maximum by 6.2-23.0 dB", close(r5["text_minus_ours_cut_max_dB"].min(), 6.2, 0.05) and close(r5["text_minus_ours_cut_max_dB"].max(), 23.0, 0.05))
    want = {"max_peak_gain_dBi": 4.45, "max_peak_directivity_dBi": 9.28, "max_broadside_gain_g0_dBi": 2.67, "radiation_efficiency_min_pct": 1.5,
            "radiation_efficiency_max_pct": 34.8, "radiation_efficiency_mean_pct": 14.4, "rows_with_peak_directivity_below_0dBi": 17,
            "corr_peakG_vs_paper_Fig11": 0.22, "corr_broadsideG_vs_paper_Fig11": -0.03, "mean_paperFig11_minus_ours_peakG_dB": 11.0, "RMSE_paperFig11_vs_ours_peakG_dB": 13.6}
    check("05: sweep statistics as documented (" + str(len(want)) + " values, +-0.01)", all(close(s5[k_], v, 0.011) for k_, v in want.items()))
    a16, z = r6[r6["set"] == "all16"], r6[r6["set"] == "z_only"]
    top = a16[a16["rank_among_7"] == 1]
    check("06: null test (16 conventions): matched best is highest of 7 only for a-H (0.878) and d-H (0.569)",
          len(top) == 2 and set(zip(top["panel"], top["curve"])) == {("a", "H"), ("d", "H")} and close(top["matched_best_pearson"].max(), 0.878, 0.001) and close(top["matched_best_pearson"].min(), 0.569, 0.001))
    check("06: null test: matched below the null median in 7 of 14, below the null maximum in 12 of 14 (16 conventions)",
          int((a16["matched_best_pearson"] < a16["null_median"]).sum()) == 7 and int((a16["matched_best_pearson"] < a16["null_max"]).sum()) == 12)
    check("06: null test (z-consistent conventions): matched never highest of 7", int((z["rank_among_7"] == 1).sum()) == 0)

    n = sum(results)
    print(f"\n{n} passed, {len(results) - n} failed, {len(results)} checks")
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
