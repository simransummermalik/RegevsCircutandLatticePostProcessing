# QFT precision adversarial audit

> Historical audit for the certificate-scaling stage. The final audit is
> `QFT_CERTIFICATE_GAP_ADVERSARIAL_AUDIT.md`; corrected held-out data falsify
> interpreting the Outcome-E certificate barrier as actual exact-QFT necessity.

This audit is separate from the positive/negative scaling claim.

## Matrix-level adversaries

The tests in `tests/test_qft_noise.py` intentionally fail under:

* reversing the roots-of-unity sign (forward versus inverse matrix error is
  materially nonzero);
* deleting the final swaps from the Qiskit decomposition;
* changing the controlled-phase cutoff (every cutoff is checked for unitarity,
  and full cutoff is checked against the direct roots-of-unity matrix);
* treating a nonsymmetric tensor-register state as if its coordinate order
  were irrelevant.

The exact Qiskit matrix agrees with the direct inverse roots-of-unity matrix
for `M=2,4,8,16` at machine precision.  The approximate matrix is generated
by the same explicit decomposition used by the circuit builder, not by a
probability-only surrogate.

## Selector adversaries

The frozen scaling grid includes every cutoff, `d=2..5`, `M=8..128`,
`m=4,8,12,24`, and budgets `0.05,0.10,0.20`.  The primary selector is
factor-blind and uses only `(d,M,m,Delta)`.  It selects exact QFT throughout
the primary `Delta=.05` grid; no post-hoc endpoint choice is substituted.

## Structured-noise adversaries

The RV-structured finite comparator was run on the same `N=35,d=2,M=8`
small pool under:

* approximate-QFT samples (`t=1`);
* three sparse corrupted runs;
* diffuse coordinate displacement by `-1,0,+1` modulo `M`;
* coherent phase bias of amplitude `0.20` radians.

All four toy cells happened to recover in the eight finite replicates.  This
does not support an RV theorem claim: the comparator records
`asymptotic_guarantee_applicable=false`, and the cell is too small to separate
the mechanisms.  The result is reported as a failed discrimination test, not
as evidence that approximate-QFT errors are sparse corruptions.

## Falsification outcome

The positive “adaptive approximate QFT saves resources” hypothesis is
falsified for the declared five-percent finite-shot certificate: the selector
chooses exact QFT, and the first non-exact layer cannot satisfy the bound for
any `M<=128` in the requested `d,m` range.  The surviving result is Outcome E:
a rigorous no-certificate scaling limit plus finite endpoint evidence, not a
resource-saving algorithm.
