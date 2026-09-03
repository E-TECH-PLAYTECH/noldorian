#!/usr/bin/env python3
"""Compatibility entrypoint for the unified Noldorian MCP server.

The former file exposed an installer/orienter MCP surface that could make an
agent believe the family was available while leaving the credential enrollment
path unimplemented.  The canonical server is now the package server, which
includes the explicit human-enrollment request and status tools.
"""

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
