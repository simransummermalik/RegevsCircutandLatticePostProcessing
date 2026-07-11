#!/usr/bin/env python3
"""Repository-local entry point for every reported experiment."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from regev_research.experiments import main


if __name__ == "__main__":
    main()
