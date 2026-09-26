"""Build plugins/sia/ -- the self-contained copy Codex installs.

Run from the repository root:  python3 tools/build_codex_plugin.py

Why a copy exists at all. Codex versions disagree on marketplace layout:

  Codex 0.136  silently drops a plugin at the marketplace root ("./"),
               but accepts a `url` source.
  Codex 0.121  rejects a `url` source outright ("unknown variant `url`,
               expected `local`"), which invalidates the WHOLE marketplace.

The one layout both accept is a plugin in a subdirectory with a `local` source
-- the layout BMAD uses. Claude Code, Kiro and Gemini keep installing from the
repository root, so moving everything would break them; instead this script
assembles a complete copy under plugins/sia/, and Codex's marketplace points
there.

The copy must be self-contained: Codex installs by copying only this directory
into its cache. That includes the policy files (AGENT.md, capture-interface.md,
guides/), which SIA looks for next to its source and refuses to run without.

tests/test_codex_plugin.py rebuilds into a temporary directory and fails if the
committed copy differs by a single byte, so it cannot drift from the source.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("plugins") / "sia"

# Everything the installed plugin needs at runtime, and nothing else.
PAYLOAD = (
    "src/sia",
    "skills",
    "agents",
    "hooks",
    "guides",
    "AGENT.md",
    "capture-interface.md",
    "cli.py",
    "sia_mcp.py",
    "sia_hook.py",
    ".mcp.json",
    "plugin.json",
    "LICENSE",
)
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info")


def build(root: Path = ROOT, out: Path | None = None) -> Path:
    out = out if out is not None else root / TARGET
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for relative in PAYLOAD:
        source = root / relative
        destination = out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=IGNORE)
        else:
            shutil.copy2(source, destination)
    # Codex looks for its manifest here when installing a local plugin; a root
    # plugin.json alone was reported as "missing plugin.json".
    manifest = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    codex_dir = out / ".codex-plugin"
    codex_dir.mkdir()
    (codex_dir / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out / "GENERATED.md").write_text(
        "# Generated -- do not edit\n\n"
        "This directory is the copy of SIA that Codex installs. It is built from the\n"
        "repository root by `python3 tools/build_codex_plugin.py`; edit the originals\n"
        "and rebuild. A test fails if this copy drifts from its source.\n",
        encoding="utf-8",
    )
    return out


if __name__ == "__main__":
    print("built", build().relative_to(ROOT))
