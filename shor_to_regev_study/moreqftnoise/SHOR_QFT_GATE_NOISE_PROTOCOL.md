# Frozen protocol: Shor QFT gate-level noise robustness

Status: **frozen before result generation**

Freeze identifier: `shor-qft-gate-noise-v1`

Freeze date: 2026-07-15

This study is an additive companion to `SHOR_QFT_ROBUSTNESS_PROTOCOL.md`. It
does not alter or regenerate `results/shor_qft_robustness/`, its endpoint, or
its conclusions. Where the robustness study varied the inverse-QFT *distance*
(dropping controlled-phase layers), this study holds the distance at its exact
cutoff and instead perturbs the *gates that are kept*.

## Research question

Once the inverse QFT is executed at full distance, does realistic gate-level
noise — controlled-phase miscalibration, single-qubit RZ over/under-rotation,
or two-qubit depolarizing — degrade verified order or factor recovery, and at
what shot budget does any degradation first appear?

## Held-out instances

The generalization unit is `(N, base)`. The eight held-out instances are frozen
identically to the robustness study:

```text
(35,2), (35,11), (39,2), (51,2),
(55,2), (65,3), (77,8), (91,9)
```

Bases `(35,11)` and `(91,9)` have verified odd orders and therefore correctly
retain the order endpoint while yielding zero factor success.

## Noise model

All noise is realized inside the exact pure-state fiber formalism, so a single
realization remains a pure state (no density matrix). Three axes are swept, each
at three strengths, plus a zero-noise baseline (16 settings total):

* **Controlled-phase miscalibration** on the two-qubit gates of ideal angle
  `theta = -pi / 2**separation`.
  * systematic gain: `theta -> theta * (1 + g)`, `g in {0.02, 0.05, 0.10}`;
  * per-gate Gaussian scatter: `theta -> theta + N(0, sigma)`,
    `sigma in {0.02, 0.05, 0.10}` rad.
* **Single-qubit RZ over/under-rotation** on the basis-gate `rz` rotations that
  compile each Hadamard, modeled as an extra target-qubit z-rotation.
  * systematic bias `b in {0.02, 0.05, 0.10}` rad;
  * per-Hadamard Gaussian scatter `sigma in {0.02, 0.05, 0.10}` rad.
* **CX depolarizing** as a global-depolarizing surrogate keyed to the transpiled
  two-qubit gate count `m`: surviving coherence `lambda = (1 - p)**m`, mixing
  `P -> lambda P + (1 - lambda) * uniform`, `p in {0.001, 0.005, 0.010}` per CX.
  The transpiled QFT contains 150–203 CX gates over the holdout, so `p = 0.01`
  already sends 78–87% of the mass to uniform.

Stochastic-scatter settings redraw a fresh quasi-static miscalibration per
realization (fixed across a shot batch, varying across batches); deterministic
settings (gain, bias, depolarizing) produce one exact law per instance.

## Grid

* shot budgets `{1, 2, 8, 16}`;
* 48 paired-seed realizations per (instance, setting);
* cutoff fixed at `q - 1` (exact distance);
* loss budget `0.05`, non-inferiority margin `0.10`;
* master seed `2026071501`.

## Endpoints

Primary: paired approximate-minus-baseline difference in per-instance verified
order-recovery and factor-recovery probability, at each shot budget. A setting
is declared non-inferior at margin `0.10` when the worst-case (minimum over
instances) difference is `>= -0.10` for both endpoints. Secondary: one-shot
distribution TV to the exact law, Hellinger affinity, and the all-state
worst-case certificate decision.

## Decoder discipline

The continued-fraction decoder receives neither the true order nor the factors.
Factor pairs are compared to a post-hoc manifest only to confirm correctness;
`known_factors_used = False` and `known_order_used_by_decoder = False` in every
row.
