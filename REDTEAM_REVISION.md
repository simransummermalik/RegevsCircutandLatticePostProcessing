# Mandatory red-team revision

## Status

This document supersedes the contribution and novelty conclusions in
`RESEARCH_REPORT.md`. The work is **not publication-ready**. The red team found
that:

1. the hard-box chi-squared formula is an immediate finite-group
   autocorrelation/Parseval identity, not a novel theorem;
2. the earlier (N=437) “root-provenance obstruction” disappears when Regev's
   chosen roots are retained correctly and is therefore an implementation
   metadata requirement;
3. the old bounded-relation endpoint was circular with the selector score;
4. the negative diversity association survives a genuine LLL endpoint for the
   notebook hard box and a finite exact Gaussian state, but does **not** survive
   theorem-compliant synthetic noisy-dual samples.

No breakthrough, priority, or novelty claim is made.

## 1. Three separately labeled claims

### Claim 1 — verified implementation correction

Every selected root (b_i) is now stored permanently in an immutable pair
((b_i,a_i)), where (a_i=b_i^2mod N). The circuit uses the (a_i), while
post-processing uses only the paired (b_i). The revised endpoint implements


```text
raw samples
→ exact augmented integer lattice
→ integer LLL
→ Regev Claim 5.1 Gram–Schmidt prefix
→ projected candidate z
→ exact z ∈ L check using a_i
→ L versus L_0 check using the stored b_i
→ gcd extraction only for L \ L_0.
```

It does not compute modular square roots, accept arbitrary replacement roots,
use known factors, use group orders, or use the ground-truth relation lattice.

### Claim 2 — verified empirical result for the uniform-box notebook

On 24 previously unused composite inputs, treating (N) as the generalization
unit, bounded-product diversity is negatively associated with the probability
that the actual augmented-lattice/LLL endpoint returns a factor under the
uniform hard-box model:


\[
\rho_{\mathrm{Spearman}}=-0.624,
\qquad
\text{(N)-cluster bootstrap CI }[-0.769,-0.422],
\qquad
p_{\mathrm{within}\ N}=10^{-4}.
\]

This is an association across the six frozen methods, not proof that the
complete selector is worse than Regev's small-prime roots. Their paired mean
difference is (-0.130), with (N)-bootstrap CI
([-0.286,0.016]) and sign-flip (p=0.122). The direct comparison is therefore
inconclusive at the 5% level.

### Claim 3 — unverified hypothesis concerning full Regev sampling

The same negative association appears for the exactly evaluated *finite*
discrete-Gaussian amplitude state at (D=64,R=16), but those toy parameters do
not satisfy Regev's asymptotic recovery inequality. Under synthetic samples
that do satisfy the bounded noisy-dual premise and sufficient inequality, the
association disappears:


\[
\rho=-0.059,
\qquad
\text{(N)-cluster bootstrap CI }[-0.201,0.099],
\qquad
p_{\mathrm{within}\ N}=0.388.
\]

Accordingly, there is no verified negative claim about Regev's full algorithm.
At most, it remains an unverified hypothesis that base-family structure may
matter in finite-precision or resource-constrained Gaussian implementations.

## 2. Exact separation of mathematical objects

Let the algorithm select and retain an ordered root family


\[
B=(b_1,\ldots,b_d),\qquad \gcd(b_i,N)=1.
\]

The circuit bases are derived, not selected independently:


\[
A=(a_1,\ldots,a_d),\qquad a_i=b_i^2\bmod N.
\]

Define the modular-product homomorphism


\[
h_A:\mathbb Z^d\longrightarrow(\mathbb Z/N\mathbb Z)^\times,
\qquad
h_A(z)=\prod_{i=1}^d a_i^{z_i}\bmod N.
\]

The relation lattice depends only on (A):


\[
L=L_A=\ker h_A
=\left\{z\in\mathbb Z^d:
\prod_i a_i^{z_i}\equiv1\pmod N\right\}.
\]

For the retained roots define


\[
\beta_B(z)=\prod_i b_i^{z_i}\bmod N.
\]

The root-dependent sublattice is


