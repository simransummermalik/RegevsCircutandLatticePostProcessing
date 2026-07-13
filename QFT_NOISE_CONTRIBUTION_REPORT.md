# A finite-parameter QFT-to-lattice criterion for Regev-style factoring

> Superseded as the central contribution by `QFT_PRECISION_SCALING_REPORT.md`.
> This file records the first finite-parameter experiment and remains useful
> background; its `d=3,M=8,m=12` result must not be read as the final claim.

## Status and claim scope

This is a new, isolated contribution on top of the notebook audit.  It is
not a claim that the notebook implements Regev's Gaussian-state algorithm,
and it is not a claim that the generic hybrid inequality below is a new
Fourier theorem.

The contribution is narrower: a roots-of-unity derivation of the exact
finite product-QFT law, an explicit finite-parameter error-to-recovery bound,
and a factor-blind precision-selection rule that is evaluated at the actual
augmented-lattice factor endpoint.  The rule is conservative enough that the
frozen experiment frequently selects the exact QFT.  That negative result is
part of the contribution.

The reproducible implementation is `regev_research/qft_noise.py`; the frozen
runner is `scripts/run_qft_noise_experiment.py`; raw rows and figures are in
`results/qft_noise/`.  The complete suite, including the new module, passes
with 94 tests.

## Research question and falsifiable hypothesis

**Question.** For dimension `d`, register size `M=2^q`, and `m` QFT samples,
what finite phase/truncation, coherent, readout, and grid errors can be
certified without destroying the samples' usefulness to the endpoint

```
samples -> augmented integer lattice -> LLL -> L versus L0 -> gcd factor
```

**Hypothesis.** A factor-blind cutoff chosen from a finite-shot QFT error
budget will either (i) certify a non-exact QFT with a measurable gate saving
and no loss in factor recovery, or (ii) correctly expose a parameter regime
where the worst-case certificate is vacuous and truncation lowers recovery.
The intervention does not inspect factors, relation labels, planted
relations, or a recovery result.

## Exact objects and the roots-of-unity law

Let the stored selected roots be `b_i in Z_N^*`, and let the circuit bases be
`a_i = b_i^2 mod N`.  For `x=(x_1,...,x_d) in X={0,...,M-1}^d`, define

```
h_A(x) = product_i a_i^(x_i) mod N,
L      = {z in Z^d : product_i a_i^(z_i) = 1 mod N},
L0     = {z in L : product_i b_i^(z_i) = +/-1 mod N}.
```

The last equality is the factor-extraction sublattice for the stored root
provenance.  A nonzero verified vector in `L\L0` gives
`beta=product_i b_i^(z_i)`, with `beta^2=1 mod N`; the two gcds of `beta-1`
and `beta+1` give a proper factor.  A vector in `L0` is valid but useless for
that extraction.  The quotient language is literal: useful classes lie in
`L/L0` outside the identity class, while `L0` directions are the misleading
short relations.

For `k in G=(Z/MZ)^d`, the inverse product QFT character is

```
chi_k(x) = exp(-2 pi i <k,x>/M).
```

The product QFT is the roots-of-unity matrix

```
F_M^(tensor d)[k,x] = M^(-d/2) exp(+2 pi i <k,x>/M),
```

with the sign reversed for the inverse convention used by the notebook.
After modular exponentiation, the arithmetic output is a classical label.
For a fiber `F_y={x:h_A(x)=y}`, the measured probability is therefore

```
P_A(k) = M^(-2d) sum_y | sum_{x in F_y} chi_k(x) |^2.
```

This is the exact high-dimensional interference law.  Equal arithmetic
labels add the roots of unity coherently; different labels are traced out.
If all fibers are singletons, every computational basis state has a flat
Fourier magnitude and the output is uniform, even if the input amplitudes are
Gaussian.  This explains why a large-N, small-M hard-box experiment can hide
the distinction between the two state-preparation models.

For the notebook hard box, define the exact requested notation:

* `P_A(k)` is the probability above.
* `U(k)=M^{-d}` is the uniform law on `G`.
* `r in G` is the residue class of the difference `x-x' mod M`.
* `K_A(r)` is the collision count

  ```
  K_A(r) = sum_{x,x' in X} 1[h_A(x)=h_A(x')] 1[x-x'=r mod M].
  ```

  Equivalently, with `z=x-x'`,

  ```
  K_A(r) = sum_{z in L, |z_i|<M, z=r mod M} product_i (M-|z_i|).
  ```

