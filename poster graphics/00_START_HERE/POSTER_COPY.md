# Short poster copy

## One-sentence headline

A worst-case QFT certificate required exact circuits, but the complete held-out finite factoring endpoint tolerated limited phase-layer truncation in every tested setting.

## Three-sentence summary

We reconstructed a finite Regev-style pipeline from modular state preparation through multidimensional Fourier sampling, exact integer-lattice reduction, verified relation classification, and factor extraction. The original sufficient certificate approved no non-exact QFT setting, yet one omitted phase layer met the frozen `0.10` non-inferiority rule in all six held-out model-by-`M` cells; two layers also passed for the finite-Gaussian model at `M=16` and `M=32`. The largest passing case removed six logical controlled phases and 12 QFT-only transpiled CX gates, but the result remains limited to eight small semiprimes, `d=2`, `M<=32`, `m=7`, two finite exact models, and the repository's present LLL decoder.

## Main research question

Does failure of a conservative, worst-case QFT certificate mean that the downstream Regev-style lattice decoder must lose factoring information at the same precision?

## Answer supported by these experiments

No—not for the tested finite settings. Certificate rejection was not a lower bound on the precision actually needed by the prepared modular-fiber states and the complete recovery endpoint.

## Mechanism sentence

The certificate bounds every input state, while modular exponentiation groups amplitudes into arithmetic fibers whose omitted phase errors can cancel before measurement and lattice recovery.

## Safe resource sentence

At `M=32` and `d=2`, exact, omit-one, and omit-two QFTs used `20/18/14` logical controlled phases and `52/48/40` QFT-only transpiled CX gates; compiled QFT depth stayed `36`.

## Limitation sentence

This is not a proof that approximate QFT is safe for cryptographic-scale Regev factoring, not a full-circuit hardware benchmark, and not evidence of end-to-end quantum speedup.

