# Frozen QFT-precision scaling protocol

Version: `qft-precision-scaling-v1`, frozen 2026-07-12.

## Primary question

For the distance-truncated product QFT, does the finite-shot operator/hybrid
certificate permit any non-exact cutoff while preserving a declared recovery
loss budget, and how does that decision scale with `d`, `M`, and `m`?

## Frozen choices

* cutoffs: every integer `t in {0,...,log2(M)-1}`;
* `M in {8,16,32,64,128}`;
* `d in {2,3,4,5}`;
* `m in {4,8,12,24}`;
* loss budgets: `Delta=0.05` (primary), with `0.10` and `0.20` retained as
  sensitivity rows;
* frozen roots for endpoint feasibility: `(2,3,4,5,7)` whenever coprime to
  the selected small modulus; no roots or factors enter analytic scaling;
* development endpoint inputs: `N=35,77,143`, where the first three roots
  are units;
* held-out endpoint inputs: `N=2279,2419,2491,2501,2537,2623,2747,2773,
  2867,2881,2911,2993,3053,3127,3139,3149,3233,3337,3431,3551,3599,3763,
  3977,3953`; all are frozen semiprimes with factors above 37;
* seeds: analytic rows use no random draw; exact-fiber endpoint seeds are
  `2026071107+20000+N+replicate`; RV comparator seeds use
  `2026071107+40000+replicate`;
* lattice settings: seven samples for small endpoint tests, `S=4`, `T=4`,
  SymPy LLL with `delta=3/4`, no BKZ and no enumeration;
* primary endpoint: factor recovery probability at matched sample count;
* secondary endpoints: verified `L\L0` candidates, controlled-phase count,
  total two-qubit QFT count, Qiskit depth where feasible, LLL runtime, and
  95% Wilson intervals over paired replicates;
* generalization unit: `N`/parameter configuration, never an individual shot.
* uncertainty: 95% Wilson intervals per configuration and 5,000-resample
  cluster bootstrap intervals over paired `N` values.

No cutoff, noise level, stopping rule, or selector parameter is changed after
the scaling rows are generated.  Factorizations are used only for post-hoc
validation of returned gcd pairs.

## Falsification rules

The adaptive-approximate-QFT claim is rejected if it selects exact QFT on the
primary budget, loses recovery on held-out inputs, saves no decomposed gates,
or requires additional samples.  The surviving claim is then the negative
scaling result stated in `QFT_PRECISION_SCALING_REPORT.md`.
