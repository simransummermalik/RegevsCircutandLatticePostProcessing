# LaTeX Methods code for the poster

This is a regular folder containing reusable LaTeX code for the poster's Methods section.

Files:

- `simple_methods_infographic.tex` — the simple four-box poster workflow:
  test → controlled error → recover → measure.
- `simple_methods_infographic_preview.tex` — standalone source for the simple
  workflow.
- `simple_methods_infographic_preview.pdf` — compiled poster-ready vector
  preview.
- `simple_methods_infographic_preview.png` — quick image preview.
- `methods_section.tex` — accurate four-step Methods text. Paste it inside your poster's Methods block.
- `methods_flowchart.tex` — compact TikZ workflow figure.
- `poster_methods_preview.tex` — complete standalone file that previews both pieces together.
- `poster_methods_preview.pdf` — compiled preview, when compilation succeeds.

The code describes the final frozen QFT certificate-gap experiment—not the superseded diversity result or the negative quotient-deflation study.

## Required packages

Add these to the poster preamble:

```latex
\usepackage{amsmath}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{enumitem}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,calc,positioning}
```

Then place the text or flowchart where wanted:

```latex
\input{methods_section.tex}
```

or

```latex
\input{methods_flowchart.tex}
```

For the simplest poster version, use:

```latex
\input{simple_methods_infographic.tex}
```

To compile the supplied preview from the repository root:

```bash
cd "latex code"
tectonic poster_methods_preview.tex
```

The wording deliberately says **QFT phase truncation**, not hardware noise. The known factors were used only for post-hoc validation.
