# Poster graphics asset manifest

Quantitative graphics are generated from the frozen `results/qft_certificate_gap/` files. 
Conceptual and decorative assets are explicitly labeled. PNG is for slides/posters; SVG is editable vector artwork.

## H01_project_title

- Folder: `01_HEADLINE_CARDS`
- Evidence: **Verified framing; frozen experiment**
- Caption: Project-title lockup for the top of a poster.
- Source: `latex_short_paper/main.tex; results/qft_certificate_gap/configuration.json`

## H02_one_layer_result

- Folder: `01_HEADLINE_CARDS`
- Evidence: **Verified frozen empirical result**
- Caption: Primary one-layer finding; N is the unit of generalization.
- Source: `results/qft_certificate_gap/certificate_gap_rows.csv; paired_cluster_rows.csv`

## H03_two_layer_qualified

- Folder: `01_HEADLINE_CARDS`
- Evidence: **Verified frozen empirical result**
- Caption: Use beside the main result to prevent overgeneralization.
- Source: `results/qft_certificate_gap/certificate_gap_rows.csv`

## H04_qft_savings_hero

- Folder: `01_HEADLINE_CARDS`
- Evidence: **Verified compiled QFT-only resource result**
- Caption: Largest observed passing QFT-only saving, finite-Gaussian M=32.
- Source: `results/qft_certificate_gap/configuration_rows.csv`

## H05_evidence_snapshot

- Folder: `01_HEADLINE_CARDS`
- Evidence: **Verified frozen experiment inventory**
- Caption: Compact numeric overview.
- Source: `results/qft_certificate_gap/configuration.json`

## H06_claim_boundary

- Folder: `01_HEADLINE_CARDS`
- Evidence: **Verified scope statement**
- Caption: A prominent limitation card for responsible poster wording.
- Source: `latex_short_paper/main.tex; results/qft_certificate_gap/configuration.json`

## B01_shor_vs_regev

- Folder: `02_BEGINNER_BACKGROUND`
- Evidence: **Conceptual background**
- Caption: Beginner-friendly comparison; no speedup claim.
- Source: `Shor (1994/1997); Regev (2023/2025)`

## B02_regev_one_picture

- Folder: `02_BEGINNER_BACKGROUND`
- Evidence: **Conceptual schematic of implemented endpoint**
- Caption: Horizontal full-pipeline explainer.
- Source: `latex_short_paper/main.tex; regev_research/`

## B03_qft_frequency_lens

- Folder: `02_BEGINNER_BACKGROUND`
- Evidence: **Conceptual schematic**
- Caption: Beginner QFT intuition.
- Source: `Standard QFT interpretation`

## B04_exact_vs_truncated_qft

- Folder: `02_BEGINNER_BACKGROUND`
- Evidence: **Conceptual schematic**
- Caption: Explains what a QFT cutoff changes.
- Source: `regev_research/qft_certificate.py`

## B05_relation_to_factor

- Folder: `02_BEGINNER_BACKGROUND`
- Evidence: **Implemented mathematical endpoint**
- Caption: Beginner factor-extraction explainer.
- Source: `latex_short_paper/main.tex; regev_research/lattice.py`

## B06_roots_and_bases

- Folder: `02_BEGINNER_BACKGROUND`
- Evidence: **Verified implementation requirement**
- Caption: Root-provenance explainer.
- Source: `ROOT_PROVENANCE_RED_TEAM.md; latex_short_paper/main.tex`

## P01_full_endpoint

- Folder: `03_PIPELINE`
- Evidence: **Verified implemented workflow**
- Caption: Detailed pipeline strip.
- Source: `latex_short_paper/main.tex; regev_research/lattice.py`

## P02_quantum_classical_split

- Folder: `03_PIPELINE`
- Evidence: **Conceptual schematic of implemented pipeline**
- Caption: Useful center-panel bridge graphic.
- Source: `latex_short_paper/main.tex`

## P03_samples_to_lattice

