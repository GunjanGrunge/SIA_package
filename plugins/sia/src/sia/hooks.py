"""Host hooks that make learned rules stick: recall, and enforcement.

SIA stores rules the user taught it (``.sia/rules.json``). Storing is not
enough: a rule only matters if the agent actually has it in mind, and for
rules that can be checked, if something checks. These hooks close both gaps
without relying on the agent to remember to ask.

  session-start   Inject every active rule into the new session's context.
                  Also fires after /compact, so rules survive compaction.
  post-tool-use   After a file write or edit, check ONLY the text the agent
                  just wrote against rules that carry a ``forbid`` pattern.
                  A violation exits 2, which hosts feed back to the agent.
  stop            Before the agent's turn ends, check its reply against
                  rules that apply everywhere. A violation blocks the stop
                  with a reason, so the agent corrects itself.

Most preferences ("keep answers short", "never touch infra/ without asking")
cannot be checked mechanically. Recall is how those stick. Enforcement is the
extra safety net for the ones that can ("no em dashes", "never say
'leverage'").

Hard rules for this module, because it runs inside someone else's session:
  - never block the user on SIA's own bug: any internal error exits 0;
  - stay silent in projects that do not use SIA;
  - check only what the agent just wrote, never pre-existing content, or a
    file that predates a rule could never be edited again;
  - honour ``stop_hook_active`` so a rule the agent cannot satisfy cannot
    trap it in a loop.
"""
from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, TextIO

EVERYWHERE = frozenset({"*", "**"})
MAX_SHOWN_MATCHES = 3
FILE_WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit", "apply_patch"})


# --- rules -----------------------------------------------------------------

def find_project_root(start: Path) -> Path | None:
    """Nearest ancestor holding .sia/, so hooks work from any subdirectory."""
    try:
        start = start.resolve()
    except OSError:
        return None
    for candidate in (start, *start.parents):
        if (candidate / ".sia").is_dir():
            return candidate
    return None


def load_active_rules(root: Path) -> list[dict[str, Any]]:
    try:
        rules = json.loads((root / ".sia" / "rules.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(rules, list):
        return []
    return [r for r in rules if isinstance(r, dict) and r.get("status") == "active" and r.get("text")]


def applies_everywhere(rule: dict[str, Any]) -> bool:
    return rule.get("scope", "**") in EVERYWHERE


def applies_to_path(rule: dict[str, Any], relative: str) -> bool:
    scope = rule.get("scope", "**")
    return scope in EVERYWHERE or fnmatch.fnmatch(relative, scope)


def find_violations(text: str, rules: Iterable[dict[str, Any]]) -> list[tuple[dict[str, Any], list[str]]]:
    found = []
    for rule in rules:
        pattern = rule.get("forbid")
        if not pattern:
            continue
        try:
            matches = [m.group(0) for m in re.finditer(pattern, text)]
        except re.error:
            continue  # a rule with a broken pattern must not break the session
        if matches:
            unique = list(dict.fromkeys(matches))[:MAX_SHOWN_MATCHES]
            found.append((rule, unique if len(matches) == len(unique) else unique + [f"({len(matches)} in total)"]))
    return found


def describe_violations(where: str, violations: list[tuple[dict[str, Any], list[str]]]) -> str:
    lines = [f"SIA: {where} breaks a rule the user set for this project. Fix it before continuing."]
    for rule, matches in violations:
        shown = ", ".join(repr(m) for m in matches)
        lines.append(f"- [{rule.get('id')}] {rule.get('text')} Found: {shown}")
    return "\n".join(lines)


# --- session start: recall ---------------------------------------------------

LEARN_INSTRUCTION = (
    "This project uses SIA. Whenever the user corrects your work or states a lasting preference "
    "for this project (tone, wording, formatting, process, files to avoid, anything), call the "
    "sia_rule_learn tool straight away with the rule and the user's own words, so it holds in "
    "every future session. If it can be checked mechanically, such as a banned character, word "
    "or phrase, also pass forbid."
)


def recall_text(rules: list[dict[str, Any]]) -> str:
    if not rules:
        # Still worth saying: without it, nothing prompts the agent to learn
        # the project's FIRST rule, and the loop never starts.
        return LEARN_INSTRUCTION
    lines = [
        "SIA standing rules for this project. The user set each of these by correcting earlier "
        "work, so follow all of them throughout this session:",
    ]
    for rule in rules:
        where = "everywhere, including your replies" if applies_everywhere(rule) else f"files matching {rule.get('scope')}"
        enforced = " (automatically checked)" if rule.get("forbid") else ""
        lines.append(f"- {rule['text']} [applies to {where}{enforced}; {rule.get('id')}]")
    lines.append(LEARN_INSTRUCTION)
    return "\n".join(lines)


def session_start(payload: dict[str, Any]) -> dict[str, Any] | None:
    root = find_project_root(Path(payload.get("cwd") or "."))
    if root is None:
        return None  # not a SIA project: say nothing
    text = recall_text(load_active_rules(root))
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}


# --- post tool use: check what was just written -------------------------------

def _patch_additions(patch: str) -> dict[str, str]:
    """Added lines per file in a Codex apply_patch payload."""
    added: dict[str, list[str]] = {}
    current: str | None = None
    for line in patch.splitlines():
        header = re.match(r"\*\*\* (?:Add|Update) File: (.+)", line)
        if header:
            current = header.group(1).strip()
            added.setdefault(current, [])
        elif line.startswith("*** "):
            current = None
        elif current and line.startswith("+") and not line.startswith("+++"):
            added[current].append(line[1:])
    return {path: "\n".join(lines) for path, lines in added.items() if lines}


def written_text(tool_name: str, tool_input: dict[str, Any]) -> dict[str, str]:
    """Only the text the agent introduced, keyed by file path."""
    if tool_name == "Write":
        return {tool_input.get("file_path", ""): tool_input.get("content") or ""}
    if tool_name == "Edit":
        return {tool_input.get("file_path", ""): tool_input.get("new_string") or ""}
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits") or []
        return {tool_input.get("file_path", ""): "\n".join(e.get("new_string") or "" for e in edits if isinstance(e, dict))}
    if tool_name == "NotebookEdit":
        return {tool_input.get("notebook_path", ""): tool_input.get("new_source") or ""}
    if tool_name == "apply_patch":
        patch = next((v for v in _strings(tool_input) if "*** Begin Patch" in v or "*** Update File:" in v), "")
        return _patch_additions(patch)
    return {}


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _relative(root: Path, cwd: Path, raw: str) -> str:
    path = Path(raw)
    if not path.is_absolute():
        path = cwd / path
    try:
        return PurePosixPath(path.resolve().relative_to(root)).as_posix()
    except (OSError, ValueError):
        return PurePosixPath(raw).as_posix()


def post_tool_use(payload: dict[str, Any]) -> tuple[int, str]:
    tool_name = payload.get("tool_name") or ""
    if tool_name not in FILE_WRITE_TOOLS:
        return 0, ""
    cwd = Path(payload.get("cwd") or ".")
    root = find_project_root(cwd)
    if root is None:
        return 0, ""
    rules = [r for r in load_active_rules(root) if r.get("forbid")]
    if not rules:
        return 0, ""
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    problems = []
    for raw_path, text in written_text(tool_name, tool_input).items():
        relative = _relative(root, cwd, raw_path)
        violations = find_violations(text, [r for r in rules if applies_to_path(r, relative)])
        if violations:
            problems.append(describe_violations(f"what you just wrote to {relative}", violations))
    return (2, "\n\n".join(problems)) if problems else (0, "")


# --- stop: check the reply ------------------------------------------------------

def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "") for part in content
            if isinstance(part, dict) and part.get("type") in ("text", "output_text")
        )
    return ""