\[
L_0(B)=\left\{z\in L:\beta_B(z)\in\{1,-1\}\pmod N\right\}.
\]

For a declared Euclidean norm bound (T), the short relations are


\[
S_T(L)=\{z\in L\setminus\{0\}:\|z\|_2\le T\},
\]

whereas the short factor-yielding relations are


\[
F_T(B)=S_T(L)\setminus L_0(B).
\]

If (z\in L\), then (eta_B(z)^2=1mod N). If additionally
(eta_B(z)\notin\{1,-1}), a proper factor is obtained from
(gcd(\beta_B(z)-1,N)) or (gcd(\beta_B(z)+1,N)).

Membership in (L) is an (A)-only statement. Membership in (L_0) and
factor extraction require the specifically selected (B).

## 3. Exact hard-box definitions

Assume every (a_i) is a unit. Let


\[
X=\{0,\ldots,M-1\}^d,
\qquad
G=(\mathbb Z/M\mathbb Z)^d,
\qquad
q=|G|=M^d.
\]

For the inverse-QFT convention use the characters


\[
\chi_k(x)=\exp\!\left(-\frac{2\pi i\langle k,x\rangle}{M}\right),
\qquad k,x\in G.
\]

The pre-QFT hard-box state is


\[
|\psi_A\rangle=q^{-1/2}\sum_{x\in X}|x\rangle|h_A(x)\rangle.
\]

The following definitions are exact:

- (P_A(k)) is the probability that Fourier measurement returns (k\in G):

  \[
  P_A(k)=q^{-2}\sum_{x,x'\in X}
  \mathbf1[h_A(x)=h_A(x')]\chi_k(x-x').
  \]

- (U) is the uniform distribution on (G):

  \[
  U(k)=q^{-1}=M^{-d}.
  \]

- (r) is a residue class in (G). It is **not** an integer relation. Integer
  relations are written (z\in L).

- (K_A(r)) is the collision count separated by modular lag (r):

  \[
  K_A(r)=
  \sum_{x,x'\in X}
  \mathbf1[h_A(x)=h_A(x')]
  \mathbf1[(x-x')\bmod M=r].
  \]

  Equivalently,

  \[
  K_A(r)=
  \sum_{\substack{z\in L\\|z_i|<M\ \forall i\\z\bmod M=r}}
  \prod_{i=1}^d(M-|z_i|).
  \]

The triangular factor counts the ordered pairs in (X^2) with integer
difference (z). Because (|z_i|<M), the only such vector congruent to zero
modulo (M) is (z=0). Hence


\[
K_A(0)=|X|=q.
\]

## 4. Line-by-line proof of the chi-squared identity

For each oracle output (y), define the fiber


\[
F_y=\{x\in X:h_A(x)=y\}.
\]

After the inverse QFT, the joint amplitude of ((k,y)) is


\[
q^{-1}\sum_{x\in F_y}\chi_k(x).
\]

Therefore


\[
\begin{aligned}
P_A(k)
&=q^{-2}\sum_y\left|\sum_{x\in F_y}\chi_k(x)\right|^2\\
&=q^{-2}\sum_y\sum_{x,x'\in F_y}\chi_k(x-x')\\
&=q^{-2}\sum_{x,x'\in X}
  \mathbf1[h_A(x)=h_A(x')]\chi_k(x-x')\\
&=q^{-2}\sum_{r\in G}K_A(r)\chi_k(r).
\end{aligned}
\]

For the unnormalized finite Fourier transform


\[
\widehat K_A(k)=\sum_{r\in G}K_A(r)\chi_k(r),
\]

this is (P_A(k)=q^{-2}\widehat K_A(k)).

Define the centered kernel


\[
f_A(r)=K_A(r)-q\,\mathbf1[r=0].
\]

Since (K_A(0)=q), (f_A(0)=0) and (f_A(r)=K_A(r)) for
(r\ne0). The transform of (q\mathbf1[r=0]) is the constant (q), so


\[
P_A(k)-U(k)=q^{-2}\widehat f_A(k).
\]

Apply the Pearson definition:


\[
\begin{aligned}
\chi^2(P_A\|U)
&=\sum_{k\in G}\frac{|P_A(k)-q^{-1}|^2}{q^{-1}}\\
&=q\sum_{k\in G}|P_A(k)-U(k)|^2\\
&=q^{-3}\sum_{k\in G}|\widehat f_A(k)|^2.
\end{aligned}
\]

Character orthogonality gives


\[
\sum_{k\in G}\chi_k(r)\overline{\chi_k(s)}
=q\,\mathbf1[r=s].
\]

Thus


\[
\begin{aligned}
\sum_k|\widehat f_A(k)|^2
&=\sum_{r,s}f_A(r)\overline{f_A(s)}
  \sum_k\chi_k(r)\overline{\chi_k(s)}\\
&=q\sum_r|f_A(r)|^2.
\end{aligned}
\]

Substitution yields


\[
\boxed{
\chi^2(P_A\|U)
=q^{-2}\sum_{r\ne0}K_A(r)^2
=M^{-2d}\sum_{r\ne0}K_A(r)^2.
}
\]

### Classification of the identity

This is an immediate finite-group Wiener–Khinchin/Parseval calculation:

1. the oracle-fiber collision indicator creates an autocorrelation;
2. character orthogonality gives its Fourier representation;
3. Parseval equates squared Fourier and lag-domain energy.

It is also the standard collision-probability formula


\[
\chi^2(P_A\|U)=q\sum_kP_A(k)^2-1
=q\operatorname{Col}(P_A)-1.
\]

The notation (K_A) is useful for auditing the notebook, but no mathematical
novelty is claimed. All 288 exact A/B distributions numerically satisfy their
weighted Parseval identity; maximum absolute errors are
(1.14\times10^{-13}) for A and (2.79\times10^{-10}) for B.

## 5. Weighted identity and the exact Gaussian state

Regev's finite initial state uses amplitudes, not probabilities,


\[
g_R(x)=\rho_R(x)=\exp(-\pi\|x\|^2/R^2),
\qquad
x\in\{-D/2,\ldots,D/2-1\}^d.
\]

Let


\[
Z_R^2=\sum_xg_R(x)^2.
\]

The exact finite Gaussian-state output law evaluated in model B is


\[
P_{A,R,D}(k)=
\frac{1}{D^dZ_R^2}
\sum_{x,x'}g_R(x)g_R(x')
\mathbf1[h_A(x)=h_A(x')]
e^{-2\pi i\langle k,x-x'\rangle/D}.
\]

The circuit's (D/2) shift of every exponent changes only a fiber label and a
global Fourier phase, not this probability law. The weighted lag kernel uses
the finite amplitude autocorrelation


\[
C_R(z)=\sum_xg_R(x)g_R(x+z)
\]

on the valid overlap. Parseval then gives


\[
\chi^2(P_{A,R,D}\|U)
=\frac{\sum_{r\ne0}K_{A,R}(r)^2}{(Z_R^2)^2}.
\]

This weighted formula is again standard Parseval, not a new theorem.

## 6. Root retention and the (N=437) reevaluation

The implementation now exposes immutable `RootedBase` and
`RootedBaseFamily` objects. Constructing `RootedBase(N,b,a)` fails unless


\[
a=b^2\bmod N.
\]

Selection returns the family object; circuit construction reads its bases;
lattice post-processing accepts that same family object; factor extraction
reads its roots. Parallel, freely replaceable root/base lists are not used by
the primary endpoint.

For (N=437=19\cdot23), (A=(4,9,85)), and (u=(1,1,1)),


\[
4\cdot9\cdot85\equiv1\pmod{437},
\]

so (u\in L).

- Stored roots (B=(2,3,73)) give
  (eta_B(u)=438\equiv1), hence (u\in L_0) and no factor.
- Stored roots (B'=(2,3,326)) give
  (eta_{B'}(u)=208), hence (u\in L\setminus L_0), with

  \[
  \gcd(207,437)=23,\qquad \gcd(209,437)=19.
  \]

Both root families happen to square to the same (A), but they are different
valid algorithm inputs. With correct metadata, both are classified correctly.
The example is therefore a regression test for root retention, not an
algorithmic obstruction or novelty claim.

## 7. What “bounded multidimensional relation recovery” meant

The old diagnostic enumerated one canonical representative of every pair
({u,-u}) in


\[
[-B,B]^d\setminus\{0\}.
\]

There are (((2B+1)^d-1)/2) such candidates. Each received the empirical
character score


\[
\widehat m(u)=\frac1s\sum_{j=1}^s
\cos\!\left(\frac{2\pi\langle k_j,u\rangle}{M}\right).
\]

The highest score was called recovered, and success was evaluated by the exact
factor-blind check (h_A(u)=1).

It used:

- brute-force enumeration: **yes**;
- an (L)-membership oracle for evaluation: **yes**, implemented by modular
  multiplication;
- LLL or BKZ: **no**;
- known factors: **no**;
- known group orders: **no**;
- planted relations in the primary cells: **no**.

Because the selector also scored the same bounded product box, this endpoint
was circular. It is now only a diagnostic and is absent from all confirmatory
statistics below.

## 8. Actual samples-to-lattice construction

Take (m=d+4) raw independent samples


\[
w_i=v_i+e_i\pmod{\mathbb Z^d},
\quad
v_i\stackrel{\$}{\leftarrow}L^*/\mathbb Z^d,
\quad
\|e_i\|_2<\delta.
\]

Put the rows (w_i^T) into (W\in\mathbb R^{m\times d}). Regev's augmented
lattice is generated by the columns of


\[
B_S=
\begin{pmatrix}
I_d&0\\
SW&SI_m
\end{pmatrix}.
\]

Its vectors have the form


\[
\begin{pmatrix}z\\S(Wz+q)\end{pmatrix},
\qquad z\in\mathbb Z^d,\quad q\in\mathbb Z^m.
\]

For grid samples (w_i=y_i/D) and an exact rational scale (S=p/q), the
implementation clears denominators:


\[
qD B_S=
\begin{pmatrix}
qD I_d&0\\
pY&pD I_m
\end{pmatrix}.
\]

SymPy's integer row-LLL receives the transpose. `lll_transform` retains the
unimodular coefficient matrix, so the first (d) coefficients recover the
integer projection (z) exactly. Floating-point LLL is not used.

For lattice dimension (k=d+m), Regev's Claim 5.1 retains the LLL prefix before
the first Gram–Schmidt vector satisfying


\[
\|\widetilde b_{\ell+1}\|\ge2^{k/2}T_{\rm aug}.
\]

The code computes the Gram–Schmidt norms as exact rational numbers and compares
against the integer-cleared squared threshold


\[
(qD)^2,2^kT_{\rm aug}^2.
\]

Only prefix vectors feed the primary factor result. Scanning the complete LLL
basis is stored separately as a non-primary diagnostic. Every projected vector
must pass (h_A(z)=1) before its stored-root product is inspected.

For A and B the frozen (T_{\rm aug}) retained all ten reduced rows; invalid
projections were still rejected exactly. For C the Claim 5.1 prefix length was
three in every trial.

## 9. Three sampling models

### A. Notebook uniform hard box

The exact notebook state type is evaluated with (d=3,D=64), uniform
amplitudes, exact oracle fibers, and an exact tensor QFT law. (D=64) also
matches the notebook-style width rule for these 11–12 bit inputs at (d=3).

### B. Exact finite Regev discrete-Gaussian state

The finite state


\[
\sum_{z\in[-32,32)^3}\rho_{16}(z)|z\rangle
\]

is evaluated exactly by finite autocorrelation and FFT. The parameters satisfy


\[
2\sqrt dR\le D<4\sqrt dR.
\]

Models A and B use the same seven samples and reconstruction scale (S=13).
Here “exact finite” means that no dual-sample approximation or Monte Carlo
state simulation replaces the finite circuit law; the transcendental Gaussian
weights and FFT are evaluated in double precision, with the reported Parseval
residuals auditing numerical roundoff.
This is a controlled finite-state comparison. Its recovery parameters do not
satisfy Regev's asymptotic sufficient inequality, so B is not a theorem-backed
execution of the full factoring algorithm.

### C. Synthetic theoretical noisy-dual samples

The generator constructs the true (L) without factors or orders by:

1. breadth-first enumeration of the image of (h_A);
2. Cayley-edge kernel relations;
3. exact column Hermite normal form;
4. verification that (det L=|\operatorname{im}h_A|).

It draws (v) uniformly from (L^*/\mathbb Z^d), adds a random error of norm
at most (delta/2), and rounds to a power-of-two grid whose quantization error
is at most (delta/4). Thus every returned sample is within (3\delta/4) of
its generating dual coset.

The scale (S=\delta^{-1}) is selected from the conservative bound
(det L\le N), with safety factor two, so every C cell satisfies


\[
\sqrt{d+m},2^{(d+m)/2}\sqrt{m+1},T
<S(4N)^{-1/m}/6.
\]

Across C cells, (S) ranges from 271,380 to 380,044 and (D) from
(2^{20}) to (2^{21}). The true HNF is confined to the generator and never
passed to LLL recovery. C satisfies the bounded-noise model, but its error is
uniform in a ball rather than the exact periodic Gaussian (Q_v).

## 10. Frozen held-out design

### Inputs

The following 24 semiprimes were frozen before their experiment was run:

| (N) | Factors used only for post-hoc validation | (N) | Factors used only for post-hoc validation |
|---:|---:|---:|---:|
| 1927 | (41\cdot47) | 2173 | (41\cdot53) |
| 2279 | (43\cdot53) | 2419 | (41\cdot59) |
| 2491 | (47\cdot53) | 2501 | (41\cdot61) |
| 2537 | (43\cdot59) | 2623 | (43\cdot61) |
| 2747 | (41\cdot67) | 2773 | (47\cdot59) |
| 2867 | (47\cdot61) | 2881 | (43\cdot67) |
| 2911 | (41\cdot71) | 2993 | (41\cdot73) |
| 3053 | (43\cdot71) | 3127 | (53\cdot59) |
| 3139 | (43\cdot73) | 3149 | (47\cdot67) |
| 3233 | (53\cdot61) | 3337 | (47\cdot71) |
| 3431 | (47\cdot73) | 3551 | (53\cdot67) |
| 3599 | (59\cdot61) | 3763 | (53\cdot71) |

All prime factors exceed the largest candidate root, 37. No selector setup
found a GCD factor.

### Exclusions and development use

- All original-analysis or notebook inputs were excluded:
  (15,21,57,169,247,289,299,323,361,391,437,2021,4199,7429).
- (N=1763) was used for pre-freeze feasibility tests of (D,R,S) and was
  excluded from confirmation.
- Even and prime inputs were excluded by design.
- No held-out cell, seed, sample, or (N) was excluded after execution.

### Frozen parameters

| Quantity | Frozen value/rule |
|---|---|
| Generalization unit | (N) |
| Dimension | (d=3) |
| Samples per LLL trial | (m=d+4=7) raw IID samples |
| Repeats within each (N\times)method(	imes)model cell | 32, used only to estimate its success probability |
| Candidate roots | ([2,3,5,7,11,13,17,19,23,29,31,37]) |
| Selector relation bound | (B=2) |
| A/B register and Gaussian radius | (D=64,R=16) |
| A/B reconstruction scale | (S=13) |
| Relation norm bound | (T=\lceil\sqrt d,2^{\operatorname{bitlength}(N)/d}\rceil) |
| Claim 5.1 augmented bound | (T_{\rm aug}=\lceil\sqrt{d+5},T\rceil) |
| Master seed | 2,026,071,101 |

For instance index (i), method index (j), model index (k), and trial (t),


\[
\text{seed}=2026071101+10{,}000{,}000i+100{,}000j+1000k+t.
\]

All 13,824 trial seeds are distinct and stored. Selection seeds use the same
formula with model index 99.

### Parameter tuning

There are no fitted selector weights. The complete selector is lexicographic.
(D=64,R=16) were fixed using Regev's (D/R) interval and exact-enumeration
feasibility on the excluded input (N=1763). (S=13) is the shared integer
approximation to (sqrt2R/\sqrt d). No held-out outcome was used for tuning.

## 11. Six-method ablation

All methods start with the same root pool and return immutable root/base pairs.

1. **Residue deduplication only:** take roots in pool order, rejecting only a
   repeated squared residue.
2. **Short-relation rejection only:** greedily minimize the number of canonical
   nonzero relations in ([-2,2]^j/\{\pm1\}) after each addition.
3. **Subgroup-overlap scoring only:** greedily minimize

   \[
   \frac{|\langle a_i\rangle\cap\langle a_j\rangle|}
   {\min(|\langle a_i\rangle|,|\langle a_j\rangle|)}
   \]

   averaged over selected pairs. Orbits are enumerated by multiplication,
   without a factorization oracle.
4. **Complete selector:** lexicographically minimize bounded-relation count,
   then subgroup overlap, then maximize bounded-product diversity.
5. **Random coprime roots:** take a seeded random permutation of valid roots.
6. **Regev small-prime roots:** take the first (d) valid small-prime roots.

The complete selector optimizes no LLL output, factor result, (L_0) class,
sample distribution, or held-out statistic.

## 12. Noncircular outcomes and results

The primary outcome is whether the **Claim 5.1 prefix** contains a verified
vector in (L\setminus L_0) and stored-root GCD extraction returns a proper
factor. Secondary noncircular outcomes are any verified (L) vector, prefix
candidate count, and prefix rejection count. No bounded-box enumeration is
used by recovery.

### Model-specific association and direct comparison

| Model | Diversity versus factor success, Spearman (ho) | (N)-cluster 95% CI | Within-(N) permutation (p) | Complete success | Small-prime success | Complete minus small-prime, 95% CI | Negative relationship persists? |
|---|---:|---:|---:|---:|---:|---:|---|
| A: uniform hard box | -0.624 | [-0.769, -0.422] | 0.00010 | 0.111 | 0.241 | -0.130 [-0.286, 0.016] | Yes, for the association |
| B: exact finite Gaussian | -0.676 | [-0.805, -0.504] | 0.00010 | 0.079 | 0.240 | -0.160 [-0.328, 0.003] | Yes, at these finite parameters |
| C: theorem-compliant noisy dual | -0.059 | [-0.201, 0.099] | 0.388 | 0.956 | 0.954 | 0.001 [-0.003, 0.005] | No |

The complete-versus-small-prime sign-flip (p)-values are 0.122, 0.079, and
1.000 for A, B, and C respectively. Thus the cross-method association in A/B
is stronger than the evidence for that single pairwise contrast.

### Complete ablation means across 24 (N)'s

| Method | A factor success | B factor success | C factor success |
|---|---:|---:|---:|
| Residue deduplication only | 0.242 | 0.250 | 0.948 |
| Short-relation rejection only | 0.168 | 0.164 | 0.956 |
| Subgroup-overlap only | 0.227 | 0.217 | 0.952 |
| Complete selector | 0.111 | 0.079 | 0.956 |
| Random coprime roots | 0.302 | 0.273 | 0.993 |
| Regev small-prime roots | 0.241 | 0.240 | 0.954 |

For model C, verified (L)-relation recovery is essentially saturated
(0.996–1.000). Factor success is lower on (N=2881) for five deterministic
methods because their recovered prefix vectors are in (L_0); the random-root
method does not share that failure. This is a root-family/(L_0) effect, not a
sample-reconstruction failure.

### Mechanistic interpretation

- In A and finite B, a high-diversity base family often has weaker or
  less-resolvable short relation structure at the available (D,R,m,S), so
  integer LLL produces fewer exactly valid relation projections.
- B shows that the result is not caused solely by the flat amplitude window.
- C shows that once samples satisfy the theorem's precision regime, the
  diversity association is not detectable and all methods almost always
  recover (L). This falsifies any claim that the A/B relationship is a
  general property of Regev dual sampling.
- Factor success additionally depends on whether recovered (L) vectors lie
  outside the stored-root sublattice (L_0). Residue diversity alone does not
  control that event.

## 13. Candidate contributions reconsidered

Scores are importance / novelty potential / tractability / falsifiability /
notebook relevance / attainable evidence, each from 1 to 10.

| Candidate | Exact research question and mechanism | Baseline and proposed intervention | Effort, expected effect, principal risk, notebook support | Literature/novelty status | Scores |
|---|---|---|---|---|---|
| **Sampling-model validity boundary + real lattice endpoint — selected for this revision** | Does a base-selection association survive the hard box, exact Gaussian amplitudes, and theorem noisy-dual model when recovery is actual LLL? Mechanism: hold rooted families fixed and change only the sampling law/precision regime. | Original hard box and bounded search versus exact A/B laws, model C, augmented integer LLL, and (L/L_0) extraction. | High effort; expected to identify which conclusions transfer. Risk: no positive method. Notebook supplies the oracle and baseline. | Construct-validity study; novelty not established. | **10/6/7/10/10/10** |
| Root-retaining factor endpoint | Can loss of (b_i\mapsto a_i) metadata corrupt (L_0) classification? Immutable pairs and strict factor API. | Arbitrary/square-root reconstruction versus stored roots. | Medium effort; correctness improvement. Risk: engineering rather than research. Excellent notebook relevance. | Required already by Regev's formulation; not novel. | 9/2/10/10/10/10 |
| Dependency-aware base selection | Does bounded diversity or relation rejection improve LLL factor success? | Small primes, random roots, dedup, overlap, and complete selector. | Medium; falsifiable factor endpoint. Risk: selector harms the signal or effect is parameter-specific. | Empirical question; priority not established. | 8/5/8/10/10/8 |
| Exact Gaussian versus practical window preparation | Which approximations to (ho_R) preserve LLL recovery at fixed preparation cost? | Uniform, exact Gaussian, piecewise/rotation-truncated states. | High; could quantify cost-quality frontier. Risk: state-preparation complexity dominates. | Gaussian state is prior; approximation frontier uncertain. | 9/5/6/9/9/8 |
| Relation-aware approximate QFT | Which controlled rotations can be removed without reducing lattice factor success? | Exact QFT versus frozen cutoffs and coordinate-aware pruning. | Medium; lower two-qubit count expected. Risk: arithmetic dominates and approximate QFT is mature. | Likely incremental. | 7/4/8/9/8/7 |
| Noise-whitened augmented embedding | Can calibrated anisotropic torus error improve LLL under structured hardware noise? | Regev isotropic (S) versus covariance-weighted residual coordinates. | High; expected robustness gain. Risk: calibration leakage/overfit. Notebook needs noise models added. | Related filtering is prior; exact proposal uncertain. | 9/6/6/9/7/7 |
| Batched multibase arithmetic | Can shared product trees reduce compiled depth at fixed ancillas? | Sequential notebook exponentiation versus multi-scalar arithmetic. | Very high; potentially important resource saving. Risk: known Regev arithmetic already uses batching. | Core mechanism is prior. | 10/3/4/9/9/6 |
| Resource-constrained (d,D,R,m) policy | Which factor-blind parameters maximize held-out LLL success per compiled cost? | Notebook heuristics versus preregistered Pareto selection. | High; practical effect possible. Risk: toy overfitting and exact-simulation limits. | Empirical extension. | 8/6/6/9/10/8 |
| Corrupt-sample filtering | Can sample-consistency checks improve recovery with a fixed corruption fraction? | Plain LLL versus robust filtering. | High; measurable under synthetic corruption. Risk: Ragavan–Vaikuntanathan already addresses this. | Strong prior art. | 8/3/6/9/7/7 |
| Arithmetic-domain and decoder metamorphic tests | Can exhaustive valid-domain and symmetry tests automatically catch dirty ancillas, sign, width, and bit-order defects? | Notebook behavior versus contract suite. | Low; high correctness evidence. Risk: diagnostic only. Strong notebook support. | Engineering contribution. | 7/3/10/10/10/7 |

The selected direction defeated the alternatives because it addressed the
central validity threat before optimizing anything: the original claim could
not be interpreted without an actual lattice endpoint and a comparison across
sampling models. It also had a clear falsifier—model C—and that falsifier
materialized. This makes it the strongest audit result, but not yet a
publication-ready original contribution.

## 14. Primary-literature and novelty audit

- [Regev, *An Efficient Quantum Factoring Algorithm*](https://arxiv.org/abs/2308.06572)
  already defines (b_i,a_i,L,L_0), the (ho_R) amplitude state, the noisy
  dual law, the augmented lattice, Claim 5.1, and stored-root GCD extraction.
- [Ragavan and Vaikuntanathan, *Space-Efficient and Noise-Robust Quantum
  Factoring*](https://arxiv.org/abs/2310.00899) restates and extends the noisy
  dual post-processing model and corrupt-sample handling.
- [Pawlitko et al., *Implementation and Analysis of Regev's Quantum
  Factorization Algorithm*](https://arxiv.org/abs/2502.09772) explicitly uses a
  uniform state in place of the Gaussian in a public implementation.
- [Barbulescu, Barcau, and Paşol, comprehensive analysis](https://eprint.iacr.org/2024/1758.pdf)
  analyzes the (L/L_0) nontrivial-period issue broadly.
- [Yang et al., *Space-Optimized and Experimental Implementations*](https://arxiv.org/abs/2511.18198)
  includes lattice-based implementation experiments.
- [Falcó et al., *From Period Finding to Lattice Sampling*](https://arxiv.org/abs/2606.17647)
  uses effective-support metrics related directly to collision probability.

The targeted audit found no justification for novelty language around the
folded kernel or root twist. The identity is routine Parseval, and root
retention is explicit in Regev's original algorithm. The 24-(N), three-model
LLL comparison is reported as a reproducible empirical audit; its novelty
relative to all possible literature has not been established.

## 15. Limitations and next experiment

1. B is an exact finite Gaussian-state simulation, but (R=16) is far below
   the theorem's asymptotic precision requirement.
2. C satisfies the bounded-error premise and sufficient inequality but samples
   error uniformly from a ball, not from Regev's exact periodic Gaussian
   (Q_v).
3. All held-out inputs are modest semiprimes with (d=3); no scaling claim is
   possible.
4. The six methods share one small root pool. Subgroup enumeration and bounded
   relation scoring are not scalable preprocessing methods.
5. Thirty-two repeats estimate each (N)-cell probability but do not create
   32 independent generalization units.
6. The complete-versus-small-prime paired contrasts are not statistically
   decisive in A or B.
7. Model C reconstruction is nearly saturated, reducing power to distinguish
   base policies in the theorem regime.

The highest-value next experiment is an exact sampler for Regev's periodic
discrete-Gaussian (Q_v) at several precision levels bridging B and C, with
larger (d), a preregistered candidate pool, and enough new (N)'s to estimate
the transition from finite-precision failure to theorem-regime saturation.

## 16. Reproduction and artifacts

Run:


```bash
.venv/bin/python scripts/run_redteam.py
.venv/bin/python -m pytest -q
```

Key artifacts:

- `regev_research/core.py`: immutable root/base data and strict (L/L_0)
  classification;
- `regev_research/lattice.py`: exact augmented lattice, integer LLL, Claim 5.1
  prefix, and factor endpoint;
- `regev_research/redteam.py`: exact A/B laws and six selectors;
- `regev_research/dual.py`: factor-blind HNF oracle and model-C generator;
- `regev_research/redteam_experiments.py`: frozen experiment and (N)-level
  statistics;
- `results/redteam/configuration.json`: complete frozen design;
- `results/redteam/families.csv`: every selected root/base pair and selector
  diagnostic;
- `results/redteam/exact_models.csv`: all exact A/B metrics and distribution
  hashes;
- `results/redteam/trials.csv`: all 13,824 raw trial outcomes and seeds;
- `results/redteam/n_level.csv`: primary (N)-level aggregates;
- `results/redteam/model_statistics.json`: cluster-aware inference;
- `results/redteam/artifact_hashes.json`: SHA-256 manifest;
- `figures/redteam_diversity_vs_lattice_success.png` and
  `figures/redteam_model_ablation.png`: model-specific plots.