- Folder: `03_PIPELINE`
- Evidence: **Verified implementation schematic**
- Caption: Sample-to-lattice construction.
- Source: `latex_short_paper/main.tex, Eq. (5)`

## P04_stored_root_endpoint

- Folder: `03_PIPELINE`
- Evidence: **Verified implementation schematic**
- Caption: Candidate classification and factor endpoint.
- Source: `latex_short_paper/main.tex; ROOT_PROVENANCE_RED_TEAM.md`

## P05_data_dependency

- Folder: `03_PIPELINE`
- Evidence: **Verified frozen analysis flow**
- Caption: Shows how inputs become the primary claim.
- Source: `results/qft_certificate_gap/configuration.json; paired_cluster_rows.csv`

## C01_certificate_chain

- Folder: `04_CERTIFICATE_AND_FIBERS`
- Evidence: **Verified proof audit schematic**
- Caption: Line-by-line certificate chain.
- Source: `QFT_CERTIFICATE_PROOF_AUDIT.md; latex_short_paper/main.tex`

## C02_worst_case_vs_prepared

- Folder: `04_CERTIFICATE_AND_FIBERS`
- Evidence: **Analytical mechanism**
- Caption: Explains the certification gap.
- Source: `QFT_CERTIFICATE_PROOF_AUDIT.md`

## C03_fiber_cancellation

- Folder: `04_CERTIFICATE_AND_FIBERS`
- Evidence: **Analytical mechanism**
- Caption: Hero mechanism diagram.
- Source: `latex_short_paper/main.tex, Eq. (4)`

## C04_n15_counterexample

- Folder: `04_CERTIFICATE_AND_FIBERS`
- Evidence: **Verified controlled example**
- Caption: Explicit equal-law counterexample.
- Source: `results/qft_certificate_gap/controlled_examples.json`

## C05_certificate_barrier

- Folder: `04_CERTIFICATE_AND_FIBERS`
- Evidence: **Verified proof-audit consequence**
- Caption: Visualizes M < 4πdm/Δ with frozen d,m,Δ.
- Source: `latex_short_paper/main.tex, Proposition 1`

## C06_three_questions

- Folder: `04_CERTIFICATE_AND_FIBERS`
- Evidence: **Verified explanatory synthesis**
- Caption: Separates three common claims.
- Source: `QFT_CERTIFICATE_PROOF_AUDIT.md; certificate_gap_rows.csv`

## E01_frozen_protocol

- Folder: `05_FROZEN_EXPERIMENT`
- Evidence: **Verified frozen design**
- Caption: Protocol overview.
- Source: `results/qft_certificate_gap/configuration.json`

## E02_heldout_moduli

- Folder: `05_FROZEN_EXPERIMENT`
- Evidence: **Verified frozen design**
- Caption: Complete held-out N list.
- Source: `results/qft_certificate_gap/configuration.json`

## E03_design_grid

- Folder: `05_FROZEN_EXPERIMENT`
- Evidence: **Verified frozen design**
- Caption: Six primary model–M cells.
- Source: `results/qft_certificate_gap/configuration.json`

## E04_unit_generalization

- Folder: `05_FROZEN_EXPERIMENT`
- Evidence: **Verified statistical design**
- Caption: Prevents pseudoreplication in poster interpretation.
- Source: `results/qft_certificate_gap/paired_cluster_rows.csv`

## E05_noninferiority_ruler

- Folder: `05_FROZEN_EXPERIMENT`
- Evidence: **Verified frozen decision rule**
- Caption: Explains the 0.10 margin.
- Source: `results/qft_certificate_gap/configuration.json`

## E06_freeze_seed

- Folder: `05_FROZEN_EXPERIMENT`
- Evidence: **Verified reproducibility metadata**
- Caption: Seed/freeze card.
- Source: `results/qft_certificate_gap/configuration.json`

## R01_primary_heatmap

- Folder: `06_PRIMARY_RESULTS`
- Evidence: **Verified frozen empirical result**
- Caption: Primary result heatmap.
- Source: `results/qft_certificate_gap/certificate_gap_rows.csv`

