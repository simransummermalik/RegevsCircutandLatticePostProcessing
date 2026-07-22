# Poster layout options

These are **48 × 36 inch landscape layout mockups**, not scientific result
figures. They show where the strongest existing graphics could go on the final
poster while keeping the story readable from left to right.

## Which option should I use?

- **L01 — Story first:** best all-purpose choice for a mixed audience. It walks
  from the question to the experiment, primary evidence, resources, and scope.
- **L02 — Result first:** best for a poster session. It gives the held-out result
  the most space and puts supporting evidence directly around it.
- **L03 — Beginner first:** best for a class or broad CS audience. It explains
  Shor versus Regev, the pipeline, and QFT truncation before showing the tests.

Each design is supplied as PNG for quick preview, SVG for editing, and PDF for
printing/importing. The filenames inside the boxes point to assets in
`14_SUPPLEMENTAL_VETO_OPTIONS/`; they are placement instructions and should not
remain as captions in the final poster.

## Recommended choice

Start with **L02** if the poster must communicate the research result in a few
seconds. Use **L01** if the audience needs more context. Keep the limitation and
the phrase **“QFT-only resources”** visible in every version.

## Reproduce

From the repository root:

```bash
MPLBACKEND=Agg .venv/bin/python \
  "poster graphics/_SCRIPTS/make_poster_layout_options.py"
```

The script only reads existing poster assets and rewrites the nine layout
mockup files in this folder.
