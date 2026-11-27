#!/usr/bin/env python3
"""Run the tool from a source checkout without installing it."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from marketplace_tool.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
