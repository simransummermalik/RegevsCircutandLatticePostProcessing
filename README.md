# Regev-style notebook mandatory red-team revision

The authoritative result is [REDTEAM_REVISION.md](REDTEAM_REVISION.md), with an
executed notebook at
[RegevImplementationAndTestingBuilding_redteam_revision.ipynb](RegevImplementationAndTestingBuilding_redteam_revision.ipynb).
The earlier `RESEARCH_REPORT.md` is retained only as a superseded audit record.

This is not publication-ready. The revision establishes a root/base metadata
correction and a reproducible finite-parameter empirical result; it does not
establish a claim about Regev's full factoring algorithm.

Key artifacts:

- `regev_research/core.py` — immutable selected-root/circuit-base pairs and
  strict (L/L_0) classification;
- `regev_research/lattice.py` — exact augmented integer lattice, LLL,
  Claim 5.1 prefix, and stored-root factor extraction;
- `regev_research/redteam.py` — exact hard-box/Gaussian laws and six rooted-base
  ablations;
- `regev_research/dual.py` — factor-blind relation-lattice oracle and
  theorem-compliant noisy-dual sample generator;
- `regev_research/redteam_experiments.py` — frozen 24-(N), three-model
  confirmatory suite and (N)-level inference;
- `results/redteam/` — complete configuration, selected families, exact model
  metrics, 13,824 trial rows, (N)-level aggregates, statistics, and hashes;
- `tests/` — 39 tests covering the original audit, rooted metadata, exact
  Gaussian evaluation, HNF generation, noisy-dual bounds, integer LLL, and
  factor extraction.

Reproduce the red-team results:

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl .venv/bin/python scripts/run_redteam.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_revised_notebook.py
```

Execute the generated notebook locally:

```bash
JUPYTER_DATA_DIR="$PWD/.jupyter/share/jupyter" \
IPYTHONDIR=/tmp/ipython MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl \
.venv/bin/python scripts/execute_revised_notebook.py
```
