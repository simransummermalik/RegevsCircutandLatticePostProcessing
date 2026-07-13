# Frozen protocol: QFT certificate-gap holdout

Freeze version: `qft-certificate-gap-v1`, written before executing the new
holdout described here.

## Primary question

Does a distance-truncated product QFT preserve the present augmented-lattice
and LLL factor endpoint in configurations that the original worst-case
operator/hybrid theorem refuses to certify?

## Frozen configurations

* selected roots: `(2,3)`, retained with squared circuit bases;
* dimension: `d=2`;
* Fourier moduli: `M in {8,16,32}`;
* sample count: `m=7`;
* loss budget: `Delta=0.05`;
* Gaussian radius for model B: `R=4`;
* models: A exact uniform hard box and B exact finite Gaussian;
* cutoffs: every `t in {0,...,log2(M)-1}`;
* endpoint: exact cleared augmented lattice, SymPy LLL, Claim-5.1 prefix,
  stored-root `L`/`L0` classification, and gcd factor extraction;
* endpoint scale `S=4`, relation norm bound `T=4`, LLL delta `3/4`;
* 64 coupled replicates per `(N,M,model,cutoff)`;
* master seed: `2026071301`;
* no BKZ, enumeration, quotient deflation, adaptive samples, or known factors.

## Held-out inputs

The following semiprimes were not used in the previous QFT endpoint design:

```text
55=5*11, 65=5*13, 85=5*17, 95=5*19,
115=5*23, 119=7*17, 133=7*19, 161=7*23.
```

All factors exceed the selected roots. Factorizations are stored only for
post-hoc validation and are not passed to state construction, certificates,
or recovery.

## Claims and endpoints

For every configuration record:

* original worst-case certificate status and loss bound;
* exact distribution-TV hybrid certificate;
* product-Hellinger certificate;
* state-specific fiber trace-distance certificate where feasible;
* exact-QFT and approximate-QFT factor recovery;
* probability of recovering at least one verified `L\L0` candidate;
* exact distribution TV, Hellinger affinity, and feasible matrix distances;
* logical controlled-phase savings and QFT-only transpiled two-qubit savings;
* LLL runtime and 95% intervals.

The primary generalization unit is `N`. Repeated trials are used only to
estimate the per-`N` success probability. Final non-inferiority intervals
resample whole `N` clusters.

## Empirical-safe definition

For each `(M,model,cutoff)`, couple approximate and exact replicates by seed.
Let `D_N` be approximate minus exact success probability for one `N`. A cutoff
is **empirically safe** only when both factor recovery and verified-`L\L0`
recovery have a 95% whole-`N` cluster-bootstrap lower bound at least `-0.10`.

This ten-percentage-point non-inferiority margin is frozen before the holdout.
It is an empirical criterion, not an information-theoretic certificate.

## Certification-gap statistic

Let omitted layers be `s=(q-1)-t`; exact QFT has `s=0`. Define

```text
certified_layers = largest s approved by a stated certificate,
empirical_layers = largest s satisfying the frozen empirical-safe rule,
G_layers = empirical_layers - certified_layers.
```

This additive definition remains meaningful when the original certificate
approves no truncation and avoids division by zero.

## Falsification and outcome rules

* Outcome A requires a factor-blind sharper certificate with nonzero gate
  savings and held-out empirical safety.
* Outcome B requires a near-tight adversarial example and no meaningful safe
  uncertified truncation across the holdout.
* Outcome C requires at least one held-out non-exact cutoff that is empirically
  safe while the original certificate rejects it, plus a proof identifying
  fiber-specific cancellation/state restriction as the missing information.
* Outcome D requires a stable two-regime threshold supported across held-out
  `N` values.
* Otherwise report Outcome E and state the unresolved inequality.

No endpoint, margin, modulus, seed, or input may be changed after execution.