For a separable amplitude `w(x)=product_i w_i(x_i)`, the same definition has
the overlap weight `product_i sum_x w_i(x)w_i(x+z_i)` instead of the triangular
weight.  The implementation evaluates both the uniform hard box and the
finite centered discrete-Gaussian amplitude state by explicit fibers.

## The chi-squared identity, line by line

Put `Q=M^d`, and write `1_y(x)` for `1[h_A(x)=y]`.  Then

```
P_A(k)
 = M^(-2d) sum_y | sum_x 1_y(x) chi_k(x) |^2
```

by the fiber measurement rule.  Expanding the squared modulus gives

```
 = M^(-2d) sum_y sum_{x,x'} 1_y(x)1_y(x') chi_k(x) overline(chi_k(x'))
 = M^(-2d) sum_{x,x'} 1[h_A(x)=h_A(x')] chi_k(x-x').
```

The second equality uses that characters multiply and that
`overline(chi_k(x'))=chi_k(-x')`.  Grouping pairs by `r=x-x' mod M` gives

```
P_A(k) = M^(-2d) sum_{r in G} K_A(r) chi_k(r).
```

Since `K_A(0)=Q`, define `f_A(r)=K_A(r)-Q 1[r=0]`.  The uniform law is
`U(k)=Q^(-1)=M^(-d)`, so

```
P_A(k)-U(k) = M^(-2d) sum_r f_A(r) chi_k(r).
```

The finite-group character orthogonality relation is

```
sum_{k in G} chi_k(r) overline(chi_k(s)) = Q 1[r=s].
```

Therefore Parseval gives

```
sum_k |P_A(k)-U(k)|^2
 = M^(-4d) Q sum_r |f_A(r)|^2.
```

Finally, because `U(k)=Q^(-1)`,

```
chi^2(P_A || U)
 = sum_k |P_A(k)-U(k)|^2/U(k)
 = Q sum_k |P_A(k)-U(k)|^2
 = M^(-2d) sum_{r != 0} K_A(r)^2.
```

Equivalently, `chi^2=Q sum_k P_A(k)^2-1`, which is `Q` times the collision
probability minus one.  This is an immediate finite-group autocorrelation,
character-orthogonality, and Parseval identity.  The notation `K_A` is useful
for auditing the notebook, but no “apparently new” result is claimed.

## Matrix formulation and perturbation propagation

With the exponent registers first and arithmetic/ancilla registers last, the
full circuit is

```
U = (F_M^(tensor d) tensor I) U_modexp
    (H^(tensor d log M) tensor I).
```

The modular-exponentiation block is a controlled permutation.  On the
subspace with arithmetic input `|0>`, it has the block form

```
U_modexp |x>|0> = |x>|h_A(x)>.
```

Tracing the second block after the QFT produces a sum of fiber amplitudes,
which is why arithmetic collisions—not screenshots of individual circuits—
determine Fourier peaks.  If `F_t` is an approximate QFT and
`e=||F_t-F||_op`, the product telescoping inequality gives

```
||F_t^(tensor d)-F^(tensor d)||_op <= d e_1,
```

where `e_1` is a one-register bound.  Any subsequent measurement has a
total-variation change at most `2d e_1` under this conservative convention.

## Four finite-error models

### 1. Controlled-phase truncation

For `q=log2 M`, retain controlled rotations whose qubit separation is at most
`t`.  There are `q-r` rotations with separation `r`, each of angle
`pi/2^r`.  The omitted one-register angle sum is

```
eta(q,t) = pi sum_{r=t+1}^{q-1} (q-r)/2^r <= pi q/2^t.
```

Each omitted controlled-phase unitary differs by at most its angle in
operator norm, so a telescoping gate bound gives `e_1 <= eta(q,t)`.  The
implemented bound is

```
delta_QFT(d,q,t) = min(1, 2 d eta(q,t)).
```

### 2. Coherent input phase perturbation

