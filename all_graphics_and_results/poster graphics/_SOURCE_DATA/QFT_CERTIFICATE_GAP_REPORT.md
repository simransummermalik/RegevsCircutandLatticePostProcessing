# Fiber cancellation creates a QFT certification gap in finite Regev-style recovery

## Paper-ready claim

**Main outcome: Outcome C — certification-gap theorem and held-out evidence.**

The worst-case product-QFT operator certificate can require exact QFT even
when a non-exact distance cutoff preserves the present `L\L0` and factor
endpoint. The logical reason is that the all-input operator norm maximizes over
states outside the modular-exponentiation fiber state and discards
roots-of-unity cancellation under measurement. An explicit finite example has
zero exact distribution distance despite certificate rejection. In a frozen
eight-semiprime holdout, the original certificate approved zero omitted layers,
whereas one layer was empirically non-inferior for both hard-box and finite-
Gaussian models at every `M in {8,16,32}`; two layers met the preregistered
absolute `0.10` non-inferiority rule for the Gaussian model at `M=16,32`.

This is not an information-theoretic theorem that truncation always works. It
is a theorem that worst-case matrix rejection cannot establish failure on the
prepared fiber state, plus algorithm-specific held-out evidence measuring the
size of that gap.

## Abstract

Distance-truncated quantum Fourier transforms reduce small-angle controlled
rotations, but a direct operator/tensor/hybrid analysis gives the finite-shot
barrier `M<4*pi*d*m/Delta`, forcing exact QFT throughout the earlier Regev-
style finite study. We audit every inequality and distinguish certificate,
empirical, information-theoretic, and decoder-specific failure. The first
omitted-phase operator bound is nearly tight (`0.9999` ratio at `M=128`), yet
large slack appears after restricting to modular-product fibers and measuring.
We implement three factor-blind refinements: exact character/fiber distribution
TV, product-Hellinger composition, and prepared-fiber-state trace distance.
An explicit `N=15` example has identical exact/approximate measurement laws
while the worst-case certificate rejects. We then freeze eight new semiprimes,
three Fourier moduli, two state models, all cutoffs, 64 coupled replicates, and
the actual augmented-lattice/LLL/stored-root endpoint. One omitted layer is
non-inferior in all six `(M,model)` cells, and two are non-inferior for the
finite Gaussian at `M=16,32`, saving up to six logical controlled phases and
12 QFT-only transpiled CX gates. Therefore the earlier exact-QFT requirement is
primarily a limitation of the proof technique in this finite regime, not
evidence of a fundamental information barrier.

## Essential implementation correction discovered by this audit

Before the holdout, matrix auditing found that the custom approximate-QFT
decomposition iterated qubits in the reverse gate order from Qiskit's exact
QFT. The old full-cutoff test masked this because it substituted `QFTGate`
instead of exercising the custom decomposition. The implementation and tests
were corrected so that:

* retaining all rotations reproduces the direct roots-of-unity matrix;
* every cutoff uses the same ordered decomposition with only stated phases
  removed;
* missing swaps, reversed sign, endian reversal, and wrong cutoff fail tests.

All earlier QFT/noise and precision-scaling result tables were regenerated.
No pre-correction approximate-QFT empirical row is used in this report.

## Exact question answered

> Does the exact-QFT requirement reflect a genuine finite-parameter
> information barrier, or only conservatism of the current certificate?

**Answer for the tested finite regime:** mainly certificate conservatism.

The all-state gate/operator step can be nearly tight, but it does not follow
that the prepared modular-fiber measurement law changes comparably or that the
present factor event fails. Held-out cutoffs rejected by the original theorem
preserved the algorithm-specific endpoint under the frozen non-inferiority
criterion. No information-theoretic failure was proved.

## Four claims that must not be conflated

