"""Run the machine learning extension for the GitHub showcase project."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ml_extension import run_ml_extension  # noqa: E402


def main() -> None:
    outputs = run_ml_extension(ROOT / "data" / "processed", ROOT / "output" / "figures")
    for label, path in outputs.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