If each pre-QFT amplitude acquires an unknown phase `theta_x` with
`|theta_x|<=xi`, then the input-state norm change is at most
`2 sin(xi/2)`.  The measurement TV bound is consequently
`min(1,2 sin(xi/2))`; the `m`-shot event bound below applies without pretending
that coherent phase error is an independent classical displacement.

### 3. Readout/bit flips

For an outcome tensor `p` and independent bit-flip probability `eta_r`, the
implemented channel moves each outcome to every flipped bit string with weight
`eta_r^j(1-eta_r)^(n-j)`.  It is a classical channel after the QFT and is
kept separate from phase truncation.  `bitflip_channel` tests mass
preservation exactly.

### 4. Fourier-grid quantization

Rounding a torus coordinate to an `M`-point grid contributes at most `1/(2M)`
per coordinate, hence

```
delta_grid <= sqrt(d)/(2M).
```

In the augmented embedding with scale `S` and `m` samples, the corresponding
bottom-block Euclidean perturbation is at most
`S sqrt(m) delta_grid`.  This is the direct bridge to the theorem's noisy-dual
condition.  Unlike phase truncation, grid error can be stated as a sample
displacement.

## Finite recovery threshold

Let `E` be any event computed by the complete classical endpoint (including
membership in `L`, the stored-root `L0` test, and gcd extraction).  For `m`
independent shots with per-shot TV distance `delta`, a hybrid replacement of
one shot at a time proves

```
|Pr_noisy(E)-Pr_ideal(E)| <= m delta.
```

Thus, if ideal recovery probability is `p0` and a target lower bound is
`p*<p0`, the sufficient finite condition is

```
m delta <= p0-p*.
```

For truncation this becomes

```
m min(1, 2 d eta(q,t)) <= p0-p*.
```

This is a deterministic finite-parameter statement conditional on the ideal
probability; it is not asymptotic and does not use known factors.  A factor-
blind engineering rule cannot know `p0`, so the implementation takes a
declared loss budget `Delta` and chooses the least `t` with
`m delta_QFT <= Delta`.  If no non-exact `t` qualifies, it returns the exact
cutoff and records “no saving certified.”  When the inequality is false, the
proof becomes vacuous; it does **not** prove that recovery is impossible.
Likewise, a grid perturbation larger than the available augmented-lattice
separation invalidates the usual nearest-lattice guarantee, but it is a
failure of that certificate, not a theorem that every decoder fails.

## Intervention and endpoint

`select_qft_cutoff(d,M,m,Delta)` is the primary intervention.  It reports the
cutoff, omitted-angle bound, TV bound, m-shot loss budget, controlled-phase
count, and exact/approximate two-qubit QFT counts.  A small-state diagnostic,
`select_fiber_qft_cutoff`, computes exact fiber-law TV rather than a recovery
outcome; it is factor-blind and used only for validation.

The endpoint is the existing exact integer construction:

1. measured integer rows are normalized as `w_i=k_i/M`;
2. the augmented row basis is the cleared form of
   `B=[[I_d,0],[S W,S I_m]]`;
3. SymPy LLL returns a reduced basis and its unimodular transform;
4. projected candidates are verified in `L` by modular multiplication;
5. stored roots, never arbitrary square roots, compute
   `beta=product b_i^(z_i)`;
6. `beta=+-1` is `L0`; otherwise the candidate is in `L\L0` and gcd extraction
   is attempted.

The method uses no enumeration, no BKZ, no known factors, no group orders,
and no planted relation.  The theorem-consistent model C generator has an HNF
oracle, but that oracle is not passed to reconstruction.

## Frozen experiment

Configuration is recorded in `results/qft_noise/configuration.json`.

* roots: `(2,3,4)`, stored permanently with their squared bases;
* dimension: `d=3`, `M=8`, `m=12` for QFT-law rows;
* Gaussian amplitude radius: `R=4` on the centered finite register;
* master seed: `2026071107`;
* declared finite-shot loss budget: `Delta=0.05`;
* relation-norm bound for model C: `T=4`, safety factor `2`;
* development semiprimes: `77, 91, 143`;
* held-out semiprimes (frozen before evaluation):
  `2279, 2419, 2491, 2501, 2537, 2623, 2747, 2773, 2867, 2881,
  2911, 2993, 3053, 3127, 3139, 3149, 3233, 3337, 3431, 3551,
  3599, 3763, 3977, 3953`.
  Every listed input is a two-prime product with factors greater than 37;
  this is a factor-blind candidate-root firewall, not a selection score.
