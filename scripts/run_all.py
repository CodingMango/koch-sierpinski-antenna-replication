#!/usr/bin/env python3
"""Run the data check, analysis scripts 01-07 and the results check (00d) in order; keep one log.

Usage (repo root, venv active):   python scripts\\run_all.py            (data in <repo>\\data)
                                  python scripts\\run_all.py --data-dir C:\\path\\to\\csv_folder
Writes results/run_all_log.txt. Exit code 0 only if every script finished without error.
00_verify_data.py is run first and 00d_verify_results.py last, when present (use --skip-verify to leave it out).
"""
import argparse
import subprocess
import sys
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ["01_s11_final_vs_paper.py", "02_fig4_iterations.py", "03_fig7_koch_only.py", "04_fig8_vswr.py",
           "05_gain_and_efficiency.py", "06_fig9_patterns.py", "07_make_hero_figure.py",
           "08_sensitivity_sweeps.py"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--figures", default=str(ROOT / "figures"))
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--skip-verify", action="store_true")
    a = ap.parse_args()
    Path(a.results).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    jobs = []
    if not a.skip_verify and (HERE / "00_verify_data.py").exists():
        jobs.append(("00_verify_data.py", ["--data-dir", a.data_dir]))
    jobs += [(s, ["--data-dir", a.data_dir, "--figures", a.figures, "--results", a.results]) for s in SCRIPTS]
    if (HERE / "00d_verify_results.py").exists():
        jobs.append(("00d_verify_results.py", ["--data-dir", a.data_dir, "--results", a.results]))
    log, failed = [], []
    for name, extra in jobs:
        r = subprocess.run([sys.executable, str(HERE / name)] + extra, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        status = "OK" if r.returncode == 0 else f"FAILED (exit {r.returncode})"
        print(f"{name:32s} {status}")
        log.append(f"\n{'=' * 78}\n{name}  ->  {status}\n{'=' * 78}\n{r.stdout}{r.stderr}")
        if r.returncode != 0:
            failed.append(name)
            print(r.stdout[-1500:] + r.stderr[-1500:])
    Path(a.results, "run_all_log.txt").write_text("".join(log), encoding="utf-8")
    print(f"\nLog: {Path(a.results, 'run_all_log.txt')}")
    print("ALL OK" if not failed else f"FAILED: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
