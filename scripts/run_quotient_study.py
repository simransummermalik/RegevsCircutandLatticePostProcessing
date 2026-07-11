"""CLI for the frozen held-out quotient-recovery study."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regev_research.quotient_study import run_heldout_quotient_study


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute the precommitted quotient-recovery holdout serially."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/quotient_study"),
        help="output directory (default: results/quotient_study)",
    )
    args = parser.parse_args()
    run_heldout_quotient_study(args.output)


if __name__ == "__main__":
    main()
