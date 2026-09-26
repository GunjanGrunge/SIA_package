"""Launcher for SIA's host hooks (recall and enforcement of learned rules).

Hosts run this with the event name, e.g.:

    python3 "${CLAUDE_PLUGIN_ROOT}/sia_hook.py" session-start

Claude Code substitutes ${CLAUDE_PLUGIN_ROOT} in hook commands, and Codex sets
it in the environment for hooks, so the shell expands it -- unlike MCP server
arguments, where Codex expands nothing. Like ``cli.py``, this puts the bundled
``src/`` on ``sys.path`` itself, so no ``pip install`` is needed.

See ``src/sia/hooks.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from sia.hooks import run  # noqa: E402

if __name__ == "__main__":
    run()