* exact fiber A/B rows: all development inputs and the first six held-out
  inputs, for cutoffs `t=0,1,2`;
* analytic bound rows: all 24 held-out inputs;
* model C rows: all 24 held-out inputs;
* model D: Qiskit resource check at `N=15`, roots `(2,4)`, `M=4`;
* endpoint feasibility rows: `N=35,77,143`, 32 replicates per A/B cutoff,
  seven samples per replicate; C uses 32 theorem-consistent replicates.

No factors were used for selection, tuning, stopping, or classification.  The
factor manifest is only used after a returned gcd pair to validate it.

## Results

### Certified bound

For the frozen `d=3,M=8,m=12,Delta=.05` rule, the operator bound selects
`t=2`, the exact three-qubit QFT.  At `t=0` and `t=1` it reports a per-shot
bound of one and an m-shot bound clipped at one.  This is a deliberately
worst-case result: it says that a five-percent finite-shot guarantee cannot be
certified for a truncated transform at these parameters.

### Exact finite A/B laws

The raw `fiber_rows.csv` contains the exact roots-of-unity laws.  On the three
development semiprimes, A's TV distances for `t=0,1` range from roughly
`0.50--0.57` and `0.54--0.69`; B's range from roughly `0.43--0.62` and
`0.45--0.68`.  Both become numerical zero at the exact cutoff `t=2`.  The
Gaussian model is therefore not silently identified with the hard box; its
fiber interference differs on these collision-rich small instances.

### Factor endpoint

The `endpoint_rows.csv` table is the primary empirical endpoint.  At seven
samples and 32 paired replicates, exact `t=2` recovery was `0.81--0.97` for A
and `0.875--1.00` for B on `N=35,77,143`.  The same inputs at `t=0` gave
`0.44--0.63` for A and `0.25--0.53` for B; `t=1` gave `0.16--0.50` for A
and `0.22--0.47` for B.  These are feasibility estimates, not a claim of
asymptotic performance.  Each row also records a 95% Wilson binomial
interval over replicates; repeated shots are not treated as independent
inputs, and `N` remains the primary paired unit.

Model C is not a QFT truncation experiment: it directly samples the theorem-
consistent noisy dual law.  On the three small endpoint inputs it recovered a
factor in all 32 replicates, while all 27 C rows (three development plus 24
held out) satisfied the generator's sufficient inequality.  This result must
not be generalized to approximate-QFT circuits; it validates the separate
sample-to-lattice implementation.

For Qiskit model D, the modular arithmetic dominates.  At `N=15,M=4,d=2`,
cutoff zero compiled to depth 4622 with no controlled-phase gates, while
cutoff one compiled to depth 4624 with two controlled phases.  This is a
resource check, not a hardware-noise result.

### Resource accounting

For the QFT-law experiment each shot uses `d*q=9` Hadamards and at most nine
controlled phases; the exact cutoff is nine controlled phases.  The lattice
endpoint has dimension `d+m=10`, uses exact LLL, zero enumeration nodes, and
no BKZ.  Mean LLL time in the small endpoint rows is about 2 ms for A/B and
about 6 ms for C; raw integer embeddings, sample rows, and exact reduction
records are retained.  The report does not claim peak hardware memory; the
configuration explicitly labels that item.

## What this does and does not establish

**Verified implementation correction.** The module and circuit builder keep
the selected roots paired with their squared bases, use the mathematical
roots-of-unity QFT definition, and feed the actual integer augmented lattice
to LLL and stored-root factor extraction.

**Verified empirical result for the uniform-box notebook.** Under the frozen
finite hard-box law, truncated QFTs at `t=0,1` materially change the exact
Fourier law and lower factor recovery on the small augmented-lattice endpoint;
the five-percent factor-blind certificate selects the exact QFT.

**Unverified hypothesis concerning full Regev sampling.** The exact finite
Gaussian state shows the same qualitative endpoint degradation in these small
collision-rich tests, but this is not a proof for Regev's asymptotic Gaussian
state, a hardware implementation, or arbitrary lattice families.  Model C is
the theorem-consistent noisy-dual check, not evidence that QFT truncation is
safe or unsafe there.

