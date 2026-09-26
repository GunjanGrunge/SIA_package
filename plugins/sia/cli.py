"""Launcher for the canonical :mod:`sia` CLI, run straight from a checkout.

This is the entry point the Claude Code plugin uses:

    python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" <command>

It puts the bundled ``src/`` on ``sys.path`` itself, so the plugin needs no
``pip install`` and no virtualenv -- Python 3 is the only prerequisite. The
published ``sia-package`` distribution installs the same ``sia.cli:main`` as a
console script, so both paths run identical code.
"""
from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from sia.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
