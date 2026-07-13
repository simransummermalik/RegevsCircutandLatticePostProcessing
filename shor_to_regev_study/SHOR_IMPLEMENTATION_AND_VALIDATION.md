# Standard Shor implementation and validation

## What is implemented

This folder adds a small-scale standard Shor pipeline without changing the
existing Regev implementation:

```text
N and base a
-> gcd shortcut
-> controlled modular exponentiation
-> inverse QFT
-> measured phase y/Q
-> directly computed continued-fraction convergents
-> denominator multiples 1..4
-> modular verification a^r = 1 mod N
-> reduction to the minimal verified order
-> gcd(a^(r/2) +/- 1,N)
-> verified factor pair
```

`shor.py` contains both a Qiskit circuit constructor and an exact finite
fiber simulator. The simulator is used for reproducible experiments; the
Qiskit circuit is independently compared with it on `N=15`. Controlled
modular multiplication is a reversible work-register permutation: values
below `N` are multiplied modulo `N`, and unused basis states are fixed.

## Decoder firewall

The decoder signature contains only `N`, `base`, measured integer `y`, and
phase modulus `Q`. It is never passed factors or a true order. A candidate is
accepted only after `pow(base,r,N)==1`; verified multiples are reduced using
additional modular exponentiation tests. Factors are accepted only after
checking that both are nontrivial and their product is exactly `N`.

The simulator does compute the order classically to construct the exact
modular-exponentiation fiber state. That value is not passed to the decoder
or empirical predictor. A test replaces the simulator-order function with an
exception and confirms that decoding still succeeds.

## Verified examples

With 64 shots and frozen seeds:

| N | Base | Recovered order | Factor result | Interpretation |
|---:|---:|---:|---|---|
| 15 | 2 | 4 | `(3,5)` | success |
| 15 | 14 | 2 | none | trivial square root `-1 mod 15` |
| 21 | 2 | 6 | `(3,7)` | success |
| 21 | 4 | 3 | none | odd order |
| 21 | 5 | 6 | none | trivial square root `-1 mod 21` |
| 33 | 10 | 2 | `(3,11)` | success |

The gcd shortcut is separately tested with `N=15, base=3`.

## QFT and measurement validation

Tests establish that:

* the custom inverse QFT, including every approximate cutoff, equals the
  repository's roots-of-unity/Qiskit matrix convention;
* full-cutoff swaps and orientation are correct;
* the `N=15, base=2` circuit marginal equals the exact fiber law;
* the four phase peaks occur at `0,Q/4,Q/2,3Q/4`;
* Qiskit's displayed classical-bit ordering decodes to the intended integer;
* continued-fraction convergents, denominator multiples, order reduction,
  odd-order failure, trivial-square-root failure, and factor validation have
  explicit tests.

## Honest scope

The circuit uses dense unitary permutation gates for clarity, not a scalable
fault-tolerant arithmetic synthesis. Exact simulation stores phase vectors of
length `Q=2^(2*ceil(log2(N)))`; it is intended only for small composites. No
claim is made that this implementation competes with optimized Shor circuits
or factors cryptographic integers.

## Reproduction

From the repository root:

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python \
  shor_to_regev_study/run_shor_experiments.py
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python -m pytest -q \
  shor_to_regev_study/test_shor.py
```

