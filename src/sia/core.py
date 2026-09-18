"""Durable project state for SIA.

The runtime deliberately orchestrates evidence rather than vendor processes.
Hosts remain responsible for creating their own native subagents.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .policy import REQUIRED_POLICY, discover_policy_files

MODES = ("advisory", "planning", "orchestrator")
STAGES = {
    "advisory": ["feedback"],
    "planning": ["intake", "spec", "project-instructions", "skills", "plan"],
    "orchestrator": ["intake", "spec", "project-instructions", "skills", "plan", "execution", "feedback"],
}
STAGE_ACTIONS = {
    "intake": "Inspect requirements and existing tooling; confirm project type, boundaries, and stage ownership.",
    "spec": "Author and obtain approval for the project spec under docs/specs/.",
    "project-instructions": "Create or update the project's own agent instructions without replacing competing framework files.",
    "skills": "Generate evidence-derived project skills and sdd/skill-manifest.md.",
    "plan": "Write an approved plan with exact file ownership and interfaces.",
    "execution": "Prepare tasks, dispatch real native host subagents, independently review them, then record integration evidence.",
    "feedback": "Record PASS/DEVIATION outcomes, run preflight, and review convergence before the next proposal.",
}
FRAMEWORK_MARKERS = {
    "bmad": ("_bmad", ".bmad", "bmad"),
    "superpowers": (".superpowers", "superpowers"),
}
TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class SiaError(RuntimeError):
    """A user-correctable SIA workflow error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SiaError(f"invalid JSON in {path}: {exc}") from exc


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


