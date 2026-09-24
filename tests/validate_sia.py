"""Structure-test harness for the sia/ package.

Verifies every deliverable markdown file contains its contractually
required section headings and phrases. This cannot check prose quality —
only that no required section was skipped or silently renamed out from
under a cross-reference in another file.
"""
import re
import sys
from pathlib import Path

SIA_ROOT = Path(__file__).resolve().parent.parent

# Each entry: (path relative to SIA_ROOT, [regex patterns required in that file])
CHECKS: list[tuple[str, list[str]]] = []

CHECKS.append((
    "AGENT.md",
    [
        r"^# SIA \(Self Improving Agents\)",
        r"## What This Is",
        r"INSTALL\.md",
        r"## Authority Order",
        r"User instructions",
        r"Integration\s+phase",
        r"## Launch Screen",
        r"banner\.py",
        r"BANNER\.txt",
        r"## Pipeline",
        r"guides/security-gate\.md",
        r"guides/questioning-and-approval\.md",
        r"guides/writing-agent-md\.md",
        r"guides/writing-spec\.md",
        r"guides/writing-plan\.md",
        r"guides/writing-project-skills\.md",
        r"guides/subagent-task-brief\.md",
        r"capture-interface\.md",
        r"Project-skill synthesis",
        r"must not implement a task-owned file itself",
    ],
))

CHECKS.append((
    "guides/security-gate.md",
    [
        r"## When To Load This Gate",
        r"software project",
        r"## Threat Classes",
        r"XSS",
        r"SQL",
        r"[Pp]rompt injection",
        r"[Hh]ard-coded secrets",
        r"## On A Finding",
    ],
))

CHECKS.append((
    "guides/questioning-and-approval.md",
    [
        r"## Batching Questions",
        r"## Severity Table",
        r"\| *Low",
        r"\| *Medium",
        r"\| *High",
        r"## Non-Negotiable Rules",
        r"[Nn]ever assume",
    ],
))

CHECKS.append((
    "guides/writing-agent-md.md",
    [
        r"## Required Sections",
        r"Session Logging",
        r"Project-Specific Rules",
        r"Accumulated Feedback Rules",
        r"tool=",
        r"Rule Provenance",
        r"active.*retired|retired.*active",
        r"Generated Project Skills",
        r"Execution Evidence Gate",
    ],
))

CHECKS.append((
    "guides/writing-spec.md",
    [
        r"## Required Sections",
        r"Architecture",
        r"Components",
        r"Data Flow",
        r"Error Handling",
        r"Testing",
        r"[Oo]ne approved pattern",
        r"one structured approval round",
    ],
))

CHECKS.append((
    "guides/writing-plan.md",
    [
        r"## Task Structure",
        r"Files",
        r"Interfaces",
        r"Steps",
        r"Commit",
        r"## Bite-Sized Steps",
        r"## Owned Files",
        r"ownership boundary",
        r"integration task",
        r"## Delegation And Evidence",
        r"task-N-dispatch\.md",
    ],
))

CHECKS.append((
    "guides/subagent-task-brief.md",
    [
        r"## Task Brief Format",
        r"## Task Report Format",
        r"## Progress Log Format",
        r"## Integration Report Format",
        r"Acceptance Criteria",
        r"[Ww]hatever subagent mechanism",
        r"Effort Budget",
        r"Escalate, don't improvise",
        r"Relevant Standing Rules",
        r"Standing rules checked",
        r"did this repeat a known mistake",
        r"## Execution Gate",
        r"Host Evidence",
        r"does not implement task-owned files itself",
    ],
))

CHECKS.append((
    "guides/writing-project-skills.md",
    [
        r"## When To Generate",
        r"## Output Locations",
        r"## Required Contents",
        r"## Skill Manifest",
        r"[Pp]roject[- ]specific",
        r"sdd/skill-manifest\.md",
        r"Execution gate",
    ],
))