## R02_all_paired_differences

- Folder: `06_PRIMARY_RESULTS`
- Evidence: **Verified frozen empirical result**
- Caption: Forest plot of all non-exact cutoffs.
- Source: `results/qft_certificate_gap/paired_cluster_rows.csv`

## R03_recovery_curve_model_A

- Folder: `06_PRIMARY_RESULTS`
- Evidence: **Verified frozen empirical result**
- Caption: Recovery vs omitted layers for uniform hard-box.
- Source: `results/qft_certificate_gap/per_N_rows.csv`

## R04_recovery_curve_model_B

- Folder: `06_PRIMARY_RESULTS`
- Evidence: **Verified frozen empirical result**
- Caption: Recovery vs omitted layers for finite discrete-Gaussian.
- Source: `results/qft_certificate_gap/per_N_rows.csv`

## R05_per_N_omit1_M32

- Folder: `06_PRIMARY_RESULTS`
- Evidence: **Verified frozen empirical result**
- Caption: Exact vs one-layer omission for every held-out N at M=32.
- Source: `results/qft_certificate_gap/per_N_rows.csv`

## R06_margin_sensitivity

- Folder: `06_PRIMARY_RESULTS`
- Evidence: **Verified post-hoc sensitivity analysis**
- Caption: How the allowed margin changes the largest passing cutoff.
- Source: `results/qft_certificate_gap/margin_summary_rows.csv`

## R07_certificate_gap_summary

- Folder: `06_PRIMARY_RESULTS`
- Evidence: **Verified frozen result**
- Caption: Direct side-by-side primary conclusion.
- Source: `results/qft_certificate_gap/certificate_gap_rows.csv`

## G01_M32_resource_bars

- Folder: `07_RESOURCE_SAVINGS`
- Evidence: **Verified compiled resource result**
- Caption: Exact, one-layer, and two-layer QFT resources.
- Source: `results/qft_certificate_gap/configuration_rows.csv`

## G02_one_layer_savings

- Folder: `07_RESOURCE_SAVINGS`
- Evidence: **Verified QFT-only resource + endpoint result**
- Caption: Universal tested one-layer resource card.
- Source: `certificate_gap_rows.csv; configuration_rows.csv`

## G03_two_layer_savings

- Folder: `07_RESOURCE_SAVINGS`
- Evidence: **Verified QFT-only resource + endpoint result**
- Caption: Qualified maximum-saving card.
- Source: `certificate_gap_rows.csv; configuration_rows.csv`

## G04_qft_layer_map

- Folder: `07_RESOURCE_SAVINGS`
- Evidence: **Conceptual schematic with verified M=32 context**
- Caption: Shows which interaction distances truncation targets.
- Source: `regev_research/circuits.py; configuration_rows.csv`

## G05_cost_vs_acceptance

- Folder: `07_RESOURCE_SAVINGS`
- Evidence: **Verified descriptive synthesis**
- Caption: Shows resource/endpoint tradeoff without implying speedup.
- Source: `certificate_gap_rows.csv; configuration_rows.csv`

## D01_leave_one_N_out

- Folder: `08_ROBUSTNESS_AND_DIAGNOSTICS`
- Evidence: **Verified sensitivity analysis**
- Caption: One-layer decision under every leave-one-N-out dataset.
- Source: `results/qft_certificate_gap/leave_one_N_out_rows.csv`

## D02_proof_slack

- Folder: `08_ROBUSTNESS_AND_DIAGNOSTICS`
- Evidence: **Verified diagnostic analysis**
- Caption: Median looseness at each certificate step.
- Source: `results/qft_certificate_gap/proof_slack_rows.csv`

## D03_distribution_tv

- Folder: `08_ROBUSTNESS_AND_DIAGNOSTICS`
- Evidence: **Verified finite diagnostic**
- Caption: TV change in the exact finite measured law.
- Source: `results/qft_certificate_gap/configuration_rows.csv`

## D04_implementation_correction

