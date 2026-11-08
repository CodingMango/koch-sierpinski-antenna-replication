# HFSS setup notes (baseline: final design)

Labels: **CONFIRMED** = read from the project or the solver by the author. **AS BUILT** = follows the build steps used, not read back from the `.aedt`. **ASSUMED** = the paper does not state it.

Software: Ansys HFSS 2025 R2.4 (Student), 1 core, Windows. The paper used HFSS v15.

## Geometry (AS BUILT)

- Units: mm. Variables: `Sl` 60, `Sw` 40, `h` 0.8, `Fw` 1.8, `Fl` 18.5, `D1` 5, `D2` 13.88, `pad` 37.5, `Wp` 10, `Hp` 6.
- `D1` and `D2` are labels only: the imported patch is not parametric.
- Patch: `geometry/dxf/KochSierpinski_patch_v3_nofeed.dxf` (layers `PATCH` and `HOLES`), slots subtracted, feed united with the patch.
- Feed: rectangle from x = 10.9 mm to x = 30 mm, 1.8 mm wide, centred on y = 0 (see `geometry/feed_dimensions.csv`).
  In the v1 baseline the feed was imported from a DXF (static, not linked to `Fw`). The v2 rebuild has a parametric feed; v1 and v2 differ by 0.16 dB on average and their dips agree within 10 MHz.
- Substrate `FR4_paper`: relative permittivity 4.7, loss tangent 0.0197, thickness 0.8 mm, board 60 x 40 mm (values from the paper).

## Assumptions (the paper does not state them)

| Item | Setting used | Status |
|---|---|---|
| Ground plane | Full, 60 x 40 mm, Perfect E, at z = -h | ASSUMED |
| Conductors | Perfect E, zero thickness (patch and feed sheet at z = 0) | ASSUMED |
| Port | Wave port on the board edge at x = +30 mm, y = +-Wp/2, z from -h to -h + Hp; 1 mode; integration line (30, 0, -0.8) to (30, 0, 0); renormalised to 50 ohm | ASSUMED |
| Radiation box | Padding `pad` = 37.5 mm on all faces except +X (0); radiation boundary | ASSUMED |
| Excitation power | 1 W incident is suggested by the far-field data (total efficiency = radiated power / 1 W) | INFERENCE |

Sensitivity tests (feed width, box size, copper loss, port size, port type) did not explain the S11 depth differences at 2.11 and 8.48 GHz. Results are in `data/simulation/`.

## Solution setup (CONFIRMED)

- `Setup1`: multi-frequency adaptive meshing at 2.11, 5.78 and 9.56 GHz, maximum 15 passes, maximum Delta S 0.02.
- `Sweep1`: interpolating, 1 to 12 GHz, step 0.01 GHz (1101 points), maximum 250 solutions, error tolerance 0.5 %, save fields off.
- **Baseline solve (CONFIRMED, typed from the solver by the author on 6 Nov 2026): 39,514 tetrahedra, 11 passes, Delta S = 0.017235.** This is below the 0.02 target, so the adaptive solution met its criterion.

## Other solves (typed by the author from the solver; not re-read from the project file)

| Design | Tetrahedra | Passes | Final Delta S | Status |
|---|---|---|---|---|
| Iter0 | 18,408 | 10 | 0.016389 | converged |
| Iter1 | 18,121 | 11 | 0.018925 | converged |
| Iter2 | 21,781 | 11 | 0.017419 | converged |
| Iter3 (final design) | 39,514 | 11 | 0.017235 | converged |
| Koch-only (Fig 7 variant) | 28,736 | 15 (limit reached) | 0.018746 | converged on the last allowed pass |

## Setup-sensitivity variants (CONFIRMED: typed from the solver, 8 Nov 2026)

Each variant changes one item of the baseline; the lumped-port variant changes two (port type and +X padding). Results: `data/simulation/sim_s11_lumped_port.csv`, `sim_s11_copper_loss.csv`, `sim_s11_port_7x4mm.csv`, compared in `results/08_sensitivity_*.csv`.

| Variant | Change from the baseline | Tetrahedra | Passes | Final Delta S | Solve time (as typed) |
|---|---|---|---|---|---|
| Lumped port | Lumped port of size Fw x h = 1.8 x 0.8 mm, integration line from ground to feed, 50 ohm, renormalised to 50 ohm; radiation-box padding added on the +X side (37.5 mm; the baseline leaves +X at 0) | 36,938 | 10 | 0.016881 | 29:48 |
| Copper | Finite-conductivity conductors instead of Perfect E (zero thickness; conductivity value: ["default value"]) | 40,666 | 11 | 0.014311 | 25:37 |
| Wave port 7 x 4 mm | Wave port Wp x Hp = 7 x 4 mm instead of 10 x 6 mm | 17,531 | 6 | 0.018536 | 7:46 |

- The lumped port could not be solved with the +X side unpadded (error: only one conductor touches the lumped port). Padding that side removed the error.
- The lumped-port run was first solved with "Use Radiation Boundary on Ports" checked, then again with it unchecked. The two S11 exports are identical (largest difference 0.0 dB over 1101 points), so the option had no effect there. The unchecked run is the one stored.
- Adaptive setup and sweep as in the baseline (author confirmed for the lumped run; assumed for the other two).
- The copper run reached 40,666 tetrahedra, the largest mesh recorded under the Student cap.

## Far-field setups (CONFIRMED: read from `KochSierp_v3_farfield.aedt` by the author, 8 Nov 2026)

- **Infinite sphere `FF_sphere`:** phi 0-360 deg in 5 deg steps, theta 0-180 deg in 1 deg steps. Peak values are therefore sampled on a 5 x 1 deg grid; a narrow lobe between grid points could be slightly higher than reported.
- **`Gain_Sweep`:** Discrete sweep, 1-10 GHz, linear step 0.1 GHz (91 points), save fields on. Source of `data/simulation/sim_farfield_summary_1-10GHz.csv` (the working file name was `sweep3_summary.csv`; assumed to be this sweep). Solve: 39,514 tetrahedra, 11 passes, final Delta S 0.017235, total time 50:05. These equal the baseline S11 solve, so the sweep reuses the baseline adaptive mesh.
- **`Disc_Fields`:** Discrete sweep at single points 3.04, 3.06, 6.92, 6.94, 8.45, 8.48, 9.18, 9.23 GHz, save fields on. Source of `data/simulation/sim_gain_cuts_discrete_freqs.csv`. Mesh, passes and time were not recorded.
- **Cuts at 2.11, 5.78 and 9.56 GHz** (`sim_gain_cuts_adaptive_freqs.csv`) come from the last adaptive pass at the adaptive frequencies, not from a sweep.
- **Exported cut planes:** phi = 0, 90, 180, 270 deg, theta 0-180 deg in 1 deg steps. The four phi values lie on the 5 deg sphere grid, but only these four planes were exported, so the maximum over the exported cuts can be below the true peak.

## Limits

- Far-field results come from the setups above; the Student mesh cap applies to them as to the S11 solves.
- Far-field setups (`FF_sphere`, `Disc_Fields`, `Gain_Sweep` in `KochSierp_v3_farfield.aedt`) are **not documented here yet**. The far-field exports are `data/simulation/sim_farfield_summary_1-10GHz.csv` and the two `sim_gain_cuts_*.csv` files.
- Boundary and material settings in the table above come from the build instructions; only `Setup1` and `Sweep1` were read back from the project.
