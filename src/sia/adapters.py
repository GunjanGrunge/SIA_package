"""Collision-safe, opt-in host launchers for SIA orchestration."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

MARKER = "<!-- managed-by-sia-adapter-v2 -->"
KNOWN_V1_HASHES = {
    "claude": "40de8a64d9f11a3fadac16502c29d83e3afd6d0b5e7ae7f4e4fcef1e88b7221a",
    "codex": "1541ff8043e239dfa3043db051b74e95ea6b0570eddda1e4e536b6b62a3461da",
    "kiro": "7e26768e56b2a0217ce1e8a5f38a34fcbbc592f33cb50e51bdc5a5e9c9d870d7",
    "antigravity": "8812b6a5f980de5944309360e9cf53476b5ee58da90c8dde420552e2dc963bdd",
}


@dataclass(frozen=True)
class AdapterSpec:
    path: Path
    content: str
    capabilities: tuple[str, ...]


NATIVE_PROTOCOL = """
## Managed multi-agent protocol

1. Run `sia next --json`. Continue only in `orchestrator` mode, at execution,
   when SIA owns that stage.
2. Prepare bounded tasks with disjoint owned files, risk, complexity, and an
   estimated token ceiling.
3. Run `sia orchestrate plan --backend native-host --host {host}`. Treat the
   persisted plan as immutable. Do not invent model aliases: use each
   operation's exact `requested_model_id` when the host supports selection.
4. Launch every ready implementer concurrently using native subagent tools.
   Keep other plugins/skills available; they are capabilities, not alternate
   SIA state stores. The controller must not edit task-owned files.
5. For each worker, save a non-empty report and submit a JSON receipt with
   plan ID/hash, operation ID, agent/run identity, requested/actual model,
   report path, and actual telemetry when exposed. Otherwise mark telemetry
   unknown/estimated. Ingest it with `sia orchestrate receipt --file <path>`.
6. After implementer receipts make reviewer operations ready, launch separate
   reviewers, preferably on the routed current/strong tier. Submit their
   receipts the same way. Run integration only after orchestration is complete.

Never claim a model, token count, cost, or native run ID the host did not expose.
"""


def _content(frontmatter: str, host: str, host_rules: str) -> str:
    return f"""{frontmatter}

# SIA cost-aware orchestrator

{MARKER}
Run `sia next --json` in the project root. Read `sia/AGENT.md` when vendored,
or run `sia guide` for the installed policy. SIA's `.sia/` state is the single
control plane. Activation is explicit; unrelated prompts and other plugins
remain independent.

{host_rules}
{NATIVE_PROTOCOL.format(host=host)}
"""


ADAPTERS: dict[str, AdapterSpec] = {
    "claude": AdapterSpec(
        Path(".claude/skills/sia/SKILL.md"),
        _content(
            """---
name: sia
description: Run SIA's cost-aware multi-agent workflow only when the user explicitly invokes /sia.
disable-model-invocation: true
---""",
            "claude",
            """Use Claude Code's Agent tool to launch independent operations in parallel.
Pass the operation model per invocation when supported; project subagents may
also define `model: haiku|sonnet|opus|<full-id>|inherit`. Use cheaper models
for bounded scans and the selected/current or strong model for demanding work
and independent review. Verify actual substitutions in `/tasks`.""",
        ),
        ("parallel-subagents", "per-invocation-model", "custom-agent-model"),
    ),
    "codex": AdapterSpec(
        Path(".agents/skills/sia/SKILL.md"),
        _content(
            """---
name: sia
description: Run SIA's cost-aware multi-agent workflow only when the user explicitly requests SIA.
---""",
            "codex",
            """Ask Codex to spawn one agent per ready operation and wait for all results.
Use each operation's requested model and appropriate reasoning effort through
custom agent configuration or the spawn request. Keep the repository's
`AGENTS.md` and existing `.agents/skills` unchanged.""",
        ),
        ("parallel-subagents", "custom-agent-model", "reasoning-effort"),
    ),
    "kiro": AdapterSpec(
        Path(".kiro/steering/sia.md"),
        _content(
            """---
inclusion: manual
---""",
            "kiro",
            """Use Kiro's native subagent tool and configured `.kiro/agents/` profiles.
Kiro selects a child model from the custom agent's top-level `model` field,
not from an external per-call API; map cheap/current/strong operations to
matching profiles. If the actual child model/run ID is unavailable, report it
as unknown rather than guessing. Independent graph nodes may run in parallel.""",
        ),
        ("parallel-subagents", "custom-agent-model", "dependency-graph"),
    ),
    "gemini": AdapterSpec(
        Path(".gemini/skills/sia/SKILL.md"),
        _content(
            """---
name: sia
description: Run SIA's cost-aware multi-agent workflow only when explicitly requested.
---""",
            "gemini",
            """Use Gemini CLI's native subagents (`.gemini/agents/*.md`) or built-ins.
Custom agent frontmatter supports an exact `model`, tools, max_turns, and
timeout_mins. Launch independent ready operations concurrently when the host
supports it; subagents cannot recursively spawn more subagents. Preserve
`GEMINI.md`, existing skills, settings, and policy rules.""",
        ),
        ("native-subagents", "custom-agent-model", "isolated-tools"),
    ),
    "antigravity": AdapterSpec(
        Path(".agents/workflows/sia.md"),
        _content(
            """---
description: Run SIA's cost-aware parallel multi-agent workflow
---""",
            "antigravity",
            """Use Antigravity's coordinator to launch independent specialized agents in
parallel and collect reports. Request each operation's model tier when the UI
or agent profile supports it; record unknown when selection or telemetry is
not exposed. Do not alter other `.agents/` workflows, skills, or definitions.""",
        ),
        ("parallel-agents", "coordinator", "artifact-handoff"),
    ),
}

ALIASES = {
    "claude-code": "claude",
    "openai-codex": "codex",
    "gemini-cli": "gemini",
    "google-antigravity": "antigravity",
}


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


def install_adapter(root: Path, host: str, upgrade: bool = False) -> tuple[str, Path]:
    host = normalize_host(host)
    spec = ADAPTERS[host]
    target = _safe_target(root, spec.path, create_parent=True)
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if existing == spec.content:
            return "unchanged", target
        digest = hashlib.sha256(existing.encode("utf-8")).hexdigest()
        if upgrade and KNOWN_V1_HASHES.get(host) == digest:
            target.write_text(spec.content, encoding="utf-8")
            return "upgraded", target
        raise FileExistsError(
            f"refusing to overwrite existing adapter: {target}; use --upgrade only for an unchanged managed v1 adapter"
        )
    target.write_text(spec.content, encoding="utf-8")
    return "installed", target


def remove_adapter(root: Path, host: str) -> tuple[str, Path]:
    host = normalize_host(host)
    spec = ADAPTERS[host]
    target = _safe_target(root, spec.path, create_parent=False)
    if not target.exists():
        return "absent", target
    if target.read_text(encoding="utf-8") != spec.content:
        raise PermissionError(f"refusing to remove modified or unmanaged file: {target}")
    target.unlink()
    return "removed", target
