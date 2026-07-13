# QFT precision theory: the finite-shot certificate and its scaling limit

> This document proves a limitation of the original worst-case certificate.
> `QFT_CERTIFICATE_PROOF_AUDIT.md` supplies the final boundary audit, and
> `QFT_CERTIFICATE_GAP_REPORT.md` shows that the certificate is conservative
> relative to corrected held-out recovery.

Let `q=log2(M)`.  The distance-truncated inverse QFT keeps all controlled
phases with qubit separation `r<=t` and removes those with `r>t`.  There are
`q-r` phases at separation `r`, each of angle `pi/2^r`.

## Exact tail

The omitted-angle sum on one register is

```
eta(q,t) = pi * sum_{r=t+1}^{q-1} (q-r)/2^r.
```

Writing `s=q-t`, the finite sum is exactly

```
eta(q,t) = pi * 2^(-t) * (s - 2 + 2^(-(s-1))).
```

The implementation checks this formula against direct summation for every
`2<=q<=7` and every cutoff.

Each omitted controlled-phase unitary differs from the identity by at most its
angle in operator norm.  A telescoping product bound therefore gives

```
||F_t-F|| <= eta(q,t)
||F_t^(tensor d)-F^(tensor d)|| <= d eta(q,t).
```

For any input state and computational-basis measurement, a conservative
one-shot total-variation bound is

```
delta_t <= min(1, 2 d eta(q,t)).
```

For `m` independent shots and any downstream event, including the complete
LLL and stored-root factor endpoint,

```
|Pr_t(E)-Pr_exact(E)| <= m delta_t.
```

This is a standard hybrid argument.  It does not assume that phase error is a
classical displacement and it does not identify the event with entropy or
peak sharpness.

## A dimensionless certificate variable

For a declared allowed event-probability loss `Delta`, define

```
B(d,M,m,t;Delta) = m * min(1, 2*d*eta(log2(M),t)) / Delta.
```

The finite theorem certifies the cutoff only when `B<=1`.  The first possible
non-exact cutoff is `t=q-2`, which removes the smallest-angle layer.  Since

```
eta(q,q-2) = pi/2^(q-1) = 2*pi/M,
```

its certificate is

```
B_min_nonexact = 4*pi*d*m/(M*Delta).
```

Because every more aggressive cutoff has a larger tail, we obtain the exact
certificate limitation

```
M < 4*pi*d*m/Delta
  => no non-exact distance cutoff is certified by this theorem.
```

This is a rigorous negative result about the available finite-shot
QFT-to-recovery certificate, not a claim that every approximate QFT must fail.
It gives a transparent scaling law: the first removable phase layer requires
`M=Omega(d*m/Delta)`.  If that layer is removable, the logical savings are
only `d` controlled phases out of `d*q*(q-1)/2`, a relative saving
`2/(q*(q-1))`; more substantial savings require a larger error budget or a
state-specific theorem.

For the primary `Delta=.05`, `m=12` setting, the threshold is
`M < 3016*d` numerically: about `6032` for `d=2`, `9048` for `d=3`, and
`15080` for `d=5`.  Therefore every `M<=128`, `d in {2,...,5}` primary row is
predicted to select the exact QFT.  This is the scaling explanation for the
small `M=8` observation, not a post-hoc fit.

## Relation to the lattice endpoint

The exact QFT produces roots-of-unity character sums over modular-exponentiation
fibers.  Truncation changes those sums coherently, so it is structured spectral
leakage, not an independent random displacement of each measured sample.  A
grid-rounding error, in contrast, has a direct torus displacement bound
`sqrt(d)/(2M)`.  In the cleared augmented lattice with scale `S` and `m`
rows, the latter contributes at most `S*sqrt(m)*sqrt(d)/(2M)` to the lower
block.  The former has only a distributional TV guarantee unless an additional
state-specific peak-separation theorem is supplied.

The Ragavan--Vaikuntanathan corruption filter is designed for a pool containing
a constant fraction of corrupted whole runs.  QFT truncation generally
changes every run's distribution in the same coherent way; it is therefore
not covered by the sparse-corruption premise.  Readout flips can be modeled as
classical corruption, and grid errors as diffuse coordinate perturbations, but
they should not be conflated with phase truncation.

## What is and is not proved

Proved: the exact tail, operator bound, product-dimension bound, m-shot hybrid
bound, and the `M < 4*pi*d*m/Delta` no-certificate regime.

Empirical: exact matrix agreement for small Qiskit registers, exact fiber-law
TV and lattice recovery on feasible small instances, and the frozen scaling
table.

Not proved: a physical lower bound on all approximate-QFT implementations, a
Gaussian-state asymptotic recovery theorem, or an equivalence between coherent
QFT error and RV sparse corruption.
