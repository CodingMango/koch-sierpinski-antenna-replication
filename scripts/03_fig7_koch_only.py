#!/usr/bin/env python3
"""03 - Fig 7: Koch outline without the Sierpinski slots vs the final (hybrid) design, and vs the paper's Fig 7 text.

Question: does our Koch-only model show the paper's Fig 7 features (wider band, better matching than the hybrid)?
Inputs : sim_s11_iter0-3_and_koch_only.csv (old name also accepted)
Outputs: figures/03_fig7_koch_only.png, results/03_fig7_claims.csv, results/03_fig7_dips.csv

Paper claims (Section 3.1, text only; Fig 7 itself was NOT digitized):
  2.0 and 2.9 GHz, about -10 dB; three merged resonances at 5.8/6.0/6.2 GHz giving a band of nearly 1000 MHz with
  RL better than -25 dB; 7.2 GHz below -20 dB; 9.7 GHz at -11 dB with 700 MHz bandwidth.
Rule: a resonance counts as 'matched' if our nearest dip is within 3 % in frequency and not shallower than the
claimed depth + 1 dB; a band claim is compared by its -10 dB width. These tolerances were set with the earlier
results in view, so they describe the comparison, they are not a blind test.
"""
import numpy as np
import pandas as pd

import _common as C
import matplotlib.pyplot as plt

TOL_F = 0.03
TOL_DB = 1.0


