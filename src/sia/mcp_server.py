"""SIA as a Model Context Protocol server, over stdio, using only the stdlib.

Why MCP: every supported host (Claude Code, Codex, Gemini CLI, Kiro,
Antigravity) can launch a plugin's MCP server itself, from the plugin's own
directory. A skill that shells out to ``cli.py`` needs the host to tell the
agent where the plugin is installed, and most hosts document that path only
for hooks and MCP configs, not for skills. Serving the CLI over MCP removes the
question: the host resolves the path when it launches the server, and the
agent just calls tools.

Why stdlib only: the official MCP Python SDK is a pip dependency. Requiring it
would reintroduce exactly the install step the plugin exists to remove. MCP over
stdio is newline-delimited JSON-RPC 2.0, which the stdlib handles directly.

Every tool delegates to ``sia.cli.main`` so behaviour is identical to the CLI,
refusals and all. Nothing here reimplements workflow logic.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, TextIO

from . import __version__
from .cli import main as cli_main

SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")

INSTRUCTIONS = (
    "SIA keeps durable, evidence-gated workflow state in <project>/.sia/. "
    "Every tool takes project_root: the ABSOLUTE path of the user's project, "
    "never this server's own directory. Call sia_next first to learn the current "
    "stage and what it requires. Orchestration (task prepare, plan) is only legal "
    "at the 'execution' stage; a refusal names the stage and the next command. "
    "Relative paths in other arguments resolve against project_root."
)

# JSON-RPC 2.0 error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

_PROJECT_ROOT = {
    "type": "string",
    "description": "Absolute path to the user's project root (the directory that holds or will hold .sia/).",
}


def _string(description: str) -> dict[str, Any]:
    return {"type": "string", "description": description}


def _string_list(description: str, min_items: int = 1) -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}, "minItems": min_items, "description": description}


def _enum(values: tuple[str, ...], description: str) -> dict[str, Any]:
    return {"type": "string", "enum": list(values), "description": description}


def _schema(properties: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"project_root": _PROJECT_ROOT, **properties},
        "required": ["project_root", *required],
        "additionalProperties": False,
    }


def _repeat(flag: str, values: list[str] | None) -> list[str]:
    argv: list[str] = []
    for value in values or []:
        argv += [flag, value]
    return argv


def _event_argv(args: dict[str, Any]) -> list[str]:
    argv = ["--signal", args["signal"], "--context", args["context"], "--severity", args["severity"]]
    if args.get("error_class"):
        argv += ["--error-class", args["error_class"]]
    return argv


# Each tool: (description, input schema, argv builder). The builder returns the
# CLI arguments that follow the global `--root <project> --json` prefix.
ToolSpec = tuple[str, dict[str, Any], Callable[[dict[str, Any]], list[str]]]

TOOLS: dict[str, ToolSpec] = {
    "sia_doctor": (
        "Read-only diagnosis of SIA in a project: whether it is initialized, whether the workflow policy is complete, and which other agent frameworks are present. Safe before sia_init.",
        _schema({}),
        lambda a: ["doctor"],
    ),
    "sia_init": (
        "Initialize SIA state in a project. Never overwrites AGENT.md, AGENTS.md or CLAUDE.md. Choose 'orchestrator' if SIA should dispatch subagents; only that mode reaches the execution stage.",
        _schema({"mode": _enum(("advisory", "planning", "orchestrator"), "Workflow mode; persisted.")}, ("mode",)),
        lambda a: ["init", "--mode", a["mode"]],
    ),
    "sia_status": (
        "Show the persisted workflow position: mode, current stage, completed stages, tasks.",
        _schema({}),
        lambda a: ["status"],
    ),
    "sia_next": (
        "The authoritative next-action packet: current stage, what it requires, and the commands that advance it. Call this first in any session.",
        _schema({}),
        lambda a: ["next"],
    ),
    "sia_guide": (
        "Print SIA's full installed workflow contract.",
        _schema({}),
        lambda a: ["guide"],
    ),
    "sia_advance": (
        "Complete the current stage, citing evidence artifacts that exist on disk. A claim is never evidence; only a path is.",
        _schema({"evidence": _string_list("Project-relative artifact paths proving the stage is done.")}, ("evidence",)),
        lambda a: ["advance", *_repeat("--evidence", a["evidence"])],
    ),
    "sia_owner": (
        "Assign a workflow stage to SIA or to another framework (bridge policy). If another owner holds execution, SIA dispatches nothing.",
        _schema({"stage": _string("Stage name, e.g. 'plan' or 'execution'."),
                 "to": _string("Owner: 'sia' or another framework, e.g. 'bmad'.")}, ("stage", "to")),
        lambda a: ["owner", "--stage", a["stage"], "--to", a["to"]],
    ),
    "sia_task_prepare": (
        "Prepare one task at the execution stage with the exact files it owns. No two tasks may share a file. Risk and complexity drive model-tier routing.",
        _schema({
            "task": _string("Task ID: letters, digits, dot, underscore or hyphen."),
            "brief": _string("Project-relative path to the task brief."),
            "files": _string_list("Project-relative files this task exclusively owns."),
            "risk": _enum(("low", "medium", "high"), "Risk; high routes to the strong tier."),
            "complexity": _enum(("simple", "normal", "complex"), "Complexity; complex routes to the strong tier."),
            "estimated_tokens": {"type": "integer", "minimum": 1, "description": "Optional token estimate for budget reservation."},
        }, ("task", "brief", "files")),
        lambda a: [
            "task", "prepare", "--task", a["task"], "--brief", a["brief"],
            *_repeat("--files", a["files"]),
            *(["--risk", a["risk"]] if a.get("risk") else []),
            *(["--complexity", a["complexity"]] if a.get("complexity") else []),
            *(["--estimated-tokens", str(a["estimated_tokens"])] if a.get("estimated_tokens") else []),
        ],
    ),
    "sia_orchestrate_example": (
        "Emit an orchestration config template. Its model IDs are placeholders that sia_orchestrate_configure rejects; ask the user for real model IDs and prices.",
        _schema({}),
        lambda a: ["orchestrate", "example"],
    ),
    "sia_orchestrate_configure": (
        "Validate and store model tiers (cheap/current/strong), prices, budget ceilings and concurrency from a JSON config file.",
        _schema({"file": _string("Project-relative path to the orchestration JSON config.")}, ("file",)),
        lambda a: ["orchestrate", "configure", "--file", a["file"]],
    ),
    "sia_orchestrate_plan": (
        "Create the immutable dispatch plan: routes prepared tasks to tiers and reserves the whole estimated budget. Refuses a plan above either ceiling.",
        _schema({
            "backend": _enum(("native-host", "standalone"), "native-host: this host spawns the subagents. standalone: SIA launches configured CLIs, which only a human can approve via the CLI."),
            "host": _string("Host name, e.g. 'claude', 'codex', 'gemini', 'kiro', 'antigravity'."),
            "replace": {"type": "boolean", "description": "Replace an existing plan that has not started."},
        }, ("backend", "host")),
        lambda a: ["orchestrate", "plan", "--backend", a["backend"], "--host", a["host"],
                   *(["--replace"] if a.get("replace") else [])],
    ),
    "sia_orchestrate_receipt": (
        "Ingest one worker's receipt. Never fabricate telemetry: use null actual_model_id and empty telemetry when the host did not expose them.",
        _schema({"file": _string("Project-relative path to the receipt JSON.")}, ("file",)),
        lambda a: ["orchestrate", "receipt", "--file", a["file"]],
    ),
    "sia_orchestrate_status": (
        "Show operations, budget use, and telemetry quality for the active plan.",
        _schema({}),
        lambda a: ["orchestrate", "status"],
    ),
    "sia_integration": (
        "Record final combined validation of the whole diff. Only legal after every task is implemented and independently reviewed.",
        _schema({"evidence": _string("Project-relative path to the combined validation evidence.")}, ("evidence",)),
        lambda a: ["integration", "--evidence", a["evidence"]],
    ),
    "sia_record": (
        "Record a PASS or DEVIATION outcome for a proposal.",
        _schema({
            "outcome": _enum(("pass", "deviation"), "Outcome."),
            "signal": _string("Short signal name."),
            "context": _string("What happened."),
            "severity": _enum(("low", "medium", "high"), "Severity."),
            "error_class": _string("Error class; required for deviations."),
        }, ("outcome", "signal", "context", "severity")),
        lambda a: ["record", "--outcome", a["outcome"], *_event_argv(a)],
    ),
    "sia_capture": (
        "Capture a DEVIATION through the feedback interface so it can become a provenance-bearing rule.",
        _schema({
            "signal": _string("Short signal name."),
            "context": _string("What went wrong."),
            "severity": _enum(("low", "medium", "high"), "Severity."),
            "error_class": _string("Error class, e.g. 'cost-overrun'."),
        }, ("signal", "context", "severity", "error_class")),
        lambda a: ["capture", *_event_argv(a)],
    ),
    "sia_preflight": (
        "Load the active rules that apply to the files about to be touched. Run before proposing work so prior corrections apply.",
        _schema({
            "scope": _string_list("Files or globs about to be touched."),
            "acknowledge": _string_list("Medium/high rule IDs the user has approved.", min_items=0),
        }, ("scope",)),
        lambda a: ["preflight", *_repeat("--scope", a["scope"]), *_repeat("--acknowledge", a.get("acknowledge"))],
    ),
    "sia_convergence": (
        "Deviation rate per error class. Falling rates mean the feedback loop is working.",
        _schema({}),
        lambda a: ["convergence"],
    ),
}

# MCP tool annotations. A tool that declares none is treated by the spec's
# defaults as destructive AND open-world, so every tool looked maximally
# dangerous and hosts demanded approval even for a read-only status check.
# These are verified, not guessed: each read-only tool was run against a
# fingerprinted .sia/ directory and changed nothing. Nothing here touches the
# network, so openWorldHint is false throughout.
READ_ONLY_TOOLS = frozenset({
    "sia_doctor", "sia_status", "sia_next", "sia_guide", "sia_preflight",
    "sia_convergence", "sia_orchestrate_example", "sia_orchestrate_status",
})
# orchestrate_configure replaces the stored config; orchestrate_plan can discard
# an existing plan when `replace` is set. Everything else only adds or advances.
DESTRUCTIVE_TOOLS = frozenset({"sia_orchestrate_configure", "sia_orchestrate_plan"})
IDEMPOTENT_WRITE_TOOLS = frozenset({"sia_owner"})
# Tools whose non-zero exit is a finding to report, not a failure to execute.
REPORT_TOOLS = frozenset({"sia_doctor"})


def annotations(name: str) -> dict[str, Any]:
    read_only = name in READ_ONLY_TOOLS
    return {
        "title": name.removeprefix("sia_").replace("_", " ").capitalize(),
        "readOnlyHint": read_only,
        "destructiveHint": name in DESTRUCTIVE_TOOLS,
        "idempotentHint": read_only or name in IDEMPOTENT_WRITE_TOOLS,
        "openWorldHint": False,
    }


# Deliberately NOT exposed:
#   orchestrate run  -- launches subprocesses; its --approve-commands flag is a
#                       HUMAN gate. Over MCP the model could pass it itself.
#   init --force     -- resets workflow state.
#   adapter install/remove -- superseded by the plugin; writes host files.


def _validate_arguments(schema: dict[str, Any], args: Any) -> str | None:
    """Minimal JSON-schema check for the shapes used above. Returns an error or None."""
    if not isinstance(args, dict):
        return "arguments must be an object"
    properties = schema["properties"]
    for key in schema["required"]:
        if key not in args:
            return f"missing required argument: {key}"
    for key, value in args.items():
        if key not in properties:
            return f"unknown argument: {key}"
        spec = properties[key]
        kind = spec.get("type")
        if kind == "string":
            if not isinstance(value, str) or not value.strip():
                return f"{key} must be a non-empty string"
            if "enum" in spec and value not in spec["enum"]:
                return f"{key} must be one of: {', '.join(spec['enum'])}"
        elif kind == "array":
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                return f"{key} must be an array of non-empty strings"
            if len(value) < spec.get("minItems", 0):
                return f"{key} needs at least {spec['minItems']} item(s)"
        elif kind == "integer":
            if not isinstance(value, int) or isinstance(value, bool) or value < spec.get("minimum", value):
                return f"{key} must be an integer >= {spec.get('minimum', 0)}"
        elif kind == "boolean":
            if not isinstance(value, bool):
                return f"{key} must be a boolean"
    return None


def _resolve_project_root(raw: str) -> Path | str:
    """The server's working directory is wherever the host launched it -- usually
    the plugin's install directory. A relative project_root would silently
    initialize SIA *inside the plugin*, so only absolute paths are accepted."""
    root = Path(raw).expanduser()
    if not root.is_absolute():
        return ("project_root must be an absolute path. This server runs from the plugin's "
                "own directory, so a relative path would point at the plugin, not the project.")
    if not root.is_dir():
        return f"project_root does not exist or is not a directory: {root}"
    return root.resolve()


def call_tool(name: str, arguments: Any) -> tuple[str, bool]:
    """Run one tool. Returns (text, is_error). Tool failures are results, not
    protocol errors, so the model can read and act on SIA's refusal messages."""
    schema, build = TOOLS[name][1], TOOLS[name][2]
    problem = _validate_arguments(schema, arguments)
    if problem:
        return problem, True
    root = _resolve_project_root(arguments["project_root"])
    if isinstance(root, str):
        return root, True

    argv = ["--root", str(root), "--json", *build(arguments)]
    out, err = io.StringIO(), io.StringIO()
    previous = Path.cwd()
    try:
        # Relative evidence/brief/file paths must resolve against the project,
        # exactly as they would for a user running the CLI from the project root.
        os.chdir(root)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cli_main(argv)
            except SystemExit as exc:  # argparse and explicit exits
                code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    except Exception as exc:  # never let one tool call take the server down
        return f"internal error running {name}: {type(exc).__name__}: {exc}", True
    finally:
        os.chdir(previous)

    stdout, stderr = out.getvalue().strip(), err.getvalue().strip()
    if code == 0:
        return stdout or stderr or "ok", False
    # `doctor` exits non-zero when any check fails -- including the ordinary
    # "not initialized yet" before sia_init. The diagnosis itself succeeded, so
    # report it as a result. Marking it an error made agents stop at step one.
    if name in REPORT_TOOLS and stdout:
        return stdout, False
    return stderr or stdout or f"{name} failed with exit code {code}", True


