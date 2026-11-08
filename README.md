# Koch-Sierpinski antenna replication

Simulation-only replication of a hybrid Koch-Sierpinski fractal antenna: Azzouz et al., *Fractal Fract.* 2026, 10, 47 ([doi:10.3390/fractalfract10010047](https://doi.org/10.3390/fractalfract10010047)). Ansys HFSS and Python.

![Resonances reproduced, gain not reproduced under the assumed setup](figures/07_hero_figure.png)

## Summary

The paper does not state the ground plane, port, radiation box, copper thickness or excitation power, and gives the outline only as a figure. I rebuilt the geometry from the paper's Figs 1-2 (to about 0.05 mm), assumed a standard setup (below), and compared my HFSS results with the paper's text, digitized curves and figures.

Under this setup:

- **Reproduced:** all 7 reported resonance frequencies, within 1.0 % (largest difference 0.95 %; setup-dependent at about this level, see Assumptions). The iteration study of Fig 4 for iterations 0-2: every dip at or below -10 dB has one of mine within 2 % in frequency.
- **Not reproduced:** the S11 depths at some bands (2.11 GHz: -5.8 dB vs -14 reported; 8.48 GHz: -12.6 dB vs -30), the Fig 7 features of the Koch-only variant, and the reported gain. The paper reports 3.92-19.38 dBi at the seven resonances. My peak gain never exceeds +4.45 dBi and my peak directivity never exceeds 9.28 dBi between 1 and 10 GHz. Radiation efficiency is 1.5-34.8 %.

"Not reproduced" means my model disagrees under assumptions the paper does not confirm. It does not show the paper is wrong. The details, with the file and script behind every number, are in [`docs/claims_vs_evidence.md`](docs/claims_vs_evidence.md).

## Status by figure

| Paper figure | Status |
|---|---|
| Figs 1-2 (geometry) | Reconstructed from the figures; overlay check passes (64 checks). The geometry of Fig 2, not the paper's text description of the iterations, is the one consistent with Fig 4. |
| Fig 3 (photograph) | Not applicable (simulation only) |
| Fig 4 (iterations) | Iterations 0-2 match in dip frequency (within 2 %) and approximately in depth. Iteration 3 (final design) differs in depth at 2.11 and 8.48 GHz. |
| Fig 5 (simulated S11) | Compared; resonance frequencies agree, depths do not. The measured curve is not a replication target. |
| Fig 6 (mesh refinement) | Not replicable: the meaning of the values 0.005 / 0.0025 / 0.00125 mm is not stated. |
| Fig 7 (Koch-only) | Not reproduced under this setup. |
| Fig 8 (VSWR) | Compared at the 7 frequencies; 2 of 7 values agree within 0.1. |
| Fig 9 (patterns) | Peak levels: the paper's Fig 9 matches its text gains; mine are 6-23 dB lower. Shapes: inconclusive (the angle convention is not stated). |
| Fig 10 (3D gain) | Peak values compared; not reproduced. |
| Fig 11 (gain vs frequency) | Not reproduced. It also disagrees with the paper's text gains by 1.7-13.7 dB at the 7 resonances. |
| Fig 12 (surface currents) | Not compared numerically (palette mapping has medium-low confidence; excitation power unknown). |
| Table 1 | Not a replication target |

## Assumptions

These are mine, not the paper's. Results depend on them, most of all the gain.

| Item | Used |
|---|---|
| Substrate | FR4, relative permittivity 4.7, loss tangent 0.0197, 0.8 mm, board 60 x 40 mm (from the paper) |
| Ground plane | Full, 60 x 40 mm, Perfect E |
| Conductors | Perfect E, zero thickness |
| Port | Wave port on the board edge, renormalised to 50 ohm |
| Radiation box | 37.5 mm padding, radiation boundary |
| Solver | HFSS 2025 R2 Student (the paper used v15), multi-frequency adaptive mesh at 2.11, 5.78, 9.56 GHz, interpolating sweep 1-12 GHz |

Full list, including solver convergence numbers: [`hfss/hfss_setup_notes.md`](hfss/hfss_setup_notes.md). Feed width, radiation-box size, finite-conductivity copper, port size and port type (lumped instead of wave port) did not close the S11 depth gaps at 2.11 and 8.48 GHz. The dip frequencies do depend on the port: a 7 x 4 mm wave port moves them down by up to 1.6 %, but that run also converged on a coarser mesh (17,531 vs 39,514 tetrahedra), so port size and mesh are not separated (`results/08_sensitivity_summary.csv`).

## Limitations

- One solver and one assumed setup; one simulation per design. An independent solver (for example openEMS) has not been run.
- The HFSS Student licence limits the mesh to about 40,000 tetrahedra (final design: 39,514), so the mesh could not be refined much.
- Gain cuts were exported for four phi planes only, so the "cut maximum" values are lower bounds of the peak gain (the true peaks at 9.18-9.56 GHz are 0.4-2.5 dB higher).
- Peak directivity is below 0 dBi at 17 of 91 frequencies (1.0-1.4 and 3.3-4.4 GHz), which is physically impossible. The cause is unresolved. The paper's seven resonances are not among the affected frequencies (the nearest, 3.06 GHz, lies just below the 3.3-4.4 GHz range), but because the cause is unknown, values near the affected range should be treated with caution.
- Digitized paper values carry about +-1 dB uncertainty. The angle convention of the paper's Fig 9 is not stated.
- In Fig 2 the horizontal edges of the iteration 0-2 shapes lie about 0.08 mm inside my geometry; the effect on S11 was not tested.
- Far-field values are sampled on a 5 deg (phi) x 1 deg (theta) grid, so a narrow lobe between grid points could be slightly higher than reported. Setup details: `hfss/hfss_setup_notes.md`.

## Reproduce

Developed on Python 3.14 and Windows. From the repo root:

```
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-lock.txt
python scripts/run_all.py
```

`run_all.py` runs the data check, analysis scripts 01-08 and the results check, writes the figures to `figures/` and the tables to `results/`, and keeps `results/run_all_log.txt`. Expected last line: `ALL OK`. Inputs are found by file name anywhere below `data/`; use `--data-dir` for another folder.

Other checks:

```
python geometry/make_geometry.py --check-only
```

Rebuilds the geometry in memory and runs 26 self-checks. Without `--check-only` it rewrites `geometry/dxf/`.

`scripts/00b_overlay_check.py` and `scripts/00c_geometry_overlay_check.py` need the paper's figure images, which are not included here. Download the paper (open access) and see each script's header for the arguments.

What the checks cover: 133 data checks, 64 results checks, 68 digitization overlay checks, 64 geometry overlay checks, 26 geometry self-checks. They show that files, notes and results agree with each other. They do not show that an interpretation is right.

## Repository layout

```
docs/       claims_vs_evidence.md, verification/ (overlay report and images)
geometry/   vertices_quadrant.csv, make_geometry.py, feed_dimensions.csv, dxf/
hfss/       KochSierp_v1_baseline.aedt (no results), hfss_setup_notes.md
data/       README.md, paper_digitized/, simulation/, derived/
scripts/    00_ and 00b-00d_ checks, 01-08 analysis, run_all.py
figures/    output of run_all.py
results/    output tables and run_all_log.txt
```

Column dictionary for every data file: [`data/README.md`](data/README.md).

## Licences and credits

- Code: MIT (`LICENSE`). Simulation data, tables and figures: CC BY 4.0 (`DATA_LICENSE.md`).
- `data/paper_digitized/` and the images in `docs/verification/` are derived from figures of Azzouz et al. (2026), published under CC BY 4.0. They are my digitizations and overlays, not the authors' data; please credit the original authors as well.
- The `.aedt` project needs ANSYS HFSS to open (a free Student version exists).

## Original paper

Azzouz, A.; Bouhmidi, R.; Munir, M.E.; Nasralla, M.M.; Chetioui, M. Characterization and Analysis of Hybrid Fractal Antennas for Multiband Communication and Radar Applications. *Fractal Fract.* **2026**, *10*, 47. https://doi.org/10.3390/fractalfract10010047

Questions about the unstated setup details were sent to the corresponding author on 31 October 2026. This note will be updated if there is a reply.

Author of this replication: Abdul Jabbar Khan, undergraduate, ECE, RGUKT Nuzvid.
