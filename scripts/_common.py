"""Shared helpers for the analysis scripts 01-07 and run_all.py (not run on its own).

Every script finds its input CSV files by NAME anywhere below --data-dir (default: <repo>/data),
accepts the new repo names and the old working names, and prints which file it loaded.
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")            # write PNG files, never open a window
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402
import pandas as pd              # noqa: E402
from scipy.signal import find_peaks  # noqa: E402

try:                              # keep printing safe if the console is not UTF-8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "paper_s11":    ["paper_s11_final_simulated_digitized.csv", "paper_S11_digitized.csv"],
    "paper_fig4":   ["paper_fig4_s11_iter0-3_digitized.csv", "paper_Fig4_digitized_all.csv"],
    "paper_fig11":  ["paper_fig11_gain_vs_freq_digitized.csv", "paper_Fig11_gain_digitized_v2.csv"],
    "paper_fig9":   ["paper_fig9_patterns_raw_pixels.csv", "paper_Fig9_digitized_pixels.csv"],
    "sim_s11":      ["sim_s11_vswr_final_design.csv", "S11_baseline.csv"],
    "sim_iters":    ["sim_s11_iter0-3_and_koch_only.csv", "S11_ours_iterations_and_koch.csv"],
    "sim_far":      ["sim_farfield_summary_1-10GHz.csv", "sweep3_summary.csv"],
    "cuts_adapt":   ["sim_gain_cuts_adaptive_freqs.csv", "Gain_setup1_lastadaptive.csv"],
    "cuts_disc":    ["sim_gain_cuts_discrete_freqs.csv", "Gain_setup1_Disc_fields.csv"],
    "fig9_levels":  ["fig9_peak_levels_paper_vs_sim.csv", "fig9_levels_comparison.csv"],
    "fig9_scan":    ["fig9_convention_scan.csv"],
}

# Values printed in the paper's TEXT (Section 3 and abstract), checked against the PDF in Chat F.
PAPER = {
    "f":    [2.11, 3.06, 5.78, 6.94, 8.48, 9.23, 9.56],       # GHz
    "rl":   [-14, -12, -16, -10, -30, -16, -17],              # dB
    "bw":   [90, 37, 67, 100, 90, 130, 220],                  # MHz
    "vswr": [1.45, 1.65, 1.37, 1.80, 1.06, 1.37, 1.31],
    "gain": [3.92, 8.24, 6.90, 11.66, 19.38, 16.76, 12.06],   # dBi
}
PANELS = ["a", "b", "c", "d", "e", "f", "g"]                  # Fig 9 panels = the 7 resonances


def rel(p):
    """Path relative to the repo root when possible (keeps logs free of machine-specific folders)."""
    try:
        return Path(p).resolve().relative_to(ROOT)
    except ValueError:
        return Path(p).name


def make_parser(doc):
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(ROOT / "data"),
                    help="folder searched (recursively) for the input CSV files [default: <repo>/data]")
    ap.add_argument("--figures", default=str(ROOT / "figures"), help="output folder for PNG figures")
    ap.add_argument("--results", default=str(ROOT / "results"), help="output folder for result tables (CSV)")
    return ap


def prepare(args):
    Path(args.figures).mkdir(parents=True, exist_ok=True)
    Path(args.results).mkdir(parents=True, exist_ok=True)


def locate(data_dir, key):
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        raise SystemExit(f"ERROR: data folder not found: {data_dir}  (use --data-dir)")
    for name in FILES[key]:
        hits = sorted(p for p in data_dir.rglob(name) if p.is_file())
        if hits:
            if len(hits) > 1:
                print(f"WARNING: {len(hits)} files named {name} below {data_dir}; using {hits[0]}")
            return hits[0]
    raise SystemExit(f"ERROR: input '{key}' not found below {data_dir}. Looked for: {FILES[key]}")


def load(data_dir, key):
    p = locate(data_dir, key)
    df = pd.read_csv(p)
    df.columns = [c.strip() for c in df.columns]
    print(f"LOAD  {key}: {rel(p)}  ({len(df)} rows)")
    return df


def clean_curve(f, s):
    """Sort by frequency and average duplicated frequencies (needed by np.interp)."""
    d = pd.DataFrame({"f": np.asarray(f, float), "s": np.asarray(s, float)}).dropna()
    d = d.groupby("f", as_index=False)["s"].mean().sort_values("f")
    return d["f"].to_numpy(), d["s"].to_numpy()


def regrid(f, s, step=0.01):
    """Resample a curve to a regular grid inside its own frequency range (no extrapolation)."""
    f, s = clean_curve(f, s)
    g = np.arange(np.ceil(f.min() / step) * step, f.max() + 1e-9, step)
    return g, np.interp(g, f, s)


def find_dips(f, s, prominence=1.0, fmin=None, fmax=None):
    """Local minima of S11 (dB) with at least `prominence` dB, inside [fmin, fmax]."""
    f = np.asarray(f, float)
    s = np.asarray(s, float)
    keep = np.ones(f.size, bool)
    if fmin is not None:
        keep &= f >= fmin - 1e-9
    if fmax is not None:
        keep &= f <= fmax + 1e-9
    ff, ss = f[keep], s[keep]
    idx, _ = find_peaks(-ss, prominence=prominence)
    return [(float(ff[i]), float(ss[i])) for i in idx]


def nearest_dip(dips, f0, tol_rel):
    """Dip closest to f0 within +-tol_rel (relative), or None."""
    best = None
    for fd, sd in dips:
        if abs(fd - f0) / f0 <= tol_rel and (best is None or abs(fd - f0) < abs(best[0] - f0)):
            best = (fd, sd)
    return best


def band_around(f, s, f0, thr=-10.0):
    """Contiguous band (flo, fhi) with S11 <= thr that contains the sample nearest to f0; None if S11 > thr there."""
    f = np.asarray(f, float)
    s = np.asarray(s, float)
    i = int(np.argmin(np.abs(f - f0)))
    if s[i] > thr:
        return None
    lo = hi = i
    while lo > 0 and s[lo - 1] <= thr:
        lo -= 1
    while hi < len(f) - 1 and s[hi + 1] <= thr:
        hi += 1
    flo = f[lo] if lo == 0 else f[lo - 1] + (thr - s[lo - 1]) * (f[lo] - f[lo - 1]) / (s[lo] - s[lo - 1])
    fhi = f[hi] if hi == len(f) - 1 else f[hi] + (thr - s[hi]) * (f[hi + 1] - f[hi]) / (s[hi + 1] - s[hi])
    return float(flo), float(fhi)


def score(fa, sa, fb, sb, lo=1.5, hi=10.0, clip=-30.0, step=0.01, overlap_only=True):
    """RMSE (dB) and Pearson correlation of two S11 curves on a common grid; both clipped at `clip` dB."""
    fa, sa = clean_curve(fa, sa)
    fb, sb = clean_curve(fb, sb)
    g = np.arange(lo, hi + 1e-9, step)
    if overlap_only:
        g = g[(g >= max(fa.min(), fb.min()) - 1e-9) & (g <= min(fa.max(), fb.max()) + 1e-9)]
    a = np.maximum(np.interp(g, fa, sa), clip)
    b = np.maximum(np.interp(g, fb, sb), clip)
    return float(np.sqrt(np.mean((a - b) ** 2))), float(np.corrcoef(a, b)[0, 1]), int(g.size)


def vswr_from_s11(s_db):
    g = 10.0 ** (np.asarray(s_db, float) / 20.0)
    return (1 + g) / (1 - g)


def show(df, **kw):
    print(df.to_string(index=False, **kw))


def save_table(df, results_dir, name):
    p = Path(results_dir) / name
    df.to_csv(p, index=False)
    print(f"WROTE {rel(p)}")


def save_fig(fig, figures_dir, name, **kw):
    p = Path(figures_dir) / name
    fig.savefig(p, dpi=kw.pop("dpi", 200), **kw)
    plt.close(fig)
    print(f"WROTE {rel(p)}")
