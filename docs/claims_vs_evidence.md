# Claims vs evidence

Every statement the README makes about the replication, with the file that holds the numbers, the script that produces them, and how sure we are. Wording is conditional: results are for **our assumed setup** (see `hfss/hfss_setup_notes.md`): full ground plane, Perfect-E conductors, 50 ohm wave port, 37.5 mm radiation box, geometry read from the paper's figures to about 0.05 mm. The paper does not state these.

**Status key**
- **Reproduced**: our model agrees with the paper's value within the stated tolerance.
- **Not reproduced (this setup)**: our model disagrees. This does not show the paper is wrong; the setup may differ from the authors'.
- **Observation**: a measured fact about our data or the paper's figures, no verdict.
- **Inconclusive**: the test cannot separate the hypotheses.
- **Not checkable here**: evidence is not stored in this repository.

**Confidence key**: *Verified* = recomputed from files by a script in this repo (`00_verify_data.py`, `00d_verify_results.py`). *Inference* = reasoned from verified numbers, not tested directly. Digitized paper values carry about +-1 dB uncertainty.

Reproduce everything: `python scripts/run_all.py` (inputs in `data/`, outputs in `results/` and `figures/`).

## 1. S11 and resonances (final design)

| # | Claim | Evidence | Script | Status | Confidence |
|---|---|---|---|---|---|
| 1.1 | All 7 resonance frequencies reported in the paper appear in our model within 1.0 % (largest difference 0.95 %, 2.09 vs 2.11 GHz; our dips sit 0.2-0.95 % below the paper's values). | `results/01_s11_resonances.csv` | `01_s11_final_vs_paper.py`; checked by `00d` | Reproduced | Verified |
| 1.2 | Depths differ at several bands. At 2.11 GHz we get -5.8 dB (paper text: -14); at 8.48 GHz our nearest dip is -16.0 dB at 8.45 GHz and S11 is -12.6 dB at 8.48 GHz (paper: -30). Our 3.04, 9.18 and 9.54 GHz dips are *deeper* than reported (-22.2, -28.6, -37.6 dB vs -12, -16, -17). | same | same | Not reproduced (this setup) | Verified |
| 1.3 | Our 9.18 and 9.54 GHz dips lie in one contiguous -10 dB band (9.09-9.66 GHz); the paper reports them as two bands. | same | same | Not reproduced (this setup) | Verified |
| 1.4 | -10 dB bandwidths differ from the paper's list (ours 0, 41, 56, 183, 104, 575, 575 MHz vs 90, 37, 67, 100, 90, 130, 220). | same | same | Not reproduced (this setup) | Verified |
| 1.5 | Feed width, radiation-box size did not close the 2.11 GHz depth gap. Dip at 2.09 GHz: -7.6 / -6.1 / -5.8 dB for Fw = 1.5 / 1.73 / 1.8 mm; -6.0 dB with a 20 mm box. At 8.4 GHz: -16.5 / -15.8 / -15.8 dB and -16.0 dB. | `data/simulation/sim_s11_feed_width_sweep.csv`, `sim_s11_radiation_box_pad20mm.csv` | read by hand for this table; no script | Observation | Verified for these two sweeps only |
| 1.6 | Copper loss, port size and port type were also tested and did not explain the gap. | not stored | none | Not checkable here | - |

## 2. Design iterations (Fig 4) and Koch-only (Fig 7)

| # | Claim | Evidence | Script | Status | Confidence |
|---|---|---|---|---|---|
| 2.1 | Iterations 0-2 (geometry as drawn in the paper's Fig 2) reproduce the dip frequencies of the paper's Fig 4: every paper dip <= -10 dB has one of ours within 2 %. Depths are approximate. | `results/02_fig4_dips.csv`, `02_fig4_summary.csv` | `02_fig4_iterations.py`; checked by `00d` | Reproduced (frequency) | Verified |
| 2.2 | RMSE vs the paper's Fig 4 curves (1.5-10 GHz, clipped at -30 dB): 1.7 / 2.85 / 2.75 / 2.80 dB for Iter0-3 (flat-extension method; overlap-only: 1.71 / 2.84 / 2.64 / 2.80). | `results/02_fig4_summary.csv` | same | Observation | Verified |
| 2.3 | The mismatch is concentrated in the final geometry (Iter3). Likely cause: unknown final outline dimensions (base side, outward shift), to which narrow deep notches are sensitive. | 2.1, 1.2 | - | Inference | Inference |
| 2.4 | Counts of dips <= -10 dB (1-10 GHz): paper 2 / 3 / 5 / 7, ours 2 / 5 / 5 / 6 for Iter0-3. | `results/02_fig4_summary.csv` | same | Observation | Verified |
| 2.5 | The geometry sequence of Fig 2 (not the text description of the iterations) is the one consistent with Fig 4. | 2.1; `docs/verification/` Fig 2 overlay | `02`, `00c` | Inference | Inference from one simulation per iteration |
| 2.6 | The Fig 7 claims (text only; Fig 7 was not digitized) are not reproduced by our Koch-only model: no dip within 3 % of 2.0 or 7.2 GHz at the claimed depth, our 5.8-6.2 GHz band is 75 MHz wide at -10 dB with a deepest value of -16.1 dB (claimed ~1000 MHz, better than -25 dB), and our 9.99 GHz dip is 236 MHz wide (claimed 700 MHz at 9.7 GHz). | `results/03_fig7_claims.csv`, `03_fig7_dips.csv` | `03_fig7_koch_only.py`; checked by `00d` | Not reproduced (this setup) | Verified. Tolerances were set with earlier results in view (not blind). |
| 2.7 | The Koch-only and hybrid models share several dips, so in our model much of the multiband behaviour comes from the outline. The paper's statement that the carpet adds resonances for the lower bands is not supported by one simulation. | `results/03_fig7_dips.csv` | `03` | Inference | Inference (single setup, single simulation) |

## 3. VSWR (Fig 8)

| # | Claim | Evidence | Script | Status | Confidence |
|---|---|---|---|---|---|
| 3.1 | VSWR computed from our S11 equals the HFSS `VSWR(1)` column (max relative difference below 1e-9). | `data/simulation/sim_s11_vswr_final_design.csv` | `04_fig8_vswr.py` | Verified | Verified |
| 3.2 | At the paper's 7 frequencies our VSWR agrees with the values printed in the text within 0.1 only at 3.06 and 9.23 GHz. At 2.11 GHz we get 3.20 (paper 1.45). | `results/04_vswr_at_paper_frequencies.csv` | `04`; checked by `00d` | Not reproduced (this setup) | Verified |
| 3.3 | The plotted "paper-implied" VSWR curve is the paper's digitized S11 converted to VSWR, not a digitization of Fig 8. | `figures/04_fig8_vswr.png` | `04` | Observation | Verified |

## 4. Gain, directivity, efficiency (Figs 9-11)

| # | Claim | Evidence | Script | Status | Confidence |
|---|---|---|---|---|---|
| 4.1 | The paper's text gains (3.92-19.38 dBi) are 6.2-23.0 dB above our maximum over four exported phi cuts at the same frequencies (cut maxima: -2.32, -14.81, -0.97, +1.61, -2.70, -6.15, -0.06 dBi). Cut maxima are lower bounds; the true peaks at 9.18-9.56 GHz are 0.4-2.5 dB higher. | `results/05_gain_at_paper_frequencies.csv`, `data/simulation/sim_gain_cuts_*.csv` | `05_gain_and_efficiency.py`; checked by `00d` | Not reproduced (this setup) | Verified |
| 4.2 | Over 1-10 GHz our peak gain never exceeds +4.45 dBi (7.4 GHz) and peak directivity never exceeds 9.28 dBi (7.5 GHz). | `results/05_farfield_summary_stats.csv`, `data/simulation/sim_farfield_summary_1-10GHz.csv` | `05`; `00d` | Not reproduced (this setup) | Verified |
| 4.3 | Radiation efficiency of our model is 1.5-34.8 % (mean 14.4 %) over 1-10 GHz. With FR4 (tan d = 0.0197) this caps gain well below the reported values. | same | `05` | Observation | Verified for our setup; the cause (dielectric loss) is Inference, see 4.6 |
| 4.4 | The paper's Fig 9 peak levels equal its text gains within 1.3 dB (after our calibration, about +-1 dB). Ours are 6.0-23.4 dB below the Fig 9 peaks. | `results/06_fig9_levels.csv`, `data/derived/fig9_peak_levels_paper_vs_sim.csv` | `06_fig9_patterns.py`; `00d` | Observation | Verified (calibration from earlier work) |
| 4.5 | The paper's Fig 11 does not agree with its text/Fig 9/Fig 10 gains: at the 7 resonances the text gain exceeds the digitized Fig 11 value by 1.7-13.7 dB (+-1 dB). Our peak gain correlates only 0.22 with Fig 11 (broadside gain: -0.03); mean offset 11.0 dB, RMSE 13.6 dB. | `results/05_gain_at_paper_frequencies.csv`, `05_farfield_summary_stats.csv` | `05`; `00d` | Observation | Verified |
| 4.6 | At 2.11 and 3.06 GHz the dielectric loss integrated over the substrate matches accepted minus radiated power to 0.1 % and 0.05 %, so our efficiencies are internally consistent there. | field integral computed in HFSS, not exported | none | Not checkable here | Reported in the replication report only |
| 4.7 | Per-frequency directivity and efficiency at the paper's exact frequencies (e.g. 19.1 % at 2.11 GHz) come from HFSS report tables that are not in `data/`. The sweep file gives them only on a 0.1 GHz grid, which the script uses (nearest grid point is printed). | `results/05_gain_at_paper_frequencies.csv` | `05` | Observation | Verified for the grid values |
| 4.8 | A 40 x 60 mm aperture gives 4 pi A / lambda^2 = 13.8 dBi at 8.48 GHz. This is a plausibility yardstick, **not** a bound. | `results/05_gain_at_paper_frequencies.csv` | `05` | Observation | Verified arithmetic |
| 4.9 | Peak directivity is below 0 dBi at 17 of 91 frequencies (1.0-1.4 and 3.3-4.4 GHz), which is physically impossible. Cause unknown. | `results/05_farfield_summary_stats.csv` | `05`; `00d` | Observation (unresolved) | Verified |
| 4.10 | The gain conclusion depends on the assumed ground plane, port and box, which the paper does not give. S11 shape tests (Section 2) cannot validate gain. | - | - | Inference | Inference |

## 5. Radiation-pattern shapes (Fig 9)

| # | Claim | Evidence | Script | Status | Confidence |
|---|---|---|---|---|---|
| 5.1 | The stored convention scan (352 correlations) is reproduced from the raw inputs to 1.7e-16. | `data/derived/fig9_convention_scan.csv` | `06_fig9_patterns.py` | Verified | Verified |
| 5.2 | No single angle convention matches the paper's pattern shapes. With a mismatched-frequency null (16 conventions, 6 other frequencies), matched is the best of 7 for only 2 of 14 curves (a-H 0.878, d-H 0.569); chance expectation is 2.0 (P(X >= 2) = 0.61). Below the null maximum in 12 of 14 curves, below the null median in 7 of 14. With only z-consistent conventions, matched is never best. | `results/06_fig9_null_test.csv` | `06`; `00d` | Inconclusive | Verified. Only 4 phi planes were exported; a 20 dB level gap makes shape agreement unlikely anyway. |
| 5.3 | The paper's E and H curves coincide at 90 and 270 deg in all 7 panels, which puts broadside at the top and bottom of the plots. | `data/paper_digitized/paper_fig9_patterns_raw_pixels.csv`; `data/derived/fig9_peak_levels_paper_vs_sim.csv` | earlier analysis, not scripted | Observation | Verified in earlier work, not re-run by the scripts here |

## 6. Geometry, digitization, solver

| # | Claim | Evidence | Script | Status | Confidence |
|---|---|---|---|---|---|
| 6.1 | The regenerated geometry matches the paper's Fig 1 and Fig 2 within about 0.05 mm (64 checks). The DXF generator passes 26 self-checks. The final-design DXF is identical to the one used in the simulations. | `docs/verification/geometry_overlay_report.txt`, `geometry_overlay_edges.csv` | `scripts/00c_geometry_overlay_check.py`, `geometry/make_geometry.py` | Verified | Verified. The vertices were read from the same figures, so this shows the reconstruction is faithful to the figures, not that the figures are the physical antenna. |
| 6.2 | The feed drawn in the paper's figures is about 1.70 mm wide (text: 1.8 mm). Whether this is real or a line-drawing effect cannot be separated. | `docs/verification/geometry_overlay_report.txt` (INFO lines) | `00c` | Observation | Verified measurement |
| 6.3 | The digitized curves (Figs 4, 5, 9, 11) lie on the drawn curves of the original figures (68 checks). Fig 9 radii are raw pixels; the dB scale is covered only by agreement with the paper's text (1.3 dB). | `docs/verification/` | `scripts/00b_overlay_check.py` | Verified | Verified |
| 6.4 | All solves met the adaptive criterion (Delta S below 0.02): final design 39,514 tetrahedra, 11 passes, Delta S 0.017235; Koch-only 28,736 tetrahedra, 15 passes (limit reached), Delta S 0.018746. | `hfss/hfss_setup_notes.md` | - | Observation | Typed from the solver by the author, not re-read from the project file |
| 6.5 | The Student licence limits the mesh to about 40,000 tetrahedra (40,666 solved, 74,904 failed), so refinement beyond the baseline was not possible. | `hfss/hfss_setup_notes.md` | - | Observation | Author's report |

## 7. Not replicated, on purpose

- **Fig 3** (photograph) and the **measured S11 curve of Fig 5**: simulation-only study.
- **Fig 6** (mesh refinement values 0.005 / 0.0025 / 0.00125 mm): the meaning of the values is not stated, so no equivalent test could be set up.
- **Fig 12** (surface currents): palette mapping gives medium-low confidence, so no numbers are published; the paper's excitation power is unknown.
- **Table 1** (comparison with other work): not a replication target.

## Limits of this document

- A passing check means files, README text and results agree with each other. It does not show that an interpretation is right.
- One solver (HFSS 2025 R2, Student), one assumed setup, one simulation per design. An independent solver (for example openEMS) has not been run.
- Items marked *Not checkable here* rely on the author's notes from the working sessions.
