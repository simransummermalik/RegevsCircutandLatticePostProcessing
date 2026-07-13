# Shor-to-Regev main result

## 1. Original summer research goal

The project now contains a reproducible path from standard Shor factoring to a
Regev-style modular-fiber and lattice-recovery implementation. The two
pipelines share QFT precision questions but use fundamentally different
classical decoders.

## 2. Standard Shor implementation

The new implementation constructs controlled modular multiplication, an
inverse exact or truncated QFT, measured phases, direct continued fractions,
candidate denominator multiples, modular order verification, and verified gcd
factor extraction. It succeeds on `(15,2)`, `(21,2)`, and `(33,10)` and records
odd-order and trivial-square-root failures without hidden order/factor inputs.

## 3. Existing Regev-style implementation

The existing repository already provides stored-root provenance, exact
augmented lattices, LLL, verified `L` versus `L0` classification, Claim-5.1
candidate selection, and gcd factor extraction. This new folder reads those
frozen results but does not modify or rerun them.

## 4. Existing certification-gap discovery

The completed Regev holdout showed that an all-state QFT certificate can
require exact QFT while limited truncation remains non-inferior at the frozen
endpoint. That result and its post-hoc labels remain unchanged.

## 5. New Shor robustness result

Eight held-out `(N,base)` instances, three shot budgets, exact through
three-layer-truncated QFTs, and 1% per-qubit readout error produced 12,288
trials. No paired order/factor batch decision changed. At three omitted layers,
the worst-case certificate rejected all primary instances, direct distribution
TV was at most `2.67e-5`, and six controlled phases/12 QFT-only CX gates were
removed.

## 6. Cross-decoder comparison

The result is **Outcome A**: both Shor and Regev exhibit finite held-out task
robustness beyond the worst-case certificate. Shor's tested gap is completely
closed by the exact finite distribution certificate; Regev retains empirical
cells not uniformly closed by that finite certificate.

## 7. Decoder-boundary analysis

Continued-fraction boundary mass was measured exactly for Shor. The frozen
Regev outputs supplied only already-recorded factor-blind proxies. The proposed
universal decoder-boundary explanation failed: its held-out accuracy was
`0.885`, below TV alone (`0.896`) and omitted layers (`0.906`, but with 27
false approvals).

## 8. Factor-blind empirical predictor

A deterministic logistic surrogate trained on development instances achieved
held-out accuracy `0.903`, precision `0.960`, recall `0.931`, and Brier score
`0.0823`. It made ten false approvals and 18 false rejections. It uses no
factors, true orders, success labels as features, or held-out identities. It is
explicitly an empirical predictor, not a certificate.

## 9. Resource implications

Both finite studies identify cells saving six logical controlled phases and 12
QFT-only CX gates. Neither establishes a full-circuit depth reduction or
device speedup.

## 10. Limitations and open theorem

The Shor holdout is saturated, contains eight small instances, and tests only
three omitted layers. The Regev evidence remains restricted to its frozen
small-state models and LLL decoder. The boundary proxies are heterogeneous,
and the predictor's failures prevent safe automatic approval. The open theorem
is a scalable, factor-blind state-and-decoder-aware precision bound.

## Publication-safe claim

> We present a reproducible Shor-to-Regev factoring testbed and evaluate QFT
> approximation at circuit, prepared-state, measurement, and verified-decoder
> levels. In separate frozen finite holdouts, both continued-fraction and
> augmented-lattice recovery tolerate truncations rejected by a worst-case
> QFT certificate, while direct distribution analysis closes the tested Shor
> gap but not every Regev cell. A factor-blind empirical surrogate reduces
> false rejections relative to the worst-case certificate but is not reliable
> enough to constitute a new certificate.

