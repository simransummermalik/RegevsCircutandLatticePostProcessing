# Shor versus Regev QFT precision comparison

## Main outcome: A

Both algorithms show held-out task robustness beyond the original worst-case
QFT certificate.

* **Shor:** three omitted layers were rejected by the worst-case certificate
  for all eight held-out instances at the primary eight-shot setting, yet all
  order/factor batch outcomes matched exact QFT. Exact distribution
  certificates approved all eight because TV was at most `2.67e-5`.
* **Regev:** the untouched frozen result retains one non-inferior omitted layer
  in all six model/modulus cells and two in two Gaussian cells under its
  declared `0.10` margin. Some, but not all, of that empirical gap is closed by
  direct finite distribution certificates.

This is Outcome A under the frozen decision rule. It does not mean the two
decoders react identically.

## Why the mechanisms differ

Standard Shor uses `Q` approximately quadratic in `N`; the tested QFTs have 12
or 14 phase qubits. Removing three smallest-angle layers perturbs the measured
periodic law only minutely. Continued fractions then maps large rational peak
regions to modularly verified orders.

The finite Regev-style endpoint uses two much smaller Fourier registers
(`M<=32`) followed by augmented-lattice construction and LLL. Its measured TVs
are much larger, and task changes vary across modulus/model cells. Fiber
cancellation remains important, but the present evidence does not isolate LLL
as the unique source of robustness.

## Comparable resource result

The largest declared truncation in each study removes six logical controlled
phases and 12 QFT-only CX gates. Neither study establishes an end-to-end depth
or hardware improvement: the fixed Shor QFT transpilation saved zero depth,
and modular arithmetic dominates both complete circuits.

## Paper-safe interpretation

Worst-case QFT distance is not a reliable *necessary* condition for finite
verified factoring recovery across these two decoders. Prepared-state and
measured-distribution calculations explain substantially more of the Shor
result and part of the Regev result. A universal decoder-boundary predictor was
not established.

