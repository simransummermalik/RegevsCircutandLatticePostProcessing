# Poster graphics library

This folder is a large menu of poster-ready graphics for the finite Regev-style QFT study. You are **not** expected to use everything. Start with the contact sheets, choose a small set that tells one clean story, and veto the rest.

## The story in plain language

The project tests how much of the quantum Fourier transform (QFT) can be removed before a complete, finite Regev-style factoring pipeline stops recovering factors. A conservative mathematical certificate said that every tested approximate QFT was too risky and therefore approved **zero** omitted phase layers. In frozen held-out experiments on eight small semiprimes, omitting one layer met the preregistered non-inferiority rule in all six model-by-register-size settings, and omitting two layers met it in two finite-Gaussian settings. The largest passing configuration removed six logical controlled-phase gates and 12 **QFT-only** transpiled CX gates. These are finite simulation results, not a proof for cryptographic-scale Regev factoring and not an end-to-end hardware speedup.

## Open these first

1. `contact_sheet_recommended.png` — the shortest, strongest selection.
2. `contact_sheet_scientific.png` — all new scientific graphics in one place.
3. `contact_sheet_decorative.png` — artwork and decorative options only.
4. `BEST_FIRST.md` — suggested graphics for a simple poster.
5. `POSTER_COPY.md` — short text that can be pasted beside the graphics.
6. `asset_manifest.csv` — evidence status, source, and a safe caption for each asset.

## Folder guide

| Folder | What is inside |
|---|---|
| `01_HEADLINE_CARDS` | Large result summaries meant to be read from far away. |
| `02_BEGINNER_BACKGROUND` | Very simple explanations of Shor, Regev, the QFT, and lattices. |
| `03_PIPELINE` | The complete circuit-to-samples-to-lattice-to-factors workflow. |
| `04_CERTIFICATE_AND_FIBERS` | Why the worst-case certificate can be conservative. |
| `05_FROZEN_EXPERIMENT` | Held-out moduli, models, parameters, and frozen design. |
| `06_PRIMARY_RESULTS` | The main held-out comparisons and confidence intervals. |
| `07_RESOURCE_SAVINGS` | QFT-only controlled-phase, CX, and depth accounting. |
| `08_ROBUSTNESS_AND_DIAGNOSTICS` | Counterexamples, sensitivity checks, and diagnostic plots. |
| `09_LIMITATIONS_AND_CLAIMS` | What is proved, what is observed, and what remains unknown. |
| `10_DECORATIVE_VECTORS` | Code-drawn backgrounds, icons, and visual accents; not evidence. |
| `11_EXISTING_REPO_FIGURES` | Earlier repository figures, with warnings about superseded results. |
| `12_DECORATIVE_AI_CONCEPTS` | Built-in generated artwork, clearly labeled `DECORATIVE_NOT_DATA`. |
| `13_CONTACT_SHEETS` | Large browseable sheets for quickly vetoing options. |
| `13_POSTER_REFERENCE` | A preview and audit of the supplied poster PDF. |
| `14_SUPPLEMENTAL_VETO_OPTIONS` | Fifteen extra code-generated alternatives in PNG, SVG, and PDF. |
| `15_POSTER_LAYOUT_OPTIONS` | Simple 48-by-36-inch layout mockups. |
| `_SOURCE_DATA` | Frozen CSV/JSON inputs copied from the completed experiment. |
| `_SCRIPTS` | Reproducible generators for the charts and package. |

## Which file format should I use?

- Use **SVG** when PowerPoint, Illustrator, Inkscape, or your poster editor imports it correctly. It stays sharp at any size.
- Use **PDF** for LaTeX or professional print workflows.
- Use **PNG** for easy drag-and-drop. The scientific PNGs are exported at high resolution.
- AI-generated raster artwork is decorative. It must never be presented as a circuit diagram, dataset, or measured result.

## Claim guardrails

- Say “met the frozen 0.10 non-inferiority rule,” not “was identical” or “proved safe.”
- Say “up to 12 QFT-only transpiled CX gates,” not “12 gates from the full algorithm.”
- Call model B a **finite discrete-Gaussian model closer to Regev's state**, not the full asymptotic Regev algorithm.
- The unit of generalization is the modulus `N`; repeated simulations are not extra held-out inputs.
- The exact `N=15` equal-measurement-law example is deliberately favorable and explanatory, not representative evidence.
- The factors were not used for selection, relation classification, or tuning; they were used only for post-hoc validation.
- Do not call this dequantization, quantum advantage, a universal approximate-QFT theorem, or a hardware speedup.

## Reproducing the library

From the repository root, run:

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl .venv/bin/python "poster graphics/_SCRIPTS/generate_supplemental_veto_options.py"
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl .venv/bin/python "poster graphics/source/generate_poster_graphics.py"
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl .venv/bin/python "poster graphics/_SCRIPTS/package_poster_graphics.py"
```

If one of the optional generator scripts is absent, the already-exported graphics remain usable. The packaging script records hashes and validates every exported raster image.
