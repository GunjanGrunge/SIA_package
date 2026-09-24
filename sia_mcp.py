"""Launcher for SIA's MCP server, run straight from a plugin install.

Every host's plugin manifest starts this with Python 3:

    python3 <plugin-root>/sia_mcp.py

Like ``cli.py`` it puts the bundled ``src/`` on ``sys.path`` itself, so no
``pip install`` is needed. The server speaks MCP over stdio; see
``src/sia/mcp_server.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from sia.mcp_server import run  # noqa: E402

if __name__ == "__main__":
    run()
