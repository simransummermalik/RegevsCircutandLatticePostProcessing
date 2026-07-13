# Beginner's guide to this Regev-style quantum factoring research repository

This repository reconstructs and red-teams a Qiskit notebook inspired by
[Regev's factoring algorithm](https://arxiv.org/abs/2308.06572). It contains:

- a verified audit of the original circuit and its external arithmetic gates;
- immutable root/base provenance and exact `L` versus `L0` classification;
- an exact integer augmented-lattice/LLL post-processing endpoint;
- four explicitly separated sample models;
- frozen base-selection and quotient-deflation experiments;
- a roots-of-unity QFT/noise model and a finite-shot precision-scaling study.

The project deliberately keeps failed hypotheses. The diversity selector did
not establish a general Regev improvement, quotient deflation did not beat its
matched baseline, and the current worst-case QFT certificate does not permit a
resource-saving approximate QFT in the tested regime.

## If you are completely new, start here

### What problem is this repository studying?

Suppose someone gives us a composite integer such as

```text
N = 15.
```

Factoring means finding smaller integers whose product is `N`:

```text
15 = 3 * 5.
```

Factoring small numbers is easy. Factoring carefully chosen very large
numbers is believed to be hard for ordinary computers and is the mathematical
problem behind RSA. Shor showed that an ideal fault-tolerant quantum computer
could factor integers in polynomial time. Regev later proposed a different
quantum factoring algorithm that reduces the asymptotic quantum gate count by
using several exponent registers and more substantial lattice-based classical
post-processing. See [Shor's original paper](https://doi.org/10.1137/S0097539795293172)
and [Regev's paper](https://arxiv.org/abs/2308.06572).

This repository does **not** factor cryptographically large integers. It takes
a public toy implementation inspired by Regev, reconstructs what it really
does, fixes correctness problems, implements the missing classical endpoint,
and tests several research ideas honestly enough to preserve negative results.

### The whole pipeline in plain English

```text
Choose N and stored roots b_i
          |
          v
Square each root: a_i = b_i^2 mod N
          |
          v
Prepare d quantum exponent registers
          |
          v
Compute products of a_i^x_i modulo N in superposition
          |
          v
Apply one QFT to each exponent register
          |
          v
Measure m Fourier samples
          |
          v
Build an augmented integer lattice from those samples
          |
          v
Run LLL to search for short multiplicative relations
          |
          v
Verify z is in L; distinguish L0 from L\L0 using stored roots
          |
          v
Use gcd(beta-1,N) and gcd(beta+1,N) to try to obtain factors
```

The quantum circuit does not directly print the factors. Its job is to produce
structured samples. The classical lattice stage must turn those samples into
a useful relation, verify it exactly, and only then attempt a greatest-common-
divisor calculation.

### The most important implementation lesson

The circuit uses squared bases

```text
a_i = b_i^2 mod N,
```

but factor extraction needs the particular roots `b_i` that produced them.
Knowing only `a_i` is not enough because a modular number can have several
square roots. The code therefore stores each pair `(b_i,a_i)` together in an
immutable `RootedBase` object. It never guesses a square root later.

For a concrete example, `4` is a nontrivial square root of `1 modulo 15`:

```text
4^2 = 16 = 1 mod 15.
gcd(4 - 1, 15) = 3
gcd(4 + 1, 15) = 5
```

That is the final number-theoretic mechanism. The hard part is recovering a
relation whose stored-root product gives a nontrivial square root such as `4`,
instead of the useless roots `+1` or `-1`.

## Beginner glossary

| Term | Meaning in this project |
|---|---|
| `N` | The odd composite integer we are trying to factor. |
| `n` | Bit length of `N`, computed as `N.bit_length()`. It is not the same as `N`. |
| `d` | Number of modular bases and exponent registers; also the relation-lattice dimension. Regev chooses it on the order of `sqrt(n)`. |
| `nd` | Number of qubits in each exponent register. The reproduced notebook mode uses `int(n/d + d)`; the audit also exposes a `ceil(2*n/d)` cover-`2n` mode instead of silently treating them as identical. |
| `M` | Number of values in one exponent/Fourier register. For `nd` qubits, `M=2^nd`. |
| `q` | In the QFT documents, shorthand for `log2(M)`, the number of qubits per Fourier register. Some older derivations use another symbol for total box size; always check the local definition. |
| `m` | Number of measured Fourier samples passed to classical recovery. This is different from `M`. |
| `S` | Scaling factor in the augmented lattice; theoretically tied to the inverse sample-noise bound. |
| `T` | Declared norm bound for target relation/embedding vectors in the Regev recovery condition. |
| `Delta` | Allowed loss in downstream recovery-event probability in the finite-shot QFT certificate. |
| Prime | An integer greater than one with no positive divisors except one and itself. |
| Composite | An integer that is a product of smaller positive integers. |
| Factor | A number that divides `N` without a remainder. |
| `gcd(x,N)` | Greatest common divisor. A value strictly between `1` and `N` is a proper factor of `N`. |
| Modulo `N` | Arithmetic where values differing by a multiple of `N` are identified. For example, `16 = 1 mod 15`. |
| Residue | The canonical representative of a value modulo `N`. |
| Coprime / unit | A value `a` with `gcd(a,N)=1`; it has a multiplicative inverse modulo `N`. |
| Root `b_i` | A selected coprime integer retained for final factor extraction. |
| Circuit base `a_i` | The squared residue `b_i^2 mod N` used by modular exponentiation. |
| Qubit | A quantum two-level system. A register is an ordered collection of qubits. |
| Ancilla | Temporary work qubits used by reversible arithmetic. Correct circuits normally return them to zero. |
| Superposition | A quantum state containing amplitudes for many computational basis values. |
| QFT | Quantum Fourier transform. It changes the basis so periodic/multiplicative structure can affect measurement probabilities. |
| Root of unity | A complex phase such as `exp(2*pi*i*j/M)` whose integer power returns to one. QFT amplitudes are sums of these phases. |
| Shot / sample / circuit execution | One preparation, circuit run, and measurement producing one Fourier vector. This README uses `m` for the number of samples given to recovery. |
| Relation `z` | An integer vector whose modular product of circuit bases equals one. |
| Lattice | A discrete additive subgroup generated by integer or rational basis vectors. Here lattices encode relations and approximate dual samples. |
| `L` | All exact multiplicative relations among the squared circuit bases. |
| `L0` | Relations in `L` whose stored-root product is `+1` or `-1`; valid but useless for splitting `N`. |
| `L\L0` | Factor-yielding relation classes: their stored-root product is a nontrivial square root of one. |
| Dual lattice `L*` | Vectors having integer inner product with every vector in `L`. Regev's ideal samples lie near dual-lattice cosets. |
| LLL | Lenstra–Lenstra–Lovász lattice-basis reduction: a polynomial-time algorithm that finds a shorter, better-conditioned basis, not necessarily the exact shortest vector. See the [original LLL paper](https://doi.org/10.1007/BF01457454). |
| BKZ | Block Korkine–Zolotarev reduction, a stronger and usually more expensive family of lattice-reduction methods. |
| HNF / SNF | Hermite and Smith normal forms, exact integer tools used to represent sublattices and quotient groups. |
| Quotient `L/L0` | Treats two relations as equivalent when their difference is in `L0`; the goal is to expose nontrivial factor-bearing classes. |
| Deflation | Suppressing or removing already verified `L0` directions so reduction/search may spend effort elsewhere. |
| LDAR | The studied loop: Lattice reduction, Deflation, and Adaptive Resampling. Its positive hypothesis was falsified at the frozen budget. |
| RV comparator | This repository's finite structural implementation inspired by Ragavan–Vaikuntanathan's corrupted-run filter; not a claim that their theorem applies. |
| Oracle | A component treated as a mapping; here modular exponentiation maps exponent vectors to residues. Model C also has generator-side oracle information that recovery is forbidden to see. |
| Hard-box state | Uniform amplitudes over a finite Cartesian exponent box. This is what the audited notebook prepares. |
| Discrete-Gaussian state | Amplitudes tapered according to a discrete Gaussian, as required by the Regev formulation being modeled. |
| Total variation distance | A number in `[0,1]` measuring how distinguishable two classical probability distributions are. |
| QFT cutoff `t` | Keeps controlled phases between qubits separated by at most `t`; larger-separation, smaller-angle rotations are omitted. |
| Factor-blind | The method may use `N`, bases, roots, samples, and declared parameters, but not the known factorization of `N`. |
| Development input | An input used while designing or debugging a method. |
| Held-out input | An input frozen before final evaluation and not used to tune the method. |
| Ablation | A controlled version of a method with one component removed. |
| Falsification condition | A result specified in advance that causes a proposed positive claim to be rejected. |

## Step-by-step mathematical story

### Step 1: choose roots and squared bases

Choose coprime values `b_1,...,b_d`, then compute

```text
a_i = b_i^2 mod N.
```

The code rejects a root that is not coprime to `N`. If a candidate already
shares a factor with `N`, that gcd has classically factored `N` during setup;
the event is labeled as a setup leak instead of being credited to the quantum
algorithm.

The repository does not call any selector “independence preserving.” In a
finite multiplicative group, generators necessarily satisfy relations, and
Regev's post-processing is specifically trying to recover short relations.
The meaningful questions are which relations exist, how short they are, and
whether their stored-root classes lie inside or outside `L0`.

### Step 2: define the modular-product map

For an integer exponent vector `x=(x_1,...,x_d)`, define

```text
h_A(x) = product_i a_i^(x_i) mod N.
```

Different exponent vectors can produce the same residue. Those collisions are
the arithmetic structure that produces interference after the QFT.

### Step 3: prepare the exponent state

The audited notebook applies Hadamard gates to every exponent qubit, producing
uniform amplitudes over a box `{0,...,M-1}^d`. Regev's paper instead uses a
discrete-Gaussian construction. The repository therefore treats the notebook
hard box and the finite Gaussian as different models rather than pretending
they are the same state.

### Step 4: compute modular exponentiation reversibly

The circuit computes `h_A(x)` without erasing `x`. Reversible modular
multiplication needs a result register and work/ancilla registers. The tests
check the arithmetic contract on its valid domain and check that ancillas are
cleaned up.

### Step 5: apply the multidimensional QFT

The transform is a tensor product of `d` one-register transforms:

```text
F_M tensor F_M tensor ... tensor F_M.
```

For inverse-QFT convention, the character at outcome `k` and input `x` is

```text
chi_k(x) = exp(-2*pi*i*<k,x>/M).
```

For one modular-exponentiation fiber `F_y={x:h_A(x)=y}`, all its character
phases add coherently. Different arithmetic outputs are orthogonal and their
probabilities add instead. This gives the exact finite law

```text
P_A(k) = M^(-2d) * sum_y |sum_{x in F_y} chi_k(x)|^2.
```

Constructive interference increases a measurement probability; destructive
interference cancels phases. QFT truncation changes these character sums
coherently before measurement. It is therefore not automatically equivalent
to randomly corrupting a few completed shots.

### Step 6: measure and decode

Each exponent register becomes an integer coordinate in `{0,...,M-1}`. Qiskit
uses little-endian qubit conventions, so swaps, classical-bit order, register
order, and forward/inverse signs must be audited together. The matrix tests
are designed to fail if these conventions are reversed.

### Step 7: build the augmented lattice

Write measured rows as `w_i=k_i/M`. For scale `S`, Regev's rational augmented
lattice has block form

```text
B = [[I_d, 0],
     [S W, S I_m]].
```

`lattice.py` clears denominators exactly, producing an integer row basis. It
does not silently round floats into a different lattice.

### Step 8: reduce with LLL

LLL produces a reduced basis and a unimodular transformation. The code checks
that the transformation really reconstructs the reduced basis. Regev's
Claim-5.1 Gram–Schmidt cutoff is evaluated with exact rational arithmetic.

### Step 9: verify, classify, and factor

Every proposed vector is checked by modular multiplication:

```text
z in L  iff  product_i a_i^(z_i) = 1 mod N.
```

If valid, the stored roots compute

```text
beta = product_i b_i^(z_i) mod N.
```

`beta=+1` or `-1` means `z in L0` and gives no factor. Otherwise the code
attempts the two gcds. Known factors are used only after the method returns a
pair, to validate the result.

## What the original notebook did versus what the repository adds

| Component | Original notebook | This repository |
|---|---|---|
| Explanation | Eighteen code cells and no markdown cells | Reports, derivations, tests, protocols, and this guide |
| Exponent state | Uniform hard box | Reproduced exactly and kept separate from finite Gaussian/model-C sampling |
| Base generation | Scans small primes; can reveal factors | Preserved for audit, with every leak explicitly labeled; adds factor-blind alternatives |
| Root provenance | Could be lost or misused in post-processing | Immutable `(b_i,a_i)` pairs throughout |
| Modular arithmetic | Imported external reversible gates | Gate contracts, domain, ancilla cleanup, and compiled resources tested |
| QFT | Mixed conventions in notebook cells | Direct roots-of-unity definition, Qiskit matrix validation, cutoff/noise models |
| Measurement | One cell measured too few qubits | Register ordering and decoding tested |
| Classical recovery | No complete Regev augmented-lattice endpoint | Exact cleared lattice, LLL transform, Claim-5.1 prefix, `L/L0`, gcd factors |
| Claims | Toy demonstrations could mix setup factoring and circuit evidence | Setup leaks, empirical endpoints, synthetic models, and theorem statements separated |

## Research timeline: what happened in each stage

### Stage 1: reconstruct the notebook

The code recovered register sizes, modular exponentiation behavior, QFT
conventions, measurement decoding, and imported dependencies directly from the
artifact. It found that the notebook was a uniform-box implementation and that
its demonstrated setup could discover factors classically while choosing
bases.

### Stage 2: dependency-aware base selection

The first intervention tried to choose squared bases with greater bounded
product diversity. This produced useful diagnostics, but the original bounded
search outcome was circular because the selector and evaluator examined the
same bounded relation box. The result is retained only as historical/audit
evidence.

### Stage 3: mandatory red-team revision

The revision permanently paired roots and bases, proved the chi-squared
identity as ordinary Parseval, implemented the real augmented-lattice
endpoint, separated hard-box/Gaussian/noisy-dual models, and evaluated six
base-selection ablations on frozen semiprimes. It found a negative
diversity/recovery association in models A and B but not C, so the observation
was not generalized to Regev's theorem regime.

### Stage 4: quotient-aware LDAR

The next hypothesis was that LLL wasted effort on short `L0` relations. Exact
integer quotienting, deflation, bounded enumeration, adaptive resampling, BKZ,
and RV-structured comparators were implemented under matched budgets. The
frozen 20-modulus study falsified the positive claim: complete LDAR was worse
than the reference under A/B/D and tied in saturated C.

### Stage 5: finite QFT/noise study

The first QFT study at `d=3,M=8,m=12` found that the five-percent certificate
selected exact QFT and that aggressive truncation reduced small-instance
factor recovery. Because a three-qubit QFT has only coarse cutoff choices,
this result was explicitly demoted to background.

### Stage 6: QFT precision scaling

The current study derived a scaling limit for the certificate and evaluated
all cutoffs across `d=2..5`, `M=8..128`, multiple sample counts, and three
loss budgets. The positive resource-saving claim was falsified for the primary
budget. The surviving result is the narrow no-certificate law described next.

## Papers and how they relate to this repository

These links are primary sources. Reading them is not required to run the code,
but they clarify which ideas belong to the literature and which results belong
only to this repository.

| Source | What it contributes | How this repository uses it |
|---|---|---|
| [Shor, *Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer*](https://doi.org/10.1137/S0097539795293172) | The foundational polynomial-time quantum factoring algorithm based on period finding. | Background and comparison only; this repository implements a Regev-style circuit, not Shor's algorithm. |
| [Regev, *An Efficient Quantum Factoring Algorithm*](https://arxiv.org/abs/2308.06572) | High-dimensional Gaussian sampling, the relation lattice, noisy-dual interpretation, augmented lattice, and classical lattice reduction. The paper describes roughly `sqrt(n)+4` independent circuit runs and a lower asymptotic gate count under a number-theoretic heuristic. | Supplies the mathematical target used to judge the notebook and build the classical endpoint. The repository does not claim to prove Regev's heuristic or reproduce the full asymptotic regime. |
| [Ragavan and Vaikuntanathan, *Space-Efficient and Noise-Robust Quantum Factoring*](https://eprint.iacr.org/2023/1501) | Space-efficient reversible arithmetic and a classical filter tolerating a constant fraction of corrupted quantum runs under stated hypotheses. | `rv_filter.py` implements a finite structural comparator. It explicitly does not claim the paper's theorem when the finite alpha/gamma, scale, well-spread-error, and recovery hypotheses are unmet. |
| [Coppersmith, *An Approximate Fourier Transform Useful in Quantum Factoring*](https://arxiv.org/abs/quant-ph/0201067) | Prior approximate-QFT truncation ideas for quantum factoring. | Establishes that approximate QFT is not novel here. This repository studies a particular distance cutoff and a conservative Regev-endpoint certificate. |
| [Nam, Su, and Maslov, *Approximate Quantum Fourier Transform with O(n log n) T Gates*](https://arxiv.org/abs/1803.04933) | Gate-efficient approximate-QFT constructions. | Literature boundary for resource claims; the repository does not claim a new general QFT synthesis algorithm. |
| [Pawlitko et al., *Implementation and Analysis of Regev's Quantum Factorization Algorithm*](https://arxiv.org/abs/2502.09772) | An independent implementation-oriented study emphasizing small-instance variability and practical costs. | Context for why toy success alone is not enough evidence for a broad algorithmic claim. |

The exact finite hard-box Parseval identity, generic operator telescoping, and
finite-shot hybrid argument used here are standard mathematics. The repository
claims only its narrow implementation corrections, frozen empirical findings,
and the explicit certificate-scaling characterization—not ownership of those
standard tools.

## Current status

The current contribution is an **Outcome-E negative scaling result**, not a
faster factoring algorithm:

```text
M < 4*pi*d*m/Delta
  => the implemented worst-case finite-shot certificate cannot certify
     any non-exact distance-truncated product QFT.
```

Here `d` is the number of exponent registers, `M=2^q` their Fourier modulus,
`m` is the number of quantum samples, and `Delta` is the allowed change in a
downstream recovery-event probability. For the frozen primary budget
`Delta=0.05`, the factor-blind selector chooses the exact QFT for every
`d in {2,3,4,5}`, `M in {8,16,32,64,128}`, and
`m in {4,8,12,24}` configuration.

This is a rigorous limitation of this operator-norm/hybrid **certificate**.
It is not a universal lower bound on approximate QFTs, a proof about Regev's
asymptotic Gaussian state, or a hardware-noise result.

Beginner interpretation: the first possible approximation removes only the
smallest-angle layer. Even that layer cannot pass this five-percent guarantee
unless `M` is at least `4*pi*d*m/Delta`. For `d=3`, `m=12`, and
`Delta=0.05`, the threshold is about `9,048`; because `M` is a power of two,
the first available value above it is `16,384`. The frozen experiment stops at
`M=128`, far below that threshold, so the selector is forced to keep the exact
QFT. This says the **bound is too conservative to authorize savings here**. It
does not say an unknown sharper, state-specific analysis could never do so.

The complete test suite currently reports **96 passed**.

## Read this first

The documents have a deliberate hierarchy:

1. [`QFT_PRECISION_SCALING_REPORT.md`](QFT_PRECISION_SCALING_REPORT.md) —
   current central result, experiments, resource accounting, and limitations.
2. [`QFT_PRECISION_THEORY.md`](QFT_PRECISION_THEORY.md) — exact omitted-phase
   formula, finite-shot hybrid proof, and certificate-scaling law.
3. [`QFT_PRECISION_PROTOCOL.md`](QFT_PRECISION_PROTOCOL.md) and
   [`QFT_ADVERSARIAL_AUDIT.md`](QFT_ADVERSARIAL_AUDIT.md) — frozen choices,
   falsification rules, matrix adversaries, and RV-comparator limitations.
4. [`REDTEAM_REVISION.md`](REDTEAM_REVISION.md) — authoritative account of the
   notebook reconstruction, root-provenance correction, three sampling models,
   and frozen base-selection red team.
   [`ROOT_PROVENANCE_RED_TEAM.md`](ROOT_PROVENANCE_RED_TEAM.md) isolates the
   corresponding metadata regression and its `N=437` reevaluation.
5. [`FROZEN_QUOTIENT_PROTOCOL.md`](FROZEN_QUOTIENT_PROTOCOL.md) and
   [`QUOTIENT_THEORY_AND_LITERATURE.md`](QUOTIENT_THEORY_AND_LITERATURE.md) —
   quotient-deflation preregistration and exact integer-quotient theory.
6. [`RESEARCH_REPORT.md`](RESEARCH_REPORT.md) — superseded first-stage analysis.
   Its early novelty and improvement language was withdrawn after red-teaming.

[`QFT_NOISE_CONTRIBUTION_REPORT.md`](QFT_NOISE_CONTRIBUTION_REPORT.md) records
the initial `d=3, M=8, m=12` QFT study. It is useful background but is
explicitly superseded as the central contribution by the scaling report.

## What is verified, falsified, and still open

### Verified implementation facts

- The original notebook prepares a finite uniform exponent box, not Regev's
  full discrete-Gaussian state.
- Its prime-root scan can reveal classical factors during setup; those events
  are now recorded as `setup_factor_leaks` and never counted as sample-based
  factoring success.
- Every selected circuit base `a_i=b_i^2 mod N` must retain the particular
  selected root `b_i`. Factor extraction now uses that stored root only.
- The earlier `N=437` “root-provenance obstruction” disappears when the chosen
  roots are retained; it is an implementation metadata requirement, not a new
  mathematical obstruction.
- The real endpoint constructs Regev's cleared augmented integer lattice,
  runs LLL, verifies candidates in `L`, distinguishes `L0` from `L\L0`, and
  extracts factors only from `L\L0`.
- Direct roots-of-unity QFT matrices agree with Qiskit's exact inverse-QFT
  matrices for `M<=16` to numerical precision. Tests detect reversed signs,
  missing swaps, wrong cutoffs, and coordinate-order mistakes.
- The hard-box chi-squared formula is an immediate finite-group
  autocorrelation/Parseval identity. No novelty is claimed for it.

### Falsified or negative experimental hypotheses

- A bounded-product-diversity selector did not establish a general
  base-selection improvement. Its apparent relationship with recovery is
  model-dependent and disappears in the theorem-consistent noisy-dual model.
- Complete quotient-aware LDAR did not beat matched exact-norm bounded
  enumeration on the frozen 20-modulus holdout. It was worse under sample
  models A, B, and D and tied in saturated model C.
- The five-percent QFT selector does not save controlled-phase gates anywhere
  in the frozen `d=2..5`, `M=8..128`, `m=4,8,12,24` grid.
- The finite RV-structured comparator does not establish that approximate-QFT
  error is equivalent to Ragavan–Vaikuntanathan sparse whole-run corruption;
  its theorem hypotheses are explicitly marked inapplicable in these toy
  cells.

### Not established

- No claim that this code is faster than Shor's or Regev's published method.
- No proof that all approximate QFTs fail; only the stated worst-case
  certificate has the derived barrier.
- No hardware experiment or calibrated device-noise result.
- No publication-priority or “breakthrough” claim.
- No generalization from the hard-box surrogate to Regev's full algorithm
  unless separately supported by the finite Gaussian or noisy-dual models.

## Mathematical objects

For stored roots `b_1,...,b_d` and squared circuit bases
`a_i=b_i^2 mod N`, define

```text
h_A(z) = product_i a_i^(z_i) mod N

L  = {z in Z^d : product_i a_i^(z_i) = 1 mod N}
L0 = {z in L   : product_i b_i^(z_i) is +1 or -1 mod N}
```

If `z in L\L0`, then `beta=product_i b_i^(z_i)` is a nontrivial square root
of unity modulo `N`; `gcd(beta-1,N)` or `gcd(beta+1,N)` yields a proper factor.

For `M=2^q`, the inverse product-QFT character is

```text
chi_k(x) = exp(-2*pi*i*<k,x>/M).
```

On a modular-exponentiation fiber `F_y={x:h_A(x)=y}`, the exact finite
measurement law is

```text
P_A(k) = M^(-2d) * sum_y |sum_{x in F_y} chi_k(x)|^2.
```

The distance cutoff `t` retains controlled phases with qubit separation
`r<=t`. Its one-register omitted-angle sum is

```text
eta(q,t) = pi * sum_{r=t+1}^{q-1} (q-r)/2^r.
```

The scaling study uses the dimensionless certificate variable

```text
B(d,M,m,t;Delta) = m * min(1, 2*d*eta(q,t)) / Delta.
```

The implemented theorem certifies a cutoff only when `B<=1`.

An exact `q`-qubit QFT has `q(q-1)/2` controlled-phase gates per register and
`d*q(q-1)/2` across all exponent registers, before transpilation. A cutoff `t`
retains

```text
d * sum_{r=1}^{min(t,q-1)} (q-r)
```

controlled phases. `t=q-1` is exact. Removing only the smallest-angle layer
uses `t=q-2` and saves exactly `d` logical controlled phases. Hardware or
transpiled savings can differ because the arithmetic circuit dominates and a
backend may decompose or optimize gates differently.

### The hard-box Parseval identity

For the notebook's uniform box, let `G=(Z/MZ)^d` be the finite Fourier outcome
group. Then:

- `P_A(k)` is the exact probability of measuring outcome `k`;
- `U(k)=M^(-d)` is the uniform probability;
- `r=x-x' mod M` is a difference between two exponent vectors;
- `K_A(r)` counts pairs with the same arithmetic output and difference `r`,
  including the finite triangular overlap weights.

Expanding the squared fiber amplitudes, grouping terms by `r`, and applying
finite-group character orthogonality gives

```text
chi^2(P_A || U) = M^(-2d) * sum_{r != 0} K_A(r)^2.
```

This says that deviation from a uniform Fourier law equals the energy in the
nonzero relation-collision kernel. It is a direct Parseval/collision-probability
identity, not a new theorem. The code retains it as an exact implementation
cross-check.

## Sampling models

The repository never pools these models under one label:

| Label | Meaning | Scope |
|---|---|---|
| A | Exact finite uniform hard-box state used by the notebook | Notebook surrogate |
| B | Exact finite, truncated discrete-Gaussian amplitude state | Closer to Regev state preparation, still finite/toy |
| C | Synthetic noisy dual-lattice samples satisfying the stated finite noise inequality | Classical theorem-model validation; generator oracle is hidden from recovery |
| D | Hard-box samples with readout/whole-shot corruption | Explicit surrogate, not gate-level or hardware noise |

The QFT work additionally separates controlled-phase truncation, coherent
phase bias, classical readout flips, and grid quantization. These mechanisms
are not treated as interchangeable noise parameters.

| QFT/noise mechanism | Where it happens | Mathematical effect | What the repository concludes |
|---|---|---|---|
| Controlled-phase truncation | Inside the QFT circuit | Removes a structured set of small rotations and changes all affected character sums coherently | Bounded by an operator/TV certificate; not assumed to be sparse bad shots |
| Coherent phase error | Before or during QFT | Systematic over/under-rotation produces correlated spectral bias | Bounded in state/TV distance; not automatically a geometric sample displacement |
| Readout bit flip | After the quantum state has been converted to measurement bits | Classical channel changes some recorded bits | Potentially calibratable/filterable, but distinct from lost pre-measurement interference |
| Fourier-grid quantization | Finite `M` resolution | Rounds a continuous/torus location to the nearest grid point | Has direct displacement bound `sqrt(d)/(2M)` and enters augmented-lattice noise geometrically |

## Repository layout

```text
regev_research/   16 Python modules for circuits, exact laws, lattices, and studies
scripts/           8 reproducible entry points
tests/            15 test files; 96 tests currently pass
results/          frozen raw and aggregate outputs
figures/          plots from the original and red-team studies
external/         audited arithmetic dependency at a fixed commit
*.ipynb           original and generated executable notebooks
*.md              reports, protocols, theory, and adversarial audits
```

## Library modules

| Module | Role |
|---|---|
| `core.py` | `RootedBase`/`RootedBaseFamily`, factor-blind modular math, bounded relation diagnostics, the superseded diversity selector, exact hard-box Fourier law, and stored-root factor extraction. |
| `circuits.py` | Qiskit circuit builder using the audited modular-exponentiation gates; supports exact or distance-truncated product QFTs and compiled resource reporting. |
| `qft_noise.py` | Direct roots-of-unity matrices, Qiskit matrix checks, exact/approximate fiber laws, four noise mappings, gate counts, omitted-angle formulas, dimensionless precision ratio, and factor-blind cutoff selectors. |
| `dual.py` | Factor-blind Cayley/HNF construction of `L` for oracle-side validation and theorem-consistent noisy-dual sample generation. The oracle is not passed to reconstruction. |
| `lattice.py` | Exact denominator clearing, integer augmented lattice, verified LLL transform, Claim 5.1 prefix, `L`/`L0` classification, and primary factor endpoint. |
| `redteam.py` | Exact hard-box and finite-Gaussian laws plus the six frozen rooted-base ablations. |
| `redteam_experiments.py` | Frozen 24-`N`, six-method, three-model study with within-`N` permutation and cluster-bootstrap inference. |
| `experiments.py` | Superseded first-stage experiments retained for audit reproduction. |
| `quotient.py` | Exact integer quotient `Z^d/U` by verified `L0` directions using HNF/SNF without unsafe floating projection or silent saturation. |
| `quotient_metrics.py` | Factor-blind oracle-side `L`, `L0`, quotient-gap, and bounded minimum diagnostics; never used as the recovery selector. |
| `quotient_predictors.py` | Joins frozen study rows and evaluates clustered predictor comparisons without rerunning recovery. |
| `quotient_recovery.py` | Cost-audited bounded enumeration, exact quotient deduplication, verified-`L0` suppression/deflation, LDAR, BKZ-or-labeled-surrogate, and matched baselines. |
| `quotient_experiments.py` | Frozen quotient-study parameters and four sample-model definitions. |
| `quotient_study.py` | Atomic/checkpointed 20-modulus held-out execution and aggregation. |
| `rv_filter.py` | Finite comparator with the lattice structure of Ragavan–Vaikuntanathan Algorithm 6.1; explicitly reports unmet theorem hypotheses. |
| `__init__.py` | Public exports for rooted bases, lattice/quotient operations, and QFT precision utilities. |

## Scripts

| Script | Purpose |
|---|---|
| `run_qft_precision_scaling.py` | Reproduces the current scaling grid, matrix audit, feasible exact-fiber endpoints, RV comparison, paired/clustered summaries, resources, and figures. |
| `run_qft_noise_experiment.py` | Reproduces the superseded first finite QFT/noise experiment and model-C/Qiskit validation rows. |
| `run_redteam.py` | Reproduces the frozen base-selection red-team study. |
| `run_quotient_study.py` | Runs the expensive quotient holdout; the checked-in run is already complete. |
| `analyze_quotient_study.py` | Reanalyzes the existing 117,760-row quotient table without rerunning recovery. |
| `run_research.py` | Reproduces the superseded first-stage analysis. |
| `build_revised_notebook.py` | Generates both revised notebook filenames from one Python source. |
| `execute_revised_notebook.py` | Executes the generated notebook with `allow_errors=False`. |

## Experimental results

### 1. QFT precision scaling — current result

Frozen analytic grid:

- `d={2,3,4,5}`;
- `M={8,16,32,64,128}`;
- `m={4,8,12,24}`;
- `Delta={0.05,0.10,0.20}`;
- every valid cutoff `t`.

There are 1,200 analytic cutoff rows, ten matrix-validation rows, 72 feasible
exact-fiber endpoint rows, 32 RV-comparator rows, 72 paired-`N` rows, and 24
whole-`N` cluster-bootstrap rows. Exact matrix overlap covers `M<=16`; exact
fiber/lattice endpoints cover `d=2`, `M<=32`, and `N={35,77,143}`. The
analytic certificate itself is independent of `N` and therefore is not a
24-semiprime empirical holdout.

The positive adaptive-QFT hypothesis is falsified at the primary five-percent
budget: every selected cutoff is exact and the selected logical
controlled-phase saving is zero. This does not prove physical failure of all
approximate QFTs; it identifies where this conservative certificate is
incapable of authorizing truncation.

### 2. Quotient-deflation holdout — completed, negative

The completed study contains 20 held-out semiprimes, four sampling models,
five sample-count budgets (`7..11`), 32 replicates per cell, 117,760 trial
rows, and 200 paired method comparisons. Every returned pair passed post-hoc
factor-manifest validation.

At 11 samples, mean factor-success rates across the 20 `N` values were:

| Method | A: hard box | B: finite Gaussian | C: noisy dual | D: corruption surrogate |
|---|---:|---:|---:|---:|
| Standard Claim-5.1 LLL | 0.181 | 0.130 | 0.950 | 0.161 |
| Exact-norm bounded enumeration reference | 0.273 | 0.216 | 0.950 | 0.247 |
| Verified BKZ + same enumeration | 0.300 | 0.233 | 0.950 | 0.247 |
| Exact augmented-row deflation | 0.181 | 0.130 | 0.950 | 0.161 |
| Complete sequential LDAR | 0.255 | 0.188 | 0.950 | 0.211 |
| Adaptive sampling without deflation | 0.273 | 0.216 | 0.950 | 0.247 |
| Root-blind post-hoc search | 0.273 | 0.216 | 0.950 | 0.247 |
| Quotient-gap scoring only | 0.273 | 0.216 | 0.950 | 0.247 |
| Random genuine extra samples | 0.277 | 0.222 | 0.950 | 0.225 |
| RV-structured comparator | 0.153 | 0.134 | 0.950 | 0.133 |

Complete LDAR was worse than the matched reference under A, B, and D and tied
in saturated model C. It did not reduce samples needed to reach the 0.8 target.
This is a bounded finite-study result, not a theorem that all quotient-aware
methods must fail.

### 3. Base-selection red team — background evidence

Across 24 frozen semiprimes, six root-selection methods, three sampling models,
and 32 trials per cell, bounded-product diversity was negatively associated
with lattice factor success in the hard-box and finite-Gaussian models
(Spearman approximately `-0.62` and `-0.68`) but not in the theorem-consistent
noisy-dual model (approximately `-0.06`). This model disagreement prevents a
general claim about Regev's algorithm and is now background evidence only.

### 4. Initial QFT/noise study — superseded background

For `d=3`, `M=8`, and `m=12`, the five-percent rule selected exact QFT and
aggressive truncation reduced small-instance factor recovery in both A and B.
That result motivated the scaling theorem; it is not the final contribution.

## Results on disk

| Directory | Contents |
|---|---|
| `results/qft_precision_scaling/` | Current configuration, 1,200 analytic rows, matrix rows, exact endpoints, paired and cluster-bootstrap comparisons, resource rows, RV rows, and two figures. |
| `results/qft_noise/` | First finite QFT/noise experiment: analytic/fiber/model-C/Qiskit/endpoint rows and two figures. |
| `results/quotient_study/` | Completed 20-`N` quotient run: 20 checkpoints, 117,760 trials/resources, per-`N` aggregates, 200 paired comparisons, manifest, hashes, and completion record. Approximately 1.1 GB. |
| `results/redteam/` | Frozen base families, exact A/B laws, 13,824 trial rows, per-`N` summaries, clustered statistics, configuration, and hashes. |
| `results/raw/`, `results/summary/` | Superseded first-stage distributions and analyses retained for reproducibility. |
| `figures/` | First-stage and base-selection red-team figures. New QFT figures live beside their result tables. |

## Notebooks

- `RegevImplementationAndTestingBuilding_work-3.ipynb` — original audited
  notebook: 18 code cells and no markdown cells.
- `RegevImplementationAndTestingBuilding_redteam_revision.ipynb`
- `RegevImplementationAndTestingBuilding_research_revision.ipynb`

The two revised notebook files are byte-identical and generated by
`scripts/build_revised_notebook.py`; their separate names exist for backward
compatibility. Edit the generator rather than hand-editing either notebook.

The revised notebook reflects the red-team reconstruction. The later quotient
and QFT scaling studies are reproducible Python studies and are not silently
presented as cells in that notebook.

## What should I run?

| Your goal | Command or file |
|---|---|
| Understand the project without running code | Read this README, then `QFT_PRECISION_SCALING_REPORT.md`. |
| Check that the installed code is healthy | Run the full pytest command below. |
| Reproduce the current contribution | Run `scripts/run_qft_precision_scaling.py`. |
| Inspect the original notebook audit | Open `REDTEAM_REVISION.md` and the revised notebook. |
| Reproduce the base-selection red team | Run `scripts/run_redteam.py`. |
| Inspect quotient-deflation results | Read `FROZEN_QUOTIENT_PROTOCOL.md` and `results/quotient_study/completion.json`. |
| Recompute quotient predictor summaries without the expensive holdout | Run `scripts/analyze_quotient_study.py`. |
| Work on QFT matrices/noise functions | Start with `regev_research/qft_noise.py` and `tests/test_qft_noise.py`. |
| Work on classical factor recovery | Start with `regev_research/lattice.py`, then `quotient_recovery.py`. |

## How to read an experiment row

Most CSV files use one row per method/configuration or one row per replicate.
Important columns include:

| Column idea | Interpretation |
|---|---|
| `N` | Composite input. Comparisons should normally be paired within the same `N`. |
| `model` | A/B/C/D sampling law. Never compare labels without checking their definitions. |
| `seed` / `replicate` | Makes the random draw reproducible. A replicate is not a new independent modulus. |
| `factor_pair` / success indicator | Whether the factor-blind endpoint returned a verified proper factorization. |
| `relation_class` | `L0`, `L_minus_L0`, or invalid/not in `L`. Only `L_minus_L0` can yield a factor. |
| `sample_count` / `m` | Number of quantum executions supplied to classical recovery. |
| `cutoff` | Maximum retained QFT qubit separation. `q-1` is exact for a `q`-qubit register. |
| `controlled_phase_gates` | Logical QFT controlled-phase count, not necessarily final hardware two-qubit count. |
| `runtime_seconds` | Measured local runtime for the recorded step. It is machine-dependent. |
| confidence interval | Sampling uncertainty for the stated unit. Cluster intervals resample whole `N` values. |

Success percentages from repeated shots at one `N` do not prove generalization
to other integers. That is why the reports aggregate at the modulus level and
why held-out `N`, not millions of pooled shots, is the relevant scientific
unit.

## Setup

### Prerequisites

You need:

- Git;
- Python 3 with virtual-environment support;
- enough disk space for dependencies and results;
- a shell. The commands below use macOS/Linux `bash`/`zsh` syntax.

The checked-in quotient results occupy about **1.1 GB**. Re-running that study
creates large checkpoint files. The current QFT scaling study is much smaller.

### Step 1: move into the repository

```bash
cd /path/to/regevs
```

Replace `/path/to/regevs` with the real folder containing this README.

### Step 2: create an isolated Python environment

```bash
python3 -m venv .venv
```

This creates `.venv/` so the research dependencies do not modify your global
Python installation.

Activate it if you want ordinary `python` and `pip` commands to use it:

```bash
source .venv/bin/activate
```

Activation is optional here because every command explicitly calls
`.venv/bin/python`.

### Step 3: install pinned dependencies

```bash
.venv/bin/python -m pip install -r requirements-research.txt
```

Important dependencies are Qiskit/Aer for circuits, NumPy/SciPy for numerical
work, SymPy for exact integer LLL/HNF/SNF, pandas/Matplotlib for analysis,
`fpylll` for verified BKZ experiments, notebook tooling, and pytest.

### Step 4: install the audited arithmetic dependency

Only do the clone command if `external/regev-quantum-algorithm/` is absent:

```bash
git clone --depth 1 https://github.com/Wlitkopa/regev-quantum-algorithm.git external/regev-quantum-algorithm
git -C external/regev-quantum-algorithm fetch --depth 1 origin a18f75d414485086db9b257407e0bd01f8a8f81c
git -C external/regev-quantum-algorithm checkout a18f75d414485086db9b257407e0bd01f8a8f81c
```

The external dependency currently resolves to commit
`a18f75d414485086db9b257407e0bd01f8a8f81c`. The requirements pin Qiskit,
Aer, NumPy, SciPy, pandas, Matplotlib, SymPy, notebook tooling, pytest,
`fpylll`, and `cysignals`.

### Step 5: run the tests before experiments

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python -m pytest -q
```

Expected final line:

```text
96 passed
```

`PYTHONPATH=.` tells Python that the current repository is an import root.
`MPLCONFIGDIR=/tmp/mpl` gives Matplotlib a writable cache directory and avoids
home-directory permission warnings.

## Reproduction

Run the full test suite:

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python -m pytest -q
```

Reproduce the current QFT scaling contribution:

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python scripts/run_qft_precision_scaling.py
```

This rewrites `results/qft_precision_scaling/`. The configuration currently
reports 1,200 analytic rows, ten matrix rows, 72 endpoint rows, 32 RV rows, 20
primary resource rows, 72 paired rows, and 24 cluster-bootstrap summary rows.
The main figures are `cutoff_scaling.png` and `recovery_transition.png`.

Reproduce the first finite QFT/noise experiment and base-selection red team:

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python scripts/run_qft_noise_experiment.py
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python scripts/run_redteam.py
```

The quotient holdout is already complete and expensive to regenerate. Analyze
its existing trial table without rerunning recovery:

```bash
PYTHONPATH=. .venv/bin/python scripts/analyze_quotient_study.py
```

Build and execute the revised notebook:

```bash
.venv/bin/python scripts/build_revised_notebook.py
.venv/bin/python -m ipykernel install --prefix .jupyter --name regev-research --display-name "Regev Research"
JUPYTER_DATA_DIR="$PWD/.jupyter/share/jupyter" \
IPYTHONDIR=/tmp/ipython MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl \
.venv/bin/python scripts/execute_revised_notebook.py
```

## Common beginner problems

### `ModuleNotFoundError: No module named 'regev_research'`

Run from the repository root and include `PYTHONPATH=.`:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q
```

### Missing `gates.r_haner` or modular-exponentiation imports

The external dependency is missing or at the wrong path. Confirm that this
file exists:

```text
external/regev-quantum-algorithm/gates/r_haner/modular_exponentiation.py
```

Then verify its commit:

```bash
git -C external/regev-quantum-algorithm rev-parse HEAD
```

Expected value:

```text
a18f75d414485086db9b257407e0bd01f8a8f81c
```

### Matplotlib says its cache directory is not writable

Prefix the command with:

```bash
MPLCONFIGDIR=/tmp/mpl
```

### Jupyter cannot find the `regev-research` kernel

Install the kernel from the repository environment:

```bash
.venv/bin/python -m ipykernel install --prefix .jupyter --name regev-research --display-name "Regev Research"
```

Then set `JUPYTER_DATA_DIR="$PWD/.jupyter/share/jupyter"` when executing the
notebook, as shown above.

### LLL or BKZ confusion

The primary lattice endpoint uses SymPy's exact integer LLL. BKZ comparisons
use `fpylll` only when the associated transformation can be verified. A
fallback is labeled as a deterministic surrogate and must not be reported as
BKZ.

### The quotient study is taking a long time or consuming disk space

That study is intentionally large and already has complete checked-in output.
Use `scripts/analyze_quotient_study.py` to analyze the existing CSV instead of
rerunning 117,760 recovery trials.

### A toy circuit factors `N`, so is the algorithm proven?

No. A toy success can result from easy group structure, setup gcd leakage, a
particularly favorable root relation, or repeated tuning on the same input.
Only the labeled sample-to-lattice endpoint counts as recovery evidence, and
even that evidence is scoped to the tested finite models and moduli.

## How to extend the project without invalidating it

When adding a new method or experiment:

1. Keep every chosen root permanently paired with its squared circuit base.
2. Never use known factors, group orders, arbitrary modular square roots, or a
   generator oracle inside selection/recovery unless the experiment is
   explicitly labeled oracle-side.
3. State the mathematical contract of the new function and test what the code
   actually computes.
4. Freeze moduli, seeds, parameter grids, budgets, and falsification rules
   before the final holdout.
5. Use `N` as the primary generalization unit; do not inflate significance by
   pooling shots from one modulus.
6. Compare at matched quantum samples and matched classical search budgets.
7. Verify `z in L` before classifying `L0` or attempting gcd extraction.
8. Separate hard-box, finite-Gaussian, theorem-consistent noisy-dual, and
   corruption-surrogate conclusions.
9. Label measured resources, analytic bounds, deterministic estimates, and
   simulator-only values separately.
10. Preserve negative results and narrow the claim instead of changing the
    endpoint after seeing holdout data.

## Primary references

- Peter W. Shor, [*Polynomial-Time Algorithms for Prime Factorization and
  Discrete Logarithms on a Quantum Computer*](https://doi.org/10.1137/S0097539795293172).
- Oded Regev, [*An Efficient Quantum Factoring Algorithm*](https://arxiv.org/abs/2308.06572).
- Seyoon Ragavan and Vinod Vaikuntanathan,
  [*Space-Efficient and Noise-Robust Quantum Factoring*](https://eprint.iacr.org/2023/1501).
- Don Coppersmith, [*An Approximate Fourier Transform Useful in Quantum
  Factoring*](https://arxiv.org/abs/quant-ph/0201067).
- Yunseong Nam, Yuan Su, and Dmitri Maslov, [*Approximate Quantum Fourier
  Transform with O(n log n) T Gates*](https://arxiv.org/abs/1803.04933).
- Przemysław Pawlitko, Natalia Moćko, Marcin Niemiec, and Piotr Chołda,
  [*Implementation and Analysis of Regev's Quantum Factorization
  Algorithm*](https://arxiv.org/abs/2502.09772).
- A. K. Lenstra, H. W. Lenstra Jr., and L. Lovász,
  [*Factoring Polynomials with Rational Coefficients*](https://doi.org/10.1007/BF01457454).

## Reproducibility and factor firewall

- Root/base families are immutable and validate `a_i=b_i^2 mod N`.
- Trial paths receive `N`, selected roots/bases, samples, and frozen budgets;
  known factors are kept in separate manifests and used only after a returned
  pair for validation.
- Model-C HNF data is generator-side oracle state and is never passed to
  reconstruction.
- Quotient outputs use atomic replacement and a completion record containing
  SHA-256 hashes.
- Random seeds, candidate pools, sample counts, noise levels, reduction
  budgets, and stopping criteria are written into the corresponding frozen
  configuration files.
- Resource tables distinguish measured runtimes and gate counts from explicit
  deterministic memory estimates.

This repository should be read as an auditable sequence of corrections and
falsification tests. Its strongest current result is a narrow precision-
certificate scaling law, with the boundary between proof, finite experiment,
and open hypothesis stated explicitly.
