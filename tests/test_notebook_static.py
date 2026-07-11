import json
from pathlib import Path


NOTEBOOK = Path("RegevImplementationAndTestingBuilding_work-3.ipynb")


def _cell_source(index):
    notebook = json.loads(NOTEBOOK.read_text())
    return "".join(notebook["cells"][index]["source"])


def test_large_diagram_cell_measures_too_few_exponent_qubits():
    source = _cell_source(16)
    assert "qc.measure(range(2*n), range(2*n))" in source
    # For N=2021: n=11, d=4, nd=6, hence 24 x qubits but only 22 measured.
    assert 2 * 11 == 22
    assert 4 * 6 == 24


def test_notebook_contains_forward_and_inverse_qft_conventions():
    helper = _cell_source(4)
    pipeline = _cell_source(8)
    final_diagram = _cell_source(16)
    assert "QFTGate(num_qubits=n_per_reg)" in helper
    assert "QFTGate(nd).inverse()" in pipeline
    assert "multidim_qft" in final_diagram


def test_toy_postprocessor_short_circuits_to_setup_factor():
    source = _cell_source(9)
    lucky_position = source.index('lucky = metadata.get("lucky_factors", [])')
    sample_position = source.index("for row in summary:")
    assert lucky_position < sample_position


def test_notebook_summary_discards_all_but_top_fifteen_outcomes():
    source = _cell_source(8)
    assert "top: int = 15" in source
    assert "most_common(top)" in source


def test_original_setup_is_colab_specific_and_dependency_unpinned():
    source = _cell_source(0)
    assert "git clone https://github.com/Wlitkopa/regev-quantum-algorithm.git" in source
    assert "@" not in source.split("git clone", 1)[1].splitlines()[0]
    assert "/content/regev-quantum-algorithm" in source
    assert "google.colab" in source