The earlier diversity/recovery observation is not used as evidence for this
claim.  In particular, no negative relationship from the uniform-box study
is generalized to B or C here.

## Candidate contribution comparison

Scores are pre-study judgment scores from 1 (weak) to 10 (strong), with the
last column measuring how directly the idea reaches an implementable,
compilation-aware endpoint.

| Candidate | Research question / intervention | Importance | Novelty potential | Tractability | Falsifiability | Notebook relevance | Compilation-aware endpoint |
|---|---|---:|---:|---:|---:|---:|---:|
| Adaptive QFT precision | Can a declared finite-shot loss budget select the least QFT cutoff? | 9 | 6 | 9 | 10 | 10 | 9 |
| Noise-aware augmented scaling | Can `S` be chosen from phase/grid error rather than a fixed heuristic? | 9 | 7 | 7 | 9 | 9 | 9 |
| Phase-confidence sample weighting | Can sample weights derived from character perturbation improve LLL? | 8 | 7 | 6 | 8 | 9 | 8 |
| Readout/grid channel correction | Can a calibrated classical channel be inverted or marginalized safely? | 7 | 6 | 8 | 9 | 8 | 8 |
| Fiber-conditioned filtering | Can arithmetic-fiber coherence identify low-information shots? | 8 | 7 | 6 | 8 | 9 | 7 |
| Batched modular arithmetic | Can shared product trees reduce compiled depth at fixed ancillas? | 8 | 5 | 5 | 8 | 7 | 10 |
| Quotient-aware LLL/deflation | Can verified `L0` directions be removed before recovery? | 9 | 7 | 5 | 8 | 8 | 6 |
| Effective-dimension base selection | Do subgroup and relation diagnostics predict useful classes? | 7 | 5 | 8 | 8 | 10 | 7 |

The adaptive precision/finite-threshold candidate defeated the alternatives
for this cycle because it is the only one that simultaneously starts from
the high-dimensional roots-of-unity matrix, has an explicit finite theorem,
changes a real circuit resource, and can be tested at the complete lattice
endpoint without making the selector optimize the recovery outcome.  The
state-aware fiber diagnostic is retained as an ablation, not as a claim of a
general scalable optimizer.

## Literature audit and novelty boundary

The relevant primary sources were checked before writing this report:

* Regev, *An Efficient Quantum Factoring Algorithm*, arXiv:2308.06572,
  https://arxiv.org/abs/2308.06572 — multidimensional Gaussian sampling,
  relation lattice, augmented lattice, and LLL post-processing.
* Ragavan and Vaikuntanathan, *Space-Efficient and Noise-Robust Quantum
  Factoring*, IACR ePrint 2023/1501,
  https://eprint.iacr.org/2023/1501 — corruption filtering and a modified
  Regev post-processing pipeline.
* Coppersmith, *An approximate Fourier transform useful in quantum factoring*,
  arXiv:quant-ph/0201067, https://arxiv.org/abs/quant-ph/0201067 — approximate
  QFT truncation in factoring-related settings.
* Nam, Su, and Maslov, *Approximate Quantum Fourier Transform with
  O(n log n) T gates*, arXiv:1803.04933,
  https://arxiv.org/abs/1803.04933 — approximate-QFT gate constructions.
* Pawlitko et al., *Implementation and Analysis of Regev's Quantum
  Factorization Algorithm*, arXiv:2502.09772,
  https://arxiv.org/abs/2502.09772 — implementation and small-instance
  resource observations.

This audit found prior work on approximate QFTs, Regev's Gaussian/lattice
endpoint, and corruption filtering, but not a source that states this exact
finite-parameter product-QFT-to-Regev event bound together with the present
factor-blind cutoff record.  That is a novelty lead, not a priority claim:
the bound itself is a standard hybrid/Parseval/operator-norm argument, and a
primary-literature search could still reveal an equivalent formulation.

## Reproduction

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q
PYTHONPATH=. .venv/bin/python scripts/run_qft_noise_experiment.py
```

The second command rewrites the frozen CSV/PNG outputs under
`results/qft_noise/`.  The implementation rejects non-power-of-two `M`,
invalid roots, invalid probabilities, and malformed sample lattices rather
than silently changing conventions.
