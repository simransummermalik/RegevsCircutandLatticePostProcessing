# Exact finite Shor QFT robustness study

## Research question

Does distance-truncating Shor's inverse QFT reduce verified order or factor
recovery before a worst-case all-state QFT certificate permits the same
approximation?

## Frozen design

The protocol was written before execution in
`SHOR_QFT_ROBUSTNESS_PROTOCOL.md`. The eight held-out instances are:

```text
(35,2), (35,11), (39,2), (51,2),
(55,2), (65,3), (77,8), (91,9)
```

The grid contains shot counts `{4,8,16}`, readout probabilities `{0,0.01}`,
omitted layers `{0,1,2,3}`, 64 paired-seed batches, and 5,000 whole-instance
bootstrap draws. The generalization unit is `(N,base)`, not a shot. Bases
`(35,11)` and `(91,9)` have verified odd orders and therefore correctly have
zero factor success while retaining the order endpoint.

## Held-out result

Across all 24 `(shots,readout,omitted-layers)` comparisons, observed
approximate-minus-exact differences were exactly zero for both order and
factor batch recovery. This includes three omitted phase layers with 1%
independent per-qubit readout flips. Every leave-one-instance-out comparison
also returned zero difference.

This empirical saturation must be interpreted alongside the exact laws. At
three omitted layers, the maximum one-shot distribution TV over the holdout
was `2.662201e-5`, and the largest prepared joint-state trace distance was
`0.0061235`. Thus paired equality is not evidence that the unitaries or states
are identical; the perturbations were simply too small to change any of the
12,288 finite batch outcomes under the paired seeds.

## Certificate comparison

At `shots=8`, the worst-case certificate approves:

| Omitted layers | Held-out instances approved by worst-case certificate | Approved by direct distribution certificate |
|---:|---:|---:|
| 0 | 8/8 | 8/8 |
| 1 | 8/8 | 8/8 |
| 2 | 3/8 | 8/8 |
| 3 | 0/8 | 8/8 |

Therefore the three-layer endpoint is a genuine worst-case certification gap,
but unlike the strongest unresolved Regev cells, Shor's exact finite
distribution certificate closes the tested gap completely. The result
supports task/state-specific precision analysis; it does not show that three
layers are universally safe for Shor.

## Resource accounting

Three omitted layers remove six logical controlled phases and 12 QFT-only
transpiled CX gates per Shor QFT. The fixed generic transpilation showed zero
QFT-only depth reduction, and modular exponentiation is excluded. This is not
an end-to-end device-speedup claim.

## Statistical sensitivity

All differences are zero, so every declared margin from `0.02` through `0.15`
classifies all three tested truncations as non-inferior. This is descriptive,
not proof of equivalence: the holdout contains eight clusters and the tested
truncations only remove the three smallest-angle layers of 12- or 14-qubit
QFTs. More aggressive cutoffs remain outside the frozen holdout.

## Exact outputs

`results/shor_qft_robustness/` contains:

* 192 configuration rows;
* 12,288 raw trial rows;
* 192 per-instance rows;
* 24 paired rows;
* 120,000 bootstrap draws with their common cluster indices;
* 36 exact sign/sign-flip rows;
* 144 leave-one-instance-out rows;
* 96 margin-sensitivity rows and 24 margin summaries;
* a configuration, hashes, and completion manifest.

## Claim boundary

**Verified:** limited Shor QFT truncation can preserve this exact finite
continued-fraction endpoint after the worst-case certificate rejects, and the
direct finite distribution law explains why.

**Not verified:** asymptotic Shor precision, arbitrary bases, calibrated
hardware performance, a nonzero depth improvement, or safety of aggressive
QFT truncation.

