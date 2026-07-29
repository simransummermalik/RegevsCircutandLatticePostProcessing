# Experiment-generated results graphs

This folder contains the **nine unique native PNG graphs produced by this
repository's experiment code**, plus three poster-readable plots aggregated
directly from frozen result tables. Poster illustrations, LaTeX previews,
duplicate copies, AI-generated graphics, and figures imported from external
repositories are excluded.

## Four-image poster set

Use these together in the Results section:

- `certification_vs_recovery.png` — main Regev held-out result.
- `regev_qft_gate_savings.png` — QFT-only CX savings at the largest passing
  truncation.
- `shor_noise_vs_shots.png` — worst held-out Shor recovery change under
  selected strong simulated QFT errors.
- `rv_filter_comparison.png` — finite RV-style comparator against ordinary
  bounded lattice recovery.

The last three are generated from existing frozen CSV/JSON outputs by:

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl \
  .venv/bin/python scripts/build_poster_results_graphs.py
```

## Current main result

- `certification_vs_recovery.png` — current held-out QFT certificate-gap
  result. This is the strongest graph to use for the main poster result.

## Earlier or supporting results

- `redteam_diversity_vs_lattice_success.png` — negative base-selection
  red-team result; background evidence, not the final contribution.
- `redteam_model_ablation.png` — red-team comparison across sampling models;
  background evidence, not the final contribution.
- `entropy_vs_relation_recovery.png` — early exploratory diversity analysis;
  do not present as the final result.
- `parseval_identity.png` — illustration of a standard Parseval identity;
  this is theoretical background, not an empirical or novel result.

## Superseded QFT studies

- `cutoff_scaling.png` — earlier QFT precision-scaling analysis.
- `recovery_transition.png` — earlier finite endpoint transition analysis.
- `endpoint_success_vs_cutoff.png` — earlier recovery-versus-QFT-cutoff plot.
- `qft_tv_vs_cutoff.png` — earlier distribution-distance-versus-cutoff plot.

These four plots were useful development evidence, but the frozen
`qft-certificate-gap-v1` holdout supersedes them as the main result.

## Derived-plot source boundaries

- The Regev savings plot joins
  `results/qft_certificate_gap/certificate_gap_rows.csv` to
  `configuration_rows.csv`.
- The Shor plot uses the frozen robustness and gate-noise result tables under
  `shor_to_regev_study/`.
- The RV plot uses `results/quotient_study/per_N_rows.csv` and its frozen
  whole-\(N\) paired intervals.

These are new visualizations of existing experiment outputs, not new
experiments or invented results.