CHECKS.append((
    "capture-interface.md",
    [
        r"capture\(signal_type, context, severity, error_class\)",
        r"## Rule Provenance",
        r"## PASS / DEVIATION",
        r"## Pre-Flight Self-Check",
        r"## Convergence Signal",
        r"## Rule Hygiene",
        r"### Rule Review And Expiry",
        r"deviation rate",
        r"error class",
        r"retired",
    ],
))

CHECKS.append((
    "CHANGELOG.md",
    [
        r"## \[0\.1\.0\] - 2026-09-13",
        r"AGENT\.md",
        r"security-gate\.md",
        r"capture-interface\.md",
    ],
))

CHECKS.append((
    "VALIDATION.md",
    [
        r"## Scenario 1",
        r"buyorwait",
        r"## Scenario 2",
        r"brownfield",
        r"## Scenario 3",
        r"## Scenario 4",
        r"second host",
        r"## Scenario 5",
        r"deviation rate",
        r"## Scenario 9",
        r"Cost-aware real multi-agent orchestration",
    ],
))

CHECKS.append((
    "BANNER.txt",
    [
        r"SIA v",
        r"Self-Improving Agents",
        r"Loop Engineering",
        r"Security Gate",
        r"<current project directory>",
    ],
))

CHECKS.append((
    "banner.py",
    [
        r"def print_banner",
        r"def get_claude_code_banner",
        r"def is_color_enabled",
    ],
))

CHECKS.append((
    "INSTALL.md",
    [
        r"## 1\. Copy the package",
        r"## 2\. Gitignore the vendored package, keep the generated artifacts",
        r"^sia/$",
        r"_bmad-output",
        r"## 3\. Give your host a way to find `sia/AGENT\.md`",
        r"integrations/claude-code/SKILL\.md",
        r"\.claude/skills/sia/SKILL\.md",
        r"project's own skill",
    ],
))

CHECKS.append((
    "integrations/claude-code/SKILL.md",
    [
        r"^name: sia$",
        r"^description:",
        r"sia/AGENT\.md",
        r"managed-by-sia-adapter-v2",
        r"sia orchestrate plan",
        r"requested_model_id",
    ],
))


CHECKS.append((
    "guides/attribution.md",
    [
        r"# SIA Attribution",
        r"public SIA distribution",
        r"Mode: both",
        r"Do not use `Co-authored-by`",
        r"Assisted-by: SIA",
        r"SIA-Run:",
        r"human Git author",
    ],
))

CHECKS.append((
    "USAGE.md",
    [
        r"## Quick Start",
        # Previously required `sia-package==0\.3\.0` -- a command that fails,
        # because PyPI only carries 0.2.0. The check was enforcing the bug.
        # Require the GitHub install, which works, until a release reaches PyPI.
        r"git\+https://github\.com/GunjanGrunge/SIA_package",
        r"sia next --json",
        r"## Cost-Aware Multi-Agent Orchestration",
        r"## Existing Project",
        r"## SIA Attribution",
        r"## During Implementation",
        r"## Checking Backend Status And Usage",
    ],
))

CHECKS.append((
    "pyproject.toml",
    [
        r'name = "sia-package"',
        # Shape only. Pinning the exact number meant every release had to edit
        # this test; the real risk -- version markers drifting apart across
        # files -- is asserted in tests/test_runtime_behaviour.py.
        r'version = "\d+\.\d+\.\d+"',
        r'requires-python = ">=3\.10"',
        r'sia = "sia\.cli:main"',
        r'where = \["src"\]',
        r'sia = \["workflow\.md"\]',
        r'"sia_policy"',
    ],
))

CHECKS.append((
    "src/sia/core.py",
    [
        r'MODES = \("advisory", "planning", "orchestrator"\)',
        r'def _project_lock',
        r'def _normalize_owned',
        r'owned path must remain inside the project root',
        r'independent review requires a different reviewer agent ID',
        r'evidence_sha256',
        r'integration evidence is stale',
        r'def configure_orchestration',
        r'def create_dispatch_plan',
        r'def apply_orchestration_receipt',
        r'budget-exceeded',
    ],
))