| Claim | Meaning | Result here |
|---|---|---|
| A. Certificate failure | A sufficient theorem cannot approve the cutoff | Proven throughout the original five-percent non-exact grid |
| B. Empirical recovery failure | Held-out factor or verified-`L\L0` rate decreases materially | Not detected beyond the frozen margin for passing cutoffs; present for some more aggressive cutoffs |
| C. Information-theoretic failure | No classical decoder could recover the information | Not proved; an identical-law counterexample refutes deriving it from certificate failure alone |
| D. Algorithm-specific failure | This augmented-lattice/LLL endpoint fails | Measured per cutoff; does not imply C |

## Frozen holdout

The protocol was written before execution in
`QFT_CERTIFICATE_GAP_PROTOCOL.md`.

* roots `(2,3)`, dimension `d=2`;
* held-out semiprimes `55,65,85,95,115,119,133,161`;
* `M={8,16,32}`, `m=7`, `Delta=.05`;
* exact hard-box model A and exact finite-Gaussian model B (`R=4`);
* every valid cutoff;
* 64 coupled replicates per `(N,M,model,cutoff)`;
* exact cleared augmented lattice, SymPy LLL, Claim-5.1 prefix, stored-root
  classification, no enumeration/BKZ/deflation;
* whole-`N` 5,000-resample cluster bootstrap;
* empirical non-inferiority requires both factor and verified-`L\L0` lower
  confidence bounds to be at least `-0.10` relative to exact QFT.

Known factors were used only after recovery to validate a returned pair.

## Certification gap

Omitted layers are `s=(q-1)-t`; exact QFT has `s=0`. The additive statistic

```text
G_layers = empirically_noninferior_layers - original_certified_layers
```

avoids division by zero. Results:

| M | Model | Original certified layers | Non-inferior layers | `G_layers` |
|---:|---|---:|---:|---:|
| 8 | hard box A | 0 | 1 | 1 |
| 8 | finite Gaussian B | 0 | 1 | 1 |
| 16 | hard box A | 0 | 1 | 1 |
| 16 | finite Gaussian B | 0 | 2 | 2 |
| 32 | hard box A | 0 | 1 | 1 |
| 32 | finite Gaussian B | 0 | 2 | 2 |

Thus every tested model/modulus cell contains a non-exact cutoff rejected by
the original certificate that nevertheless met the frozen non-inferiority
rule.

## Paired recovery results

The rows below are approximate-minus-exact differences over eight held-out
`N` clusters for the largest truncation meeting the frozen rule in each cell:

| M | Model | Omitted layers | Factor mean difference | 95% cluster lower bound | `L\L0` mean difference | 95% cluster lower bound |
|---:|---|---:|---:|---:|---:|---:|
| 8 | A | 1 | -0.0117 | -0.0273 | -0.0117 | -0.0273 |
| 8 | B | 1 | -0.0020 | -0.0117 | -0.0020 | -0.0117 |
| 16 | A | 1 | -0.0059 | -0.0137 | -0.0059 | -0.0137 |
| 16 | B | 2 | -0.0371 | -0.0742 | -0.0371 | -0.0742 |
| 32 | A | 1 | -0.0059 | -0.0176 | -0.0059 | -0.0176 |
| 32 | B | 2 | -0.0176 | -0.0352 | -0.0176 | -0.0352 |

Every lower bound is above the frozen `-0.10` margin. Factor and `L\L0`
results coincide in these cells because every recovered nontrivial stored-root
class produced the verified factor pair; this is observed behavior, not an
assumed identity for arbitrary composites.

More aggressive cutoffs did fail the empirical rule in most cells. The result
is therefore not “truncation never matters”; it identifies a finite gap
between certificate rejection and the declared recovery-loss tolerance.

## Post-hoc robustness and margin sensitivity

These checks were added after the primary holdout and are explicitly
secondary. They reuse the same eight `N` clusters and therefore do not enlarge
the generalization sample.

