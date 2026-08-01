"""Independent structural tests for the complexity-fidelity discrepancy.

This module deliberately uses Python's AST rather than the recursive resource
counter in :mod:`regev_research.resource_analysis`.  Agreement between the two
methods is therefore a cross-check rather than the same formula reported twice.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable


def _function_node(path: Path, function_name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(), filename=str(path))
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one top-level {function_name!r} in {path}, found {len(matches)}"
        )
    return matches[0]


def loop_iterators(path: Path, function_name: str) -> tuple[str, ...]:
    """Return normalized iterator expressions for every loop in a function."""

    node = _function_node(path, function_name)
    return tuple(
        ast.unparse(child.iter)
        for child in ast.walk(node)
        if isinstance(child, ast.For)
    )


def named_call_count(path: Path, function_name: str, called_name: str) -> int:
    """Count calls to a named function within one top-level function."""

    node = _function_node(path, function_name)
    count = 0
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        target = child.func
        if isinstance(target, ast.Name) and target.id == called_name:
            count += 1
        elif isinstance(target, ast.Attribute) and target.attr == called_name:
            count += 1
    return count


def source_structure_audit(root: Path) -> list[dict[str, object]]:
    """Audit the independent loop facts that determine the missing factor."""

    external = root / "external/regev-quantum-algorithm/gates"
    checks = (
        (
            "Shor exponent schedule",
            external / "haner/modular_exponentiation.py",
            "modular_exponentiation_gate",
            "range(2 * n)",
        ),
        (
            "Regev exponent schedule",
            external / "r_haner/modular_exponentiation.py",
            "modular_exponentiation_gate",
            "range(qd)",
        ),
        (
            "Shor result-register swap loop",
            external / "haner/modular_exponentiation.py",
            "controlled_modular_multiplication_gate",
            "range(n)",
        ),
        (
            "Regev result-register swap loop",
            external / "r_haner/modular_exponentiation.py",
            "controlled_modular_multiplication_gate",
            "range(n)",
        ),
        (
            "Shor constant-multiplier addition loop",
            external / "haner/constant_modulo_multiplier.py",
            "controlled_constant_modulo_multiplier",
            "reversed(range(n))",
        ),
        (
            "Regev constant-multiplier addition loop",
            external / "r_haner/constant_modulo_multiplier.py",
            "controlled_constant_modulo_multiplier",
            "reversed(range(n))",
        ),
    )
    rows: list[dict[str, object]] = []
    for label, path, function, expected in checks:
        observed = loop_iterators(path, function)
        rows.append({
            "check": label,
            "file": str(path.relative_to(root)),
            "function": function,
            "expected_iterator": expected,
            "observed_iterators": " | ".join(observed),
            "passed": expected in observed,
        })

    for family in ("haner", "r_haner"):
        path = external / family / "modular_exponentiation.py"
        calls = named_call_count(
            path,
            "controlled_modular_multiplication_gate",
            "controlled_constant_modulo_multiplier",
        )
        rows.append({
            "check": f"{family} forward/inverse constant multipliers",
            "file": str(path.relative_to(root)),
            "function": "controlled_modular_multiplication_gate",
            "expected_iterator": "two calls",
            "observed_iterators": str(calls),
            "passed": calls == 2,
        })
    return rows


def dimensional_split_rows(bit_lengths: Iterable[int]) -> list[dict[str, object]]:
    """Test every exact power-of-two split of a ``2n``-bit binary schedule.

    When ``d*q=2n``, distributing exponent bits over more dimensions cannot
    change the code's ``2*d*q*n = 4n^2`` modular-addition count.  This is a
    negative control against attributing the discrepancy to ceiling effects.
    """

    rows: list[dict[str, object]] = []
    for n_value in bit_lengths:
        n = int(n_value)
        if n <= 0 or n & (n - 1):
            raise ValueError("dimensional split audit requires powers of two")
        total_exponent_bits = 2 * n
        q = 1
        while q <= total_exponent_bits:
            d = total_exponent_bits // q
            code_additions = 2 * d * q * n
            paper_substitution = 2 * d * q * q
            rows.append({
                "n": n,
                "d": d,
                "q": q,
                "d_times_q": d * q,
                "code_modular_additions": code_additions,
                "paper_substitution_additions": paper_substitution,
                "code_over_paper": code_additions / paper_substitution,
                "invariant_expected": 4 * n * n,
                "invariant_passed": code_additions == 4 * n * n,
            })
            q *= 2
    return rows


def all_checks_pass(rows: Iterable[dict[str, object]], key: str = "passed") -> bool:
    return all(bool(row[key]) for row in rows)

