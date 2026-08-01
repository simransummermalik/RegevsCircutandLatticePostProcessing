# What We Just Discovered: Factor-or-Fuse

## The headline

I developed a new **pre-circuit auditing and compilation method** for
Regev-style quantum factoring. Before spending quantum resources, the method
checks whether the circuit's modular bases contain a public mathematical
dependency and turns that dependency into either an immediate factor, a
smaller equivalent arithmetic circuit, or a certified return to the original
baseline.

The most surprising finding is that some published toy Regev inputs are much
easier than their nominal circuit dimension suggests. In the `N=15` example,
two advertised bases become identical modulo 15, collapsing a two-dimensional
arithmetic map to one effective dimension; their stored generating roots also
reveal the factors `3` and `5` before the quantum circuit is executed.

This is more than pointing out a coding mistake. The contribution is an
implemented algorithm, an exact mathematical certificate, a benchmark audit,
controlled held-out experiments, and a rigorous explanation of where the
method stops working.

---

## The problem in plain English

Regev-style factoring uses several exponent registers to calculate something
like

```text
a1^x1 * a2^x2 * ... * ad^xd  (mod N).
```

The number of registers is called the nominal dimension. But two different
looking bases can secretly represent the same modular behavior. For example,

```text
49 mod 15 = 4.
```

Therefore a circuit using bases `4` and `49` really calculates

```text
4^x1 * 49^x2 = 4^(x1+x2)  (mod 15).
```

The circuit has two exponent registers, but its arithmetic depends on only one
combination, `x1+x2`.

That can make a toy experiment look more successful than a genuinely
independent two-dimensional Regev instance.

---

## The new algorithm

We call the method **Factor-or-Fuse**.

Suppose the public bases satisfy

```text
aj = ai^k  (mod N).
```

Each base has a permanently stored generating root:

```text
ai = bi^2 mod N.
```

Factor-or-Fuse compares the particular stored roots—not arbitrary square
roots—and follows one of three branches:

```text
Detected public base dependency
              |
              v
Check its stored-root product R
              |
       +------+------+
       |             |
       v             v
R is a nontrivial    R is +1 or -1
square root of 1     modulo N
       |             |
       v             v
Factor N with GCD    Certified L0 dependency
before the circuit   and attempt exact fusion
                           |
                     +-----+-----+
                     |           |
                     v           v
                 cheaper       not cheaper
                     |           |
                     v           v
                 use fusion   use baseline
```

The method never receives the known factors, group orders, Euler's totient,
or planted relations.

---

## Why the mathematics works

Let

```text
z = k*ei - ej.
```

The public dependency proves that `z` is a valid relation among the squared
bases:

```text
product al^zl = 1 mod N.
```

Now evaluate the same relation with the specifically stored roots:

```text
R = product bl^zl mod N.
```

Because every base is the square of its root,

```text
R^2 = 1 mod N.
```

There are only two relevant outcomes:

- If `R` is not `+1` or `-1`, then `gcd(R-1,N)` and `gcd(R+1,N)` reveal
  proper divisors.
- If `R` is `+1` or `-1`, the relation belongs to `L0`. It does not directly
  yield a factor, but it may be removed from the arithmetic while preserving
  the exact factor-bearing quotient `L/L0`.

The nontrivial-square-root GCD fact is classical. What may be original is the
complete stored-root-aware decision rule, exact quotient-preserving compiler,
automatic fallback, and its use as a Regev benchmark-integrity audit.

---

## The published toy-input finding

### `N = 15`

The audited input uses

```text
roots: 2 and 7
bases: 4 and 49
```

Modulo 15, both bases equal 4. The short relation is

```text
z = (1, -1).
```

Using the stored roots gives

```text
R = 2 * inverse(7) mod 15 = 11.
```

Then

```text
11^2 mod 15 = 1
gcd(11 - 1, 15) = 5
gcd(11 + 1, 15) = 3.
```

So this particular `N=15` base family already contains a public
factor-yielding relation. Its nominal two-dimensional arithmetic also has only
one effective modular direction.

### `N = 21`

The first-coprime-prime-square rule retains roots `[2,5,11]`, whose bases are
`[4,25,121]`. Modulo 21, the first two bases are both 4, and their stored roots
return factors `3` and `7`.

This does not mean that Regev's algorithm is wrong or that every experiment in
the papers is invalid. It means these smallest inputs are structurally easier
than their nominal dimensions imply and should be disclosed or excluded when
making general benchmark claims.

---

## The frozen held-out test

We froze 24 previously untouched semiprimes before running the method.

Every case used:

```text
d = 4 exponent dimensions
q = 8 qubits per exponent register
roots = [2, 3, 5, 7]
bases = [4, 9, 25, 49]
relation bound K = 64
```

The factors were isolated from the method and loaded only after raw results
were written and hashed.

### What actually happened

| Outcome | Number of moduli |
|---|---:|
| Immediate factors | 0 |
| Profitable exact fusions | 1 |
| Baseline fallbacks | 23 |

The preregistered hypothesis required at least 6 actionable moduli and a
strictly positive lower bootstrap bound. It **failed**.

Across all 24 moduli:

