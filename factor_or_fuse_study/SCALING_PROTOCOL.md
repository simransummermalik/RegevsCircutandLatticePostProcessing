# Deterministic post-holdout scaling census

This census was specified after the 24-case held-out result was sealed.  It is
descriptive follow-up evidence, not a second held-out test and not a source of
parameter tuning.

- Bit lengths: 12, 16, 20, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512,
  768, 1024, 1536, and 2048.
- Cases per bit length: 100 deterministic distinct balanced-ish semiprimes.
- Root rule: the same first `ceil(sqrt(n))` coprime primes.
- Relation bound: the already frozen `K=64`.
- Classification: the method-side scan receives only `N`; generation factors
  are attached only after it returns.
- Endpoints: fraction with any bounded pair-power relation, fraction yielding
  an immediate factor, fraction yielding only L0 dependencies, smallest
  exponent, and the exact positive-power no-wrap certificate.
- No exclusions.  A setup GCD, relation-free case, or arithmetic exception is
  retained with an explicit label.

The no-wrap certificate is deliberately narrow.  For distinct prime roots
`b_i != b_j`, if both positive integers `b_i^(2k)` and `b_j^2` are below `N`,
then `a_i^k = a_j (mod N)` would imply integer equality
`b_i^(2k) = b_j^2`, contradicting unique factorization.  Therefore

```text
max_i b_i^(2K) < N
```

certifies that this positive bounded pair-power detector must be inactive.  It
is not a lower bound against arbitrary multiplicative relations, discrete-log
methods, or other circuit optimizations.