* Removing each held-out `N` in turn left all six selected cutoffs
  non-inferior at the original absolute `0.10` margin: 48 of 48
  cell/omission checks passed. The worst leave-one-out lower bound among those
  cells was `-0.08482` for finite-Gaussian `M=16` with two omitted layers.
* Exact paired sign-flip tests at the `-0.10` boundary gave one-sided
  sensitivity `p<=0.015625` for both endpoints in every selected cell. This
  calculation assumes sign symmetry and is not substituted for the frozen
  cluster-bootstrap decision.
* At margin `0.05`, at least one omitted layer still passed in all six cells;
  finite-Gaussian `M=32` still passed with two, whereas `M=16` fell from two
  to one. At margin `0.02`, hard-box `M=8` permitted zero omitted layers, so
  the statement “one layer in every cell” depends on allowing more than a
  two-percentage-point absolute loss.
* Raw values for all 120,000 bootstrap draws are preserved rather than only
  their confidence endpoints.

The exact outputs are `bootstrap_draw_rows.csv`,
`paired_exact_test_rows.csv`, `leave_one_N_out_rows.csv`,
`margin_sensitivity_rows.csv`, and `margin_summary_rows.csv`.

## Resources at the cutoffs meeting the frozen rule

| M | Model | Passing omitted layers | Logical controlled-phase saving | QFT-only transpiled CX saving | QFT-only depth saving |
|---:|---|---:|---:|---:|---:|
| 8 | A/B | 1 | 2 | 4 | 2 |
| 16 | A | 1 | 2 | 4 | 0 |
| 16 | B | 2 | 6 | 12 | 4 |
| 32 | A | 1 | 2 | 4 | 0 |
| 32 | B | 2 | 6 | 12 | 0 |

These are QFT-only transpilation results to a fixed `rz/sx/x/cx` basis. The
full modular-arithmetic circuit can dominate depth, so this table is not a
claim of end-to-end hardware speedup.

## Sharper certificates: what they do and do not close

The new isolated module `regev_research/qft_certificate.py` implements:

1. exact finite character/fiber distribution TV plus m-sample hybrid;
2. exact distribution affinity plus product-Hellinger bound;
3. prepared modular-fiber joint-state trace distance plus hybrid;
4. exact feasible matrix errors and proof-step slack accounting.

The direct distribution certificate approved at least some non-exact held-out
instances in every modulus. For the finite Gaussian at `M=32`, the one-layer
cutoff was distribution-certified for all eight held-out `N` values; one
representative row had TV `0.00575`, m-shot bound `0.04024`, and Hellinger
bound `0.03955`, below `Delta=.05`.

These certificates do not fully close the empirical gap. For example, the
Gaussian two-layer cutoffs at `M=16,32` met the frozen margin but were not
uniformly distribution-certified across all held-out
moduli. A scalable recovery-aware theorem remains open.

## Where the original proof loses tightness

The first omitted-layer gate bound can be nearly exact: at `M=128,t=5`, the
observed operator error is `0.0490825` versus bound `0.0490874`. Median gate-
triangle slack is only `1.18`.

The larger losses come later:

| Proof step | Median finite slack |
|---|---:|
| omitted-gate triangle | 1.18 |
| product tensor triangle | 1.96 |
| all-state to prepared-state restriction | 2.09 |
| state to measured distribution | 6.80 |
| sample union versus product Hellinger | 1.38 |
| distribution bound versus factor event | 3.92 |

Extremely large state-to-measurement slack occurs when phase errors lie in
directions canceled by fiber summation or discarded by measurement.

## Explicit tight and loose examples

* **Near-tight operator step:** `M=128,t=5`, tightness ratio `0.9998996`.
* **Extreme loose complete certificate:** `N=15`, bases `(4,1)`, `M=4,t=0`;
  exact distribution TV is numerical zero (`5.9e-35`) although the original
  certificate rejects.
