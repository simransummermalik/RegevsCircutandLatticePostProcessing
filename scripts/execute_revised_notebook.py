#!/usr/bin/env python3
"""Execute the generated notebook in place and fail on the first cell error."""

from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "RegevImplementationAndTestingBuilding_redteam_revision.ipynb"
COMPAT_PATH = ROOT / "RegevImplementationAndTestingBuilding_research_revision.ipynb"
notebook = nbformat.read(PATH, as_version=4)
client = NotebookClient(
    notebook,
    timeout=900,
    kernel_name="regev-research",
    resources={"metadata": {"path": str(ROOT)}},
    allow_errors=False,
)
client.execute()
nbformat.write(notebook, PATH)
nbformat.write(notebook, COMPAT_PATH)
print(PATH)
print(COMPAT_PATH)
