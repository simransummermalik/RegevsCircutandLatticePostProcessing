"""Execute the standalone demonstration notebook in place."""

from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parent
PATH = ROOT / "Shor_to_Regev_Demonstration.ipynb"
notebook = nbformat.read(PATH, as_version=4)
client = NotebookClient(
    notebook,
    timeout=300,
    kernel_name="regev-research",
    resources={"metadata": {"path": str(REPOSITORY)}},
    allow_errors=False,
)
client.execute()
nbformat.write(notebook, PATH)
print(PATH)