* **Peak shift:** `N=119`, A, `M=16,t=0`; peak moves from `[12,2]` to `[0,0]`.
* **Broadening:** `N=55`, A, `M=32,t=0`; entropy increases by about two bits.

The full records are in `controlled_examples.json` and
`QFT_CERTIFICATE_TIGHTNESS.md`.

## Roots-of-unity mechanism

The all-state norm asks for the input vector that maximizes
`||(F-F_t)v||`. The actual state instead has amplitudes partitioned by
arithmetic labels `h_A(x)`. Inside each label, complex roots of unity add; at
measurement, only squared summed amplitudes remain. Omitted phases may:

* align and move/broaden peaks;
* cancel within a fiber;
* change only low-probability outcomes;
* rotate amplitudes without changing their measured magnitudes.

The exact-law counterexample realizes the last two possibilities. Therefore a
worst-case singular vector outside the prepared fiber geometry cannot by
itself establish loss of useful Regev samples.

## Ragavan–Vaikuntanathan boundary

Approximate-QFT truncation is a coherent change to every run's distribution,
not automatically a constant fraction of fully corrupted runs.
Ragavan–Vaikuntanathan's filtering result addresses corrupted quantum runs
under specific hypotheses. The repository's finite RV comparator remains
explicitly non-theorem-backed in its toy cells and is not used to claim that
filtering closes this certification gap.

## Novelty comparison

| Claim | Closest prior result | Difference here | Status |
|---|---|---|---|
| Small QFT rotations may be omitted while retaining algorithmic performance | Coppersmith; Barenco–Ekert–Suominen–Törmä | Different high-dimensional modular-fiber state and actual Regev-style lattice endpoint | Prior principle; endpoint study is repository-specific |
| Gate-efficient approximate QFT | Nam–Su–Maslov | No new synthesis construction; only fixed distance truncation/resource accounting | Not novel |
| Gaussian samples and augmented-lattice factoring | Regev | Finite exact laws, stored-root endpoint, and cutoff comparison | Regev framework is prior |
| Tolerance of corrupted circuit runs | Ragavan–Vaikuntanathan | Coherent all-run QFT bias is not assumed to satisfy sparse-corruption hypotheses | Distinction/negative applicability result |
| TV, Hellinger, trace-distance certificates | Standard probability/quantum-information inequalities | Instantiated factor-blindly on exact modular fibers and connected to `L\L0` recovery | Standard inequalities; application is the contribution |
| Worst-case rejection with held-out non-inferior truncation | AQFT literature already shows task-specific bounds outperform worst-case intuition | Frozen Regev-style `L\L0`/factor endpoint, additive layer-gap statistic, and proof-step slack | Novelty lead only; no priority claim |

Primary sources include [Regev](https://arxiv.org/abs/2308.06572),
[Ragavan–Vaikuntanathan](https://eprint.iacr.org/2023/1501),
[Coppersmith](https://arxiv.org/abs/quant-ph/0201067),
[Barenco et al.](https://arxiv.org/abs/quant-ph/9601018), and
[Nam–Su–Maslov](https://arxiv.org/abs/1803.04933). The generic inequalities
are not claimed as new, and an unsuccessful keyword search is not treated as
proof of priority.

## Exact claim boundary

**Verified:** the previous custom cutoff ordering was wrong and is corrected;
the original certificate rejects all non-exact frozen cells; held-out
uncertified cutoffs meet the declared non-inferiority rule for the current
finite A/B laws and current LLL
endpoint; direct state/distribution certificates can approve some of them.

**Not verified:** information-theoretic impossibility or sufficiency, full
Regev asymptotics, calibrated hardware performance, end-to-end circuit speedup,
or a scalable certificate that approves every empirically non-inferior cutoff.

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python -m pytest -q
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python scripts/run_qft_certificate_gap.py
```

Raw outputs, paired cluster rows, all bootstrap draws, sensitivity tables,
slack tables, controlled examples, and the figure are under
`results/qft_certificate_gap/`.
