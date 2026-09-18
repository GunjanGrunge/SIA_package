"""Opt-in host adapter templates.

Adapters only expose SIA's shared state packet. They intentionally contain no
host-specific copy of the workflow and never modify a project's root agent
instructions.
"""
from __future__ import annotations

from pathlib import Path

MARKER = "<!-- managed-by-sia-adapter-v1 -->"

ADAPTERS: dict[str, tuple[Path, str]] = {
    "claude": (
        Path(".claude/skills/sia/SKILL.md"),
        """---
name: sia
description: Continue the SIA workflow when the user explicitly invokes /sia.
disable-model-invocation: true
---

# SIA

<!-- managed-by-sia-adapter-v1 -->
Run `sia next --json` in the project root. Read `sia/AGENT.md` when SIA is
vendored, otherwise use the installed package's workflow contract. Follow the
returned stage and mode. Keep every task's native subagent run ID in SIA with
`sia task dispatch`; do not implement a dispatched task in the controller.
Other skills and plugins remain available and keep ownership of their files.
""",
    ),
    "codex": (
        Path(".agents/skills/sia/SKILL.md"),
        """---
name: sia
description: Continue the SIA workflow only when the user explicitly asks for SIA or invokes this skill.
---

# SIA

<!-- managed-by-sia-adapter-v1 -->
Run `sia next --json` in the project root and follow the returned stage and
mode. Read `sia/AGENT.md` if it is vendored. Use Codex native subagents for
independent implementation/review work and record their run IDs with
`sia task dispatch`. Do not replace `AGENTS.md` or interfere with other skills.
""",
    ),
    "kiro": (
        Path(".kiro/steering/sia.md"),
        """---
inclusion: manual
---

# SIA

<!-- managed-by-sia-adapter-v1 -->
Run `sia next --json` in the project root and follow the returned stage and
mode. Read `sia/AGENT.md` if it is vendored. In orchestrator mode, delegate
prepared tasks to Kiro subagents and persist each returned run/agent ID with
`sia task dispatch`. Keep BMAD, Superpowers, steering, skills, and hooks active;
SIA owns only `.sia/` and explicitly generated SIA artifacts.
""",
    ),
    "antigravity": (
        Path(".agents/workflows/sia.md"),
        """---
description: Continue the persistent SIA workflow for this project
---

# SIA workflow

<!-- managed-by-sia-adapter-v1 -->
When the user invokes `/sia`, run `sia next --json` in the project root and
follow the returned stage and mode. Read `sia/AGENT.md` if vendored. Use
Antigravity's native agents for prepared implementation and review tasks, then
record their run IDs with `sia task dispatch`. Do not alter other `.agents/`
workflows, skills, or agent definitions.
""",
    ),
}

ALIASES = {"claude-code": "claude", "openai-codex": "codex", "google-antigravity": "antigravity"}


def normalize_host(host: str) -> str:
    value = ALIASES.get(host.lower(), host.lower())
    if value not in ADAPTERS:
        raise ValueError(f"unsupported host {host!r}; choose: {', '.join(ADAPTERS)}")
    return value


def _safe_target(root: Path, relative: Path, create_parent: bool) -> Path:
    resolved_root = root.resolve()
    candidate = root / relative
    current = resolved_root
    for part in relative.parent.parts:
        current = current / part
        if current.exists():
            try:
                current.resolve().relative_to(resolved_root)
            except ValueError as exc:
                raise PermissionError(f"adapter path escapes project through redirected directory: {current}") from exc
    if create_parent:
        candidate.parent.mkdir(parents=True, exist_ok=True)
    if candidate.parent.exists():
        try:
            candidate.parent.resolve().relative_to(resolved_root)
            candidate.resolve(strict=False).relative_to(resolved_root)
        except ValueError as exc:
            raise PermissionError(f"adapter target escapes project root: {candidate}") from exc
    return candidate


def install_adapter(root: Path, host: str) -> tuple[str, Path]:
    host = normalize_host(host)
    relative, content = ADAPTERS[host]
    target = _safe_target(root, relative, create_parent=True)
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if existing == content:
            return "unchanged", target
        raise FileExistsError(f"refusing to overwrite existing adapter: {target}")
    target.write_text(content, encoding="utf-8")
    return "installed", target


def remove_adapter(root: Path, host: str) -> tuple[str, Path]:
    host = normalize_host(host)
    relative, content = ADAPTERS[host]
    target = _safe_target(root, relative, create_parent=False)
    if not target.exists():
        return "absent", target
    if target.read_text(encoding="utf-8") != content:
        raise PermissionError(f"refusing to remove modified or unmanaged file: {target}")
    target.unlink()
    return "removed", target
