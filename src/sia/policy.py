"""Locate the complete SIA policy in a source checkout or installed wheel."""
from __future__ import annotations

from importlib import metadata
from pathlib import Path
import sysconfig

REQUIRED_POLICY = {
    "AGENT.md",
    "capture-interface.md",
    "questioning-and-approval.md",
    "writing-agent-md.md",
    "writing-spec.md",
    "writing-plan.md",
    "writing-project-skills.md",
    "orchestration.md",
    "subagent-task-brief.md",
    "attribution.md",
    "security-gate.md",
}


def discover_policy_files() -> list[Path]:
    repository = Path(__file__).resolve().parents[2]
    source_files = [repository / "AGENT.md", repository / "capture-interface.md"]
    source_files.extend(sorted((repository / "guides").glob("*.md")))
    if REQUIRED_POLICY.issubset({path.name for path in source_files if path.is_file()}):
        return [path for path in source_files if path.is_file()]
    candidates = [
        Path(__file__).resolve().parent.parent / "sia_policy",
        Path(sysconfig.get_path("data")) / "sia_policy",
    ]
    for directory in candidates:
        installed = sorted(directory.glob("*.md")) if directory.exists() else []
        if REQUIRED_POLICY.issubset({path.name for path in installed}):
            return installed
    try:
        installed = []
        for entry in metadata.files("sia-package") or []:
            if "sia_policy" in entry.parts and entry.name.endswith(".md"):
                path = Path(entry.locate()).resolve()
                if path.is_file():
                    installed.append(path)
        if REQUIRED_POLICY.issubset({path.name for path in installed}):
            return sorted(installed, key=lambda path: path.name)
    except metadata.PackageNotFoundError:
        pass
    return []


def render_policy() -> str:
    files = discover_policy_files()
    if not files:
        fallback = Path(__file__).with_name("workflow.md")
        return fallback.read_text(encoding="utf-8")
    sections = []
    for path in files:
        sections.append(f"\n<!-- SIA POLICY FILE: {path.name} -->\n\n{path.read_text(encoding='utf-8').rstrip()}\n")
    return "".join(sections).lstrip()
