# Frozen quotient-recovery protocol

Status: frozen before any execution on the 20 quotient-study holdout moduli.
Freeze identifier: `quotient-recovery-freeze-v2-final-before-holdout`.

## Research question and falsifiable hypothesis

At finite dimension, does exact, unsaturated deflation of relations already
verified to lie in `L0`, combined with quotient-aware bounded enumeration and
genuine new-sample acquisition, improve recovery of `L \ L0` relative to the
same LLL/enumeration budget without deflation?

The positive hypothesis is that complete LDAR has higher factor-recovery
probability within the frozen resource envelope or reaches probability 0.8
with fewer circuit executions.  The hypothesis is falsified if it does not
outperform the matched no-deflation endpoint across held-out `N`, especially
under the exact finite Gaussian and theorem-consistent models.

## Frozen inputs

- Development only: the 25 semiprimes listed in
  `regev_research.quotient_experiments.DEVELOPMENT_SEMIPRIMES`.
- Holdout: the 20 literal semiprimes listed in
  `regev_research.quotient_experiments.HELDOUT_SEMIPRIMES`.
- Primary generalization unit: `N`, not a repeated shot batch.
- Dimension: `d = 3`.
- Roots: scan `[2, 3, 5]`, skip a candidate only when its GCD with `N` is not
  one, and expand deterministically through later primes if necessary.  The
  selector receives no factors, group orders, or planted relations.

## Frozen sampling models

- A: exact notebook uniform hard-box output law.
- B: exact finite truncated discrete-Gaussian amplitude-state output law.
- C: theorem-consistent bounded noisy-dual samples; the generator-only exact
  relation oracle is withheld from recovery.
- D: exact notebook output followed by declared classical readout flips and
  whole-shot corruption.  D is a circuit-derived surrogate, not gate-level or
  hardware-calibrated noise.

For A, B, and D, `D = 64`, Fourier precision is six bits per coordinate,
Gaussian radius is `R = 16`, and reconstruction scale is `S = 13`.  Model C
records its theorem-selected grid and scale.  Each replicate generates one
11-row batch and all sample curves use its nested prefixes 7 through 11.

## Frozen budgets and stopping rules

- 32 replicates per `(N, model)` cell.
- Common bounded search: six reduced rows, coefficient bound two, support at
  most three, and at most 50 visited coefficient candidates per sample count.
  Exact-norm ordering materializes its declared finite search set first;
  generated nodes, runtime, and memory are charged separately.
- Complete LDAR: at most two 25-node rounds per sample count; a second round
  is allowed only after the exact integer `U` changes.
- Exact augmented-row deflation: at most three deleted primitive basis rows.
- BKZ block size: six, using only a transform-verified `fpylll` result.
- Sample counts: 7, 8, 9, 10, 11.  Stop immediately on a verified factor.
- Target probability: 0.8.  Report `>11` if it is not reached.
- Post-hoc quotient-gap box: `[-16,16]^3`; natural precommitted threshold
  `log2(lambda_L0/lambda_useful) > 0`.
- Competing base-diversity predictor: bounded product diversity on
  `[-2,2]^3`; all other predictor definitions are fixed by their audited
  implementation (empirical Fourier-sample entropy/covariance, exact
  relation-lattice determinant, sample count, and bounded ordinary minimum).
- Inference: paired comparisons and 5,000-resample cluster bootstrap over
  holdout `N`.

Every candidate is first verified in `L`; only then may the permanently stored
roots classify it as `L0` or `L \ L0` and trigger final GCD extraction.  Known
factors are used only after recovery to audit a reported factor pair.

## Frozen comparison arms

Standard Regev Claim-5.1 LLL; exact-norm LLL plus bounded enumeration;
transform-verified BKZ plus the same enumeration; exact quotient
deduplication; exact augmented free-basis-row deflation; the finite-parameter
Ragavan--Vaikuntanathan-structured filter where it terminates; random genuine
extra-sample acquisition; and the six declared ablations: no deflation,
deflation without adaptive sampling, adaptive sampling without deflation,
root-blind reduction, quotient-gap scoring only, and complete LDAR.

No parameter or stopping rule may be changed after reading holdout outcomes.
Bug fixes must be documented and may not depend on whether they improve the
result.
