#!/usr/bin/env python3
"""Build the executable mandatory red-team revision notebook."""

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "RegevImplementationAndTestingBuilding_redteam_revision.ipynb"
COMPAT_OUTPUT = ROOT / "RegevImplementationAndTestingBuilding_research_revision.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip() + "\n")


def code(text: str):
    return nbf.v4.new_code_cell(text.strip() + "\n")


cells = [
    md(
        r"""
# Mandatory red-team revision: Regev-style sampling, rooted bases, and a real lattice endpoint

**Status: not publication-ready.** This notebook supersedes the earlier
contribution and novelty conclusions. The hard-box chi-squared formula is a
standard Parseval identity, the (N=437) example is a root-metadata regression
test, and the old bounded-search endpoint was circular with the selector.

The revised experiment uses immutable ((b_i,a_i=b_i^2mod N)) pairs, exact
integer augmented-lattice LLL, Regev's Claim 5.1 prefix, exact (L/L_0)
classification, 24 new held-out values of (N), and three sampling models.
"""
    ),
    md(
        r"""
## 1. Frozen design and full recomputation

The complete configuration is written before any held-out result. (N), not
the 32 Monte Carlo repeats within a cell, is the generalization unit.
"""
    ),
    code(
        """
from pathlib import Path
import json, subprocess, sys
import numpy as np
import pandas as pd
import qiskit, qiskit_aer
from IPython.display import Image, display

ROOT = Path.cwd()
assert (ROOT / 'RegevImplementationAndTestingBuilding_work-3.ipynb').exists()
print('Python:', sys.version.split()[0])
print('Qiskit:', qiskit.__version__, 'Aer:', qiskit_aer.__version__)
print('External arithmetic commit audited:', 'a18f75d414485086db9b257407e0bd01f8a8f81c')
"""
    ),
    code(
        """
# Recompute 24 N x 6 methods x 3 models x 32 trials, plus exact A/B laws.
subprocess.run([sys.executable, 'scripts/run_redteam.py'], check=True)
config = json.loads((ROOT / 'results/redteam/configuration.json').read_text())
config
"""
    ),
    md(
        r"""
## 2. Original notebook baseline

The notebook prepares uniform amplitudes on a Cartesian exponent box, computes

\[
h_A(x)=\prod_i a_i^{x_i}\bmod N,
\]

discards the oracle register, and applies one QFT per coordinate. It does not
prepare Regev's Gaussian state and contains no multidimensional lattice
reconstruction. Its displayed factor for (N=15) comes from base-generation
GCDs before samples are inspected.
"""
    ),
    code(
        """
from regev_research.core import (
    RootedBaseFamily, audit_square_base_family,
    exact_uniform_fourier_distribution, notebook_squared_prime_bases,
)

for N, d, bases, D in [(15, 2, [4, 4], 16), (21, 3, [4, 4, 16], 16)]:
    generated = notebook_squared_prime_bases(N, d)
    audit = audit_square_base_family(generated['family'], relation_bound=2)
    p, _ = exact_uniform_fourier_distribution(N, bases, D)
    top = np.argsort(p.ravel())[-3:][::-1]
    print({
        'N': N, 'pairs': generated['pairs'],
        'setup_GCD_leaks': generated['setup_factor_leaks'],
        'relation_or_collision_factors': audit['setup_factor_leaks'],
        'top_exact_probabilities': [
            (tuple(int(v) for v in np.unravel_index(i, p.shape)), float(p.ravel()[i]))
            for i in top
        ],
    })
"""
    ),
    md(
        r"""
## 3. Roots, bases, (L), and (L_0)

The selected roots and derived circuit bases are different objects:

\[
B=(b_i),\qquad a_i=b_i^2\bmod N,
\]

\[
L=\{z:\prod_i a_i^{z_i}=1\bmod N\},
\qquad
L_0(B)=\{z\in L:\prod_i b_i^{z_i}=\pm1\bmod N\}.
\]

A relation in (L\setminus L_0) yields a nontrivial square root of unity and
a GCD factor. The implementation never replaces a stored root by another
modular square root of the same base.
"""
    ),
    code(
        """
from regev_research.core import classify_square_relation, extract_factor_from_relation

u = (1, 1, 1)
trivial = RootedBaseFamily.from_roots(437, [2, 3, 73])
factor_bearing = RootedBaseFamily.from_roots(437, [2, 3, 326])
print('same A:', trivial.bases == factor_bearing.bases, trivial.bases)
print('retained roots (2,3,73):', classify_square_relation(trivial, u))
print('retained roots (2,3,326):', classify_square_relation(factor_bearing, u))
assert extract_factor_from_relation(trivial, u) is None
assert extract_factor_from_relation(factor_bearing, u) == 23
"""
    ),
    md(
        r"""
## 4. Exact hard-box definitions and the standard Parseval identity

Let (X=\{0,\ldots,M-1\}^d), (G=(\mathbb Z/M\mathbb Z)^d), and
(q=M^d). For (k\in G), (P_A(k)) is the exact Fourier measurement law and
(U(k)=q^{-1}). Here (r\in G) is a residue class, while (z\in L) is an
integer relation. Define

\[
K_A(r)=\sum_{x,x'\in X}
\mathbf1[h_A(x)=h_A(x')]
\mathbf1[(x-x')\bmod M=r].
\]

Equivalently,

\[
K_A(r)=\sum_{\substack{z\in L,\ |z_i|<M\\z\bmod M=r}}
\prod_i(M-|z_i|).
\]

The fiber expansion gives

\[
P_A(k)=q^{-2}\sum_rK_A(r)e^{-2\pi i\langle k,r\rangle/M}.
\]

Since (K_A(0)=q), set (f_A=K_A-q\mathbf1_0). Then

\[
P_A-U=q^{-2}\widehat f_A.
\]

Character orthogonality and Parseval give

\[
\chi^2(P_A\|U)
=q\sum_k|P_A(k)-U(k)|^2
=q^{-2}\sum_{r\ne0}K_A(r)^2.
\]

This is the standard autocorrelation/Parseval identity, equivalently
(\chi^2=q\operatorname{Col}(P_A)-1). No novelty is claimed.
"""
    ),
    code(
        """
exact = pd.read_csv(ROOT / 'results/redteam/exact_models.csv')
exact.groupby('model').parseval_absolute_error.agg(['max', 'mean'])
"""
    ),
    md(
        r"""
## 5. Why the previous endpoint was circular

“Bounded multidimensional relation recovery” enumerated every canonical
(u\in[-B,B]^d/\{\pm1\}), ranked it by an empirical Fourier character moment,
and checked (h_A(u)=1). It used brute force and an exact membership check,
not LLL, BKZ, factors, orders, or planted relations. Because the selector also
optimized the same bounded product box, this remains only a diagnostic.
"""
    ),
    md(
        r"""
## 6. Actual augmented-lattice endpoint

For raw samples (w_i=y_i/D), rows of (W), and (S=p/q), Regev's column
basis is

\[
B_S=\begin{pmatrix}I_d&0\\SW&SI_m\end{pmatrix}.
\]

The exact cleared integer column basis is

\[
qD B_S=\begin{pmatrix}qD I_d&0\\pY&pD I_m\end{pmatrix}.
\]

The row transpose is reduced by integer LLL. Exact Gram–Schmidt norms select
Regev's Claim 5.1 prefix. Projected vectors are verified in (L), classified
with the stored roots, and only (L\setminus L_0) reaches GCD extraction.
"""
    ),
    code(
        """
from regev_research.dual import synthetic_noisy_dual_samples
from regev_research.lattice import regev_lattice_postprocess
from regev_research.redteam_experiments import relation_norm_bound, augmented_norm_bound

family = RootedBaseFamily.from_roots(1763, [2, 3, 5])
T = relation_norm_bound(1763)
batch = synthetic_noisy_dual_samples(family, seed=20260710, relation_norm_bound_T=T)
result = regev_lattice_postprocess(
    family, batch.samples, batch.modulus,
    claim_norm_bound=augmented_norm_bound(T), scale=batch.scale,
)
print({
    'theorem_inequality': batch.theorem_sufficient_inequality,
    'maximum_error': batch.maximum_realized_torus_error,
    'noise_bound': batch.noise_bound,
    'Claim_5_1_prefix_length': result.claim_prefix.prefix_length,
    'relations': [candidate.relation for candidate in result.claim_prefix_candidates],
    'factor': result.factor_pair,
})
"""
    ),
    md(
        r"""
## 7. Sampling models

- **A:** exact notebook-type uniform hard box, (d=3,D=64).
- **B:** exact finite Regev amplitude state
  (\sum_z\rho_{16}(z)|z\rangle), (D=64). This obeys Regev's finite
  (D/R) interval but not the asymptotic recovery inequality.
- **C:** uniform (v\in L^*/\mathbb Z^d), bounded additive noise, and grid
  quantization, with every sample satisfying the theorem noise bound and the
  conservative sufficient inequality based on (det L\le N).

The model-C HNF oracle is confined to the data generator and is never passed to
reconstruction.
"""
    ),
    code(
        """
heldout = pd.DataFrame(config['heldout_instances'])
heldout
"""
    ),
    md(
        r"""
## 8. Six factor-blind ablations

The frozen methods are residue deduplication only, bounded short-relation
rejection only, subgroup-overlap scoring only, the lexicographic complete
selector, random coprime roots, and Regev's small-prime roots. Every method
retains its exact root/base pairs. No selector sees factors, LLL outputs,
samples, (L_0), or held-out results.
"""
    ),
    code(
        """
stats = json.loads((ROOT / 'results/redteam/model_statistics.json').read_text())
rows = []
for model, values in stats['models'].items():
    rows.append({
        'model': model,
        'rho_diversity_vs_factor': values['diversity_vs_lattice_factor_success_spearman'],
        'rho_CI': (values['N_cluster_bootstrap_ci_low'], values['N_cluster_bootstrap_ci_high']),
        'within_N_permutation_p': values['within_N_permutation_p'],
        'complete_success': values['method_summary']['complete_selector']['mean_factor_success_across_N'],
        'small_prime_success': values['method_summary']['regev_small_prime_roots']['mean_factor_success_across_N'],
        'negative_persists': values['negative_relationship_persists'],
    })
pd.DataFrame(rows)
"""
    ),
    code(
        """
ablation = []
for model, values in stats['models'].items():
    for method, summary in values['method_summary'].items():
        ablation.append({
            'model': model,
            'method': method,
            'mean_factor_success_across_24_N': summary['mean_factor_success_across_N'],
            'N_bootstrap_CI': (summary['N_bootstrap_ci_low'], summary['N_bootstrap_ci_high']),
        })
pd.DataFrame(ablation)
"""
    ),
    code(
        """
display(Image(filename=ROOT / 'figures/redteam_diversity_vs_lattice_success.png'))
display(Image(filename=ROOT / 'figures/redteam_model_ablation.png'))
"""
    ),
    md(
        r"""
## 9. Three final claims

1. **Verified implementation correction:** root/base provenance and the exact
   samples-to-lattice-to-factor path are implemented and tested.
2. **Verified uniform-box result:** diversity is negatively associated with
   actual LLL factor success across the 24 held-out (N)'s, but the direct
   complete-versus-small-prime contrast is not decisive.
3. **Unverified full-Regev hypothesis:** finite Gaussian B shows the same
   association, while theorem-compliant C does not. No full-Regev
   generalization is supported.

`REDTEAM_REVISION.md` contains the line-by-line proof, all 24 inputs, seeds,
selection rules, exclusions, candidate table, primary-literature audit,
limitations, and complete model-specific statistics.
"""
    ),
    md(
        """
## 10. Validation

The test suite covers the original notebook audit, arithmetic contracts,
root/base immutability, N=437 classification, exact hard-box and Gaussian
laws, Parseval, factor-blind HNF generation, bounded-noise model C, exact
integer lattice construction, Claim 5.1 scaling/cutoff, and factor extraction.
"""
    ),
    code(
        """
completed = subprocess.run(
    [sys.executable, '-m', 'pytest', '-q'],
    check=True, text=True, capture_output=True,
)
print(completed.stdout)
"""
    ),
    code(
        """
hashes = json.loads((ROOT / 'results/redteam/artifact_hashes.json').read_text())
print('Artifact files:', len(hashes))
hashes
"""
    ),
]

notebook = nbf.v4.new_notebook(
    cells=cells,
    metadata={
        "kernelspec": {
            "display_name": "Regev Research",
            "language": "python",
            "name": "regev-research",
        },
        "language_info": {"name": "python", "version": "3.14"},
    },
)
nbf.write(notebook, OUTPUT)
nbf.write(notebook, COMPAT_OUTPUT)
print(OUTPUT)
print(COMPAT_OUTPUT)