CHECKS.append((
    "src/sia/adapters.py",
    [
        r'def _safe_target',
        r'adapter target escapes project root',
        r'refusing to overwrite existing adapter',
        r'refusing to remove modified or unmanaged file',
        r'managed-by-sia-adapter-v2',
        r'"gemini": AdapterSpec',
        r'KNOWN_V1_HASHES',
    ],
))

CHECKS.append((
    "src/sia/policy.py",
    [
        r'"attribution\.md"',
        r'"orchestration\.md"',
        r'metadata\.files\("sia-package"\)',
    ],
))

CHECKS.append((
    "guides/orchestration.md",
    [
        r"# Cost-Aware Multi-Agent Orchestration",
        r"cheap/current/strong",
        r"native-host",
        r"standalone",
        r"shell=False",
        r"actual",
        r"calculated",
        r"estimated",
        r"unknown",
        r"cost-overrun",
    ],
))

CHECKS.append((
    "src/sia/routing.py",
    [
        r"def validate_orchestration_config",
        r"def route_task",
        r"def normalize_telemetry",
        r"ALLOWED_PLACEHOLDERS",
        r"warning_fraction",
    ],
))

CHECKS.append((
    "src/sia/orchestration.py",
    [
        r"asyncio\.create_subprocess_exec",
        r"shell=False|create_subprocess_exec",
        r"SIA_USAGE_JSON:",
        r"--approve-commands",
        r"run_standalone",
    ],
))

CHECKS.append((
    "HOST-INTEGRATION.md",
    [
        r"## Execution Backends",
        r"## Cost-Aware Model Routing",
        r"Native Re-entry And Receipt Protocol",
        r"Gemini CLI",
        r"Standalone Worker Security",
    ],
))

CHECKS.append((
    "integrations/gemini-cli/SKILL.md",
    [
        r"^name: sia$",
        r"managed-by-sia-adapter-v2",
        r"\.gemini/agents",
        r"sia orchestrate plan",
    ],
))

CHECKS.append((
    "cli.py",
    [
        # cli.py is the Claude Code plugin's entry point, not a legacy shim.
        # These two patterns pin the property that matters: it documents the
        # CLAUDE_PLUGIN_ROOT invocation, and it puts the bundled src/ on
        # sys.path itself. Lose the second and the plugin silently needs a
        # pip install again.
        r'CLAUDE_PLUGIN_ROOT',
        r'sys\.path\.insert',
        r'from sia\.cli import main',
    ],
))

CHECKS.append((
    "bin/sia.js",
    [
        r'#!/usr/bin/env node',
        r"'-m', 'sia'",
        # Previously required `pip install sia-package`, which installs 0.2.0
        # (no orchestration runtime). The launcher's error message must point
        # somewhere that actually works.
        r'git\+https://github\.com/GunjanGrunge/SIA_package',
    ],
))


def assert_contains(rel_path: str, patterns: list[str]) -> None:
    path = SIA_ROOT / rel_path
    if not path.exists():
        raise AssertionError(f"{rel_path} does not exist")
    text = path.read_text(encoding="utf-8")
    missing = [p for p in patterns if not re.search(p, text, re.MULTILINE)]
    if missing:
        raise AssertionError(f"{rel_path} missing required patterns: {missing}")
    print(f"PASS: {rel_path} ({len(patterns)} checks)")


def main() -> int:
    failures = []
    for rel_path, patterns in CHECKS:
        try:
            assert_contains(rel_path, patterns)
        except AssertionError as exc:
            print(f"FAIL: {exc}")
            failures.append(rel_path)
    if failures:
        print(f"\n{len(failures)} file(s) failed: {failures}")
        return 1
    print(f"\nAll {len(CHECKS)} file(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
