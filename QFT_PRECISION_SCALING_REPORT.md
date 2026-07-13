# Outcome E: a finite-shot scaling limit for non-exact Regev QFTs

> Superseded as the final contribution by `QFT_CERTIFICATE_GAP_REPORT.md`.
> The analytic no-certificate law remains valid, but the final corrected
> holdout shows empirically safe non-exact cutoffs that this worst-case theorem
> rejects. Approximate-QFT tables in this stage were regenerated after fixing
> the custom decomposition's reversed layer order.

## Title and abstract

**Title.** *A finite-shot precision barrier for distance-truncated
multidimensional QFTs in Regev-style lattice factoring*

**Abstract.** We study whether removing small controlled phases from the
product QFT can preserve the samples needed by Regev's augmented-lattice
post-processing.  For a `q=log2(M)` register and distance cutoff `t`, the
omitted roots-of-unity phase mass is
`eta(q,t)=pi sum_{r>t}(q-r)2^{-r}`.  A direct operator telescoping argument and
a finite-shot hybrid argument give the factor-blind certificate
`m*min(1,2*d*eta)/Delta <= 1` for an allowed recovery-probability loss
`Delta`.  The first non-exact cutoff has `eta=2pi/M`, yielding the exact
certificate limitation `M >= 4pi*d*m/Delta`.  The frozen grid covers
`d=2..5`, `M=8..128`, `m=4,8,12,24`, and three loss budgets; it selects exact
QFT throughout the primary five-percent range.  Exact matrix checks pass for
`M<=16`, and exact fiber/lattice experiments at `d=2,M<=32` show that
truncation can lower factor recovery in both hard-box and finite-Gaussian
states.  The result is a rigorous negative statement about this finite-shot
certificate, not a universal lower bound on every approximate QFT and not an
asymptotic Gaussian-state theorem.

## One contribution

The contribution is the scaling law

```
M < 4*pi*d*m/Delta
  => the stated worst-case finite-shot QFT-to-recovery certificate
     cannot certify any non-exact distance cutoff.
```

It explains why the earlier `d=3,M=8,m=12` observation was not merely a
three-qubit artifact: the same certificate barrier strengthens with dimension
and sample count.  It also exposes why the current adaptive rule is not a
resource-saving algorithm at realistic finite budgets.  The exact derivation
is in `QFT_PRECISION_THEORY.md`; all grid rows are in
`results/qft_precision_scaling/precision_rows.csv`.

## Mathematical definitions

The selected roots `b_i` are stored permanently, and circuit bases are
`a_i=b_i^2 mod N`.  The relation lattices are

```
L  = {z in Z^d : product_i a_i^(z_i) = 1 mod N},
L0 = {z in L : product_i b_i^(z_i) = +/-1 mod N}.
```

The exact product-QFT character is
`chi_k(x)=exp(-2pi i <k,x>/M)`.  For an arithmetic fiber
`F_y={x:product_i a_i^(x_i)=y}`, the measurement law is

```
P_A(k) = M^(-2d) sum_y |sum_{x in F_y} chi_k(x)|^2.
```

For the hard-box state, `U(k)=M^(-d)` and

```
r = x-x' mod M,
K_A(r) = sum_{x,x'} 1[h_A(x)=h_A(x')] 1[x-x'=r mod M].
```

Grouping the character expansion by `r`, subtracting the `K_A(0)=M^d`
uniform background, and applying finite-group character orthogonality gives

```
chi^2(P_A || U) = M^(-2d) sum_{r != 0} K_A(r)^2.
```

This identity is ordinary autocorrelation/Parseval, not a novel theorem.

## Approximation definition and resources

The cutoff `t` retains controlled rotations with qubit separation `r<=t` and
removes all `r>t`.  It is not an angle threshold or a fixed gate count.

For one register:

```
retained controlled phases = sum_{r=1}^{min(t,q-1)} (q-r),
removed phases = q(q-1)/2 - retained phases,
maximum omitted angle = pi/2^(t+1),
sum omitted magnitudes = eta(q,t).
```

`qft_noise.py` reports exact logical counts, matrix error when feasible,
unitarity, and fiber-law TV distance.  Qiskit resources are separately
validated in `results/qft_noise/qiskit_rows.csv`; modular arithmetic dominates
the `N=15` compiled circuit, so a logical QFT saving must not be mistaken for
a transpiled end-to-end saving.

## Proof of the scaling barrier

Each omitted controlled-phase unitary differs from the identity by at most
its phase angle.  Telescoping over omitted gates gives a one-register operator
error at most `eta(q,t)`, and telescoping over `d` tensor factors gives
`d*eta(q,t)`.  Measurement TV is at most twice this norm.  Replacing one of
`m` independent shots at a time bounds any downstream factor event by
`m*min(1,2d eta)`.

The least aggressive non-exact cutoff is `t=q-2`; its only omitted layer has
one phase of angle `pi/2^(q-1)=2pi/M` per register.  Hence

```
m*delta/Delta >= 4*pi*d*m/(M*Delta).
```

If the right-hand side exceeds one, every more aggressive cutoff also fails
the certificate.  This is a proof of a no-certificate regime.  It is not a
claim that physical approximate QFTs necessarily fail, because the operator
bound is worst-case and the hybrid step does not use fiber geometry.

