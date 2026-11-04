"""
00_verify_data.py - consistency checks for the replication data.

What it does
------------
Recomputes the numbers quoted in the project notes / README directly from the
CSV files and prints PASS / FAIL for each one. It checks that the files are
internally consistent and match the numbers we report. It does NOT prove that
the digitized paper curves match the original figures; that needs the overlay
check described in docs/verification.md.

Usage (from the repository root, with the virtual environment active):
    python scripts/00_verify_data.py                 # searches ./data
    python scripts/00_verify_data.py --data-dir D:\\some\\flat\\folder

Files are looked up by name anywhere under --data-dir. Both the new (clear)
names and the old working names are accepted.
Exit code is 0 if all checks pass, 1 otherwise.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

# logical id -> candidate file names (new name first, old name second)
FILES = {
    "paper_s11":    ["paper_s11_final_simulated_digitized.csv", "paper_S11_digitized.csv"],
    "paper_fig4":   ["paper_fig4_s11_iter0-3_digitized.csv", "paper_Fig4_digitized_all.csv"],
    "paper_fig11":  ["paper_fig11_gain_vs_freq_digitized.csv", "paper_Fig11_gain_digitized_v2.csv"],
    "paper_fig9":   ["paper_fig9_patterns_raw_pixels.csv", "paper_Fig9_digitized_pixels.csv"],
    "s11_final":    ["sim_s11_vswr_final_design.csv", "S11_baseline.csv"],
    "s11_iters":    ["sim_s11_iter0-3_and_koch_only.csv", "S11_ours_iterations_and_koch.csv"],
    "s11_fw":       ["sim_s11_feed_width_sweep.csv", "S11_Fw_sweep.csv"],
    "s11_pad20":    ["sim_s11_radiation_box_pad20mm.csv", "S11_pad20.csv"],
    "far_sweep":    ["sim_farfield_summary_1-10GHz.csv", "sweep3_summary.csv"],
    "gain_adapt":   ["sim_gain_cuts_adaptive_freqs.csv", "Gain_setup1_lastadaptive.csv"],
    "gain_disc":    ["sim_gain_cuts_discrete_freqs.csv", "Gain_setup1_Disc_fields.csv"],
    "fig9_levels":  ["fig9_peak_levels_paper_vs_sim.csv", "fig9_levels_comparison.csv"],
}
ROWS = {  # expected number of data rows
    "paper_s11": 949, "paper_fig4": 4508, "paper_fig11": 939, "paper_fig9": 1008,
    "s11_final": 1101, "s11_iters": 5505, "s11_fw": 3303, "s11_pad20": 1101,
    "far_sweep": 91, "gain_adapt": 2172, "gain_disc": 5792, "fig9_levels": 7,
}
F7 = [2.11, 3.06, 5.78, 6.94, 8.48, 9.23, 9.56]          # the paper's 7 resonances (GHz)
TEXT_RL = [-14, -12, -16, -10, -30, -16, -17]            # paper text, return loss (dB)

results = []


def record(group, name, ok, detail):
    results.append((group, name, bool(ok), detail))


def close(group, name, got, exp, tol, unit=""):
    ok = abs(got - exp) <= tol
    record(group, name, ok, f"got {got:.3f}, expected {exp:.3f} +/- {tol} {unit}")


def at(freq, curve_f, curve_y):
    return float(np.interp(freq, curve_f, curve_y))


def dips(f, s, thr=-10.0):
    idx, _ = find_peaks(-np.asarray(s), prominence=1.0)
    return [(float(f[i]), float(s[i])) for i in idx if s[i] <= thr]


def has_dip(dlist, f0, s0, tf=0.03, ts=0.25):
    return any(abs(f - f0) <= tf and abs(s - s0) <= ts for f, s in dlist)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    root = Path(ap.parse_args().data_dir)
    if not root.exists():
        sys.exit(f"Folder not found: {root}")

    paths, D = {}, {}
    for key, names in FILES.items():
        found = None
        for n in names:
            hits = list(root.rglob(n))
            if hits:
                found = hits[0]
                break
        if found is None:
            record("A files", key, False, f"not found (looked for {names[0]} / {names[1]})")
            continue
        paths[key] = found
        D[key] = pd.read_csv(found)

    # ---------- A. integrity ----------
    for key, df in D.items():
        record("A files", f"{key}: row count", len(df) == ROWS[key], f"{len(df)} rows, expected {ROWS[key]}")
        nan_ok = 29 if key == "paper_fig9" else 0
        record("A files", f"{key}: NaN count", int(df.isna().sum().sum()) == nan_ok,
               f"{int(df.isna().sum().sum())} NaN, expected {nan_ok}")
    for key in ("paper_s11", "paper_fig11", "s11_final"):
        if key in D:
            record("A files", f"{key}: frequency strictly increasing",
                   bool(np.all(np.diff(D[key].iloc[:, 0]) > 0)), "")

    # ---------- B. S11 (final design) ----------
    if "s11_final" in D:
        b = D["s11_final"]; f, s = b.iloc[:, 0].values, b.iloc[:, 1].values
        G = 10 ** (s / 20); v = (1 + G) / (1 - G)
        record("B S11/VSWR", "VSWR column = (1+|G|)/(1-|G|)", np.abs(v - b.iloc[:, 2].values).max() < 1e-6,
               f"max diff {np.abs(v - b.iloc[:, 2].values).max():.1e}")
        for f0, s0 in [(2.09, -5.8), (3.04, -22.2), (5.76, -13.3), (6.92, -13.4),
                       (8.45, -16.0), (9.18, -28.6), (9.54, -37.6)]:
            close("B S11/VSWR", f"our S11 at {f0} GHz", at(f0, f, s), s0, 0.15, "dB")
        vs = [1.45, 1.65, 1.37, 1.80, 1.06, 1.37, 1.31]  # paper text
        ours_v = [3.20, 1.67, 1.71, 1.57, 1.61, 1.34, 1.14]  # handoff 4b
        for fr, ov in zip(F7, ours_v):
            close("B S11/VSWR", f"our VSWR at {fr} GHz", at(fr, f, v), ov, 0.02)

    # ---------- C. digitized paper curves ----------
    if "paper_s11" in D:
        p = D["paper_s11"]; pf, ps = p.iloc[:, 0].values, p.iloc[:, 1].values
        for fr, rl in zip(F7, TEXT_RL):   # anchor test vs numbers printed in the paper text
            close("C digitized vs paper TEXT", f"digitized S11 at {fr} GHz vs text RL", at(fr, pf, ps), rl, 1.1, "dB")
    if "paper_s11" in D and "paper_fig4" in D:
        p4 = D["paper_fig4"]; i3 = p4[p4.Iter == "Iter3"]
        for fr in F7:
            a = at(fr, pf, ps); c = at(fr, i3.Freq_GHz.values, i3.iloc[:, 2].values)
            close("C two digitizations agree", f"paper_s11 vs Fig4-Iter3 at {fr} GHz", a, c, 0.35, "dB")
    if "paper_fig4" in D:
        p4 = D["paper_fig4"]
        exp4 = {"Iter0": [(5.54, -11.9), (7.44, -12.5)],
                "Iter1": [(5.37, -13.0), (7.40, -13.6), (8.36, -15.0)],
                "Iter2": [(3.78, -22.8), (7.50, -14.1), (8.17, -13.1), (8.70, -15.6), (9.73, -11.9)],
                "Iter3": list(zip(F7, [-14.7, -12.3, -16.2, -10.9, -29.9, -16.2, -17.3]))}
        for it, lst in exp4.items():
            g = p4[p4.Iter == it]; dl = dips(g.Freq_GHz.values, g.iloc[:, 2].values)
            record("C Fig 4 digitized", f"{it}: number of dips <= -10 dB", len(dl) == len(lst), f"{len(dl)} vs {len(lst)}")
            for f0, s0 in lst:
                record("C Fig 4 digitized", f"{it}: dip {f0} GHz / {s0} dB", has_dip(dl, f0, s0, tf=0.035), "")
        record("C Fig 4 digitized", "Iter0 curve starts at ~2.07 GHz (not 0.5)",
               abs(p4[p4.Iter == "Iter0"].Freq_GHz.min() - 2.07) < 0.02, "dotted curve has gaps at the left")
    if "paper_fig11" in D:
        q = D["paper_fig11"]; qf, qg = q.iloc[:, 0].values, q.iloc[:, 1].values
        for fr, g0 in zip(F7, [-2.5, 6.5, -6.7, 2.2, 13.7, 10.6, 5.0]):
            close("C Fig 11 digitized", f"gain at {fr} GHz", at(fr, qf, qg), g0, 0.1, "dBi")
        close("C Fig 11 digitized", "max value (near 7.80 GHz)", qg.max(), 20.5, 0.1, "dBi")
        close("C Fig 11 digitized", "frequency of max", qf[qg.argmax()], 7.80, 0.02, "GHz")
        close("C Fig 11 digitized", "value near 4.10 GHz", at(4.10, qf, qg), 16.8, 0.1, "dBi")
        close("C Fig 11 digitized", "minimum value (NOTE: old handoff said -16.5)", qg.min(), -15.5, 0.1, "dBi")

    # ---------- D. far field / gain ----------
    if "far_sweep" in D:
        w = D["far_sweep"]
        close("D far field", "peak IEEE gain max", w.G_dBi.max(), 4.45, 0.01, "dBi")
        close("D far field", "  ... at frequency", w.f[w.G_dBi.idxmax()], 7.4, 0.01, "GHz")
        close("D far field", "peak directivity max", w.D_dBi.max(), 9.28, 0.01, "dBi")
        close("D far field", "  ... at frequency", w.f[w.D_dBi.idxmax()], 7.5, 0.01, "GHz")
        close("D far field", "radiation efficiency min (%)", 100 * w["Radiation Efficiency"].min(), 1.5, 0.05)
        close("D far field", "radiation efficiency max (%)", 100 * w["Radiation Efficiency"].max(), 34.8, 0.05)
        close("D far field", "radiation efficiency mean (%)", 100 * w["Radiation Efficiency"].mean(), 14.4, 0.1)
        close("D far field", "points with peak directivity < 0 dBi", int((w.D_dBi < 0).sum()), 17, 0)
        e = np.abs(w.G_dBi - (w.D_dBi + 10 * np.log10(w["Radiation Efficiency"]))).max()
        record("D far field", "G = D x efficiency (dB)", e < 0.01, f"max diff {e:.4f} dB")
        e = np.abs(w.Prad_W / w.Pacc_W - w["Radiation Efficiency"]).max()
        record("D far field", "efficiency = Prad/Pacc", e < 1e-5, f"max diff {e:.1e}")
        close("D far field", "g0 column max (= broadside gain, inferred)", w.g0.max(), 2.67, 0.01, "dBi")
        if "paper_fig11" in D:
            gg = np.arange(1.0, 9.96, 0.1)
            a = np.interp(gg, w.f, w.G_dBi); c = np.interp(gg, qf, qg); b0 = np.interp(gg, w.f, w.g0)
            close("D far field", "corr(Fig 11, our peak gain)", np.corrcoef(a, c)[0, 1], 0.22, 0.04)
            close("D far field", "corr(Fig 11, our broadside g0)", np.corrcoef(b0, c)[0, 1], -0.03, 0.04)
            close("D far field", "mean offset Fig 11 - ours (dB)", float(np.mean(c - a)), 11.0, 0.5)
            close("D far field", "RMSE Fig 11 vs ours (dB)", float(np.sqrt(np.mean((a - c) ** 2))), 13.6, 0.3)
    cuts = {}
    for k in ("gain_adapt", "gain_disc"):
        if k in D:
            d = D[k]; d.columns = ["f", "phi", "th", "g"]
            record("D far field", f"{k}: phi cuts are 0/90/180/270, theta 0..180",
                   sorted(d.phi.unique().tolist()) == [0, 90, 180, 270] and d.th.min() == 0 and d.th.max() == 180, "")
            cuts.update(d.groupby("f").g.max().to_dict())
    for fr, g0 in zip(F7, [-2.32, -14.81, -0.97, 1.61, -2.70, -6.15, -0.06]):
        if fr in cuts or any(abs(fr - k) < 1e-9 for k in cuts):
            close("D far field", f"max of 4 principal cuts at {fr} GHz", cuts[min(cuts, key=lambda k: abs(k - fr))], g0, 0.01, "dBi")
        else:
            record("D far field", f"max of 4 principal cuts at {fr} GHz", False, "frequency missing")

    # ---------- E. Fig 9 ----------
    if "fig9_levels" in D:
        L = D["fig9_levels"]
        record("E Fig 9", "paper Fig 9 peak vs text gain within 1.4 dB (all 7)", L.diff_Fig9_vs_text.abs().max() <= 1.4,
               f"max {L.diff_Fig9_vs_text.abs().max():.1f} dB")
        record("E Fig 9", "ours below paper by 6-23.5 dB (all 7)",
               (-L.diff_ours_vs_Fig9).between(5.9, 23.5).all(),
               f"range {(-L.diff_ours_vs_Fig9).min():.1f}-{(-L.diff_ours_vs_Fig9).max():.1f} dB")
    if "paper_fig9" in D:
        x = D["paper_fig9"]
        record("E Fig 9", "7 panels x 2 curves x 72 angles", x.groupby(["panel", "curve"]).size().eq(72).all(), "")

    # ---------- F. iteration S11 (ours) ----------
    if "s11_iters" in D:
        o = D["s11_iters"]
        record("F iterations", "5 designs x 1101 points", o.groupby("Design").size().eq(1101).all() and o.Design.nunique() == 5,
               ", ".join(sorted(o.Design.unique())))
        exp_o = {"Iter0": [(5.48, -11.9), (7.38, -19.7)],
                 "Iter1": [(5.31, -12.6), (7.31, -17.6), (8.24, -14.4), (8.74, -37.1), (9.80, -12.6)],
                 "Iter2": [(3.81, -18.8), (7.50, -19.8), (8.03, -15.9), (8.67, -19.3), (9.64, -20.3)]}
        for it, lst in exp_o.items():
            g = o[(o.Design == it) & (o.Freq_GHz <= 10.0)]   # paper's plot window is 0.5-10 GHz
            dl = dips(g.Freq_GHz.values, g.S11_dB.values)
            record("F iterations", f"{it}: number of our dips <= -10 dB (1-10 GHz)", len(dl) == len(lst), f"{len(dl)} vs {len(lst)}")
            for f0, s0 in lst:
                record("F iterations", f"{it}: dip {f0} GHz / {s0} dB", has_dip(dl, f0, s0, tf=0.035, ts=0.4), "")
        g = o[o.Design == "Iter3_hybrid_baseline"]
        if "s11_final" in D:
            d = np.abs(np.interp(f, g.Freq_GHz, g.S11_dB) - s).max()
            record("F iterations", "Iter3 in this file = baseline S11 file (rounded to 3 decimals)", d < 0.01, f"max diff {d:.4f} dB")

    # ---------- report ----------
    wid = max(len(r[1]) for r in results) + 2
    last = None
    bad = 0
    for grp, name, ok, detail in results:
        if grp != last:
            print(f"\n=== {grp} ==="); last = grp
        print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(wid)} {detail}")
        bad += (not ok)
    print(f"\n{len(results) - bad} passed, {bad} failed, {len(results)} checks")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()