# Frozen protocol: Shor QFT robustness and cross-decoder comparison

Status: **frozen before result generation**

Freeze identifier: `shor-qft-robustness-v1`

Freeze date: 2026-07-12

This study is an additive companion to the completed Regev/QFT work. It does
not alter or regenerate `results/qft_certificate_gap/`, its protocol, its
endpoint, or its conclusions.

## Development and held-out instances

Development instances may be used for implementation debugging and predictor
fitting:

```text
(N, base) = (15,2), (15,14), (21,2), (21,4), (21,5), (33,10)
```

The robustness holdout is frozen as:

```text
(35,2), (35,11), (39,2), (51,2),
(55,2), (65,3), (77,8), (91,9)
```

The unit of generalization is the complete `(N,base)` instance. Individual
shots and repeated trial batches are not treated as independent held-out
instances. No held-out pair may be removed after execution. Bases were chosen
without supplying factors to the decoder and intentionally include both
factor-yielding and non-factor-yielding verified orders.

## Shor circuit and decoder

For `n=ceil(log2(N))`, each phase register has `q=2n` qubits and
`Q=2^q` outcomes. The circuit is:

```text
uniform phase register
-> controlled multiplication by base^(2^j) mod N
-> inverse QFT with declared cutoff
-> computational-basis phase measurement
```

The work-register permutation leaves basis states `y>=N` unchanged. The
decoder receives only `N`, `base`, `Q`, and measured `y`. It computes continued
fraction convergents directly, checks denominator multiples `1..4`, verifies
`base^r = 1 mod N`, reduces a verified multiple to the minimal order using
modular tests, and then attempts `gcd(base^(r/2) +/- 1,N)`. It receives neither
the true order nor factors. A non-coprime base uses the standard gcd shortcut.

## Frozen experimental grid

For every held-out pair:

* shot counts: `{4,8,16}`;
* per-qubit readout flip probabilities: `{0,0.01}`;
* omitted QFT phase layers: `{0,1,2,3}`, clipped only if the register has
  fewer layers;
* 64 repeated batches per complete configuration;
* master seed: `2026071201`;
* bootstrap seed: `2026071201 + 90000`;
* bootstrap replicates: 5,000;
* declared absolute non-inferiority margin: `0.10`;
* sensitivity margins: `{0.02,0.05,0.10,0.15}`.

Exact and approximate cutoffs use the same batch seed for fixed
`(instance,shots,readout_probability,replicate)`. Order and factor endpoints
are resampled with the same cluster indices in every paired bootstrap draw.

## Endpoints

Primary recorded endpoints are:

1. probability of recovering a modularly verified order;
2. probability of returning a verified nontrivial factor pair.

The primary one-layer comparison is approximate minus exact at `shots=8` and
zero readout error. A cutoff is non-inferior only if the 2.5% whole-instance
cluster-bootstrap lower bound for both endpoints is at least `-0.10`.

Secondary outputs include every grid cell, all bootstrap draws,
leave-one-instance-out results, exact sign and sign-flip tests, margin
sensitivity, distribution TV/Hellinger values, decoder-boundary metrics, and
QFT-only resources. Secondary analyses do not change the primary rule.

## Cross-algorithm comparison

The completed Regev holdout is loaded read-only from
`../results/qft_certificate_gap/`. The cross study compares four distinct
levels: circuit/operator error, prepared-state error where available,
measured-distribution error, and verified task recovery. Regev task endpoints
remain verified `L\\L0` and factor recovery; Shor endpoints remain verified
order and factor recovery.

The central hypothesis is that worst-case QFT distance is a poor universal
proxy because prepared states and classical decoder boundaries determine which
Fourier errors matter. Outcomes are assigned exactly as follows at each
study's frozen margin:

* A: held-out uncertified non-inferior truncations occur for both algorithms;
* B: only Regev;
* C: only Shor;
* D: neither;
* E: model/endpoint/instance evidence is mixed and no single A-D statement is
  supported.

## Predictor firewall

The empirical predictor is fitted only on the declared development instances
and evaluated only on the held-out Shor pairs and completed Regev holdout. Its
features may include algorithm, register size, cutoff, shots, distribution
features, decoder-boundary features that do not use a known order, and resource
savings. Factors, known orders, returned success indicators, and hand-selected
holdout identities are forbidden as features. Labels are used only as training
targets and held-out evaluation outcomes. The predictor is never called a
certificate.

## Required files and falsification

The run must retain raw trials, per-instance rows, paired differences, all
bootstrap draws, leave-one-instance-out rows, exact sensitivity tests, margin
tables, configuration metadata, SHA-256 hashes, and a completion manifest.
Missing configurations, factor/order leakage, endpoint-specific bootstrap
indices, a failed manifest, or a failed test invalidates completion.
