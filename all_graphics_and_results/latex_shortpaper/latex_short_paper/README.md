# Overleaf-ready short paper

This folder is a self-contained LaTeX draft of the repository's strongest
current result: the finite Regev-style QFT certification gap. The paper uses
the linked `carolinaoamorim/RegevImplementation` repository as a cited
engineering predecessor, while all truncation claims and numbers come from
this repository's frozen `qft-certificate-gap-v1` study.

## Fastest way to compile

1. Open [Overleaf](https://www.overleaf.com/).
2. Choose **New Project → Upload Project**.
3. Upload `Regev_QFT_Certificate_Gap_LaTeX.zip`.
4. Confirm that **Main document** is `main.tex` and compile with pdfLaTeX.

The archive is intentionally arranged with `main.tex` at its root, so no file
paths need to be changed after upload.

## Compile locally

With the self-contained [Tectonic](https://tectonic-typesetting.github.io/)
engine:

```bash
make
```

Equivalent command:

```bash
tectonic main.tex
```

With a standard TeX Live or MacTeX installation, use:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

## Verify the packaged evidence

The verification step uses only Python's standard library:

```bash
python3 verify_data.py
```

It checks the frozen hashes, protocol values, selected cutoffs, reported
recovery differences and confidence intervals, means, and QFT-only resource
counts against the included repository data.

## Important before submission

- Confirm the author list, order, affiliations, and acknowledgments with all
  collaborators. The draft author block currently names Summer Malik only and
  explicitly labels itself provisional.
- Choose a target venue and apply its document class only after the scientific
  text is approved. The current two-column `article` format is portable and is
  not meant to imitate a particular publisher.
- Do not remove the limitation that savings are **QFT-only**, not measured
  whole-circuit or hardware speedups.
- Do not describe the finite-Gaussian model as the full asymptotic Regev
  algorithm, and do not call the classical exact simulator a dequantization.

## Contents

| Path | Purpose |
|---|---|
| `main.tex` | Short-paper source |
| `main.pdf` | Successfully compiled five-page preview |
| `references.bib` | Primary literature and software citations |
| `figures/certification_vs_recovery.png` | Frozen two-panel result figure |
| `data/` | Frozen configuration, summaries, proof-slack rows, and checksums |
| `verify_data.py` | Independent package consistency checks |
| `SOURCE_AND_CLAIM_NOTES.md` | Evidence provenance and claim boundaries |
| `Makefile` | Local build and cleanup commands |

The full 12,288 trial rows and 120,000 bootstrap draws remain in the parent
research repository rather than being duplicated in this compact paper ZIP.