def _is_real_user_turn(content: Any) -> bool:
    """A user message, as opposed to a tool result recorded under role user."""
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return any(isinstance(p, dict) and p.get("type") in ("text", "input_text") for p in content)
    return False


def last_reply(transcript_path: str) -> str:
    """Everything the assistant said since the user's last message.

    Understands Claude Code transcripts and Codex rollouts. A turn's reply can
    be split across several assistant entries, so they are joined.
    """
    reply: list[str] = []
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        message = entry.get("message") if isinstance(entry.get("message"), dict) else None
        if message is None and entry.get("type") == "response_item" and isinstance(entry.get("payload"), dict):
            message = entry["payload"] if entry["payload"].get("type") == "message" else None
        if message is None:
            continue
        role, content = message.get("role"), message.get("content")
        if role == "user" and _is_real_user_turn(content):
            reply = []
        elif role == "assistant":
            text = _message_text(content)
            if text:
                reply.append(text)
    return "\n".join(reply)


def stop(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("stop_hook_active"):
        return None  # already corrected once this turn; never loop
    root = find_project_root(Path(payload.get("cwd") or "."))
    if root is None:
        return None
    rules = [r for r in load_active_rules(root) if r.get("forbid") and applies_everywhere(r)]
    if not rules:
        return None
    reply = payload.get("last_assistant_message")
    if not isinstance(reply, str):
        reply = last_reply(payload.get("transcript_path") or "")
    violations = find_violations(reply, rules)
    if not violations:
        return None
    return {"decision": "block", "reason": describe_violations("your last reply", violations)
            + "\nRewrite the reply so it follows these rules."}


# --- entry point ------------------------------------------------------------

def main(argv: list[str], stdin: TextIO, stdout: TextIO, stderr: TextIO) -> int:
    event = argv[1] if len(argv) > 1 else ""
    try:
        raw = stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            return 0
        if event == "session-start":
            result = session_start(payload)
            if result:
                stdout.write(json.dumps(result))
            return 0
        if event == "post-tool-use":
            code, message = post_tool_use(payload)
            if message:
                stderr.write(message + "\n")
            return code
        if event == "stop":
            result = stop(payload)
            if result:
                stdout.write(json.dumps(result))
            return 0
        return 0
    except Exception as exc:  # SIA's own bug must never block the user's session
        stderr.write(f"sia hook ({event}) skipped after an internal error: {type(exc).__name__}: {exc}\n")
        return 0


def run() -> None:
    for stream, options in ((sys.stdin, {}), (sys.stdout, {"newline": "\n"}),
                            (sys.stderr, {"errors": "backslashreplace"})):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", **options)
    sys.exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
