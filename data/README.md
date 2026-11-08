# Data README

All frequencies are in GHz. Gains are in dBi unless a column says otherwise.

## Read this first

- **`paper_digitized/`** holds values read off figures of Azzouz et al., Fractal Fract. 2026, 10, 47 (CC BY 4.0). They are not the authors' raw data. Uncertainty is about +-1 dB, larger at narrow notches and sharp peaks. The curves were checked by overlaying the points on the original figures.
- **`simulation/`** holds Ansys HFSS 2025 R2 (Student) exports. The paper does not state the ground plane, port or radiation box, so these were **assumed**: full ground plane, Perfect-E conductors, 50 ohm wave port, 37.5 mm radiation box. No uncertainty estimate exists. The Student licence limits the mesh (about 40,000 tetrahedra), and far-field data above about 9 GHz look noisier (inference).
- **`derived/`** holds tables computed from the two groups above.

## paper_digitized/

### paper_s11_final_simulated_digitized.csv
Paper's simulated S11 of the final design (Fig 5, red curve). 949 rows, 0.51-9.99 GHz, 0.01 GHz step.
- `Freq_GHz`: frequency (GHz)
- `S11_dB_paper_simulated`: S11 (dB)

### paper_fig4_s11_iter0-3_digitized.csv
Paper's Fig 4, four iterations. 4508 rows. Spacing is not verified to be uniform. Dotted and dashed curves have gaps.
- `Iter`: Iter0, Iter1, Iter2 or Iter3
- `Freq_GHz`: frequency (GHz)
- `S11_dB_paper_Fig4`: S11 (dB)

Iter0 starts at 2.07 GHz because its dotted curve is hidden under later curves (inference). The other iterations start at about 0.52 GHz.

### paper_fig11_gain_vs_freq_digitized.csv
Paper's Fig 11, gain vs frequency. 939 rows, 0.57-9.95 GHz, 0.01 GHz step.
- `Freq_GHz`: frequency (GHz)
- `Gain_dBi_paper_Fig11`: gain (dBi). Values are stroke-centre values. The drawn stroke is about 0.7 dB thick.

### paper_fig9_patterns_raw_pixels.csv
Paper's Fig 9 radiation patterns, **uncalibrated**. 1008 rows (7 panels x 2 curves x 72 angles); 29 have no radius.
- `panel`: a-g, in the order of the paper's seven resonances
- `f`: panel frequency (GHz)
- `curve`: E (E-plane legend) or H (H-plane legend)
- `ang`: angle **on the printed plot** in degrees (0 = right, counter-clockwise), 5 degree steps. This is not necessarily the antenna angle theta; the paper does not define it.
- `r_px`: radius in image pixels, **not dB**. The dB scale was calibrated separately, to about +-1 dB.
- `nclusters`: number of curve-coloured pixel groups found on that ray (0 means no radius; 2 or 3 means the curve crossed the ray more than once)

## simulation/

### sim_s11_lumped_port.csv
Final design with a lumped port instead of the wave port (radiation-box padding also added on the +X side). 1101 rows, 1-12 GHz, 0.01 GHz step.
- `Freq [GHz]`, `dB(S(Port1,Port1)) []` (S11 in dB; the header differs from the other S11 files)

### sim_s11_copper_loss.csv
Final design with finite-conductivity conductors (no thickness; HFSS default copper, bulk conductivity 58,000,000 S/m) instead of Perfect E. 1101 rows, 1-12 GHz, 0.01 GHz step.
- `Freq [GHz]`, `dB(S(1,1)) []`

### sim_s11_port_7x4mm.csv
Final design with a 7 x 4 mm wave port instead of 10 x 6 mm. 1101 rows, 1-12 GHz, 0.01 GHz step.
- `Freq [GHz]`, `dB(S(1,1)) []`

### sim_s11_vswr_final_design.csv
Final design. 1101 rows, 1-12 GHz, 0.01 GHz step.
- `Freq [GHz]`, `dB(S(1,1)) []` (dB), `VSWR(1) []`
- `re(Zo(1)) []`, `im(Zo(1)) []`: the **port reference impedance** (always 50 and 0). This is not the antenna input impedance.

### sim_s11_iter0-3_and_koch_only.csv
5505 rows = 5 designs x 1101 points, 1-12 GHz.
- `Design`: Iter0, Iter1, Iter2, Iter3_hybrid_baseline, Fig7_KochOnly
- `Freq_GHz`, `S11_dB`

`Iter3_hybrid_baseline` duplicates `sim_s11_vswr_final_design.csv` (maximum difference 0.0005 dB). It is not a separate solve.

