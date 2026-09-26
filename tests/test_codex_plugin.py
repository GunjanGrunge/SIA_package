"""The Codex copy under plugins/sia must match its source exactly.

Codex installs SIA from plugins/sia/, a generated copy (see
tools/build_codex_plugin.py for why). A copy that silently drifts would ship
Codex users an older SIA than everyone else, with no error anywhere.
"""
from __future__ import annotations

import filecmp
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COPY = REPO / "plugins" / "sia"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_codex_plugin", REPO / "tools" / "build_codex_plugin.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def tree(root: Path) -> set[str]:
    return {
        p.relative_to(root).as_posix() for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }


def test_the_committed_copy_matches_a_fresh_build(tmp_path: Path) -> None:
    fresh = load_builder().build(REPO, tmp_path / "sia")
    committed, rebuilt = tree(COPY), tree(fresh)
    assert committed == rebuilt, (
        f"plugins/sia is stale: run python3 tools/build_codex_plugin.py "
        f"(missing: {sorted(rebuilt - committed)[:5]}, extra: {sorted(committed - rebuilt)[:5]})")
    changed = [f for f in sorted(committed) if not filecmp.cmp(COPY / f, fresh / f, shallow=False)]
    assert not changed, f"plugins/sia is stale: run python3 tools/build_codex_plugin.py (changed: {changed[:5]})"


def test_codex_marketplace_uses_a_source_every_codex_version_accepts() -> None:
    """Codex 0.121 rejects `url` sources and invalidates the whole marketplace;
    Codex 0.136 silently drops a plugin at the marketplace root. A `local`
    source pointing at a subdirectory is the one both accept."""
    marketplace = json.loads((REPO / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    for plugin in marketplace["plugins"]:
        source = plugin["source"]
        assert source == {"source": "local", "path": "./plugins/sia"}, source


def test_the_copy_is_self_contained(tmp_path: Path) -> None:
    """Codex copies only this directory into its cache. SIA refuses to run
    without its policy files, so they must travel with it."""
    project = tmp_path / "project"
    project.mkdir()
    run = lambda *a: subprocess.run([sys.executable, str(COPY / "cli.py"), "--json", *a],
                                    cwd=project, capture_output=True, text=True)
    assert run("init", "--mode", "orchestrator").returncode == 0
    checks = {c["name"]: c["ok"] for c in json.loads(run("doctor").stdout)["checks"]}
    assert checks["complete-workflow-policy"] is True
    assert (COPY / ".codex-plugin" / "plugin.json").is_file(), "Codex needs this to install a local plugin"
