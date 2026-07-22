# Reproducible graphics source

Run from the repository root:

```bash
MPLCONFIGDIR=/tmp/mpl MPLBACKEND=Agg .venv/bin/python "poster graphics/source/generate_poster_graphics.py"
```

The generator reads only the frozen files under `results/qft_certificate_gap/`,
rebuilds the PNG and SVG assets in folders `01` through `10`, writes an
evidence/source manifest, and makes category and all-assets contact sheets.
It also indexes the PNGs in `11_EXISTING_REPO_FIGURES` and
`12_DECORATIVE_AI_CONCEPTS` without changing their README or prompt files.

Important interpretation rules:

- `Delta = 0.05` is the original certificate's event-loss budget.
- `0.10` is the frozen empirical non-inferiority margin.
- All gate savings are QFT-only, not complete-circuit savings.
- Model B is an exact *finite* discrete-Gaussian simulation, not an
  experimental validation of Regev's asymptotic theorem regime.
- The eight held-out moduli—not 12,288 repeated trial rows—are the primary
  units of generalization.