## Scaling experiment and frozen holdout

The frozen protocol is `QFT_PRECISION_PROTOCOL.md`.

* analytic grid: `d={2,3,4,5}`, `M={8,16,32,64,128}`,
  `m={4,8,12,24}`, `Delta={.05,.10,.20}`, every cutoff;
* exact matrix overlap: `M={2,4,8,16}`, every cutoff;
* exact fiber/lattice endpoint: `N={35,77,143}`, `d=2`, `M={8,16,32}`,
  seven samples, 16 paired replicates, hard-box and finite Gaussian;
* a 24-semiprime list is frozen in the protocol for future endpoint work, but
  the analytic certificate is independent of `N` and is not duplicated into
  nominal per-`N` rows;
* RV comparator: 32 finite rows over approximate-QFT, sparse-corruption,
  diffuse-displacement, and coherent-phase conditions.

Generalization is reported by `N`/configuration, never by treating shots from
one modulus as independent moduli.  `paired_N_comparisons.csv` and
`resource_rows.csv` provide the aggregate views; `cluster_bootstrap_rows.csv`
contains deterministic 5,000-resample bootstrap intervals over the paired
`N` clusters.

## Results

### Analytic scaling

At `Delta=.05,m=12`, the selector chooses `t=q-1` (exact QFT) for all 20
`(d,M)` combinations in the requested `d=2..5,M<=128` range.  The exact
threshold for the first removable layer is approximately `6032` for `d=2`,
`9048` for `d=3`, and `15080` for `d=5`.  Thus `M<=128` is far inside the
no-certificate regime.  Relaxing `Delta` to `.10` or `.20` remains recorded
in the raw grid; those sensitivity rows do not alter the primary claim.

### Matrix and fiber validation

The direct roots-of-unity matrix agrees with Qiskit's exact inverse-QFT matrix
to machine precision for `M<=16`.  Deliberately reversed signs, missing swaps,
wrong cutoffs, and coordinate-order mistakes are caught by tests.

Exact fiber laws and the real lattice endpoint are evaluated beyond `M=8`:
`M=16` and `M=32`, `d=2`, and three paired semiprimes.  The recovery curves
are in `recovery_transition.png`; raw rows include 95% Wilson intervals.
These experiments are feasibility evidence, not a substitute for a scalable
statevector simulation.

### RV-structured comparator

The finite comparator is structurally faithful to the auxiliary LLL lattice in
Ragavan--Vaikuntanathan, but its theorem status is explicitly false in these
small cells.  All four toy conditions happened to recover in the eight-row
replicates.  This is an adversarial negative finding: the comparator did not
discriminate structured truncation from the other toy perturbations, so no
claim is made that approximate-QFT error is sparse corruption.  Coherent
truncation changes every run's distribution before measurement, unlike a
constant fraction of whole-run corruptions.

## Noise taxonomy

* **Approximate-QFT truncation:** coherent, structured spectral bias; not
  generally sparse corruption or independent displacement.
* **Coherent phase error:** a correlated character perturbation; its generic
  safe description is state-distance/TV, not a sample displacement.
* **Readout flips:** a classical post-QFT channel; potentially repairable or
  filterable if calibrated, but not equivalent to QFT phase error.
* **Grid quantization:** a bounded torus displacement with an explicit
  `sqrt(d)/(2M)` bound; this is the closest model to a noisy-dual sample.

The full samples-to-lattice endpoint still verifies `z in L`, evaluates the
stored-root product, classifies `L0` versus `L\L0`, and extracts factors only
from `L\L0`.  No known factors or lattice oracle are used for classification.

## Mandatory falsification audit

The positive adaptive-QFT claim is falsified in the declared regime because:

1. the selector chooses exact QFT throughout the primary grid;
2. the first non-exact layer cannot satisfy the bound for `M<=128`;
3. any one-layer logical saving is only `d` gates, with no demonstrated
   transpiled end-to-end saving;
4. the RV comparator does not establish that filtering repairs truncation;
5. the conclusion is not rescued by increasing samples, because `m` makes the
   certificate stricter.

The surviving result is **Outcome E**, a rigorous finite-certificate negative
result with matrix and endpoint validation.  It is not a breakthrough and it
does not generalize the earlier diversity result from the hard box to Regev's
full Gaussian algorithm.

## Literature and novelty boundary

The comparison includes Regev's augmented-lattice endpoint,
Ragavan--Vaikuntanathan's corruption-tolerant post-processing, Coppersmith's
approximate QFT, and later approximate-QFT implementation work.  The current
tail formula and hybrid argument are elementary; the defensible novelty claim
is only their explicit finite `d,M,m,Delta` certificate barrier for this
Regev endpoint and its held-out validation.  A broader literature search could
still find an equivalent bound, so no “first” or “breakthrough” language is
used.

## Reproduction

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q
MPLCONFIGDIR=.mplconfig PYTHONPATH=. .venv/bin/python scripts/run_qft_precision_scaling.py
```

The required raw tables, paired comparisons, resource rows, RV rows, and
figures are written under `results/qft_precision_scaling/`.
