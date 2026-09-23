"""Command-line entry point for SIA."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .adapters import ADAPTERS, install_adapter, remove_adapter
from .core import MODES, Project, SiaError
from .orchestration import OrchestrationError, load_json, run_standalone
from .routing import example_config
from .policy import render_policy


def emit(value: Any, as_json: bool = False) -> None:
    if as_json or isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        text = str(value)
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="replace").decode(encoding))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="sia", description="Persistent, host-neutral SIA orchestration")
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    root.add_argument("--root", default=".", help="project root (default: current directory)")
    root.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="initialize durable SIA state")
    init.add_argument("--mode", choices=MODES, default="orchestrator")
    init.add_argument("--force", action="store_true", help="reset workflow state but keep existing evidence files")

    commands.add_parser("status", help="show persisted workflow position")
    next_command = commands.add_parser("next", help="emit the next host-neutral action packet")
    next_command.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="emit machine-readable JSON")
    commands.add_parser("guide", help="print the installed workflow contract")
    commands.add_parser("doctor", help="diagnose package and project integration")

    owner = commands.add_parser("owner", help="assign a workflow stage to SIA or another framework")
    owner.add_argument("--stage", required=True)
    owner.add_argument("--to", required=True, dest="stage_owner")

    advance = commands.add_parser("advance", help="complete the current stage after validating evidence")
    advance.add_argument("--evidence", action="append", default=[], help="project-local artifact path; repeatable")

    record = commands.add_parser("record", help="record a PASS or DEVIATION proposal outcome")
    record.add_argument("--outcome", required=True, choices=("pass", "deviation"))
    _event_arguments(record, deviation=False)

    capture = commands.add_parser("capture", help="capture a DEVIATION using the feedback interface")
    _event_arguments(capture, deviation=True)

    commands.add_parser("convergence", help="compute persisted deviation rates")

    preflight = commands.add_parser("preflight", help="load applicable active rules before work")
    preflight.add_argument("--scope", action="append", required=True, help="file or glob; repeatable")
    preflight.add_argument("--acknowledge", action="append", default=[], help="approved medium/high rule ID")

    rule = commands.add_parser("rule", help="manage provenance-bearing feedback rules").add_subparsers(dest="rule_command", required=True)
    add_rule = rule.add_parser("add", help="add an approved active rule")
    add_rule.add_argument("--text", required=True)
    add_rule.add_argument("--scope", required=True)
    add_rule.add_argument("--severity", required=True, choices=("low", "medium", "high"))
    add_rule.add_argument("--error-class", required=True)
    add_rule.add_argument("--source-event", required=True)
    retire = rule.add_parser("retire", help="retire, but do not erase, a rule")
    retire.add_argument("--id", required=True)
    retire.add_argument("--reason", required=True)

    adapter = commands.add_parser("adapter", help="manage explicit host launchers").add_subparsers(dest="adapter_command", required=True)
    install = adapter.add_parser("install")
    install.add_argument("--host", required=True, choices=tuple(ADAPTERS))
    install.add_argument("--upgrade", action="store_true", help="replace only an unchanged managed v1 adapter")
    remove = adapter.add_parser("remove")
    remove.add_argument("--host", required=True, choices=tuple(ADAPTERS))

    task = commands.add_parser("task", help="record native subagent execution evidence").add_subparsers(dest="task_command", required=True)
    prepare = task.add_parser("prepare")
    prepare.add_argument("--task", required=True)
    prepare.add_argument("--brief", required=True, type=Path)
    prepare.add_argument("--files", action="append", required=True)
    prepare.add_argument("--risk", choices=("low", "medium", "high"), default="medium")
    prepare.add_argument("--complexity", choices=("simple", "normal", "complex"), default="normal")
    prepare.add_argument("--estimated-tokens", type=int)
    dispatch = task.add_parser("dispatch")
    dispatch.add_argument("--task", required=True)
    dispatch.add_argument("--host", required=True)
    dispatch.add_argument("--agent-id", required=True)
    dispatch.add_argument("--native-run-id", required=True)
    finish = task.add_parser("finish")
    finish.add_argument("--task", required=True)
    finish.add_argument("--report", required=True, type=Path)
    finish.add_argument("--review", required=True, type=Path)
    finish.add_argument("--reviewer-agent-id", required=True)
    finish.add_argument("--review-native-run-id", required=True)

    integration = commands.add_parser("integration", help="record final combined validation and review")
    integration.add_argument("--evidence", required=True, type=Path)

    orchestrate = commands.add_parser(
        "orchestrate", help="plan and run cost-aware native or standalone subagents"
    ).add_subparsers(dest="orchestrate_command", required=True)
    configure = orchestrate.add_parser("configure", help="validate and store model, budget, and worker config")
    configure.add_argument("--file", required=True, type=Path)
    plan = orchestrate.add_parser("plan", help="route prepared tasks and reserve run budget")
    plan.add_argument("--backend", choices=("native-host", "standalone"), required=True)
    plan.add_argument("--host", required=True)
    plan.add_argument("--replace", action="store_true")
    run = orchestrate.add_parser("run", help="execute an approved standalone dispatch plan")
    run.add_argument("--approve-commands", action="store_true")
    receipt = orchestrate.add_parser("receipt", help="ingest one native-host operation receipt")
    receipt.add_argument("--file", required=True, type=Path)
    orchestrate.add_parser("status", help="show operation, budget, and telemetry status")
    orchestrate.add_parser("example", help="print a safe orchestration config template")
    return root


def _event_arguments(command: argparse.ArgumentParser, deviation: bool) -> None:
    command.add_argument("--signal", required=True)
    command.add_argument("--context", required=True)
    command.add_argument("--severity", required=True, choices=("low", "medium", "high"))
    command.add_argument("--error-class", required=deviation)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    project = Project(args.root)
    try:
        result: Any
        if args.command == "init":
            result = project.initialize(args.mode, args.force)
        elif args.command == "status":
            result = project.status()
        elif args.command == "next":
            result = project.next_packet()
        elif args.command == "guide":
            emit(render_policy(), False)
            return 0
        elif args.command == "doctor":
            result = project.doctor()
            emit(result, args.json)
            return 0 if result["ok"] else 1
        elif args.command == "advance":
            result = project.advance(args.evidence)
        elif args.command == "owner":
            result = project.set_stage_owner(args.stage, args.stage_owner)
        elif args.command in {"record", "capture"}:
            outcome = args.outcome if args.command == "record" else "deviation"
            result = project.record_event(outcome, args.signal, args.context, args.severity, args.error_class)
        elif args.command == "convergence":
            result = project.convergence()
        elif args.command == "preflight":
            result, clear = project.preflight(args.scope, set(args.acknowledge))
            emit(result, args.json)
            return 0 if clear else 2
        elif args.command == "rule":
            if args.rule_command == "add":
                result = project.add_rule(args.text, args.scope, args.severity, args.error_class, args.source_event)
            else:
                result = project.retire_rule(args.id, args.reason)
        elif args.command == "adapter":
            if args.adapter_command == "install":
                status, path = install_adapter(project.root, args.host, args.upgrade)
            else:
                status, path = remove_adapter(project.root, args.host)
            result = {"status": status, "host": args.host, "path": str(path.relative_to(project.root))}
        elif args.command == "task":
            if args.task_command == "prepare":
                result = project.prepare_task(
                    args.task,
                    args.brief,
                    args.files,
                    args.risk,
                    args.complexity,
                    args.estimated_tokens,
                )
            elif args.task_command == "dispatch":
                result = project.dispatch_task(args.task, args.host, args.agent_id, args.native_run_id)
            else:
                result = project.finish_task(args.task, args.report, args.review, args.reviewer_agent_id, args.review_native_run_id)
        elif args.command == "integration":
            result = project.record_integration(args.evidence)
        elif args.command == "orchestrate":
            if args.orchestrate_command == "configure":
                result = project.configure_orchestration(load_json(args.file.resolve()))
            elif args.orchestrate_command == "plan":
                result = project.create_dispatch_plan(args.backend, args.host, args.replace)
            elif args.orchestrate_command == "run":
                plan_path, _ = project.dispatch_plan()
                result = asyncio.run(run_standalone(project, plan_path, args.approve_commands))
            elif args.orchestrate_command == "receipt":
                result = project.apply_orchestration_receipt(load_json(args.file.resolve()), args.file.resolve())
            elif args.orchestrate_command == "example":
                result = example_config()
            else:
                result = project.orchestration_status()
        else:  # pragma: no cover - argparse prevents this
            raise SiaError(f"unknown command: {args.command}")
        emit(result, args.json)
        return 0
    except (SiaError, OrchestrationError, FileExistsError, PermissionError, ValueError) as exc:
        print(f"sia: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
