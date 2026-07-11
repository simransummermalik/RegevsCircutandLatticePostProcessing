#!/usr/bin/env python3
"""Analyze an existing quotient-study trial table without running the holdout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regev_research.quotient_predictors import (
    DEFAULT_BOOTSTRAP_RESAMPLES,
    DEFAULT_BOOTSTRAP_SEED,
    analyze_predictor_comparison,
    write_predictor_comparison,
)


def main(argv: list[str] | None = None) -> tuple[Path, Path]:
    parser = argparse.ArgumentParser(
        description=(
            "Join frozen standard-Regev outcomes to quotient scoring rows and "
            "write clustered predictor comparisons. This command never runs recovery."
        )
    )
    parser.add_argument(
        "--trial-rows",
        type=Path,
        default=Path("results/quotient_study/trial_rows.csv"),
        help="existing trial_rows.csv to analyze",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="output directory (default: the trial table's directory)",
    )
    parser.add_argument(
        "--bootstrap-resamples",
        type=int,
        default=DEFAULT_BOOTSTRAP_RESAMPLES,
        help="fixed whole-N bootstrap resample count",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_BOOTSTRAP_SEED,
        help="deterministic bootstrap seed",
    )
    args = parser.parse_args(argv)
    output = args.output if args.output is not None else args.trial_rows.parent
    analysis = analyze_predictor_comparison(
        args.trial_rows,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
    )
    paths = write_predictor_comparison(output, analysis)
    print(paths[0])
    print(paths[1])
    return paths


if __name__ == "__main__":
    main()