@contextmanager
def _project_lock(path: Path):
    """Serialize project mutations across host-agent processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def state_locked(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with _project_lock(self.sia / "project.lock"):
            return method(self, *args, **kwargs)
    return wrapped


def _copy_evidence(source: Path, target: Path) -> None:
    if not source.is_file():
        raise SiaError(f"evidence file does not exist: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _normalize_owned(root: Path, value: str) -> str:
    if any(character in value for character in "*?[]"):
        raise SiaError(f"ownership must be an exact file or directory path, not a glob: {value}")
    candidate = (root / value).resolve(strict=False) if not Path(value).is_absolute() else Path(value).resolve(strict=False)
    try:
        relative = candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise SiaError(f"owned path must remain inside the project root: {value}") from exc
    if str(relative) in {"", "."}:
        raise SiaError("a task cannot own the entire project root")
    normalized = relative.as_posix()
    return normalized.casefold() if os.name == "nt" else normalized


def _paths_overlap(left: str, right: str) -> bool:
    first, second = PurePosixPath(left), PurePosixPath(right)
    return first == second or first in second.parents or second in first.parents


class Project:
    def __init__(self, root: Path | str = ".") -> None:
        self.root = Path(root).resolve()
        self.sia = self.root / ".sia"
        self.config_path = self.sia / "config.json"
        self.state_path = self.sia / "state.json"
        self.events_path = self.sia / "events.jsonl"
        self.rules_path = self.sia / "rules.json"

    def require_initialized(self) -> tuple[dict[str, Any], dict[str, Any]]:
        config = _read_json(self.config_path)
        state = _read_json(self.state_path)
        if not isinstance(config, dict) or not isinstance(state, dict):
            raise SiaError(f"{self.root} is not initialized; run `sia init`")
        return config, state

    def detect_frameworks(self) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for name, markers in FRAMEWORK_MARKERS.items():
            paths = [marker for marker in markers if (self.root / marker).exists()]
            if paths:
                found[name] = paths
        return found

    @state_locked
    def initialize(self, mode: str, force: bool = False) -> dict[str, Any]:
        if mode not in MODES:
            raise SiaError(f"invalid mode {mode!r}; choose: {', '.join(MODES)}")
        if self.config_path.exists() and not force:
            raise SiaError(f"already initialized at {self.sia}; use --force to reset state")
        self.sia.mkdir(parents=True, exist_ok=True)
        (self.sia / "runs").mkdir(exist_ok=True)
        config = {
            "schema_version": 1,
            "mode": mode,
            "framework_policy": "bridge",
            "detected_frameworks": self.detect_frameworks(),
            "stage_owners": {stage: "sia" for stage in STAGES[mode]},
            "created_at": utc_now(),
        }
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        state = {
            "schema_version": 1,
            "run_id": run_id,
            "current_stage": STAGES[mode][0],
            "completed_stages": [],
            "history": [],
            "tasks": {},
            "integration": None,
            "updated_at": utc_now(),
        }
        _write_json(self.config_path, config)
        _write_json(self.state_path, state)
        _write_json(self.rules_path, [])
        self.events_path.touch(exist_ok=True)
        return self.status()

    def status(self) -> dict[str, Any]:
        config, state = self.require_initialized()
        tasks = state.get("tasks", {})
        return {
            "root": str(self.root),
            "mode": config["mode"],
            "framework_policy": config.get("framework_policy", "bridge"),
            "detected_frameworks": config.get("detected_frameworks", {}),
            "stage_owners": config.get("stage_owners", {}),
            "current_stage_owner": config.get("stage_owners", {}).get(state.get("current_stage")) if state.get("current_stage") else None,
            "run_id": state["run_id"],
            "current_stage": state.get("current_stage"),
            "completed_stages": state.get("completed_stages", []),
            "tasks": {key: value.get("status") for key, value in tasks.items()},
            "integration_recorded": bool(state.get("integration")),
        }

    def next_packet(self) -> dict[str, Any]:
        config, state = self.require_initialized()
        stage = state.get("current_stage")
        if stage is None:
            return {**self.status(), "action": "Workflow complete. Start a new run with `sia init --force` only after preserving evidence."}
        owner = config.get("stage_owners", {}).get(stage, "sia")
        action = STAGE_ACTIONS[stage] if owner == "sia" else f"Hand this stage to {owner}; require its artifact evidence before SIA advances. " + STAGE_ACTIONS[stage]
        return {
            **self.status(),
            "action": action,
            "reentry_contract": [
                "Treat this packet as authoritative workflow position.",
                "Keep competing frameworks active and honor stage_owners in .sia/config.json.",
                "Persist evidence before advancing; conversation claims are not evidence.",
            ],
            "commands": self._stage_commands(stage),
            "workflow_contract": "Run `sia guide` if sia/AGENT.md is not vendored in this project.",
        }

    @staticmethod
    def _stage_commands(stage: str) -> list[str]:
        if stage == "execution":
            return [
                "sia task prepare --task <id> --brief <file> --files <owned-path> [...]",
                "sia task dispatch --task <id> --host <host> --agent-id <id> --native-run-id <id>",
                "sia task finish --task <id> --report <file> --review <file> --reviewer-agent-id <id> --review-native-run-id <id>",
                "sia integration --evidence <file>",
                "sia advance",
            ]
        if stage == "feedback":
            return ["sia record --outcome pass ...", "sia capture ...", "sia preflight --scope <path>", "sia convergence", "sia advance"]
        return ["sia advance --evidence <artifact> [...]"]

    @state_locked
    def set_stage_owner(self, stage: str, owner: str) -> dict[str, Any]:
        config, _ = self.require_initialized()
        if stage not in STAGES[config["mode"]]:
            raise SiaError(f"stage {stage!r} is not active in {config['mode']} mode")
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$", owner):
            raise SiaError("owner must use letters, digits, dot, underscore, or hyphen")
        config.setdefault("stage_owners", {})[stage] = owner
        _write_json(self.config_path, config)
        return {"stage": stage, "owner": owner, "stage_owners": config["stage_owners"]}

    @state_locked
    def advance(self, evidence: Iterable[str]) -> dict[str, Any]:
        config, state = self.require_initialized()
        stage = state.get("current_stage")
        if stage is None:
            raise SiaError("workflow is already complete")
        evidence_paths = [self._relative_existing(value) for value in evidence]
        if stage in {"spec", "project-instructions", "skills", "plan"} and not evidence_paths:
            raise SiaError(f"stage {stage!r} requires at least one --evidence file")
        if stage == "execution":
            tasks = state.get("tasks", {})
            if not tasks:
                raise SiaError("execution cannot complete without prepared tasks")
            unfinished = [task_id for task_id, task in tasks.items() if task.get("status") != "reviewed"]
            if unfinished:
                raise SiaError(f"execution tasks are not independently reviewed: {', '.join(unfinished)}")
            integration = state.get("integration")
            if not integration:
                raise SiaError("execution requires `sia integration --evidence <file>`")
            if sorted(integration.get("covered_tasks", [])) != sorted(tasks):
                raise SiaError("integration evidence is stale; rerun integration for the current task set")
        state.setdefault("completed_stages", []).append(stage)
        state.setdefault("history", []).append({"stage": stage, "completed_at": utc_now(), "evidence": evidence_paths})
        stages = STAGES[config["mode"]]
        index = stages.index(stage)
        state["current_stage"] = stages[index + 1] if index + 1 < len(stages) else None
        state["updated_at"] = utc_now()
        _write_json(self.state_path, state)
        return self.next_packet()

    def _relative_existing(self, value: str) -> str:
        path = (self.root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
        if not path.exists():
            raise SiaError(f"evidence path does not exist: {path}")
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise SiaError(f"evidence must be inside project root: {path}") from exc

    @state_locked
    def record_event(self, outcome: str, signal: str, context: str, severity: str, error_class: str | None) -> dict[str, Any]:
        self.require_initialized()
        normalized = outcome.upper()
        if normalized not in {"PASS", "DEVIATION"}:
            raise SiaError("outcome must be PASS or DEVIATION")
        if normalized == "DEVIATION" and not error_class:
            raise SiaError("DEVIATION requires --error-class")
        event = {
            "id": "evt-" + uuid.uuid4().hex[:12],
            "timestamp": utc_now(),
            "outcome": normalized,
            "signal_type": signal,
            "context": context,
            "severity": severity.lower(),
            "error_class": error_class,
        }
        with self.events_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
        return event

    def events(self) -> list[dict[str, Any]]:
        self.require_initialized()
        result = []
        for number, line in enumerate(self.events_path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise SiaError(f"invalid event JSON on line {number}: {exc}") from exc
        return result

    def convergence(self) -> dict[str, Any]:
        events = self.events()
        total = len(events)
        deviations = [event for event in events if event.get("outcome") == "DEVIATION"]
        classes = Counter(event.get("error_class") for event in deviations if event.get("error_class"))
        return {
            "total_proposals": total,
            "passes": total - len(deviations),
            "deviations": len(deviations),
            "overall_deviation_rate": len(deviations) / total if total else 0.0,
            "by_error_class": {
                key: {"deviations": count, "rate_per_proposal": count / total if total else 0.0}
                for key, count in sorted(classes.items())
            },
        }

    @state_locked
    def add_rule(self, text: str, scope: str, severity: str, error_class: str, source_event: str) -> dict[str, Any]:
        events = self.events()
        source = next((event for event in events if event.get("id") == source_event), None)
        if source is None:
            raise SiaError(f"source event not found: {source_event}")
        rules = _read_json(self.rules_path, [])
        rule = {
            "id": "rule-" + uuid.uuid4().hex[:10],
            "text": text,
            "scope": scope,
            "severity": severity.lower(),
            "error_class": error_class,
            "source_event": source_event,
            "evidence": source.get("context"),
            "introduced_at": utc_now(),
            "status": "active",
        }
        rules.append(rule)
        _write_json(self.rules_path, rules)
        return rule

    @state_locked
    def retire_rule(self, rule_id: str, reason: str) -> dict[str, Any]:
        self.require_initialized()
        rules = _read_json(self.rules_path, [])
        rule = next((item for item in rules if item.get("id") == rule_id), None)
        if rule is None:
            raise SiaError(f"rule not found: {rule_id}")
        rule.update({"status": "retired", "retired_at": utc_now(), "retirement_reason": reason})
        _write_json(self.rules_path, rules)
        return rule

    def preflight(self, scopes: Iterable[str], acknowledgements: set[str]) -> tuple[dict[str, Any], bool]:
        self.require_initialized()
        scope_list = list(scopes)
        active = [rule for rule in _read_json(self.rules_path, []) if rule.get("status") == "active"]
        relevant = [
            rule for rule in active
            if any(fnmatch.fnmatch(scope, rule.get("scope", "*")) or fnmatch.fnmatch(rule.get("scope", "*"), scope) for scope in scope_list)
        ]
        blocked = [rule for rule in relevant if rule.get("severity") in {"medium", "high"} and rule["id"] not in acknowledgements]
        return {"scopes": scope_list, "relevant_rules": relevant, "unacknowledged_gates": [rule["id"] for rule in blocked], "clear": not blocked}, not blocked

    @state_locked
    def prepare_task(self, task_id: str, brief: Path, files: Iterable[str]) -> dict[str, Any]:
        config, state = self.require_initialized()
        if config["mode"] != "orchestrator" or state.get("current_stage") != "execution":
            raise SiaError("tasks can only be prepared during execution in orchestrator mode")
        if not TASK_ID.match(task_id):
            raise SiaError("task ID must use letters, digits, dot, underscore, or hyphen")
        owned = sorted({_normalize_owned(self.root, value) for value in files})
        if not owned:
            raise SiaError("at least one --files ownership path is required")
        if task_id in state.get("tasks", {}):
            raise SiaError(f"task already exists: {task_id}")
        for other_id, task in state.get("tasks", {}).items():
            if task.get("status") in {"prepared", "dispatched"}:
                overlap = sorted({left for left in owned for right in task.get("files", []) if _paths_overlap(left, right)})
                if overlap:
                    raise SiaError(f"file ownership overlaps active task {other_id}: {', '.join(overlap)}")
        task_dir = self.sia / "runs" / state["run_id"] / "tasks" / task_id
        _copy_evidence(brief.resolve(), task_dir / "brief.md")
        task = {"id": task_id, "files": owned, "status": "prepared", "prepared_at": utc_now(), "directory": task_dir.relative_to(self.root).as_posix()}
        state.setdefault("tasks", {})[task_id] = task
        state["integration"] = None
        state["updated_at"] = utc_now()
        _write_json(task_dir / "task.json", task)
        _write_json(self.state_path, state)
        return task

    @state_locked
    def dispatch_task(self, task_id: str, host: str, agent_id: str, native_run_id: str) -> dict[str, Any]:
        _, state = self.require_initialized()
        task = state.get("tasks", {}).get(task_id)
        if not task or task.get("status") != "prepared":
            raise SiaError(f"task {task_id!r} is not prepared")
        evidence = {"task": task_id, "host": host, "agent_id": agent_id, "native_run_id": native_run_id, "dispatched_at": utc_now()}
        task_dir = self.root / task["directory"]
        _write_json(task_dir / "dispatch.json", evidence)
        task.update({"status": "dispatched", "dispatch": evidence})
        state["integration"] = None
        _write_json(self.state_path, state)
        return evidence

    @state_locked
    def finish_task(self, task_id: str, report: Path, review: Path, reviewer_agent_id: str, review_native_run_id: str) -> dict[str, Any]:
        _, state = self.require_initialized()
        task = state.get("tasks", {}).get(task_id)
        if not task or task.get("status") != "dispatched":
            raise SiaError(f"task {task_id!r} has no recorded native dispatch")
        if reviewer_agent_id == task.get("dispatch", {}).get("agent_id"):
            raise SiaError("independent review requires a different reviewer agent ID")
        if not report.is_file() or not report.read_text(encoding="utf-8").strip():
            raise SiaError("implementer report must be a non-empty UTF-8 file")
        if not review.is_file() or not review.read_text(encoding="utf-8").strip():
            raise SiaError("review must be a non-empty UTF-8 file")
        task_dir = self.root / task["directory"]
        _copy_evidence(report.resolve(), task_dir / "report.md")
        _copy_evidence(review.resolve(), task_dir / "review.md")
        review_dispatch = {
            "task": task_id,
            "host": task.get("dispatch", {}).get("host"),
            "agent_id": reviewer_agent_id,
            "native_run_id": review_native_run_id,
            "reviewed_at": utc_now(),
        }
        _write_json(task_dir / "review-dispatch.json", review_dispatch)
        task.update({"status": "reviewed", "reviewed_at": review_dispatch["reviewed_at"], "review_dispatch": review_dispatch})
        state["integration"] = None
        _write_json(self.state_path, state)
        return task

    @state_locked
    def record_integration(self, evidence: Path) -> dict[str, Any]:
        config, state = self.require_initialized()
        if config["mode"] != "orchestrator" or state.get("current_stage") != "execution":
            raise SiaError("integration evidence is only accepted during orchestrator execution")
        tasks = state.get("tasks", {})
        if not tasks:
            raise SiaError("integration requires at least one task")
        unfinished = [task_id for task_id, task in tasks.items() if task.get("status") != "reviewed"]
        if unfinished:
            raise SiaError(f"integration must follow all independent reviews: {', '.join(unfinished)}")
        if not evidence.is_file() or not evidence.read_text(encoding="utf-8").strip():
            raise SiaError("integration evidence must be a non-empty UTF-8 file")
        task_dir = self.sia / "runs" / state["run_id"]
        _copy_evidence(evidence.resolve(), task_dir / "integration.md")
        digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
        state["integration"] = {
            "path": (task_dir / "integration.md").relative_to(self.root).as_posix(),
            "recorded_at": utc_now(),
            "covered_tasks": sorted(tasks),
            "evidence_sha256": digest,
        }
        _write_json(self.state_path, state)
        return state["integration"]

    def doctor(self) -> dict[str, Any]:
        checks = []
        initialized = self.config_path.exists() and self.state_path.exists()
        checks.append({"name": "initialized", "ok": initialized, "detail": str(self.sia)})
        policy_files = discover_policy_files()
        found_policy = {path.name for path in policy_files}
        checks.append({
            "name": "complete-workflow-policy",
            "ok": REQUIRED_POLICY.issubset(found_policy),
            "detail": {"required": sorted(REQUIRED_POLICY), "found": sorted(found_policy)},
        })
        checks.append({"name": "competing-frameworks", "ok": True, "detail": self.detect_frameworks()})
        return {"ok": all(item["ok"] for item in checks), "checks": checks}