### sim_s11_feed_width_sweep.csv
3303 rows = 3 feed widths x 1101 points, 1-12 GHz.
- `Fw [mm]`: 1.5, 1.73 or 1.8
- `Freq [GHz]`, `dB(S(1,1)) []`

### sim_s11_radiation_box_pad20mm.csv
One case, 1101 rows, 1-12 GHz.
- `Fw [mm]`: 1.8; `pad [mm]`: 20 (radiation-box padding instead of 37.5 mm)
- `Freq [GHz]`, `dB(S(1,1)) []`

### sim_farfield_summary_1-10GHz.csv
91 rows, 1-10 GHz, 0.1 GHz step. Peak values over the sphere.
- `f`: frequency (GHz)
- `Peak Directivity`, `Peak Gain`, `Peak Realized Gain`, `Radiation Efficiency`, `Total Efficiency`: **linear, not dB**
- `Front to Back Ratio`: dimensionless, apparently linear (not verified)
- `Pacc_W`, `Prad_W`: accepted and radiated power (W)
- `G_dBi`, `D_dBi`, `RG_dBi`: peak gain, directivity and realized gain (dBi)
- `g0`: broadside gain (dBi). **Inferred**, not confirmed from the HFSS setup.
- `s11`: S11 (dB)

Checks: G = D x radiation efficiency (within 0.0002 dB); radiation efficiency = Prad/Pacc; total efficiency is about Prad/(1 W), which suggests 1 W incident power (inference).
**Known problem:** peak directivity is below 0 dBi at 17 of 91 frequencies (1.0-1.4 GHz and 3.3-4.4 GHz). That is physically impossible and is unresolved.

### sim_gain_cuts_adaptive_freqs.csv
Gain cuts at 2.11, 5.78 and 9.56 GHz. 2172 rows = 3 x 4 x 181.
- `Freq [GHz]`, `Phi [deg]` (0, 90, 180, 270), `Theta [deg]` (0-180, 1 degree step), `dB(GainTotal) []` (dBi, IEEE gain)

### sim_gain_cuts_discrete_freqs.csv
Same layout at 3.04, 3.06, 6.92, 6.94, 8.45, 8.48, 9.18 and 9.23 GHz. 5792 rows = 8 x 4 x 181. Only four phi planes were exported, so the true peak can lie outside them (by 0.4-2.5 dB at 9.18, 9.23 and 9.56 GHz).

## derived/

### fig9_peak_levels_paper_vs_sim.csv
7 rows, one per Fig 9 panel. Levels in dBi.
- `panel`, `f_GHz`
- `paper_Fig9_E_peak`, `paper_Fig9_H_peak`: peak of each calibrated Fig 9 curve
- `paper_Fig9_center`, `label_fit_resid`: calibration quantities (**inferred meaning; panels d and e show exactly 0.0 for the centre value**)
- `paper_text_gain`: gain printed in the paper's text
- `paper_Fig11`: Fig 11 value at that frequency
- `ours_max_4cuts`: our maximum over the four exported phi cuts (not the true peak)
- `paper_cutmax`: larger of the E and H peaks
- `diff_ours_vs_Fig9`: ours_max_4cuts minus paper_cutmax
- `diff_Fig9_vs_text`: paper_cutmax minus paper_text_gain

### fig9_convention_scan.csv
Test of which angle convention would make our simulated gain cuts match the paper's Fig 9 curve shapes. 352 rows = 22 (panel, frequency, curve) groups x 16 conventions.
- `panel`: a-g (Fig 9 panel)
- `f`: frequency of the **simulated** cut used in the comparison (GHz). Panels b, d, e and f appear twice: at the paper's frequency (3.06, 6.94, 8.48, 9.23) and at our paired resonance (3.04, 6.92, 8.45, 9.18). Panels a, c and g appear once.
- `curve`: E or H (paper curve)
- `cut`: simulated plane, `XZ` (phi 0/180) or `YZ` (phi 90/270)
- `s`: sign of the angle direction, 1 or -1
- `off`: angle offset in degrees, 0, 90, 180 or 270
- `pearson`, `spearman`: shape correlation between the paper curve and the simulated cut

Summary (computed from this file, paper frequencies only): for the eight conventions that put the antenna axis at the top and bottom of the plot (`off` = 90 or 270), the mean Pearson correlation over the 14 curves is between -0.105 and -0.001 per convention. The best of the 16 conventions per curve reaches 0.22-0.88, but the winning convention differs from curve to curve, and no mismatched-frequency null is stored here, so these maxima are not evidence for any convention. The exact formula mapping `s` and `off` to the plotted angle is implemented in `scripts/06_fig9_patterns.py`, which reproduces this file.