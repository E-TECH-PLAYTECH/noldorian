#!/usr/bin/env python3
"""Repository wrapper for the packaged :mod:`noldorian.mcp` server."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from noldorian.mcp import main
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from noldorian.mcp import main


if __name__ == "__main__":
    main()
