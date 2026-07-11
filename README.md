# Regev-style quantum factoring: audit, lattice post-processing, and red-team revision

This repository audits the Qiskit implementation of **Regev's quantum
factoring algorithm** ([arXiv:2308.06572](https://arxiv.org/abs/2308.06572)).
It found real implementation bugs, built a from-scratch exact lattice (LLL)
post-processing pipeline, ran a frozen/pre-registered experiment comparing
base-selection strategies across three sampling models, and then red-teamed
its own claims — downgrading or retracting anything that turned out to be a
routine identity or a circular endpoint rather than a genuine result. A
second, larger body of code (`quotient*.py`, `rv_filter.py`) implements a
follow-on "quotient deflation" study, pre-registered in
[`FROZEN_QUOTIENT_PROTOCOL.md`](FROZEN_QUOTIENT_PROTOCOL.md); its held-out
run has now completed (`results/quotient_study/`) and its own pre-registered
falsification criterion was met — see "Quotient-study result" below.

**Read this first:** [`REDTEAM_REVISION.md`](REDTEAM_REVISION.md) is the
authoritative, current result. `RESEARCH_REPORT.md` is the original,
pre-red-team analysis and is kept only as a superseded audit record — its
novelty and "improvement" claims were walked back. If the two disagree,
`REDTEAM_REVISION.md` wins.

## What this is *not*

- Not a working factoring algorithm faster than existing ones.
- Not a proof about Regev's algorithm in general — the empirical result
  (Claim 2 in `REDTEAM_REVISION.md`) is scoped to a uniform hard-box
  simulation on 3-dimensional, toy-sized inputs.
- Not publication-ready. The repo says this explicitly and tracks *why*.

## The math in one page

Regev's algorithm factors `N` by choosing `d` coprime roots
`b_1, ..., b_d`, building circuit bases `a_i = b_i^2 mod N`, and querying a
quantum oracle `h_A(z) = prod a_i^z_i mod N`. Fourier samples from that
oracle let you reconstruct short vectors in the relation lattice

```
L = ker(h_A) = { z in Z^d : prod a_i^z_i == 1 (mod N) }
```

A relation `z` is only useful for factoring if it also lands outside the
root-dependent sublattice

```
L0 = { z in L : prod b_i^z_i in {+1, -1} (mod N) }
```

If `z in L \ L0`, then `gcd(prod(b_i^z_i) - 1, N)` and
`gcd(prod(b_i^z_i) + 1, N)` split `N`. **Membership in `L` depends only on
the squared bases `A`; membership in `L0` depends on which square roots `B`
were actually chosen.** Losing track of that distinction is the recurring
bug class in this codebase (see `ROOT_PROVENANCE_RED_TEAM.md`) — not new
mathematics, but an easy way to silently corrupt an implementation.

## Repository layout

```
regev_research/     Library code (math, circuits, experiments) — see below
scripts/             CLI entry points that run experiments / build notebooks
tests/               84 pytest tests, one file per library module
results/             Frozen experiment outputs (raw distributions, CSVs, JSON)
figures/             Plots generated from results/
external/            Pinned clone of the audited notebook's third-party dependency
*.ipynb              Executable notebooks (see "Notebooks" below)
*.md                 Research documents (see "Documents" below)
```

## `regev_research/` — the library, file by file

### `core.py` — foundational math and the original (now-superseded) experiment primitives

- `RootedBase` / `RootedBaseFamily`: frozen dataclasses that pair each root
  `b_i` with its circuit base `a_i`. The constructor raises unless
  `base == root**2 mod N`, `gcd(root, N) == 1`, and both are canonical
  residues — this is the single fix that closes the root-provenance bug
  class across the whole codebase.
- `notebook_parameters`, `notebook_squared_prime_bases`,
  `deduplicated_squared_prime_bases`: reproduce the audited notebook's own
  (leaky) base generators, explicitly returning any factor discovered while
  scanning candidate primes as a labeled `setup_factor_leaks` field rather
  than silently using it.
- `canonical_vectors` / `bounded_relations` / `bounded_product_diversity` /
  `pairwise_power_collisions` / `base_diagnostics`: exhaustive small-box
  relation search and diagnostics used by the original (pre-red-team)
  selector and audits.
- `select_dependency_aware_bases`: the original greedy "maximize bounded
  product diversity" base selector. This is the intervention the red team
  later showed can *remove* the very relations a lattice endpoint needs
  (see Claim 2 in `REDTEAM_REVISION.md`).
- `classify_square_relation` / `extract_factor_from_relation`: the central
  `L`/`L0` classifier — checks `z in L` against the bases, then evaluates
  the *stored roots'* product and returns a GCD factor only if it's
  `L \ L0`. Never computes a modular square root itself.
- `exact_uniform_fourier_distribution`: computes the notebook's exact
  output probability law by FFT of a triangular relation-collision kernel,
  without simulating any quantum gates.
- `distribution_metrics` / `sample_metrics` / `fourier_relation_diagnostic`
  / `relation_recovery_trial`: entropy/correlation/covariance diagnostics
  and the original bounded-search relation-recovery endpoint — later shown
  to be circular with the selector's own scoring box (§7 of
  `REDTEAM_REVISION.md`), so it survives only as a diagnostic.
- `logical_resources`: qubit/gate-count bookkeeping for a given `(N, d, M)`.

### `circuits.py` — the actual Qiskit circuit

`build_arbitrary_base_circuit` builds a real circuit for an arbitrary root
family, reusing the modular-exponentiation gate from the pinned external
dependency (`external/regev-quantum-algorithm`). `compiled_resources`
transpiles it and reports qubit count, logical/compiled depth, and gate
counts — used to check that different base-selection methods don't win by
secretly using more circuit resources (see the `resource_experiments`
results in `results/summary/compiled_resources.json`).

### `dual.py` — factor-blind oracle-side sample generator

- `exact_relation_lattice_hnf`: builds a column-Hermite-normal-form basis of
  `L` using only a breadth-first Cayley traversal of the image of `h_A` and
  modular multiplication — no factorization, no group order. Its
  determinant is cross-checked against the independently enumerated image
  size (first isomorphism theorem) as a correctness assertion.
- `synthetic_noisy_dual_samples`: draws points uniformly from `L*/Z^d` using
  that HNF basis, adds bounded random noise, and quantizes to a power-of-two
  grid sized so total error stays under Regev's theorem noise bound. Every
  batch verifies `theorem_sufficient_inequality` before use. This produces
  **sampling Model C** ("theorem-compliant noisy dual") used throughout the
  frozen experiments — the oracle/HNF basis itself is discarded before
  samples are handed to recovery.

### `lattice.py` — the only place real LLL happens

- `build_augmented_lattice`: exactly clears denominators of Regev's
  rational augmented lattice `[[I_d, 0], [SW, SI_m]]` into an integer row
  basis SymPy can reduce, given either an explicit `scale` or `noise_bound`.
- `lll_reduce_augmented_lattice`: SymPy integer LLL, with the returned
  unimodular transform matrix verified to actually reconstruct the reduced
  basis before it's trusted.
- `claim_5_1_prefix`: implements Regev's Claim 5.1 stopping rule exactly —
  keeps the LLL-reduced-row prefix up to (but not including) the first row
  whose Gram–Schmidt norm exceeds `2^(k/2) * T`, using exact `Fraction`
  arithmetic scaled by the integer clearing factor so no float comparison
  is involved.
- `regev_lattice_postprocess`: the **primary factoring endpoint**. Takes a
  `RootedBaseFamily` plus raw samples, builds the lattice, LLL-reduces it,
  takes the Claim 5.1 prefix, verifies every candidate row is actually in
  `L`, classifies it `L0` vs. `L \ L0` using the *paired* roots, and returns
  a factor pair only from the prefix (the full-basis scan is reported
  separately and explicitly marked non-primary/diagnostic).

### `redteam.py` — exact sampling laws and the six frozen base-selection ablations

- `exact_weighted_fourier_distribution` / `exact_regev_gaussian_distribution`:
  a generalization of `core.py`'s uniform-only Fourier law to **any**
  one-dimensional amplitude weighting, evaluated exactly via finite
  autocorrelation + FFT (not gate simulation). Plugging in uniform
  amplitudes reproduces the notebook's "Model A"; plugging in
  `regev_gaussian_amplitudes` (the finite truncated `rho_R`) gives the
  exact finite discrete-Gaussian "Model B".
- `weighted_chi_square_from_kernel`: the Parseval-identity cross-check used
  to validate every exact distribution to ~1e-12 (see `parseval_absolute_error`
  columns in the results).
- `select_rooted_ablation_family`: implements the **six frozen methods**
  compared in the headline experiment — `residue_deduplication_only`,
  `short_relation_rejection_only`, `subgroup_overlap_only`,
  `complete_selector` (lexicographic: relation count, then subgroup
  overlap, then diversity), `random_coprime_roots`, and
  `regev_small_prime_roots`. All six return the same `RootedBaseFamily`
  type, so downstream code can't tell them apart except by their choices.

### `redteam_experiments.py` — the authoritative frozen experiment

Runs the full 24-`N` × 6-method × 3-model × 32-trial design described in
`REDTEAM_REVISION.md` §10–12: `HELDOUT_INSTANCES` (24 semiprimes frozen
before execution, factors recorded only for post-hoc validation),
deterministic per-cell seeding (`_seed`), exact Model A/B distribution
computation, real `regev_lattice_postprocess` factor attempts for every
trial, Model C generation via `dual.py`, per-`N` aggregation
(`aggregate_to_N`), and `model_statistics` — Spearman correlation between
base-family diversity and factor-success rate, with **within-`N` cluster
permutation p-values** and **`N`-cluster bootstrap confidence intervals**
(never a naive pooled p-value, since trials within one `N` aren't
independent). `main()` writes everything under `results/redteam/` and the
two `figures/redteam_*.png` plots.

### `experiments.py` — the original (superseded) experiment suite

Runs the earlier 12-instance × 5-method × 200-batch design behind
`RESEARCH_REPORT.md`: `notebook_squared_primes`, `squared_primes_deduplicated`,
`random_coprime_residues` (sampling-only — has no factor endpoint since raw
residues aren't retained squares), `random_coprime_squares`, and
`dependency_aware`. Also contains `synthetic_validation` (the exact `N=437`
root-twist counterexample plus planted duplicate/power/multivariate/
progressive relation adversaries), `indistinguishability_audit`,
`ablation_experiments`, `correlation_analysis` (the within-instance
permutation + cluster-bootstrap machinery that `redteam_experiments.py`
later reused), and `resource_experiments`. Writes `results/raw/`,
`results/summary/`, and `figures/entropy_vs_relation_recovery.png` /
`figures/parseval_identity.png`.

### `quotient.py` — exact group quotients by verified `L0` subgroups

`build_l0_quotient` takes a set of directions, verifies every one is
genuinely in `L0` (raises otherwise), and builds `Z^d / U` via row-Hermite
normal form — giving exact coset reduction (`reduce_with_witness`), lifting,
and group operations (`add`, `negate`, `scalar_multiply`) on the quotient.
Smith normal form is computed separately for the abstract torsion
decomposition (`Z^(d-r) ⊕ ⊕ Z/s_iZ`) but is explicitly *never* used to
enlarge `U` — `QUOTIENT_THEORY_AND_LITERATURE.md` §4–5 proves that silently
saturating or Euclidean-projecting can destroy the exact factor-bearing
class, with a worked `N=15` counterexample. `classify_quotient_candidate`
and `factor_yielding_quotient_gap` (an *observed-candidate*, not exact-CVP,
norm-gap statistic) round out the module.

### `quotient_metrics.py` — factor-blind, post-hoc `L`/`L0` diagnostics

`exact_l0_hnf` builds a full-rank basis of `L0` itself via a Cayley
traversal of the *signed* root image `<b_1,...,b_d>/{±1}`, with its
determinant checked against the independently enumerated image size — no
factorization or order supplied. `bounded_base_lambda_metrics` and
`bounded_sample_augmented_quotient_gap` compute bounded-box relative minima
(`λ(L)`, `λ(L0)`, `λ(L\L0)`) under the plain Euclidean norm and under
Regev's exact augmented sample norm respectively, entirely in
`fractions.Fraction` arithmetic. Every docstring in this module repeats:
these are oracle-side audit statistics, never a selector objective or a
substitute for actual sample-to-lattice recovery.

### `quotient_recovery.py` — cost-audited recovery strategies (the largest module, 1735 lines)

Builds several recovery strategies on top of `lattice.py`'s LLL output, all
sharing a `RecoveryBudget`/`RecoveryResources` accounting system (nodes
visited, modular checks, classifications, a deterministic memory-footprint
*estimate*, runtime):

- **Intervention A** (`short_combination_recovery`): bounded coefficient
  search over reduced rows, ordered by exact embedding norm.
- **Intervention B** (`exact_quotient_deduplicated_recovery`): the same
  search, but candidates are de-duplicated by their exact Hermite-reduced
  coset key from `quotient.py` instead of raw identity.
- **Intervention C** (`adaptive_l0_suppression_recovery`): the same search,
  but suppresses any candidate in the exact *integer* span of already-verified
  `L0` directions (deliberately never the *rational* span — see the
  `N=15` counterexample this guards against).
- **Exact augmented basis-row deflation** (`exact_augmented_basis_deflation_recovery`):
  a stronger variant that actually deletes verified-`L0` rows from the
  reduced basis and re-LLLs the remaining rectangular basis, composing
  transforms back to the original embedding — the "chosen section" approach
  whose geometry-dependence is proven in `QUOTIENT_THEORY_AND_LITERATURE.md` §9.2.
- **`sequential_ldar_recovery`**: the full "Lattice / Deflation / Adaptive
  Resampling" loop combining A+B+C with genuine new-sample acquisition from
  a separate fresh pool (never bootstrapped from existing rows), under a
  frozen per-sample-count round cap. Has a `root_blind` ablation mode that
  never reads root metadata, classifies `L0`, or extracts a factor.
- **Baselines**: `standard_lll_enumeration_baseline`,
  `random_extra_samples_baseline`, and `bkz_or_deterministic_surrogate_baseline`
  (uses `fpylll` BKZ only if a transform can be independently verified;
  otherwise falls back to a strong-LLL-plus-block-search surrogate that is
  explicitly labeled "NOT BKZ" everywhere it appears, including in its own
  `strategy` string).
- `matched_cost_recovery_suite` runs all six arms under one shared node
  budget so comparisons aren't skewed by unequal search effort.

This is the infrastructure that `quotient_study.py` (below) drives for the
now-completed held-out run.

### `quotient_experiments.py` — frozen configuration only (no execution loop)

`QuotientExperimentFreeze` is a frozen dataclass with extensive
`__post_init__` self-consistency checks (D/R interval, sample-count
schedule, budget-matching rules, etc.) pinning every parameter — `D=64`,
`R=16`, `S=13`, sample counts 7–11, master seed, LDAR round caps, BKZ block
size, RV pool/target sizes, target recovery probability 0.8. Defines four
sampling models (A: uniform hard box, B: finite discrete Gaussian,
C: theorem-consistent noisy dual, D: an explicitly-labeled non-hardware
"circuit-derived readout corruption surrogate" — random bit flips and
whole-shot corruption layered on Model A, never claimed to be gate-level or
device noise). `DEVELOPMENT_SEMIPRIMES` (25, reused from earlier work) and
`HELDOUT_SEMIPRIMES` (20 new products of primes 79–107) are disjoint and
frozen under version tag `quotient-recovery-freeze-v2-final-before-holdout`.
`frozen_manifest()` returns this configuration as a dict and always sets
`"heldout_executed": False` — it's a pre-run manifest function, called before
`quotient_study.py` does the actual run described next.

### `quotient_study.py` — the holdout execution orchestrator (now executed)

Defines the **nine primary comparison methods** for the quotient study
(standard Regev LLL, common exact-norm enumeration, verified-BKZ
enumeration, exact augmented-row deflation, complete sequential LDAR,
adaptive-sampling-without-deflation, root-blind post-hoc search,
quotient-gap-scoring-only, random genuine extra samples) plus an optional
RV-structured-comparator arm. Uses **atomic writes** everywhere (write to a
`.tmp` file, then `rename`) so a crash mid-run never leaves a half-written
result file, and `study_configuration()` records the SHA-256 of every
source file plus installed dependency versions for reproducibility.
`write_factor_manifest` keeps known `(p, q)` factors in a separate file from
the trial path — trial functions receive only `N`. `tests/test_quotient_study.py`
exercises its pieces (batch generation, a toy LDAR cell, RV-comparator pool
accounting, nested-prefix determinism, bootstrap aggregation) independently
of the real holdout.

`run_heldout_quotient_study` has since been run to completion — see
"Quotient-study result" below and `results/quotient_study/completion.json`
(`"heldout_executed": true`).

### `rv_filter.py` — a named, honest comparator for Ragavan–Vaikuntanathan filtering

Implements the *lattice structure* of Ragavan–Vaikuntanathan's Algorithm 6.1
corrupt-sample filter (index set `E`, exact integer-cleared row LLL,
recovering coefficients `(beta, a)` from the first reduced row) as
`rv_structured_finite_filter`. Deliberately named an "RV-structured finite
comparator," not "RV filtering": `rv_theorem_status` computes the
alpha/gamma combinatorial inequality from finite pool/dimension/target
sizes and explicitly reports which of RV's asymptotic hypotheses were *not*
certified (scale hypothesis, well-spread corruption model, special recovery
inequality) — the frozen stress cell (`d=3, m=11, target=7`) actually fails
that inequality, and the code says so rather than hiding it.
`rv_filter_then_short_combination_recovery` composes the filter with
`quotient_recovery.py`'s Intervention A.

### `__init__.py` — public API surface

Re-exports the `core`, `lattice`, and `quotient` public functions (root/base
types, `L`/`L0` classification, lattice post-processing, quotient
construction). `redteam.py`, `dual.py`, `experiments.py`,
`redteam_experiments.py`, `quotient_recovery.py`, `quotient_experiments.py`,
`quotient_study.py`, and `rv_filter.py` are used via direct submodule
import — check each file's own docstring for its entry points.

## `scripts/` — CLI entry points

| Script | Purpose |
|---|---|
| `run_research.py` | Runs the superseded experiment suite (`regev_research.experiments.main`) → `results/raw/`, `results/summary/`. |
| `run_redteam.py` | Runs the authoritative frozen experiment (`regev_research.redteam_experiments.main`) → `results/redteam/`. **Run this one.** |
| `run_quotient_study.py` | Executes the frozen quotient holdout (`regev_research.quotient_study.run_heldout_quotient_study`) → `results/quotient_study/`. Already run; takes on the order of 40 minutes and writes one ~40 MB checkpoint per held-out `N` as it goes. |
| `build_revised_notebook.py` | Builds the notebook cell-by-cell via `nbformat` and writes it to **both** `..._redteam_revision.ipynb` and `..._research_revision.ipynb` — these two files are byte-identical (confirmed by hash); the second name exists only for backward-compatible linking. |
| `execute_revised_notebook.py` | Executes the generated notebook via `nbclient` with `allow_errors=False` (fails loud on the first cell error). Requires the `regev-research` Jupyter kernel to be installed first (see Setup below). |

## `tests/` — 84 pytest tests, one file per library module

Every module above has a matching `tests/test_*.py`. Notably:
`test_circuits.py` exhaustively checks the controlled-multiplier and
modular-exponentiation gate contracts on their valid domain *and* shows what
happens just outside it (dirty ancillas for `y >= N`); `test_core.py`
reproduces the exact Qiskit-simulated `N=15`/`N=21` notebook probabilities
and the `N=437` root-twist regression case; `test_lattice.py` runs a real
end-to-end dual-sample → LLL → `L \ L0` → factor recovery; `test_notebook_static.py`
statically documents bugs in the original notebook (cell 16 measures too few
qubits, mixed QFT conventions, unpinned Colab-specific setup);
`test_quotient_recovery.py` and `test_rv_filter.py` verify the cost-audited
recovery strategies don't silently use rational-span suppression, do
genuinely acquire new samples, and correctly report "NOT BKZ" when no
verified `fpylll` transform is available. Run everything with:

```bash
.venv/bin/python -m pytest -q
```

which currently reports **84 passed**.

## Notebooks

- `RegevImplementationAndTestingBuilding_work-3.ipynb` — the original
  notebook under audit: 18 code cells, **no markdown cells** (confirmed by
  inspection — this is itself one of the audit findings in
  `RESEARCH_REPORT.md` §2.4).
- `RegevImplementationAndTestingBuilding_redteam_revision.ipynb` and
  `RegevImplementationAndTestingBuilding_research_revision.ipynb` — **the
  same file, written twice** by `build_revised_notebook.py` (byte-identical,
  verified by hash). It's the current, authoritative executable companion
  to `REDTEAM_REVISION.md`.

Notebooks are generated from Python, not hand-edited — change
`scripts/build_revised_notebook.py` and re-run it instead of editing the
`.ipynb` directly.

## `results/` and `figures/`

- `results/raw/` — 40 compressed `N*_distribution.npz` files (one per
  `(N, method)` cell of the superseded experiment) plus `batch_metrics.csv`
  (200 batches × 128 shots per cell) and `artifact_hashes.json`.
- `results/summary/` — aggregated statistics from the superseded experiment:
  `baseline_exact.csv`, `baseline_batches.csv`, `correlations.json`,
  `synthetic_validation.json`, `indistinguishability_audit.json`,
  `ablations.json`, `compiled_resources.json`, `configuration.json`.
- `results/redteam/` — the current, authoritative experiment's full output:
  `families.csv` (every selected root family + selector diagnostics),
  `exact_models.csv` (exact A/B distribution metrics and Parseval checks),
  `trials.csv` (all 13,824 raw trial rows, ~2 MB), `n_level.csv` (per-`N`
  aggregates), `model_statistics.json` (the cluster-aware inference behind
  the headline numbers), `configuration.json`, and `artifact_hashes.json`
  (SHA-256 of every file in the directory).
- `figures/` — `parseval_identity.png` and `entropy_vs_relation_recovery.png`
  (from the superseded experiment), `redteam_diversity_vs_lattice_success.png`
  and `redteam_model_ablation.png` (from the current one, per-model scatter
  and bar charts with bootstrap error bars).
- `results/quotient_study/` — the completed quotient-deflation holdout:
  `checkpoints/N*.json` (20 files, one per held-out semiprime, ~40 MB each —
  every raw trial row for that `N` across all methods/models/sample-counts/
  replicates, written incrementally as the run progressed), `trial_rows.csv`
  (117,760 rows — the same data flattened and concatenated across all 20
  `N`), `resource_rows.csv` (per-trial cost accounting), `per_N_rows.csv`
  (3,680 rows — factor-success rates and resource means aggregated per
  `(N, method, model, sample_count)`), `paired_N_comparisons.json` (200
  cluster-bootstrap paired comparisons of every method against the
  `common_exact_norm_LLL_bounded_enumeration` reference), `configuration.json`
  / `factor_manifest.json` (written before the run started), and
  `completion.json` (written only after every output was replaced —
  `"heldout_executed": true`, SHA-256 of every output file, and
  `"posthoc_factor_manifest_validation": "passed for every returned pair"`).

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-research.txt
git clone --depth 1 https://github.com/Wlitkopa/regev-quantum-algorithm.git external/regev-quantum-algorithm
git -C external/regev-quantum-algorithm checkout a18f75d414485086db9b257407e0bd01f8a8f81c
```

`requirements-research.txt` pins: `qiskit`/`qiskit-aer` (the circuit under
audit), `numpy`/`scipy` (exact-law FFT evaluation and statistics),
`sympy` (exact integer LLL, Hermite/Smith normal form — the actual math
engine behind every "exact" claim in this repo), `pandas`/`matplotlib`
(result tables and figures), `nbformat`/`nbclient`/`ipykernel` (notebook
generation and execution), `pytest`, and `fpylll`/`cysignals` (optional
verified BKZ backend for `quotient_recovery.py`).

`external/regev-quantum-algorithm` is the third-party notebook's dependency
(the Häner modular-exponentiation gate); it's pinned to an exact commit
because the original notebook cloned it at mutable `HEAD`.

## Reproducing the current (red-team) result

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl .venv/bin/python scripts/run_redteam.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_revised_notebook.py
```

To execute the generated notebook locally:

```bash
.venv/bin/python -m ipykernel install --prefix .jupyter --name regev-research --display-name "Regev Research"
JUPYTER_DATA_DIR="$PWD/.jupyter/share/jupyter" \
IPYTHONDIR=/tmp/ipython MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl \
.venv/bin/python scripts/execute_revised_notebook.py
```

## Headline result (see `REDTEAM_REVISION.md` for full statistics and caveats)

Across the frozen 24 held-out semiprimes, three sampling models, and six
base-selection strategies:

- Under the notebook's **uniform hard-box** model and under an **exact finite
  discrete-Gaussian** model, bounded-product base diversity is *negatively*
  associated with the probability that the real augmented-lattice/LLL
  pipeline returns a factor (Spearman ρ ≈ −0.62 and −0.68 respectively,
  both significant within-`N`).
- That association **disappears** (ρ ≈ −0.06, not significant) once samples
  are drawn from a synthetic model that actually satisfies Regev's
  theorem-required noisy-dual precision bound.
- Conclusion: whatever is driving the diversity/success relationship is a
  finite-precision or resource-constrained artifact of models A/B, not a
  property of Regev's algorithm in the regime the theorem covers. No claim
  is made about Regev's full algorithm.

## Quotient-study result (see `results/quotient_study/`)

The frozen hypothesis in `FROZEN_QUOTIENT_PROTOCOL.md` was: does **complete
LDAR** (Lattice-reduce → Deflate verified-`L0` directions → Adaptively
resample, repeated) recover `L \ L0` more often than the matched
no-deflation baseline (`common_exact_norm_LLL_bounded_enumeration`), at the
same bounded-search budget? The protocol's own stated falsification
condition — "it does not outperform the matched no-deflation endpoint
across held-out `N`" — **was met**, i.e. the hypothesis is falsified by its
own pre-registered test, based on all 20 held-out `N`, 4 sampling models,
5 sample-count budgets, and 32 replicates per cell (117,760 trials total):

- At the full 11-sample budget, mean factor-success rate across the 20
  held-out `N`, by method and model:

  | method | A: hard box | B: finite Gaussian | C: noisy dual | D: corruption surrogate |
  |---|---:|---:|---:|---:|
  | standard Regev LLL (Claim 5.1 only) | 0.181 | 0.130 | 0.950 | 0.161 |
  | common exact-norm bounded enumeration (reference) | 0.273 | 0.216 | 0.950 | 0.247 |
  | verified BKZ + same enumeration | 0.300 | 0.233 | 0.950 | 0.247 |
  | exact augmented-row deflation | 0.181 | 0.130 | 0.950 | 0.161 |
  | **complete sequential LDAR** | **0.255** | **0.188** | 0.950 | **0.211** |
  | adaptive sampling, no deflation | 0.273 | 0.216 | 0.950 | 0.247 |
  | root-blind post-hoc search | 0.273 | 0.216 | 0.950 | 0.247 |
  | quotient-gap scoring only | 0.273 | 0.216 | 0.950 | 0.247 |
  | random genuine extra samples | 0.277 | 0.222 | 0.950 | 0.225 |
  | RV-structured comparator (not theorem-backed) | 0.153 | 0.134 | 0.950 | 0.133 |

- Complete LDAR is **not better** than the reference — it's measurably
  *worse* under models A, B, and D, with `N`-cluster bootstrap confidence
  intervals that exclude zero (A: mean diff −0.019, 95% CI [−0.030, −0.008],
  0 wins/8 losses/12 ties across the 20 `N`; B: −0.028, CI [−0.055, −0.006];
  D: −0.036, CI [−0.059, −0.016]). Under model C both are already
  saturated near 0.95, so there's no room for either to show an advantage
  (0 wins/0 losses/20 ties).
- The secondary target — reaching 80% recovery probability with fewer
  circuit executions — was essentially unreachable within the 7–11 sample
  budget for any method under models A, B, and D (177/200, 180/200, and
  180/200 method×`N` cells respectively never hit the 0.8 target and are
  censored at "more than 11"). Under model C, 190/200 cells did reach it.
  Complete LDAR needed exactly as many samples as the reference wherever
  both were measurable (paired mean difference 0.000 in all four models).
- Several ablations (adaptive-sampling-without-deflation, exact
  augmented-row deflation, quotient-gap-scoring-only, root-blind search)
  produced numerically identical success rates to either the reference or
  the plain standard-LLL baseline at this budget — deflation and quotient-gap
  scoring didn't change which relations were found, only how they were
  labeled or ordered.
- The RV-structured comparator was the weakest method everywhere, consistent
  with its own code explicitly flagging that the frozen stress cell fails
  RV's asymptotic recovery inequality (see `rv_filter.py` above) — it isn't
  claimed to be theorem-backed, and the data bears that out.
- Every returned factor pair passed post-hoc validation against the known
  `(p, q)` for its `N` (`completion.json`), so the "worse" outcome isn't a
  correctness bug — deflation and adaptive resampling, as implemented and at
  this bounded-search budget, simply didn't help.
