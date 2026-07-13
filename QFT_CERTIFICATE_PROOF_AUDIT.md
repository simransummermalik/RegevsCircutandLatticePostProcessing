# Complete audit of the finite-shot QFT certificate

## Audited statement

Let:

* `M=2^q`, with integer `q>=2`, be the number of values in each Fourier
  register;
* `d>=1` be the number of exponent/Fourier registers;
* `m>=1` be the number of independent circuit executions supplied to the
  classical endpoint;
* `Delta` satisfy `0<Delta<1` and denote the allowed absolute change in the
  probability of any downstream event;
* cutoff `t in {0,...,q-1}` retain every controlled phase whose qubit
  separation is at most `t`; `t=q-1` is exact and `t<=q-2` is non-exact.

The implemented worst-case certificate approves `t` when

```text
min(1, m * min(1, 2*d*eta(q,t))) <= Delta,
```

where

```text
eta(q,t) = pi * sum_{r=t+1}^{q-1} (q-r)/2^r.
```

Because `Delta<1`, the outer clipping does not change an approval decision.
The audited implication is

```text
M < 4*pi*d*m/Delta
  => no non-exact distance cutoff is approved by this certificate.
```

“Certified” means only that the stated inequalities prove that **every event
computed from the m measured samples** changes in probability by at most
`Delta`. It does not mean the cutoff empirically succeeds, and failure to
certify does not mean it fails.

## Norms and probability metrics

* Gate and QFT matrix error use the spectral/operator norm
  `||A||_2 = max_{||v||=1} ||Av||_2`.
* Pure-state error is audited with Euclidean norm and trace distance.
* Measured laws use total variation
  `TV(P,Q)=1/2 sum_x |P(x)-Q(x)|`.
* Recovery success is a classical event after samples, augmented lattice,
  LLL, exact `L` verification, stored-root `L0` classification, and gcd
  extraction.

All quantities are dimensionless. Angles are in radians; radians are
dimensionless.

## Line-by-line proof

### 1. Count omitted rotations

At qubit separation `r`, one `q`-qubit QFT has `q-r` controlled phases, each
of angle `theta_r=pi/2^r`. Cutoff `t` omits `r=t+1,...,q-1`, so the sum of
omitted angle magnitudes is exactly `eta(q,t)`.

### 2. Bound one omitted gate

A controlled phase is identity on three computational states and multiplies
the fourth by `exp(i theta)`. Therefore

```text
||CP(theta)-I||_2 = |exp(i theta)-1| = 2|sin(theta/2)| <= |theta|.
```

The final inequality is strict for nonzero finite `theta`; it is already one
source of slack.

### 3. Telescope one QFT circuit

Write the exact and truncated circuits as products that differ only at omitted
controlled phases. Insert and subtract one intermediate circuit at a time.
Unitary invariance of the operator norm and the triangle inequality give

```text
||F_M - F_t||_2 <= sum_omitted ||CP(theta)-I||_2 <= eta(q,t).
```

This permits adversarial coherent alignment of every omitted-gate error. It
does not use roots-of-unity cancellation or the prepared modular-fiber state.

### 4. Telescope the d-register product QFT

For unitary tensor factors,

```text
F^tensor d - F_t^tensor d
```

is expanded by replacing one tensor factor at a time. Hence

```text
||F^tensor d - F_t^tensor d||_2 <= d*eta(q,t).
```

This is a full product-QFT statement, not a one-coordinate statement.

### 5. Convert state error to measurement error

For any normalized input state—including states unrelated to modular
exponentiation—the output vector difference is at most `d*eta`. The first
study uses the conservative measurement bound

```text
TV(P_exact,P_t) <= min(1, 2*d*eta(q,t)).
```

The factor two is safe but not tight for pure states. This step applies to all
input states; it ignores that the actual input occupies a modular-arithmetic
fiber subspace.

### 6. Compose m executions

The implemented experiment draws `m` independent samples from the same
one-shot law. Replacing one coordinate of the product law at a time gives

```text
TV(P_exact^tensor m, P_t^tensor m)
  <= min(1, m*TV(P_exact,P_t)).
```

Any downstream classical event differs by at most the TV distance. The same
hybrid idea can handle conditional draws when every conditional replacement
has the same bound, but this repository claims only the independent-run case.

### 7. Evaluate the first non-exact cutoff

The least aggressive non-exact choice is `t=q-2`. It omits exactly one phase
per register, with

```text
eta(q,q-2) = pi/2^(q-1) = 2*pi/M.
```

Every more aggressive cutoff has at least this omitted-angle sum.

### 8. Apply the strict threshold

Assume

```text
M < 4*pi*d*m/Delta.
```

Then `4*pi*d*m/M > Delta`. If `4*pi*d/M<=1`, the unclipped m-shot bound for
the first omitted layer already exceeds `Delta`. If `4*pi*d/M>1`, the
one-shot bound clips to one and the m-shot bound is one, which also exceeds
`Delta` because `Delta<1`. Thus the first non-exact cutoff is rejected, and
monotonicity of `eta` rejects every more aggressive cutoff. QED.

## Boundary cases

| Case | Correct behavior |
|---|---|
| `t=q-1` | `eta=0`; exact QFT is certified for any positive budget. |
| `M=4*pi*d*m/Delta` exactly | The first-layer bound equals the budget and is approved because certification uses `<=`; therefore the theorem correctly uses strict `<`. |
| `Delta=1` | Excluded from the strict barrier theorem. A clipped bound of one could be approved, so the implication would otherwise be false at `m=1`. |
| `Delta<=0`, `d<=0`, or `m<=0` | Rejected as invalid input. |
| non-power-of-two `M` | Rejected by this implementation; its gate convention assumes `M=2^q`. |
| `q=1` | There is no controlled phase to truncate; the scaling study starts at `q>=2`. |

`tests/test_qft_certificate.py` exercises equality, strictness, clipping,
exact cutoff, invalid budgets, and every-non-exact-cutoff rejection.

## Hidden assumptions and scope

1. The exact and approximate circuits differ only by deletion of the stated
   controlled phases. The certificate-gap audit found that the previous
   custom circuit used reversed gate order; it was corrected and all QFT
   empirical outputs were regenerated.
2. All other gates are ideal.
3. Repeated circuit executions are independent for the product-law statement.
4. Omitted errors may align adversarially in the triangle inequalities.
5. The bound applies to every input state and therefore does not exploit
   modular-exponentiation fibers, Gaussian weights, or arithmetic labels.
6. It bounds every classical event uniformly. It does not use the actual
   augmented-lattice separation or LLL behavior.
7. Certificate approval is sufficient, never necessary.

## Four claims kept separate

### A. Certificate failure

`original_certified=false` means this proof cannot approve the cutoff. The
strict barrier proves this for all non-exact cutoffs in the frozen range.

### B. Empirical recovery failure

This means measured held-out factor or verified-`L\L0` recovery decreases.
It is estimated with repeated trials and whole-`N` cluster intervals. The new
holdout shows that some rejected cutoffs are empirically non-inferior, so A
does not imply B.

### C. Information-theoretic failure

This would mean no possible classical postprocessor can recover the needed
information. No result in this repository proves C. An explicit example even
has identical exact/approximate measurement laws despite certificate failure.

### D. Algorithm-specific failure

This means the present augmented-lattice/LLL endpoint fails. It is weaker than
information-theoretic failure because another decoder might succeed. All
reported recovery losses are D-type evidence unless a separate information
theorem is supplied.