- Folder: `08_ROBUSTNESS_AND_DIAGNOSTICS`
- Evidence: **Verified pre-holdout implementation correction**
- Caption: Transparent software-audit card.
- Source: `QFT_CERTIFICATE_GAP_ADVERSARIAL_AUDIT.md; latex_short_paper/main.tex`

## D05_near_tight_gate_step

- Folder: `08_ROBUSTNESS_AND_DIAGNOSTICS`
- Evidence: **Verified controlled adversarial example**
- Caption: Shows why the proof cannot be dismissed wholesale.
- Source: `results/qft_certificate_gap/controlled_examples.json`

## L01_scope_grid

- Folder: `09_LIMITATIONS_AND_CLAIMS`
- Evidence: **Verified scope statement**
- Caption: Tested vs unestablished claims.
- Source: `latex_short_paper/main.tex`

## L02_no_speedup_claim

- Folder: `09_LIMITATIONS_AND_CLAIMS`
- Evidence: **Verified claim limitation**
- Caption: Poster guardrail against end-to-end speedup language.
- Source: `latex_short_paper/main.tex`

## L03_model_B_limit

- Folder: `09_LIMITATIONS_AND_CLAIMS`
- Evidence: **Verified model limitation**
- Caption: Precise finite-Gaussian boundary.
- Source: `latex_short_paper/main.tex`

## L04_three_claims

- Folder: `09_LIMITATIONS_AND_CLAIMS`
- Evidence: **Verified evidence taxonomy**
- Caption: Ready-to-use conclusion graphic.
- Source: `latex_short_paper/main.tex`

## L05_why_it_matters

- Folder: `09_LIMITATIONS_AND_CLAIMS`
- Evidence: **Interpretive implication supported by mechanism + experiment**
- Caption: Closing significance card; framed as future direction.
- Source: `QFT_CERTIFICATE_PROOF_AUDIT.md; certificate_gap_rows.csv`

## V01_lattice_field

- Folder: `10_DECORATIVE_VECTORS`
- Evidence: **Decorative schematic; not data**
- Caption: Square poster background or accent.
- Source: `Conceptual`

## V02_fourier_rings

- Folder: `10_DECORATIVE_VECTORS`
- Evidence: **Decorative schematic; not data**
- Caption: Square visual accent.
- Source: `Conceptual`

## V03_fiber_streams

- Folder: `10_DECORATIVE_VECTORS`
- Evidence: **Decorative schematic; not data**
- Caption: Wide visual divider.
- Source: `Conceptual`

## BACKGROUND_earlier_entropy_relation_recovery

- Folder: `11_EXISTING_REPO_FIGURES`
- Evidence: **Existing repository figure; inspect README evidence labels**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/11_EXISTING_REPO_FIGURES/BACKGROUND_earlier_entropy_relation_recovery.png`

## BACKGROUND_standard_parseval_identity

- Folder: `11_EXISTING_REPO_FIGURES`
- Evidence: **Existing repository figure; inspect README evidence labels**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/11_EXISTING_REPO_FIGURES/BACKGROUND_standard_parseval_identity.png`

## BACKGROUND_superseded_cutoff_scaling

- Folder: `11_EXISTING_REPO_FIGURES`
- Evidence: **Existing repository figure; inspect README evidence labels**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/11_EXISTING_REPO_FIGURES/BACKGROUND_superseded_cutoff_scaling.png`

## BACKGROUND_superseded_endpoint_success_vs_cutoff

- Folder: `11_EXISTING_REPO_FIGURES`
- Evidence: **Existing repository figure; inspect README evidence labels**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/11_EXISTING_REPO_FIGURES/BACKGROUND_superseded_endpoint_success_vs_cutoff.png`

## BACKGROUND_superseded_qft_tv_vs_cutoff

- Folder: `11_EXISTING_REPO_FIGURES`
- Evidence: **Existing repository figure; inspect README evidence labels**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/11_EXISTING_REPO_FIGURES/BACKGROUND_superseded_qft_tv_vs_cutoff.png`

## BACKGROUND_superseded_recovery_transition

- Folder: `11_EXISTING_REPO_FIGURES`
- Evidence: **Existing repository figure; inspect README evidence labels**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/11_EXISTING_REPO_FIGURES/BACKGROUND_superseded_recovery_transition.png`

