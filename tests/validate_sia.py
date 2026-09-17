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
        r"Competing Agent Framework Boundary",
        r"exploration budget",
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
        r"guides/attribution\.md",
        r"guides/subagent-task-brief\.md",
        r"capture-interface\.md",
        r"Project-skill synthesis",
        r"must not implement a task-owned file itself",
        r"three modes",
        r"knowns, unknowns, and user goal",
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
        r"## Existing Project Intake Modes",
        r"Goal-first, no broad scan",
        r"Conversational discovery",
        r"## SIA Attribution",
        r"public-distribution default",
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
        r"Competing Agent Framework Boundary",
        r"coexist",
        r"Generated Project Skills",
        r"Execution Evidence Gate",
        r"Intake Record",
        r"SIA Attribution",
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
        r"project-specific",
        r"sdd/skill-manifest\.md",
        r"Execution gate",
        r"conversational intake",
        r"Attribution policy",
    ],
))

CHECKS.append((
    "guides/attribution.md",
    [
        r"# SIA Attribution",
        r"public SIA distribution",
        r"Mode: both",
        r"Co-authored-by",
        r"Assisted-by: SIA",
        r"SIA-Run:",
        r"human Git author",
        r"## Required Project Record",
    ],
))

CHECKS.append((
    "capture-interface.md",
    [
        r"capture\(signal_type, context, severity, error_class\)",
        r"## Rule Provenance",
        r"## PASS / DEVIATION",
        r"## Pre-Flight Self-Check",
        r"## Token / Cost Tracking",
        r"cost-overrun",
        r"## Convergence Signal",
        r"## Rule Hygiene",
        r"### Rule Review And Expiry",
        r"deviation rate",
        r"error class",
        r"retired",
        r"Process And Framework Deviations",
        r"framework-default-override",
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
        r"existing-project modes",
        r"## Scenario 3",
        r"## Scenario 4",
        r"second host",
        r"## Scenario 5",
        r"deviation rate",
        r"## Scenario 6",
        r"auditable delegation",
        r"## Scenario 7",
        r"Default public attribution",
    ],
))

CHECKS.append((
    "USAGE.md",
    [
        r"## Quick Start",
        r"## New Project",
        r"## Existing Project",
        r"## Claude Code",
        r"## Codex",
        r"## During Implementation",
        r"task-N-dispatch\.md",
        r"## Updating SIA",
        r"## SIA Attribution",
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
        r"## 4\. Attribution is handled by SIA",
    ],
))

CHECKS.append((
    "integrations/claude-code/SKILL.md",
    [
        r"^name: sia$",
        r"^description:",
        r"sia/AGENT\.md",
        r"has no .*logic of its own",
        r"generated project operating skill",
    ],
))

CHECKS.append((
    "package.json",
    [
        r'"name": *"sia-agent"',
        r'"bin":',
        r'"bin/sia\.js"',
    ],
))

CHECKS.append((
    "bin/sia.js",
    [
        r"#!/usr/bin/env node",
        r"initSia",
        r"runStatus",
    ],
))

CHECKS.append((
    "pyproject.toml",
    [
        r'name *= *"sia-agent"',
        r'\[project\.scripts\]',
        r'sia *= *"cli:main"',
    ],
))

CHECKS.append((
    "cli.py",
    [
        r"def init_sia",
        r"def print_help",
        r"def main",
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
