# Frozen protocol: Factor-or-Fuse held-out study

Protocol ID: `factor-or-fuse-holdout-v1`  
Freeze date: 2026-08-01  
Status at freeze: none of the 24 held-out moduli had been passed to the
relation detector, factor classifier, fusion planner, circuit counter, or
factor endpoint.

## Question and falsifiable hypothesis

Can a stored-root-aware pre-circuit pass turn bounded public dependencies
among Regev circuit bases into either (1) an immediate verified factor or (2)
an exactly equivalent arithmetic circuit with strictly lower source canonical
CX cost?

The preregistered hypothesis is that at least 6 of 24 held-out moduli are
actionable and that the complete method has positive mean paired quantum
arithmetic savings whose 95% modulus-level bootstrap interval excludes zero.
Failure to meet either threshold rejects the intended broad finite-instance
claim.  There are no exclusions after execution.

## Frozen inputs

The 24 moduli are the first 24 lexicographic products of distinct primes in
the closed interval 163 through 211.  The complete ordered list and a separate
post-hoc factor manifest is isolated in `factor_manifest.py`; the method-side
freeze is in `freeze.py`.  Each case has 15 or 16 bits.

The method receives only `N`.  It computes:

- `n = N.bit_length()`;
- `d = ceil(sqrt(n))`;
- `q = ceil(2*n/d)`;
- roots: the first `d` ascending primes coprime to `N`;
- circuit bases: the permanently paired values `a_i = b_i^2 mod N`;
- bounded directed-power limit `K = 64`.

The factors, Euler/Carmichael values, group orders, arbitrary square roots,
and planted relations are forbidden method inputs.  A proper GCD encountered
while choosing roots is a reported setup-factor outcome, not an exclusion.

## Factor-or-fuse rule

For each ordered pair `i != j`, find the least `1 <= k <= 64` satisfying

```text
a_j = a_i^k (mod N).
```

The verified relation vector is `z = k*e_i - e_j`.  Compute

```text
R = product_l b_l^z_l (mod N).
```

Because `product_l a_l^z_l = 1`, necessarily `R^2 = 1 (mod N)`.

- If `R` is neither `+1` nor `-1`, return the proper divisor obtained from
  `gcd(R-1,N)` or `gcd(R+1,N)`.  The quantum arithmetic demand is zero.
- If `R` is `+1` or `-1`, certify `z in L0`.  Only these certified directions
  may enter the complete fusion planner.
- If no relation is found or no fusion is cheaper, execute the exact serial
  baseline.

For an L0 group with anchor `g` and verified weights `k_i`, the compiled
oracle reversibly computes the full ordinary integer

```text
s = sum_i k_i*x_i,
```

applies one existing modular-exponentiation block for `g^s`, and uncomputes
the accumulator.  It never reduces `s` modulo the Fourier-register size.  The
accumulator width is

```text
bit_length((2^q - 1) * sum_i k_i).
```

The exact planner minimizes arithmetic-only source canonical CX, including
accumulator compute/uncompute.  Serial singletons are always available, and a
fusion must be a strict improvement.  Ties prefer fewer extra clean qubits,
then fewer full-width controlled multipliers, then lexicographic plan order.

## Arms

1. serial baseline;
2. factor-only bounded scan, with serial fallback;
3. duplicate (`k=1`) fusion only, without root classification;
4. root-blind bounded orbit fusion, without factor extraction;
5. factor-or-fuse with deterministic greedy grouping;
6. complete factor-or-fuse with exact cost-optimal set partitioning.

These ablate direct GCD extraction, duplicate-only compilation, bounded orbit
compilation, and global cost optimization.

## Endpoints and resource accounting

The primary generalization unit is `N`; repeated synthetic trials are not
independent cases.

Co-primary endpoints:

1. factor-or-strict-fuse coverage across the 24 moduli;
2. paired percent reduction in quantum arithmetic canonical CX, charging zero
   quantum CX only when the preprocessor itself returns a proper divisor;
3. change in full-width controlled-multiplier calls, which is not the
   planner's optimized objective.

Every row records relations, root classification, factor validity, source
`x/cx/ccx/cswap` counts, canonical CX, multiplier calls, extra qubits,
accumulator widths, deterministic planner, runtime, memory, and exact
certificate status.  Every selected plan is checked on zero, all-maximum,
all single-bit exponent inputs, and 256 seeded exponent vectors.  A failed
certificate forces baseline fallback and remains a failure row.

Binary intervals use Wilson 95% intervals.  Mean paired savings use 5,000
bootstrap resamples of the 24 moduli with seed `2026080102`.  All per-modulus
rows must be reported.  `K` is not varied until the primary result is sealed.

## Interpretation boundary

A positive result would establish only that a bounded, factor-free-input
preprocessor can exploit some finite public base dependencies.  It would not
establish a new number-theoretic factoring theorem, a generic asymptotic
speedup, improved Regev sampling/recovery probability, reduced quantum sample
count for fusion-only cases, or hardware advantage.  A null result would show
that the method's toy-benchmark mechanism does not generalize to this frozen
standard small-prime family at `K=64`.
