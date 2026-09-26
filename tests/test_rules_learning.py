"""Learned rules: capture, recall, and enforcement.

The user's example was "never use em dashes", but the feature is general:
ANY correction or preference becomes a standing rule. These tests use three
different kinds deliberately:

  * a preference no machine can check ("keep replies short") -- recall only;
  * a banned word ("leverage") -- recall plus enforcement;
  * a folder-scoped rule ("no print() in services/") -- applies to some files only.

Hooks are driven through the real launcher (sia_hook.py) as a subprocess,
exactly as Claude Code and Codex run them.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "cli.py"
HOOK = REPO / "sia_hook.py"
EM_DASH = "—"


def sia(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CLI), "--json", *args], cwd=root, capture_output=True, text=True)


def hook(event: str, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(HOOK), event], input=json.dumps(payload),
                          capture_output=True, text=True, encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    assert sia(tmp_path, "init", "--mode", "orchestrator").returncode == 0
    return tmp_path


def learn(root: Path, text: str, quote: str, **extra: str) -> dict:
    args = ["rule", "learn", "--text", text, "--user-quote", quote]
    for key, value in extra.items():
        args += [f"--{key.replace('_', '-')}", value]
    result = sia(root, *args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


# --- capture ----------------------------------------------------------------

def test_learning_records_the_users_words_as_evidence(project: Path) -> None:
    rule = learn(project, "Keep replies short.", "your answers are way too long")
    assert rule["status"] == "active"
    assert rule["evidence"] == "your answers are way too long"
    assert rule["scope"] == "**" and rule["severity"] == "low"
    events = [json.loads(l) for l in (project / ".sia" / "events.jsonl").read_text().splitlines() if l]
    assert any(e["id"] == rule["source_event"] and e["outcome"] == "DEVIATION" for e in events)


def test_an_invalid_or_match_everything_pattern_is_refused(project: Path) -> None:
    """A bad pattern would silently switch enforcement off, or flag everything."""
    bad = sia(project, "rule", "learn", "--text", "x", "--user-quote", "x", "--forbid", "(unclosed")
    empty = sia(project, "rule", "learn", "--text", "x", "--user-quote", "x", "--forbid", ".*")
    assert bad.returncode != 0 and "regular expression" in bad.stderr
    assert empty.returncode != 0 and "empty text" in empty.stderr


# --- recall -----------------------------------------------------------------

def test_session_start_recalls_every_active_rule(project: Path) -> None:
    learn(project, "Keep replies short.", "too long")
    learn(project, "Never use the word 'leverage'.", "stop saying leverage", forbid=r"\bleverage\b")
    retired = learn(project, "Use American spelling.", "use US spelling")
    assert sia(project, "rule", "retire", "--id", retired["id"], "--reason", "changed mind").returncode == 0

    result = hook("session-start", {"cwd": str(project), "hook_event_name": "SessionStart"})
    assert result.returncode == 0
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Keep replies short." in context            # recall works for uncheckable preferences
    assert "leverage" in context and "automatically checked" in context
    assert "American spelling" not in context, "a retired rule must not be recalled"
    assert "sia_rule_learn" in context, "the agent is told how to record new corrections"


def test_session_start_works_from_a_subdirectory(project: Path) -> None:
    learn(project, "Keep replies short.", "too long")
    sub = project / "src" / "deep"
    sub.mkdir(parents=True)
    result = hook("session-start", {"cwd": str(sub)})
    assert "Keep replies short." in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


def test_hooks_stay_silent_in_projects_without_sia(tmp_path: Path) -> None:
    for event, payload in (
        ("session-start", {"cwd": str(tmp_path)}),
        ("post-tool-use", {"cwd": str(tmp_path), "tool_name": "Write",
                           "tool_input": {"file_path": str(tmp_path / "a.md"), "content": EM_DASH}}),
        ("stop", {"cwd": str(tmp_path), "last_assistant_message": EM_DASH}),
    ):
        result = hook(event, payload)
        assert result.returncode == 0 and result.stdout == "" and result.stderr == "", event


# --- enforcement: file writes -------------------------------------------------

def test_a_write_breaking_a_checkable_rule_is_pushed_back(project: Path) -> None:
    learn(project, "Never use em dashes.", "no em dashes please", forbid=EM_DASH)
    result = hook("post-tool-use", {
        "cwd": str(project), "tool_name": "Write",
        "tool_input": {"file_path": str(project / "docs" / "guide.md"), "content": f"Fast {EM_DASH} and safe."},
    })
    assert result.returncode == 2, "exit 2 is what hosts feed back to the agent"
    assert "docs/guide.md" in result.stderr and "Never use em dashes." in result.stderr


def test_only_newly_written_text_is_checked(project: Path) -> None:
    """An Edit that adds clean text to a file already containing the banned text
    must pass -- otherwise any file predating a rule could never be edited."""
    learn(project, "Never say 'leverage'.", "stop it", forbid=r"\bleverage\b")
    legacy = project / "old.md"
    legacy.write_text("We leverage synergy.\n")
    result = hook("post-tool-use", {
        "cwd": str(project), "tool_name": "Edit",
        "tool_input": {"file_path": str(legacy), "old_string": "synergy", "new_string": "teamwork"},
    })
    assert result.returncode == 0, result.stderr


def test_a_folder_scoped_rule_only_applies_inside_that_folder(project: Path) -> None:
    learn(project, "No print() in services code; use the logger.", "don't print in services",
          scope="services/**", forbid=r"\bprint\(")
    inside = hook("post-tool-use", {"cwd": str(project), "tool_name": "Write",
                                    "tool_input": {"file_path": str(project / "services" / "api.py"), "content": "print('x')"}})
    outside = hook("post-tool-use", {"cwd": str(project), "tool_name": "Write",
                                     "tool_input": {"file_path": str(project / "scripts" / "dev.py"), "content": "print('x')"}})
    assert inside.returncode == 2
    assert outside.returncode == 0


def test_codex_apply_patch_additions_are_checked(project: Path) -> None:
    learn(project, "Never say 'leverage'.", "stop it", forbid=r"\bleverage\b")
    patch = ("*** Begin Patch\n*** Update File: notes.md\n@@\n-We use synergy.\n"
             "+We leverage synergy.\n*** End Patch\n")
    result = hook("post-tool-use", {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"input": patch}})
    assert result.returncode == 2 and "notes.md" in result.stderr


def test_removed_lines_in_a_patch_are_not_violations(project: Path) -> None:
    learn(project, "Never say 'leverage'.", "stop it", forbid=r"\bleverage\b")
    patch = "*** Begin Patch\n*** Update File: notes.md\n-We leverage synergy.\n+We use synergy.\n*** End Patch\n"
    result = hook("post-tool-use", {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"input": patch}})
    assert result.returncode == 0, "removing banned text is a fix, not a violation"


# --- enforcement: replies -----------------------------------------------------

def test_a_reply_breaking_an_everywhere_rule_blocks_the_stop(project: Path) -> None:
    learn(project, "Never use em dashes.", "no em dashes please", forbid=EM_DASH)
    result = hook("stop", {"cwd": str(project), "last_assistant_message": f"Done {EM_DASH} all good."})
    decision = json.loads(result.stdout)
    assert decision["decision"] == "block"
    assert "Never use em dashes." in decision["reason"]


def test_the_stop_hook_never_loops(project: Path) -> None:
    """If the agent cannot satisfy a rule, blocking forever would trap it."""
    learn(project, "Never use em dashes.", "no em dashes", forbid=EM_DASH)
    result = hook("stop", {"cwd": str(project), "last_assistant_message": EM_DASH, "stop_hook_active": True})
    assert result.returncode == 0 and result.stdout == ""


def test_a_file_scoped_rule_does_not_police_replies(project: Path) -> None:
    learn(project, "No print() in services.", "no print", scope="services/**", forbid=r"\bprint\(")
    result = hook("stop", {"cwd": str(project), "last_assistant_message": "Use print('x') to debug."})
    assert result.stdout == ""


def test_the_reply_is_read_from_a_claude_code_transcript(project: Path, tmp_path: Path) -> None:
    """Without last_assistant_message, the hook reads the transcript. Only the
    current turn counts: an em dash in an earlier turn is already done."""
    learn(project, "Never use em dashes.", "no em dashes", forbid=EM_DASH)
    transcript = tmp_path / "t.jsonl"
    entries = [
        {"type": "user", "message": {"role": "user", "content": "first question"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": f"old {EM_DASH} turn"}]}},
        {"type": "user", "message": {"role": "user", "content": "second question"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Read"}]}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "..."}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "clean answer"}]}},
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries))
    clean = hook("stop", {"cwd": str(project), "transcript_path": str(transcript)})
    assert clean.stdout == "", "the em dash was in an earlier turn; a tool result is not a new user turn"

    entries[-1]["message"]["content"][0]["text"] = f"new {EM_DASH} answer"
    transcript.write_text("\n".join(json.dumps(e) for e in entries))
    dirty = hook("stop", {"cwd": str(project), "transcript_path": str(transcript)})
    assert json.loads(dirty.stdout)["decision"] == "block"


# --- robustness ---------------------------------------------------------------

def test_a_corrupt_rules_file_never_blocks_the_session(project: Path) -> None:
    (project / ".sia" / "rules.json").write_text("{not json")
    for event, payload in (
        ("session-start", {"cwd": str(project)}),
        ("stop", {"cwd": str(project), "last_assistant_message": EM_DASH}),
    ):
        assert hook(event, payload).returncode == 0, event


def test_garbage_input_never_blocks_the_session() -> None:
    result = subprocess.run([sys.executable, str(HOOK), "stop"], input="not json at all",
                            capture_output=True, text=True)
    assert result.returncode == 0
