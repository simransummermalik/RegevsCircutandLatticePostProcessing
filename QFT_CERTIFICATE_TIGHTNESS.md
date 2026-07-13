# Tightness, cancellation, and sharper QFT certificates

## Main finding

The first certificate is tight at its **single-register omitted-gate operator
step** but loose after restricting to modular-exponentiation fiber states,
measuring, composing samples, and asking only for the present factor event.
Consequently, its exact-QFT decision is not a fundamental information barrier.

All numbers below come from the corrected approximate-QFT decomposition and
`results/qft_certificate_gap/`.

## Proof-step slack

For a bound `B` and nonzero observed value `v`, slack is `B/v`. A value near
one is tight; large values are conservative. A zero observed value is recorded
without inventing an infinite numeric value.

Across the new holdout, median finite slack factors were:

| Proof step | Theoretical quantity | Observed comparison | Median slack | Maximum finite slack |
|---|---:|---:|---:|---:|
| Omitted-gate triangle | `eta(q,t)` | exact one-register operator error | 1.18 | 4.81 |
| Product tensor triangle | `d*eta` | feasible exact product-operator error | 1.96 | 6.68 |
| All-state to prepared-state restriction | product operator error | modular-fiber joint-state trace distance | 2.09 | `1.42e7` |
| State to measured law | fiber-state trace distance | exact distribution TV | 6.80 | over `1e33` when measurement cancels almost everything |
| Sample union | `min(1,m*TV)` | product-Hellinger TV bound | 1.38 | 2.29 |
| Distribution bound to factor event | Hellinger product bound | observed absolute factor-success change | 3.92 | 18.68 |

The raw 912 step rows are in `proof_slack_rows.csv`. The dominant
conservatism is not the last omitted phase itself; it is the use of an
all-input operator norm followed by data-processing bounds that discard the
fiber and measurement cancellation structure.

## Explicit near-tight example

For a seven-qubit one-register QFT (`M=128`) with cutoff `t=5`, exactly the
smallest-angle phase layer is omitted:

```text
phase-sum bound       = 0.04908738521234052
exact operator error  = 0.04908245704582458
ratio                 = 0.999899604216142
```

The right singular vector of the matrix difference supplies an adversarial
input direction that nearly saturates this step. Thus the elementary gate
triangle bound is not the main problem for the first omitted layer.

This does **not** make the complete recovery certificate tight: the adversarial
singular vector is not generally a modular-exponentiation fiber state, and a
matrix-vector error need not survive measurement or change a factor event.

## Explicit extreme-looseness example

For `N=15`, bases `(4,1)`, `d=2`, `M=4`, and cutoff `t=0`:

```text
original worst-case certificate: rejects
exact distribution TV:           5.9e-35 (numerical zero)
distribution-level certificate:  approves
```

The exact and approximate measurement laws coincide even though their
unitaries differ on other input states. Modular fibers and roots-of-unity
cancellation erase the observable error. This proves that all-state
matrix-level rejection cannot be interpreted as information-theoretic failure
for the prepared state.

The example is deliberately favorable/degenerate and is not by itself a broad
factoring result. Its role is to refute the logical implication “operator
certificate fails, therefore useful Fourier information is necessarily lost.”

## Held-out peak examples

The controlled-example file also records mechanisms seen in the frozen rows:

* **Peak shift:** `N=119`, hard box, `M=16`, `t=0`; the maximum moves from
  `[12,2]` to `[0,0]`, with normalized torus displacement about `0.280` and TV
  about `0.410`.
* **Broadening:** `N=55`, hard box, `M=32`, `t=0`; entropy grows by about
  `2.00` bits and TV is about `0.685`, while the top coordinate remains
  `[0,0]`.
* **Low-probability-only change:** `N=85`, finite Gaussian, `M=8`, `t=0`;
  under the frozen uniform-probability threshold, all absolute probability
  change lies on outcomes below the exact uniform mass, while the top peak is
  unchanged.
* **Top-peak merging diagnostic:** `N=161`, hard box, `M=8`, `t=0` gives the
  largest observed reduction in the top-two probability gap in this holdout.

These are controlled diagnostics, not universal peak taxonomy theorems.

## Three sharper factor-blind certificates

### 1. Exact character/fiber distribution-TV certificate

For the declared `N`, stored bases, finite amplitude vector, `M`, and cutoff,
the code sums the roots-of-unity amplitudes within each arithmetic fiber and
computes exact finite laws `P` and `Q` (up to floating evaluation). It then
uses

```text
TV(P^m,Q^m) <= min(1,m*TV(P,Q)).
```

This retains character cancellation and is factor-blind. It is much sharper
but exponentially expensive in `M^d`, so it is a finite validation certificate
rather than a scalable replacement for Regev's asymptotic analysis.

### 2. Product-Hellinger certificate

Let

```text
A(P,Q) = sum_x sqrt(P(x)Q(x)).
```

For independent samples, affinity multiplies exactly: `A(P^m,Q^m)=A(P,Q)^m`.
The certificate uses

```text
TV(P^m,Q^m) <= sqrt(1-A(P,Q)^(2m)).
```

It avoids the sample-wise union bound and was typically about `1.38` times
smaller in the holdout. It remains factor-blind and distribution-level.

### 3. Prepared modular-fiber state certificate

Instead of maximizing over every possible input, the code constructs the
actual joint state

```text
sum_x w(x)|x>|h_A(x)>
```

and computes the trace distance between exact- and approximate-QFT outputs.
Measurement and any classical recovery event cannot increase trace distance.
This retains the fiber subspace but is still more conservative than direct
measurement TV and is feasible only for small state spaces.

## Approaches not promoted to certificates

* A probabilistic omitted-phase concentration theorem was **not** asserted:
  deterministic QFT truncation does not supply independent random phase signs.
* The ten-percentage-point recovery non-inferiority rule is empirical, not a
  proof for unseen states or postprocessors.
* No conversion from TV to a deterministic sample displacement was invented.
  QFT truncation changes a distribution coherently; grid quantization is the
  model with a direct displacement interpretation.
* No information-theoretic impossibility result is claimed.

## Representative one-layer state-specific row

For `N=55`, finite Gaussian, `d=2`, `M=32`, `t=3`, `m=7`:

| Quantity | Value |
|---|---:|
| original m-shot bound | 1.000 |
| exact one-shot distribution TV | 0.00575 |
| TV union bound | 0.04024 |
| product-Hellinger bound | 0.03955 |
| original certificate | rejects |
| TV and Hellinger certificates | approve |
| logical controlled-phase saving | 2 |
| QFT-only transpiled CX saving | 4 |

This is direct evidence that the original exact-QFT decision can be a proof-
technique artifact. The full held-out inference, rather than this one row,
determines the main claim.