```text
mean canonical-CX saving: 0.354%
median saving: 0%
95% N-level bootstrap interval: [0%, 1.062%]
certificate failures: 0
```

### The one successful fusion

For `N=35237`, the method discovered

```text
4^27 = 25 mod 35237.
```

The stored-root value was `-1`, so the relation was safely inside `L0` rather
than factor-yielding.

| Resource | Baseline | Fused |
|---|---:|---:|
| Canonical CX | 6,320,402 | 5,783,248 |
| Full-width multiplier calls | 32 | 29 |
| Extra clean qubits | 0 | 14 |

This saved `537,154` canonical CX gates, or `8.50%`, at the cost of 14 extra
qubits.

---

## The all-witness correction

The first implementation stored only the earliest exponent reaching each
target. Red-team testing showed that this can lose useful information.

For

```text
N = 3277 = 29 * 113,
```

the same ordered base pair produced:

```text
k = 8   -> valid but non-factor-yielding L0 relation
k = 64  -> factor-yielding relation
```

The final variant therefore retains and classifies **every witness up to K**
before deciding whether to factor or fuse. This found the factor missed by the
earliest-witness policy without increasing the number of modular-power steps.

On the original 24 held-out inputs, the all-witness correction did not change
the overall result: 0 factors, 1 fusion, and 23 fallbacks.

---

## Does the method scale?

The descriptive follow-up census tested 1,700 deterministic semiprimes from
12 through 2048 bits with the same bound `K=64`.

| Bit length | Inputs with a detected dependency |
|---:|---:|
| 12 | 50/100 |
| 16 | 4/100 |
| 20 | 1/100 |
| 24 through 2048 | 0/1,400 |

At 1024 bits and above, an exact no-wrap certificate proved that this bounded
positive pair-power detector could not activate for any tested standard
small-prime family.

This gives the honest interpretation:

> Factor-or-Fuse is valuable for catching misleading toy instances and can
> occasionally reduce finite arithmetic cost, but fixed-bound pair-power
> fusion is not a scalable Regev factoring speedup under the standard
> small-prime rule.

The census is deterministic and reuses some factors inside each bit-length
stratum. Its proportions are descriptive, not estimates from an independent
random population.

---

## Why this result matters

1. **Benchmark integrity:** circuit dimension alone does not establish
   independent arithmetic dimension.
2. **Root provenance:** storing only squared bases can erase the information
   that distinguishes a useless relation from a factor.
3. **Quantum resource protection:** some inputs can be factored before any
   circuit is built.
4. **Compiler correctness:** safe dependencies can be fused exactly, with
   accumulator cleanup and a no-regression cost check.
5. **Scientific honesty:** the held-out hypothesis failed, revealing the
   boundary between an important toy-benchmark phenomenon and a scalable
   algorithmic improvement.

---

## The strongest defensible research claim

> We introduce Factor-or-Fuse, a stored-root-aware preprocessing and
> compilation procedure for Regev-style modular arithmetic. The procedure
> converts bounded public base dependencies into either immediate factor
> certificates, exact quotient-preserving `L0` fusions, or certified baseline
> fallbacks. It exposes rank-collapsed, pre-factorable published toy inputs,
> while held-out and scaling experiments establish that fixed-bound pair-power
> activation does not generalize under the standard small-prime rule.

This is not a claim of a new number-theoretic factoring theorem, a generic
Regev speedup, or a replacement for lattice post-processing.

---

## Verification

The complete repository test suite passed:

```text
181 tests passed
25 subtests passed
```

Run the focused study:

```bash
source .venv/bin/activate
export MPLBACKEND=Agg
export MPLCONFIGDIR=/tmp/mpl

python -m pytest tests/test_orbit_fusion.py -q
python -m factor_or_fuse_study.run_study
python -m factor_or_fuse_study.run_all_witness_sensitivity
python -m factor_or_fuse_study.run_scaling_census
```

## Where everything is

- Full technical explanation: [`README.md`](README.md)
- Frozen protocol: [`PROTOCOL.md`](PROTOCOL.md)
- Main implementation: [`../regev_research/orbit_fusion.py`](../regev_research/orbit_fusion.py)
- Held-out results: [`results/heldout_per_arm.csv`](results/heldout_per_arm.csv)
- Scaling census: [`results/scaling_census/per_modulus.csv`](results/scaling_census/per_modulus.csv)
- Generated figures: [`results/figures`](results/figures)

## Primary papers

- [Regev, *An Efficient Quantum Factoring Algorithm*](https://arxiv.org/abs/2308.06572)
- [Ragavan and Vaikuntanathan, *Space-Efficient and Noise-Robust Quantum Factoring*](https://arxiv.org/abs/2310.00899)
- [Pawlitko et al., *Implementation and Analysis of Regev's Quantum Factorization Algorithm*](https://reference-global.com/download/article/10.2478/qic-2026-0012.pdf)
- [Falcó et al., *From Period Finding to Lattice Sampling*](https://arxiv.org/abs/2606.17647)
- [Rabin, *Digitalized Signatures and Public-Key Functions as Intractable as Factorization*](https://publications.csail.mit.edu/lcs/pubs/pdf/MIT-LCS-TR-212.pdf)