## NEGATIVE_earlier_diversity_vs_lattice_success

- Folder: `11_EXISTING_REPO_FIGURES`
- Evidence: **Existing repository figure; inspect README evidence labels**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/11_EXISTING_REPO_FIGURES/NEGATIVE_earlier_diversity_vs_lattice_success.png`

## NEGATIVE_earlier_model_ablation

- Folder: `11_EXISTING_REPO_FIGURES`
- Evidence: **Existing repository figure; inspect README evidence labels**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/11_EXISTING_REPO_FIGURES/NEGATIVE_earlier_model_ablation.png`

## PRIMARY_current_certificate_vs_recovery

- Folder: `11_EXISTING_REPO_FIGURES`
- Evidence: **Existing repository figure; inspect README evidence labels**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/11_EXISTING_REPO_FIGURES/PRIMARY_current_certificate_vs_recovery.png`

## D01_quantum_to_lattice_hero_dark_DECORATIVE_NOT_DATA

- Folder: `12_DECORATIVE_AI_CONCEPTS`
- Evidence: **Decorative AI concept; NOT DATA**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/12_DECORATIVE_AI_CONCEPTS/D01_quantum_to_lattice_hero_dark_DECORATIVE_NOT_DATA.png`

## D01a_dark_header_4x1_DECORATIVE_NOT_DATA

- Folder: `12_DECORATIVE_AI_CONCEPTS`
- Evidence: **Decorative AI concept; NOT DATA**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/12_DECORATIVE_AI_CONCEPTS/D01a_dark_header_4x1_DECORATIVE_NOT_DATA.png`

## D01b_dark_panel_3x2_DECORATIVE_NOT_DATA

- Folder: `12_DECORATIVE_AI_CONCEPTS`
- Evidence: **Decorative AI concept; NOT DATA**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/12_DECORATIVE_AI_CONCEPTS/D01b_dark_panel_3x2_DECORATIVE_NOT_DATA.png`

## D01c_dark_lattice_square_DECORATIVE_NOT_DATA

- Folder: `12_DECORATIVE_AI_CONCEPTS`
- Evidence: **Decorative AI concept; NOT DATA**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/12_DECORATIVE_AI_CONCEPTS/D01c_dark_lattice_square_DECORATIVE_NOT_DATA.png`

## D02_certificate_fiber_lattice_hero_light_DECORATIVE_NOT_DATA

- Folder: `12_DECORATIVE_AI_CONCEPTS`
- Evidence: **Decorative AI concept; NOT DATA**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/12_DECORATIVE_AI_CONCEPTS/D02_certificate_fiber_lattice_hero_light_DECORATIVE_NOT_DATA.png`

## D02a_light_header_4x1_DECORATIVE_NOT_DATA

- Folder: `12_DECORATIVE_AI_CONCEPTS`
- Evidence: **Decorative AI concept; NOT DATA**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/12_DECORATIVE_AI_CONCEPTS/D02a_light_header_4x1_DECORATIVE_NOT_DATA.png`

## D02b_light_panel_3x2_DECORATIVE_NOT_DATA

- Folder: `12_DECORATIVE_AI_CONCEPTS`
- Evidence: **Decorative AI concept; NOT DATA**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/12_DECORATIVE_AI_CONCEPTS/D02b_light_panel_3x2_DECORATIVE_NOT_DATA.png`

## D02c_light_lattice_square_DECORATIVE_NOT_DATA

- Folder: `12_DECORATIVE_AI_CONCEPTS`
- Evidence: **Decorative AI concept; NOT DATA**
- Caption: Pre-existing asset included for poster selection.
- Source: `poster graphics/12_DECORATIVE_AI_CONCEPTS/D02c_light_lattice_square_DECORATIVE_NOT_DATA.png`
