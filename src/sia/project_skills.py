"""Project skills that SIA derives from the project's own requirements.

A project skill is a SKILL.md written where hosts discover project skills
(`.claude/skills/` for Claude Code, `.agents/skills/` for Codex), so the main
agent, every subagent and any collaborating plugin can invoke it.

The contract that keeps the pack from being invented:

* **Every skill cites the requirement it serves.** Each citation is a quote
  that must literally appear in a requirement source: a file recorded as
  evidence for an intake, spec, project-instructions or plan stage, or the
  project's own agent instructions (AGENTS.md, CLAUDE.md, AGENT.md, GEMINI.md).
  No citable requirement, no skill. There is deliberately no built-in catalog
  of domains: what a project needs comes from its spec, not from a guess about
  its dependencies.
* **SIA never overwrites a file it did not write.** A skill directory that
  exists without SIA's marker is someone else's; a SIA skill edited by hand
  (its hash no longer matches the registry) is the user's now.
* **Skills keep up with the project.** Each skill carries the learned rules
  whose scope overlaps its paths, re-rendered whenever a rule is added or
  retired.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11: skip pyproject parsing
    tomllib = None
from pathlib import Path
from typing import Any, Iterable

from .core import Project, SiaError, _project_lock, _read_json, _write_json, installed_plugin_frameworks, utc_now

HOST_DIRS = {"claude": ".claude/skills", "codex": ".agents/skills"}
DEFAULT_HOSTS = ("claude", "codex")
REQUIREMENT_STAGES = ("intake", "spec", "project-instructions", "plan")
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", "AGENT.md", "GEMINI.md")
MARKER = "<!-- sia:generated -- edits by hand make SIA stop updating this file -->"
RULES_START = "<!-- sia:rules:start -->"
RULES_END = "<!-- sia:rules:end -->"
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
SECRET = re.compile(
    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{20,}|\bghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}"
)
MANIFESTS = ("requirements.txt", "pyproject.toml", "package.json", "go.mod", "Cargo.toml", "Gemfile", "pom.xml", "build.gradle")


def _registry_path(project: Project) -> Path:
    return project.sia / "skills.json"


def _registry(project: Project) -> list[dict[str, Any]]:
    return _read_json(_registry_path(project), [])


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _squash(text: str) -> str:
    return " ".join(text.split()).casefold()


def requirement_sources(project: Project) -> list[str]:
    """Files a skill may cite: requirement-stage evidence plus agent instructions."""
    _, state = project.require_initialized()
    sources: list[str] = []
    for entry in state.get("history", []):
        if entry.get("stage") in REQUIREMENT_STAGES:
            sources.extend(entry.get("evidence", []))
    sources.extend(name for name in INSTRUCTION_FILES if (project.root / name).is_file())
    return list(dict.fromkeys(path for path in sources if (project.root / path).is_file()))


def _dependencies(root: Path) -> dict[str, list[str]]:
    """Dependency names per manifest: context for the agent, never a verdict."""
    found: dict[str, list[str]] = {}
    for name in MANIFESTS:
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        names: list[str] = []
        try:
            if name == "package.json":
                data = json.loads(text)
                for key in ("dependencies", "devDependencies"):
                    names += list((data.get(key) or {}).keys())
            elif name == "pyproject.toml" and tomllib is not None:
                data = tomllib.loads(text)
                raw = list(data.get("project", {}).get("dependencies", []))
                raw += list(data.get("tool", {}).get("poetry", {}).get("dependencies", {}).keys())
                names += [re.split(r"[<>=!~\[; ]", item, maxsplit=1)[0] for item in raw]
            elif name == "requirements.txt":
                for line in text.splitlines():
                    line = line.split("#", 1)[0].strip()
                    if line and not line.startswith("-"):
                        names.append(re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0])
            else:
                names.append("(present)")
        except ValueError:  # JSONDecodeError and TOMLDecodeError both subclass it
            names.append("(unparseable)")
        found[name] = sorted({item for item in names if item and item.lower() != "python"})[:80]
    return found


def _existing_skills(project: Project) -> list[dict[str, Any]]:
    registered = {entry["name"] for entry in _registry(project) if entry.get("status") == "active"}
    seen: dict[str, dict[str, Any]] = {}
    for host, directory in HOST_DIRS.items():
        for skill in sorted((project.root / directory).glob("*/SKILL.md")):
            name = skill.parent.name
            entry = seen.setdefault(name, {"name": name, "hosts": [], "generated_by_sia": name in registered})
            entry["hosts"].append(host)
    return list(seen.values())


def skill_context(project: Project) -> dict[str, Any]:
    """Everything an agent needs to decide which project skills to write."""
    config, state = project.require_initialized()
    sources = requirement_sources(project)
    return {
        "current_stage": state.get("current_stage"),
        "requirement_sources": sources,
        "repository": {
            "dependencies": _dependencies(project.root),
            "top_level": sorted(p.name + ("/" if p.is_dir() else "") for p in project.root.iterdir()
                                if not p.name.startswith(".") or p.name in {".github"})[:60],
        },
        "installed_frameworks": installed_plugin_frameworks(),
        "detected_frameworks": config.get("detected_frameworks", {}),
        "existing_project_skills": _existing_skills(project),
        "active_rules": [{"id": r["id"], "text": r["text"], "scope": r.get("scope", "**")} for r in project.active_rules()],
        "instructions": (
            "Read every requirement source. Write one skill per distinct capability the "
            "requirements call for that no existing or installed skill already covers. "
            "Each skill must cite, verbatim, the requirement text it serves. Dependencies "
            "and layout tell you how to do the work (real commands, real paths), not what "
            "work to do. Do not write a skill the requirements do not call for."
            if sources else
            "No requirement sources yet. Advance intake/spec with their documents as "
            "evidence (or add AGENTS.md) before generating project skills."
        ),
    }


def _validate_requirements(project: Project, requirements: Any) -> list[dict[str, str]]:
    if not isinstance(requirements, list) or not requirements:
        raise SiaError("a project skill must cite at least one requirement it serves")
    allowed = requirement_sources(project)
    if not allowed:
        raise SiaError("no requirement sources yet; advance intake/spec with evidence first (see sia_skill_context)")
    cited = []
    for item in requirements:
        if not isinstance(item, dict) or not isinstance(item.get("source"), str) or not isinstance(item.get("quote"), str):
            raise SiaError("each requirement needs a 'source' path and a 'quote'")
        candidate = Path(item["source"])
        candidate = candidate if candidate.is_absolute() else project.root / candidate
        try:
            source = candidate.resolve().relative_to(project.root).as_posix()
        except ValueError:
            source = item["source"]
        if source not in allowed:
            raise SiaError(f"{item['source']!r} is not a requirement source; cite one of: {', '.join(allowed)}")
        quote = item["quote"].strip()
        if len(_squash(quote)) < 12:
            raise SiaError(f"quote from {source} is too short to identify a requirement: {quote!r}")
        text = (project.root / source).read_text(encoding="utf-8", errors="replace")
        if _squash(quote) not in _squash(text):
            raise SiaError(f"quote not found in {source}: {quote!r}. Cite the requirement verbatim.")
        # Stored on one line: specs wrap mid-sentence, and a raw newline broke
        # the manifest table in the first live run.
        cited.append({"source": source, "quote": " ".join(quote.split())})
    return cited


def _overlaps(rule_scope: str, paths: list[str]) -> bool:
    if rule_scope in {"*", "**", "**/*"}:
        return True
    return any(fnmatch.fnmatch(path, rule_scope) or fnmatch.fnmatch(rule_scope, path) for path in paths)


def _rules_block(project: Project, paths: list[str]) -> str:
    rules = [rule for rule in project.active_rules() if _overlaps(rule.get("scope", "**"), paths)]
    lines = [RULES_START, "## Standing rules for this project", ""]
    if rules:
        # The user's own words are deliberately not repeated: a quote can contain
        # the very text a rule forbids, and a skill is read as an example.
        lines += [f"- {rule['text']} ({rule['id']})" for rule in rules]
    else:
        lines.append("- None learned yet.")
    lines.append(RULES_END)
    return "\n".join(lines)


def _render(project: Project, entry: dict[str, Any]) -> str:
    description = entry["description"].replace("\n", " ").strip()
    why = "\n".join(f"- `{item['source']}`: \"{item['quote']}\"" for item in entry["requirements"])
    scope = ", ".join(f"`{path}`" for path in entry["paths"])
    return (
        f"---\nname: {entry['name']}\ndescription: {json.dumps(description)}\n---\n\n"
        f"{MARKER}\n\n"
        f"{entry['body'].strip()}\n\n"
        f"## Why this skill exists\n\nGenerated by SIA from this project's requirements:\n\n{why}\n\n"
        f"Applies to: {scope}\n\n"
        f"{_rules_block(project, entry['paths'])}\n"
    )


def _targets(project: Project, entry: dict[str, Any]) -> list[Path]:
    return [project.root / HOST_DIRS[host] / entry["name"] / "SKILL.md" for host in entry["hosts"]]


def _write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_skill(
    project: Project,
    name: str,
    description: str,
    body: str,
    requirements: Any,
    paths: Iterable[str] | None = None,
    hosts: Iterable[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(name, str) or not NAME.match(name):
        raise SiaError("name must be kebab-case: lowercase letters, digits and hyphens, 2-63 chars")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise SiaError("description is required and must be at most 1024 characters")
    if "use when" not in description.casefold():
        raise SiaError("description must say when to use the skill (include 'Use when ...') so hosts can trigger it")
    if not isinstance(body, str) or len(body.strip()) < 80:
        raise SiaError("body must hold the skill's actual instructions (at least a short paragraph)")
    for label, text in (("description", description), ("body", body)):
        if SECRET.search(text):
            raise SiaError(f"{label} looks like it contains a credential; never put secrets in a skill")
    host_list = list(dict.fromkeys(hosts or DEFAULT_HOSTS))
    unknown = [host for host in host_list if host not in HOST_DIRS]
    if unknown:
        raise SiaError(f"unknown host(s) {unknown}; choose from {sorted(HOST_DIRS)}")
    path_list = [str(path) for path in (paths or ["**"])]
    cited = _validate_requirements(project, requirements)

    with _project_lock(project.sia / "project.lock"):
        registry = _registry(project)
        previous = next((item for item in registry if item["name"] == name), None)
        entry = {
            "name": name,
            "description": description.strip(),
            "body": body,
            "requirements": cited,
            "paths": path_list,
            "hosts": host_list,
            "status": "active",
            "created_at": previous.get("created_at") if previous else utc_now(),
            "updated_at": utc_now(),
            "version": (previous.get("version", 0) + 1) if previous else 1,
            "files": {},
        }
        old_files = (previous or {}).get("files", {}) if previous and previous.get("status") == "active" else {}
        for target in _targets(project, entry):
            relative = target.relative_to(project.root).as_posix()
            if target.exists():
                current = target.read_text(encoding="utf-8", errors="replace")
                if relative not in old_files:
                    raise SiaError(f"{relative} already exists and was not written by SIA; choose another name")
                if _sha(current) != old_files[relative]:
                    raise SiaError(f"{relative} was edited by hand since SIA wrote it; SIA will not overwrite it")
        text = _render(project, entry)
        for target in _targets(project, entry):
            _write_file(target, text)
            entry["files"][target.relative_to(project.root).as_posix()] = _sha(text)
        registry = [item for item in registry if item["name"] != name] + [entry]
        _write_json(_registry_path(project), registry)
        _write_manifest(project, registry)
    return _summary(entry)


def refresh_rules(project: Project) -> dict[str, Any]:
    """Re-render the standing-rules block of every SIA skill. Skips hand-edited files."""
    if not _registry_path(project).exists():
        return {"updated": [], "skipped": []}
    updated, skipped = [], []
    with _project_lock(project.sia / "project.lock"):
        registry = _registry(project)
        for entry in registry:
            if entry.get("status") != "active":
                continue
            text = _render(project, entry)
            for relative, recorded in list(entry.get("files", {}).items()):
                target = project.root / relative
                if not target.is_file() or _sha(target.read_text(encoding="utf-8", errors="replace")) != recorded:
                    skipped.append(relative)
                    continue
                if recorded != _sha(text):
                    _write_file(target, text)
                    entry["files"][relative] = _sha(text)
                    updated.append(relative)
        _write_json(_registry_path(project), registry)
    return {"updated": updated, "skipped": skipped}


def retire_skill(project: Project, name: str, reason: str) -> dict[str, Any]:
    with _project_lock(project.sia / "project.lock"):
        registry = _registry(project)
        entry = next((item for item in registry if item["name"] == name and item.get("status") == "active"), None)
        if entry is None:
            raise SiaError(f"no active SIA-generated skill named {name!r}")
        removed, kept = [], []
        for relative, recorded in entry.get("files", {}).items():
            target = project.root / relative
            if target.is_file() and _sha(target.read_text(encoding="utf-8", errors="replace")) == recorded:
                target.unlink()
                if not any(target.parent.iterdir()):
                    target.parent.rmdir()
                removed.append(relative)
            elif target.exists():
                kept.append(relative)
        entry.update({"status": "retired", "retired_at": utc_now(), "retirement_reason": reason, "files": {}})
        _write_json(_registry_path(project), registry)
        _write_manifest(project, registry)
    return {"name": name, "removed": removed, "kept_hand_edited": kept}


def list_skills(project: Project) -> list[dict[str, Any]]:
    project.require_initialized()
    return [_summary(entry) for entry in _registry(project)]


def _summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: entry.get(key) for key in ("name", "description", "status", "version", "paths", "hosts", "requirements", "updated_at")} | {
        "files": sorted(entry.get("files", {}))
    }


def _clip(text: str, limit: int = 100) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _write_manifest(project: Project, registry: list[dict[str, Any]]) -> None:
    lines = [
        "# Skill manifest",
        "",
        "Generated by SIA. Every skill cites the project requirement it serves.",
        "",
        "| Skill | Status | Version | Hosts | Applies to | Requirement | Updated |",
        "|---|---|---|---|---|---|---|",
    ]
    for entry in registry:
        requirement = "; ".join(f"{item['source']}: \"{_clip(item['quote'])}\"" for item in entry["requirements"]).replace("|", "\\|")
        lines.append(
            f"| {entry['name']} | {entry.get('status')} | {entry.get('version')} | {', '.join(entry['hosts'])} "
            f"| {', '.join(entry['paths'])} | {requirement} | {entry.get('updated_at')} |"
        )
    frameworks = installed_plugin_frameworks()
    if frameworks:
        lines += ["", "Installed frameworks these skills complement: " + ", ".join(sorted(frameworks)) + "."]
    target = project.root / "sdd" / "skill-manifest.md"
    _write_file(target, "\n".join(lines) + "\n")
