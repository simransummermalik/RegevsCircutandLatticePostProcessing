# Task-aware QFT precision and decoder-boundary analysis

## Four approximation levels

The cross study keeps four quantities separate:

1. **Circuit level:** omitted controlled phases, operator certificate, and
   compiled QFT-only resources.
2. **Prepared-state level:** exact joint-state trace distance where feasible.
3. **Measurement level:** exact finite TV, Hellinger affinity, peak/fiber, and
   continued-fraction-boundary statistics.
4. **Task level:** verified Shor order/factor recovery or verified Regev
   `L\\L0`/factor recovery.

Failure or rejection at one level is not silently promoted to another.

## Decoder-boundary quantities

For Shor, every phase-grid point is mapped to its continued-fraction
denominator signature. A boundary occurs where adjacent grid points produce
different signatures. The study records exact and approximate mass within one
grid cell of those boundaries, how much changed probability lies there, and—
for analysis only—distance to the nearest rational associated with the
simulated modular order. Order-dependent fields are excluded from prediction.

The completed Regev holdout is not rerun. Its available factor-blind proxies
are measured TV, Hellinger affinity, state trace distance where feasible,
Fourier peak displacement, entropy broadening, low-probability outcome change,
and QFT resources. Candidate-prefix boundary data were not stored in the
frozen result, so this study does not invent or reconstruct them after seeing
outcomes.

## Boundary hypothesis result: negative

The proposed universal claim—decoder-boundary movement predicts held-out
failure better than simpler QFT metrics—did not survive.

On 288 held-out factor-decision rows:

| Method | Accuracy | False approvals | False rejections |
|---|---:|---:|---:|
| Worst-case certificate | 0.302 | 0 | 201 |
| Measured TV alone | 0.896 | 6 | 24 |
| Omitted layers alone | 0.906 | 27 | 0 |
| Algorithm-specific boundary proxy alone | 0.885 | 27 | 6 |
| Factor-blind logistic surrogate | 0.903 | 10 | 18 |

The boundary proxy is not uniform across algorithms and did not outperform TV
or omitted-layer accuracy. Omitted layers achieved the highest raw accuracy
only because it approved every negative held-out case, producing 27 false
approvals. The logistic surrogate had the best nontrivial precision/recall
tradeoff and Brier score `0.0823`, but it still made ten false approvals and
18 false rejections. It is a heuristic, not a certificate.

## Predictor firewall

The deterministic logistic surrogate was fitted on 210 development rows and
evaluated on 288 held-out rows. Features were algorithm identity, register
bits, omitted layers, shots, measured TV, an algorithm-specific factor-blind
boundary proxy, and controlled-phase savings. Factors, true orders, recovered
success, task difference, and holdout identity were not features.

All 319 failed cases across all five comparators are stored in
`predictor_failure_rows.csv`; none were suppressed. The Shor holdout was
saturated at the tested cutoffs, so all surrogate errors occurred on Regev
rows. That imbalance is an important limitation rather than evidence that the
predictor has solved Shor precision selection.

## What survives

Worst-case certification is a very conservative universal decision rule in
this combined finite dataset. Direct measured-law information and a fitted
factor-blind surrogate reject far fewer usable truncations, but neither is a
proven replacement. The strong decoder-boundary mechanism remains an open
hypothesis, and the present heterogeneous proxy produced a negative result.

