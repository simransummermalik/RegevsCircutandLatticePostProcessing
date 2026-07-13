# Standalone Shor-to-Regev notebook study

Open **`Shor_to_Regev_Demonstration.ipynb`** first. It is an executed notebook
that walks through the standard Shor implementation, frozen Shor QFT holdout,
cross-decoder Outcome A, decoder-boundary negative result, and empirical
predictor.

Everything added for this task lives in this folder. The parent repository's
frozen Regev protocol, results, lattice endpoint, stored roots, and reports are
read-only inputs.

## Folder map

| Path | Purpose |
|---|---|
| `Shor_to_Regev_Demonstration.ipynb` | Beginner-facing executed demonstration |
| `shor.py` | Standard circuit, exact finite simulation, continued fractions, verified factors |
| `task_aware_precision.py` | Common schema, paired inference, empirical predictor |
| `run_shor_experiments.py` | Development success/failure demonstrations |
| `run_shor_qft_robustness.py` | Frozen eight-instance Shor holdout |
| `run_cross_algorithm_precision_study.py` | Read-only Regev comparison and predictor evaluation |
| `SHOR_QFT_ROBUSTNESS_PROTOCOL.md` | Protocol frozen before result generation |
| `SHOR_TO_REGEV_MAIN_RESULT.md` | Unified paper-ready result |
| `results/` | Raw rows, aggregates, hashes, and completion manifests |
| `test_shor.py`, `test_task_aware_precision.py` | Tests collected by the repository-wide pytest run |

## Reproduce

From the parent repository root:

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python shor_to_regev_study/run_shor_experiments.py
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python shor_to_regev_study/run_shor_qft_robustness.py
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python shor_to_regev_study/run_cross_algorithm_precision_study.py
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python -m pytest -q
```

