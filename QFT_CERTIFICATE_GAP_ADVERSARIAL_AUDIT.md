# Adversarial audit of the QFT certification-gap result

## Implementation audit

The new theorem audit found a real bug: the custom approximate-QFT circuit
applied the standard QFT layers in reverse order. Full cutoff appeared to pass
only because `qft_matrix` switched to Qiskit's `QFTGate` instead of evaluating
the custom circuit. The fix now constructs layers from the most-significant
Qiskit qubit downward, applies controlled phases at the documented separation,
then swaps and inverts. Full cutoff uses this same construction.

Consequences:

* all pre-fix approximate-QFT result rows were invalidated;
* `results/qft_noise/` and `results/qft_precision_scaling/` were regenerated;
* the certificate-gap holdout was executed only after the correction;
* tests compare the custom full cutoff directly with roots-of-unity matrices.

## Claim-separation audit

The report never infers:

* empirical failure from certificate rejection;
* information-theoretic failure from LLL failure;
* hardware savings from logical or QFT-only transpilation;
* Regev asymptotic behavior from the hard-box or finite Gaussian;
* RV theorem coverage from the finite structural comparator.

## Holdout and tuning audit

The non-inferiority margin, roots, moduli, models, sample count, seeds,
replicates, endpoint, and eight semiprimes were frozen in
`QFT_CERTIFICATE_GAP_PROTOCOL.md` before execution. No held-out input was
excluded. Development QFT endpoint inputs `35,77,143` are not in the new list.

The exact factorization of each held-out `N` is kept in a post-hoc manifest.
It is used only to assert that a returned pair is correct. State construction,
certificates, and LLL recovery receive no factors or group orders.

## Statistical audit

* Each per-`N` probability uses 64 replicates.
* Approximate/exact configurations use the same seed schedule.
* Final differences are computed per `N`; confidence intervals resample eight
  whole-`N` clusters 5,000 times.
* Empirical safety requires both factor and verified-`L\L0` lower bounds to
  exceed the preregistered `-0.10` margin.
* The margin is a finite engineering non-inferiority definition, not a theorem
  and not proof of exact equality.
* Multiple cutoff rows are descriptive under a frozen rule; no uncorrected
  minimum p-value is reported as a discovery claim.

## Adversarial and favorable examples

The controlled examples include:

* an operator-level near-saturating singular-vector case;
* an identical-measurement-law case rejected by the original certificate;
* peak shift;
* entropy broadening;
* top-peak-gap reduction;
* changes confined to low-probability outcomes under the frozen diagnostic.

These examples establish that both alignment and cancellation occur. They do
not prove a universal two-regime threshold.

## Resource audit

Controlled-phase counts are exact logical counts. CX/depth savings are from a
QFT-only transpilation to the fixed `rz/sx/x/cx` basis and fixed seed. Modular
arithmetic is excluded from those rows, so the result is not described as an
end-to-end device speedup.

## Certificate audit

The original certificate is all-input and worst-case. The three sharper
certificates are factor-blind but finite/exponential because they construct
the exact modular-fiber state or measured law. They are validation tools, not
claimed scalable algorithms.

No probabilistic concentration theorem is used for deterministic omitted
phases. No TV value is reinterpreted as deterministic lattice displacement.
No recovery-aware theorem is claimed where only empirical non-inferiority was
measured.

## Remaining threats to validity

1. The heldout covers `d=2`, `M<=32`, `m=7`, two finite exact state models,
   and small semiprimes. Larger dimension/sample regimes remain untested at the
   exact endpoint.
2. Eight `N` clusters give limited precision even with many replicate shots.
3. SymPy LLL/Claim-5.1 is one decoder; another algorithm can behave differently.
4. Finite Gaussian radius `R=4` is not Regev's asymptotic parameter regime.
5. Exact laws use floating complex arithmetic after an exact finite
   combinatorial construction; normalization and matrix tests bound coding
   errors but do not provide arbitrary-precision interval proofs.
6. QFT-only transpilation is backend-independent logical compilation, not
   calibrated hardware execution.

These limitations narrow the claim to Outcome C: a demonstrated finite
certification gap caused by discarded state/fiber/measurement structure.

