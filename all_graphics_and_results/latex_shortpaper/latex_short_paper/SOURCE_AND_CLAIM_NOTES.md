# Source and claim notes

## Current-repository evidence

The paper was prepared from research snapshot
`a4a47c77aa9e5935597d9a3c37fc6efe9f8b1d04` of
`simransummermalik/RegevsCircutandLatticePostProcessing`.

The primary evidence is frozen study `qft-certificate-gap-v1`:

- protocol: `QFT_CERTIFICATE_GAP_PROTOCOL.md`;
- main interpretation: `QFT_CERTIFICATE_GAP_REPORT.md`;
- proof audit: `QFT_CERTIFICATE_PROOF_AUDIT.md`;
- tightness/mechanism audit: `QFT_CERTIFICATE_TIGHTNESS.md`;
- implementation: `regev_research/qft_certificate.py`,
  `regev_research/qft_noise.py`, and `regev_research/lattice.py`;
- experiment entry point: `scripts/run_qft_certificate_gap.py`;
- complete raw results: `results/qft_certificate_gap/`.

The compact archive includes the configuration and summary tables needed to
audit every number printed in the paper. It omits the large raw-trial and
bootstrap-draw files; their SHA-256 hashes remain recorded in
`data/completion.json`.

## Companion-repository boundary

The cited predecessor is
[`carolinaoamorim/RegevImplementation`](https://github.com/carolinaoamorim/RegevImplementation)
at commit `595e755a93976ab865c795b61195b7f8c4fa7634`. Its README credits Carolina
Amorim, Owen Barnes, and Summer Malik for the project. The repository does not
document individual technical roles, so the paper credits the team jointly
and does not assign specific contributions to a person.

The companion supplies useful engineering background: an exact uniform-box
Fourier-law simulator, retained roots for squared bases, exact-rational LLL
post-processing, and a uniform null control. It does **not** supply the current
finite-Gaussian, approximate-QFT, certificate, held-out, or compiled-resource
evidence. No companion source code or binary is copied into this ZIP.

## Three claim levels

1. **Verified implementation correction.** The custom approximate-QFT layer
   order was corrected and all affected rows were regenerated before the
   holdout.
2. **Verified finite empirical result.** In the frozen eight-semiprime A/B
   experiment, the original sufficient certificate approved zero omitted
   layers while limited omissions met the declared non-inferiority rule.
3. **Unverified general hypothesis.** Fiber-aware precision analysis may
   reduce QFT resources in larger Regev regimes. The current study does not
   establish this.

## Language that should not be introduced during editing

- “Approximate QFT is new.”
- “Truncation improves recovery.”
- “The certificate is wrong.”
- “The full Regev algorithm was dequantized or simulated.”
- “The project demonstrates quantum advantage.”
- “Six controlled phases and twelve CX gates are full-circuit savings.”
- “The finite RV-inspired comparator refutes Ragavan–Vaikuntanathan.”

## Authorship

The LaTeX author block is intentionally provisional. Repository history and a
team README are not substitutes for an authorship discussion. Confirm author
eligibility, order, affiliations, contact information, and permission to
circulate before treating this draft as a submission.