def main():
    args = C.make_parser(__doc__).parse_args()
    C.prepare(args)
    sim = C.load(args.data_dir, "sim_iters")
    k = sim[sim["Design"] == "Fig7_KochOnly"].sort_values("Freq_GHz")
    h = sim[sim["Design"] == "Iter3_hybrid_baseline"].sort_values("Freq_GHz")
    fk, sk = k["Freq_GHz"].to_numpy(), k["S11_dB"].to_numpy()
    fh, sh = h["Freq_GHz"].to_numpy(), h["S11_dB"].to_numpy()

    dk = C.find_dips(fk, sk, 1.0, 1.0, 12.0)
    dh = C.find_dips(fh, sh, 1.0, 1.0, 12.0)
    drows = [{"design": n, "dip_f_GHz": round(a, 2), "dip_dB": round(b, 1)} for n, dl in (("Koch-only", dk), ("hybrid", dh)) for a, b in dl]
    print("\nDips >= 1 dB prominence, 1-12 GHz (GHz / dB)")
    print("  Koch-only:", ", ".join(f"{a:.2f}/{b:.1f}" for a, b in dk))
    print("  hybrid   :", ", ".join(f"{a:.2f}/{b:.1f}" for a, b in dh))

    claims = [("dip near 2.0 GHz, about -10 dB", 2.0, -10.0), ("dip near 2.9 GHz, about -10 dB", 2.9, -10.0),
              ("dip near 7.2 GHz, below -20 dB", 7.2, -20.0)]
    rows = []
    for text, f0, lvl in claims:
        d = C.nearest_dip(dk, f0, TOL_F)
        any_d = min(dk, key=lambda x: abs(x[0] - f0))
        if d is None:
            rows.append({"claim": text, "ours_nearest_dip_GHz": round(any_d[0], 2), "ours_dip_dB": round(any_d[1], 1),
                         "df_pct": round(100 * (any_d[0] - f0) / f0, 1), "result": "NOT matched (no dip within 3 %)"})
        else:
            ok = d[1] <= lvl + TOL_DB
            rows.append({"claim": text, "ours_nearest_dip_GHz": round(d[0], 2), "ours_dip_dB": round(d[1], 1),
                         "df_pct": round(100 * (d[0] - f0) / f0, 1), "result": "matched" if ok else "frequency ok, shallower than claimed"})
    mid = (fk >= 5.5) & (fk <= 6.5)
    best_mid = float(sk[mid].min())
    bd = C.band_around(fk, sk, float(fk[mid][np.argmin(sk[mid])]), -10.0)
    w_mid = 0 if bd is None else (bd[1] - bd[0]) * 1000
    rows.append({"claim": "5.8-6.2 GHz: band of nearly 1000 MHz, RL better than -25 dB", "ours_nearest_dip_GHz": round(float(fk[mid][np.argmin(sk[mid])]), 2),
                 "ours_dip_dB": round(best_mid, 1), "df_pct": np.nan,
                 "result": f"NOT matched: our -10 dB band there is {w_mid:.0f} MHz, deepest {best_mid:.1f} dB"})
    d97 = min((d for d in dk if 9.0 <= d[0] <= 10.5), key=lambda x: abs(x[0] - 9.7))
    b97 = C.band_around(fk, sk, d97[0], -10.0)
    w97 = 0 if b97 is None else (b97[1] - b97[0]) * 1000
    ok97 = abs(d97[0] - 9.7) / 9.7 <= TOL_F and d97[1] <= -11.0 + TOL_DB and w97 >= 0.5 * 700
    rows.append({"claim": "9.7 GHz: -11 dB, 700 MHz wide", "ours_nearest_dip_GHz": round(d97[0], 2), "ours_dip_dB": round(d97[1], 1),
                 "df_pct": round(100 * (d97[0] - 9.7) / 9.7, 1),
                 "result": ("matched" if ok97 else "NOT matched") + f": our -10 dB band there is {w97:.0f} MHz wide (claimed 700)"
                           f", dip {abs(d97[0] - 9.7) / 9.7 * 100:.1f} % from 9.7 GHz"})
    tab = pd.DataFrame(rows)
    print("\nPaper's Fig 7 claims vs our Koch-only model")
    C.show(tab)

    print(f"\nDeepest S11 of the Koch-only model below 9.5 GHz: {sk[fk <= 9.5].min():.1f} dB (paper claims better than -25 dB at 5.8-6.2 GHz)")
    rm, co, n = C.score(fk, sk, fh, sh)
    print(f"Koch-only vs hybrid, both ours: RMSE {rm:.1f} dB, correlation {co:.2f} (1.5-10 GHz, clipped -30 dB)")
    for tol in (0.02, 0.04):
        sh_ = [round(a, 2) for a, _ in dk if C.nearest_dip(dh, a, tol)]
        print(f"Koch-only dips that have a hybrid dip within {tol*100:.0f} %: {len(sh_)} of {len(dk)} {sh_}")
    C.save_table(tab, args.results, "03_fig7_claims.csv")
    C.save_table(pd.DataFrame(drows), args.results, "03_fig7_dips.csv")

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(fh, sh, color="C0", lw=1.4, label="Hybrid (Koch outline + 73 slots), ours")
    ax.plot(fk, sk, color="C2", lw=1.6, label="Koch-only (no slots), ours")
    ax.axvspan(5.8, 6.2, color="C1", alpha=0.15, label="Paper: 5.8-6.2 GHz band 'better than -25 dB' (text)")
    for _, f0, lvl in claims + [("", 9.7, -11.0)]:
        ax.scatter([f0], [lvl], marker="D", color="C1", zorder=5)
    ax.scatter([], [], marker="D", color="C1", label="Paper: other Fig 7 values from the text")
    ax.axhline(-10, color="0.5", lw=0.8); ax.axhline(-25, color="C1", lw=0.8, ls=":")
    ax.set_xlim(1, 12); ax.set_ylim(-50, 2); ax.set_xlabel("Frequency (GHz)"); ax.set_ylabel("S11 (dB)")
    ax.set_title("Koch-only vs hybrid: the wide, deep 5.8-6.2 GHz band claimed for Fig 7 is not reproduced")
    ax.legend(loc="lower left", fontsize=9); ax.grid(alpha=0.25)
    C.save_fig(fig, args.figures, "03_fig7_koch_only.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
