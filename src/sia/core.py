"""Durable project state for SIA.

SIA persists workflow, routing, budget, and receipt state. Native hosts may
execute a dispatch plan with in-process subagents; standalone mode may execute
explicitly approved command-array workers.
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
from .orchestration import canonical_hash, file_hash
from .routing import (
    COMPLEXITY,
    RISK,
    estimate_cost,
    estimate_tokens,
    normalize_telemetry,
    route_task,
    validate_orchestration_config,
)

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
    "claude-code": (".claude",),
    "codex": (".agents",),
    "kiro": (".kiro",),
    "gemini-cli": (".gemini",),
    "antigravity": (".antigravity",),
}


def execution_gate_message(action: str, config: dict[str, Any], state: dict[str, Any]) -> str:
    """Explain an execution-stage refusal AND name the command that fixes it.

    Stating only the constraint is what makes SIA look broken on first contact:
    `sia init` and `sia orchestrate configure` both succeed, so a new user
    reasonably expects work to dispatch, and instead reads a rule with no
    remedy attached. The remaining stages and the exact next command are what
    turn a dead end into a next step.
    """
    mode = config.get("mode")
    if mode != "orchestrator":
        return (
            f"{action} requires orchestrator mode; this project is in '{mode}' mode. "
            "Re-initialize with `sia init --mode orchestrator`, or leave execution "
            "to whichever framework owns it."
        )

    stages = STAGES["orchestrator"]
    current = state.get("current_stage")
    if current in stages:
        remaining = stages[stages.index(current) : stages.index("execution") + 1]
    else:
        remaining = stages[: stages.index("execution") + 1]

    return (
        f"{action} is only available at the 'execution' stage; this project is at "
        f"'{current}'. Remaining stages: {' -> '.join(remaining)}. "
        "Advance each one with `sia advance --evidence <artifact>` once its evidence "
        "exists. Run `sia next --json` for the current stage's required action."
    )
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
            "orchestration": None,
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
            "orchestration": self._orchestration_summary(state),
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
        config, state = self.require_initialized()
        if stage not in STAGES[config["mode"]]:
            raise SiaError(f"stage {stage!r} is not active in {config['mode']} mode")
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$", owner):
            raise SiaError("owner must use letters, digits, dot, underscore, or hyphen")
        config.setdefault("stage_owners", {})[stage] = owner
        if stage == "execution" and owner != "sia" and isinstance(state.get("orchestration"), dict):
            state["orchestration"]["status"] = "suspended-owner"
            state["orchestration"]["suspended_at"] = utc_now()
            state["orchestration"]["suspended_for_owner"] = owner
            _write_json(self.state_path, state)
        _write_json(self.config_path, config)
        return {"stage": stage, "owner": owner, "stage_owners": config["stage_owners"]}

    def _validate_integration_binding(self, state: dict[str, Any]) -> None:
        integration = state.get("integration")
        if not isinstance(integration, dict):
            raise SiaError("integration evidence is missing")
        evidence = self.root / integration["path"]
        if not evidence.is_file() or file_hash(evidence) != integration.get("evidence_sha256"):
            raise SiaError("integration evidence changed after it was recorded")
        orchestration = state.get("orchestration")
        plan_hash = None
        if isinstance(orchestration, dict):
            _, plan = self.dispatch_plan()
            plan_hash = plan["plan_hash"]
        receipt_manifest = []
        report_manifest = []
        for task in state.get("tasks", {}).values():
            for receipt in sorted((self.root / task["directory"] / "receipts").glob("*.json")):
                receipt_manifest.append({"path": receipt.relative_to(self.root).as_posix(), "sha256": file_hash(receipt)})
                receipt_data = _read_json(receipt, {})
                report_path = receipt_data.get("report_path") if isinstance(receipt_data, dict) else None
                if report_path:
                    report = self.root / report_path
                    if not report.is_file():
                        raise SiaError(f"orchestration report is missing: {report_path}")
                    report_digest = file_hash(report)
                    if receipt_data.get("report_sha256") != report_digest:
                        raise SiaError(f"orchestration report changed after receipt: {report_path}")
                    report_manifest.append({"path": report_path, "sha256": report_digest})
        manifest = {
            "integration_sha256": integration["evidence_sha256"],
            "orchestration_plan_hash": plan_hash,
            "receipts": receipt_manifest,
            "reports": report_manifest,
        }
        if receipt_manifest != integration.get("receipt_manifest", []) or report_manifest != integration.get("report_manifest", []):
            raise SiaError("orchestration receipt/report set changed after integration")
        if canonical_hash(manifest) != integration.get("evidence_manifest_sha256"):
            raise SiaError("integration evidence manifest is stale")

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
            self._validate_integration_binding(state)
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
    def prepare_task(
        self,
        task_id: str,
        brief: Path,
        files: Iterable[str],
        risk: str = "medium",
        complexity: str = "normal",
        estimated_tokens: int | None = None,
    ) -> dict[str, Any]:
        config, state = self.require_initialized()
        if config["mode"] != "orchestrator" or state.get("current_stage") != "execution":
            raise SiaError(execution_gate_message("preparing tasks", config, state))
        if not TASK_ID.match(task_id):
            raise SiaError("task ID must use letters, digits, dot, underscore, or hyphen")
        if risk not in RISK:
            raise SiaError(f"risk must be one of: {', '.join(RISK)}")
        if complexity not in COMPLEXITY:
            raise SiaError(f"complexity must be one of: {', '.join(COMPLEXITY)}")
        if estimated_tokens is not None and estimated_tokens <= 0:
            raise SiaError("estimated tokens must be positive")
        owned = sorted({_normalize_owned(self.root, value) for value in files})
        if not owned:
            raise SiaError("at least one --files ownership path is required")
        if task_id in state.get("tasks", {}):
            raise SiaError(f"task already exists: {task_id}")
        for other_id, task in state.get("tasks", {}).items():
            if task.get("status") in {"prepared", "dispatched", "implemented"}:
                overlap = sorted({left for left in owned for right in task.get("files", []) if _paths_overlap(left, right)})
                if overlap:
                    raise SiaError(f"file ownership overlaps active task {other_id}: {', '.join(overlap)}")
        task_dir = self.sia / "runs" / state["run_id"] / "tasks" / task_id
        _copy_evidence(brief.resolve(), task_dir / "brief.md")
        task = {
            "id": task_id,
            "files": owned,
            "risk": risk,
            "complexity": complexity,
            "estimated_tokens": estimated_tokens,
            "status": "prepared",
            "prepared_at": utc_now(),
            "directory": task_dir.relative_to(self.root).as_posix(),
        }
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
        orchestration = state.get("orchestration")
        if isinstance(orchestration, dict) and orchestration.get("status") != "complete":
            raise SiaError(f"integration requires a complete orchestration plan, not {orchestration.get('status')}")
        if not evidence.is_file() or not evidence.read_text(encoding="utf-8").strip():
            raise SiaError("integration evidence must be a non-empty UTF-8 file")
        task_dir = self.sia / "runs" / state["run_id"]
        _copy_evidence(evidence.resolve(), task_dir / "integration.md")
        digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
        receipt_manifest = []
        report_manifest = []
        for task in tasks.values():
            for receipt in sorted((self.root / task["directory"] / "receipts").glob("*.json")):
                receipt_manifest.append({
                    "path": receipt.relative_to(self.root).as_posix(),
                    "sha256": file_hash(receipt),
                })
                receipt_data = _read_json(receipt, {})
                report_path = receipt_data.get("report_path") if isinstance(receipt_data, dict) else None
                if report_path:
                    report = self.root / report_path
                    report_digest = file_hash(report)
                    if receipt_data.get("report_sha256") != report_digest:
                        raise SiaError(f"orchestration report changed after receipt: {report_path}")
                    report_manifest.append({"path": report_path, "sha256": report_digest})
        evidence_manifest = {
            "integration_sha256": digest,
            "orchestration_plan_hash": orchestration.get("plan_hash") if isinstance(orchestration, dict) else None,
            "receipts": receipt_manifest,
            "reports": report_manifest,
        }
        state["integration"] = {
            "path": (task_dir / "integration.md").relative_to(self.root).as_posix(),
            "recorded_at": utc_now(),
            "covered_tasks": sorted(tasks),
            "evidence_sha256": digest,
            "evidence_manifest_sha256": canonical_hash(evidence_manifest),
            "receipt_manifest": receipt_manifest,
            "report_manifest": report_manifest,
        }
        _write_json(self.state_path, state)
        return state["integration"]

    @staticmethod
    def _orchestration_summary(state: dict[str, Any]) -> dict[str, Any] | None:
        orchestration = state.get("orchestration")
        if not isinstance(orchestration, dict):
            return None
        operations = orchestration.get("operations", {})
        counts = Counter(item.get("status", "unknown") for item in operations.values())
        return {
            "plan_id": orchestration.get("plan_id"),
            "backend": orchestration.get("backend"),
            "host": orchestration.get("host"),
            "status": orchestration.get("status"),
            "operation_counts": dict(counts),
            "budget": orchestration.get("budget"),
        }

    @state_locked
    def configure_orchestration(self, raw: Any) -> dict[str, Any]:
        config, state = self.require_initialized()
        normalized = validate_orchestration_config(raw)
        config["orchestration"] = normalized
        config["updated_at"] = utc_now()
        _write_json(self.config_path, config)
        state["orchestration"] = None
        state["updated_at"] = utc_now()
        _write_json(self.state_path, state)
        return {
            "configured": True,
            "models": {tier: model["id"] for tier, model in normalized["models"].items()},
            "budget": normalized["budget"],
            "concurrency": normalized["concurrency"],
            "standalone_workers": sorted(normalized["workers"]),
        }

    @state_locked
    def create_dispatch_plan(self, backend: str, host: str, replace: bool = False) -> dict[str, Any]:
        config, state = self.require_initialized()
        if backend not in {"native-host", "standalone"}:
            raise SiaError("backend must be native-host or standalone")
        if config.get("mode") != "orchestrator" or state.get("current_stage") != "execution":
            raise SiaError(execution_gate_message("creating a dispatch plan", config, state))
        if config.get("stage_owners", {}).get("execution", "sia") != "sia":
            raise SiaError("SIA cannot launch workers while another framework owns execution")
        routing_config = config.get("orchestration")
        if not isinstance(routing_config, dict):
            raise SiaError("orchestration is not configured; run `sia orchestrate configure --file ...`")
        if backend == "standalone" and not routing_config.get("workers"):
            raise SiaError("standalone backend requires at least one configured worker command array")
        existing = state.get("orchestration")
        if isinstance(existing, dict) and existing.get("status") in {"planned", "running", "warning"} and not replace:
            raise SiaError("an active dispatch plan already exists; use --replace before any worker completes")
        if replace and isinstance(existing, dict):
            if any(value.get("status") == "complete" for value in existing.get("operations", {}).values()):
                raise SiaError("cannot replace a plan after an operation completed")

        tasks = {key: value for key, value in state.get("tasks", {}).items() if value.get("status") == "prepared"}
        if not tasks:
            raise SiaError("prepare at least one task before creating a dispatch plan")
        plan_id = "plan-" + uuid.uuid4().hex[:12]
        operations: list[dict[str, Any]] = []
        operation_state: dict[str, dict[str, Any]] = {}
        total_tokens = 0
        total_cost = 0.0
        for task_id, task in sorted(tasks.items()):
            task_dir = Path(task["directory"])
            brief_path = task_dir / "brief.md"
            absolute_brief = self.root / brief_path
            for role in ("implementer", "reviewer"):
                tier, reason = route_task(task, role, routing_config)
                model = routing_config["models"][tier]
                tokens, estimate_source = estimate_tokens(task, role, absolute_brief.stat().st_size)
                cost = estimate_cost(tokens, model)
                operation_id = f"{task_id}:{'implement' if role == 'implementer' else 'review'}"
                depends_on = [] if role == "implementer" else [f"{task_id}:implement"]
                operation = {
                    "operation_id": operation_id,
                    "task_id": task_id,
                    "role": role,
                    "depends_on": depends_on,
                    "owned_files": task["files"] if role == "implementer" else [],
                    "task_directory": task_dir.as_posix(),
                    "brief_path": brief_path.as_posix(),
                    "brief_sha256": file_hash(absolute_brief),
                    "tier": tier,
                    "requested_model_id": model["id"],
                    "routing_reason": reason,
                    "estimated_tokens": tokens,
                    "estimate_source": estimate_source,
                    "estimated_cost_usd": cost,
                }
                operations.append(operation)
                operation_state[operation_id] = {
                    "status": "ready" if role == "implementer" else "blocked",
                    "task_id": task_id,
                    "role": role,
                    "tier": tier,
                    "requested_model_id": model["id"],
                    "report_path": None,
                    "receipt_path": None,
                }
                total_tokens += tokens
                total_cost += cost
        budget_config = routing_config["budget"]
        if total_tokens > budget_config["max_tokens"]:
            raise SiaError(f"planned token reservation {total_tokens} exceeds budget {budget_config['max_tokens']}")
        if total_cost > budget_config["max_cost_usd"]:
            raise SiaError(
                f"planned cost reservation ${total_cost:.6f} exceeds budget ${budget_config['max_cost_usd']:.6f}"
            )
        token_ratio = total_tokens / budget_config["max_tokens"]
        cost_ratio = total_cost / budget_config["max_cost_usd"]
        warning = max(token_ratio, cost_ratio) >= budget_config["warning_fraction"]
        plan = {
            "schema_version": 1,
            "plan_id": plan_id,
            "run_id": state["run_id"],
            "backend": backend,
            "host": host,
            "stage_owner": "sia",
            "generated_at": utc_now(),
            "models": {tier: value["id"] for tier, value in routing_config["models"].items()},
            "model_specs": routing_config["models"],
            "worker_specs": routing_config["workers"] if backend == "standalone" else {},
            "concurrency": routing_config["concurrency"],
            "budget": {
                "reserved_tokens": total_tokens,
                "reserved_cost_usd": round(total_cost, 8),
                "max_tokens": budget_config["max_tokens"],
                "max_cost_usd": budget_config["max_cost_usd"],
                "warning_fraction": budget_config["warning_fraction"],
                "warning": warning,
            },
            "operations": operations,
        }
        plan["plan_hash"] = canonical_hash(plan)
        plan_path = self.sia / "runs" / state["run_id"] / "dispatch-plan.json"
        _write_json(plan_path, plan)
        state["orchestration"] = {
            "plan_id": plan_id,
            "plan_hash": plan["plan_hash"],
            "plan_path": plan_path.relative_to(self.root).as_posix(),
            "backend": backend,
            "host": host,
            "status": "warning" if warning else "planned",
            "operations": operation_state,
            "budget": {
                **plan["budget"],
                "used_tokens": 0,
                "used_cost_usd": 0.0,
                "telemetry_quality": {},
            },
        }
        state["integration"] = None
        state["updated_at"] = utc_now()
        _write_json(self.state_path, state)
        return plan

    def dispatch_plan(self) -> tuple[Path, dict[str, Any]]:
        _, state = self.require_initialized()
        orchestration = state.get("orchestration")
        if not isinstance(orchestration, dict):
            raise SiaError("no dispatch plan exists")
        path = self.root / orchestration["plan_path"]
        plan = _read_json(path)
        if not isinstance(plan, dict) or canonical_hash({key: value for key, value in plan.items() if key != "plan_hash"}) != plan.get("plan_hash"):
            raise SiaError("dispatch plan is missing or its hash does not match")
        for operation in plan.get("operations", []):
            brief = self.root / operation["brief_path"]
            if not brief.is_file() or file_hash(brief) != operation.get("brief_sha256"):
                raise SiaError(f"dispatch plan input changed after approval: {operation.get('brief_path')}")
        return path, plan

    def orchestration_operation(self, plan_id: str, operation_id: str) -> dict[str, Any]:
        _, state = self.require_initialized()
        orchestration = state.get("orchestration")
        if not isinstance(orchestration, dict) or orchestration.get("plan_id") != plan_id:
            return {}
        operation = orchestration.get("operations", {}).get(operation_id)
        return dict(operation) if isinstance(operation, dict) else {}

    def orchestration_status(self) -> dict[str, Any]:
        _, state = self.require_initialized()
        return self._orchestration_summary(state) or {"status": "not-planned"}

    @state_locked
    def assert_orchestration_execution(self, plan_id: str) -> None:
        config, state = self.require_initialized()
        orchestration = state.get("orchestration")
        if config.get("mode") != "orchestrator" or state.get("current_stage") != "execution":
            raise SiaError("orchestration is no longer at orchestrator execution")
        if config.get("stage_owners", {}).get("execution", "sia") != "sia":
            raise SiaError("SIA execution is suspended because another framework owns the stage")
        if not isinstance(orchestration, dict) or orchestration.get("plan_id") != plan_id:
            raise SiaError("dispatch plan is no longer active")
        if orchestration.get("status") in {"budget-exceeded", "suspended-owner", "failed"}:
            raise SiaError(f"orchestration cannot continue from status {orchestration.get('status')}")

    @state_locked
    def apply_orchestration_receipt(self, raw: Any, source_path: Path | None = None) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise SiaError("receipt must be a JSON object")
        config, state = self.require_initialized()
        orchestration = state.get("orchestration")
        if not isinstance(orchestration, dict):
            raise SiaError("no active orchestration plan")
        if config.get("mode") != "orchestrator" or state.get("current_stage") != "execution":
            raise SiaError("receipt rejected outside orchestrator execution")
        if config.get("stage_owners", {}).get("execution", "sia") != "sia":
            raise SiaError("receipt rejected because another framework owns execution")
        if orchestration.get("status") in {"budget-exceeded", "suspended-owner", "failed"}:
            raise SiaError(f"receipt rejected after terminal orchestration status {orchestration.get('status')}")
        if raw.get("plan_id") != orchestration.get("plan_id") or raw.get("plan_hash") != orchestration.get("plan_hash"):
            raise SiaError("receipt plan ID/hash does not match the active immutable plan")
        operation_id = raw.get("operation_id")
        operation_state = orchestration.get("operations", {}).get(operation_id)
        if not isinstance(operation_state, dict):
            raise SiaError(f"unknown operation: {operation_id}")
        if operation_state.get("status") in {"complete", "failed"}:
            raise SiaError(f"operation already finalized: {operation_id}")
        _, plan = self.dispatch_plan()
        operation = next((item for item in plan["operations"] if item["operation_id"] == operation_id), None)
        if operation is None:
            raise SiaError("operation is absent from the immutable plan")
        for dependency in operation["depends_on"]:
            if orchestration["operations"].get(dependency, {}).get("status") != "complete":
                raise SiaError(f"operation dependency is not complete: {dependency}")
        status = raw.get("status")
        if status not in {"complete", "failed"}:
            raise SiaError("receipt status must be complete or failed")
        agent_id = raw.get("agent_id")
        run_id = raw.get("native_run_id")
        if not isinstance(agent_id, str) or not agent_id.strip() or not isinstance(run_id, str) or not run_id.strip():
            raise SiaError("receipt requires non-empty agent_id and native_run_id")
        actual_model = raw.get("actual_model_id")
        if actual_model and actual_model != operation["requested_model_id"] and not config["orchestration"]["allow_model_fallback"]:
            raise SiaError(
                f"host used model {actual_model!r}, not requested {operation['requested_model_id']!r}; fallback is disabled"
            )
        model = plan["model_specs"][operation["tier"]]
        telemetry = normalize_telemetry(raw.get("telemetry"), operation, model)
        task = state["tasks"].get(operation["task_id"])
        if not isinstance(task, dict):
            raise SiaError("receipt task is missing from state")
        task_dir = self.root / task["directory"]
        report_relative = raw.get("report_path")
        canonical_report = None
        if status == "complete":
            if not isinstance(report_relative, str):
                raise SiaError("complete receipt requires report_path")
            report = (self.root / report_relative).resolve()
            try:
                report.relative_to(self.root)
            except ValueError as exc:
                raise SiaError("receipt report must remain inside the project root") from exc
            if not report.is_file() or not report.read_text(encoding="utf-8").strip():
                raise SiaError("receipt report must be a non-empty UTF-8 file")
            target_name = "orchestrated-report.md" if operation["role"] == "implementer" else "orchestrated-review.md"
            target = task_dir / target_name
            if report != target:
                _copy_evidence(report, target)
            canonical_report = target.relative_to(self.root).as_posix()
        if operation["role"] == "reviewer" and status == "complete":
            implement_agent = task.get("dispatch", {}).get("agent_id")
            if implement_agent == agent_id:
                raise SiaError("independent review requires a different reviewer agent ID")

        normalized_receipt = {
            **raw,
            "schema_version": 1,
            "operation_id": operation_id,
            "agent_id": agent_id.strip(),
            "native_run_id": run_id.strip(),
            "requested_model_id": operation["requested_model_id"],
            "report_path": canonical_report,
            "report_sha256": file_hash(self.root / canonical_report) if canonical_report else None,
            "telemetry": telemetry,
            "recorded_at": utc_now(),
        }
        receipts_dir = task_dir / "receipts"
        receipt_target = receipts_dir / (operation_id.replace(":", "-") + ".json")
        _write_json(receipt_target, normalized_receipt)
        operation_state.update({
            "status": status,
            "agent_id": agent_id.strip(),
            "native_run_id": run_id.strip(),
            "actual_model_id": actual_model,
            "report_path": canonical_report,
            "receipt_path": receipt_target.relative_to(self.root).as_posix(),
            "telemetry": telemetry,
        })
        if status == "failed":
            task["status"] = "blocked"
            orchestration["status"] = "failed"
        elif operation["role"] == "implementer":
            task["status"] = "implemented"
            task["dispatch"] = {
                "host": raw.get("host", orchestration["host"]),
                "agent_id": agent_id.strip(),
                "native_run_id": run_id.strip(),
                "model_id": actual_model or operation["requested_model_id"],
                "provenance": raw.get("provenance", "native_attested"),
            }
            review_id = f"{operation['task_id']}:review"
            orchestration["operations"][review_id]["status"] = "ready"
            orchestration["status"] = "running"
        else:
            task["status"] = "reviewed"
            task["review_dispatch"] = {
                "host": raw.get("host", orchestration["host"]),
                "agent_id": agent_id.strip(),
                "native_run_id": run_id.strip(),
                "model_id": actual_model or operation["requested_model_id"],
                "provenance": raw.get("provenance", "native_attested"),
            }

        budget = orchestration["budget"]
        budget["used_tokens"] += telemetry["total_tokens"]
        budget["used_cost_usd"] = round(budget["used_cost_usd"] + telemetry["cost_usd"], 8)
        quality = telemetry["quality"]
        budget["telemetry_quality"][quality] = budget["telemetry_quality"].get(quality, 0) + 1
        over_budget = budget["used_tokens"] > budget["max_tokens"] or budget["used_cost_usd"] > budget["max_cost_usd"]
        statuses = [value["status"] for value in orchestration["operations"].values()]
        if over_budget:
            orchestration["status"] = "budget-exceeded"
        elif statuses and all(value == "complete" for value in statuses):
            orchestration["status"] = "complete"
        elif "failed" not in statuses and orchestration["status"] != "warning":
            orchestration["status"] = "running"
        _write_json(task_dir / "task.json", task)
        state["integration"] = None
        state["updated_at"] = utc_now()
        _write_json(self.state_path, state)
        return {
            "operation_id": operation_id,
            "status": status,
            "tier": operation["tier"],
            "requested_model_id": operation["requested_model_id"],
            "actual_model_id": actual_model,
            "telemetry": telemetry,
            "orchestration_status": orchestration["status"],
        }

    def fail_orchestration_operation(self, plan_id: str, operation_id: str, error: str) -> dict[str, Any]:
        _, plan = self.dispatch_plan()
        operation = next((item for item in plan["operations"] if item["operation_id"] == operation_id), None)
        if operation is None:
            raise SiaError(f"unknown operation: {operation_id}")
        receipt = {
            "schema_version": 1,
            "plan_id": plan_id,
            "plan_hash": plan["plan_hash"],
            "operation_id": operation_id,
            "status": "failed",
            "provenance": "standalone_observed",
            "host": plan["host"],
            "agent_id": "standalone:launcher",
            "native_run_id": "launcher-failure-" + uuid.uuid4().hex[:8],
            "actual_model_id": None,
            "telemetry": {},
            "error": error,
        }
        return self.apply_orchestration_receipt(receipt)

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