class Server:
    def __init__(self, write: Callable[[dict[str, Any]], None]) -> None:
        self._write = write

    def _result(self, request_id: Any, result: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "id": request_id, "result": result})

    def _error(self, request_id: Any, code: int, message: str) -> None:
        self._write({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})

    def handle(self, message: Any) -> None:
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            self._error(None, INVALID_REQUEST, "expected a single JSON-RPC 2.0 object")
            return
        method = message.get("method")
        is_request = "id" in message
        if not isinstance(method, str):
            if is_request:
                self._error(message["id"], INVALID_REQUEST, "missing method")
            return  # a response or malformed notification: nothing to answer
        if not is_request:
            return  # notifications, including notifications/initialized, get no reply
        request_id = message["id"]
        params = message.get("params") or {}

        if method == "initialize":
            requested = params.get("protocolVersion") if isinstance(params, dict) else None
            version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
            self._result(request_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "sia", "version": __version__},
                "instructions": INSTRUCTIONS,
            })
        elif method == "ping":
            self._result(request_id, {})
        elif method == "tools/list":
            self._result(request_id, {"tools": [
                {"name": name, "description": spec[0], "inputSchema": spec[1],
                 "annotations": annotations(name)}
                for name, spec in TOOLS.items()
            ]})
        elif method == "tools/call":
            name = params.get("name") if isinstance(params, dict) else None
            if name not in TOOLS:
                self._error(request_id, INVALID_PARAMS, f"unknown tool: {name}")
                return
            text, is_error = call_tool(name, params.get("arguments", {}))
            self._result(request_id, {"content": [{"type": "text", "text": text}], "isError": is_error})
        else:
            self._error(request_id, METHOD_NOT_FOUND, f"method not found: {method}")


def serve(stdin: TextIO, protocol_out: TextIO) -> None:
    def write(payload: dict[str, Any]) -> None:
        # One message per line; json.dumps never emits a raw newline.
        protocol_out.write(json.dumps(payload, separators=(",", ":")) + "\n")
        protocol_out.flush()

    server = Server(write)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            write({"jsonrpc": "2.0", "id": None, "error": {"code": PARSE_ERROR, "message": f"parse error: {exc}"}})
            continue
        try:
            server.handle(message)
        except Exception as exc:
            request_id = message.get("id") if isinstance(message, dict) else None
            write({"jsonrpc": "2.0", "id": request_id,
                   "error": {"code": INTERNAL_ERROR, "message": f"{type(exc).__name__}: {exc}"}})


def run() -> None:
    # stdout carries the protocol. Anything else that reaches it corrupts the
    # stream, so keep the real handle for protocol writes and point sys.stdout
    # at stderr for the lifetime of the server.
    protocol_out = sys.stdout
    sys.stdout = sys.stderr
    serve(sys.stdin, protocol_out)
