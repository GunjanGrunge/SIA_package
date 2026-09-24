"""Behavioural tests for the orchestration runtime.

`validate_sia.py` checks that documents and sources contain required strings.
It cannot notice a runtime that *behaves* wrongly, which is how a budget-bypass
finding could stand unchallenged: nothing ever drove a run past its ceiling to
see what happened. These tests drive the real CLI end to end in a scratch
project and assert on outcomes.

Each test builds its own project, so they are independent and order-free.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CLI = Path(__file__).resolve().parents[1] / "cli.py"
STAGE_EVIDENCE = ("sdd/a.md", "docs/specs/s.md", "sdd/b.md", "sdd/c.md", "sdd/d.md")


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=root,
        capture_output=True,
        text=True,
    )


def ok(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = run(root, *args)
    assert result.returncode == 0, f"{args} failed: {result.stderr.strip()}"
    return result


def write(root: Path, relative: str, text: str = "evidence\n") -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return relative


def project_at_execution(root: Path, max_tokens: int = 100_000) -> dict:
    """Initialise, walk every gate to `execution`, configure, prepare, plan."""
    ok(root, "init", "--mode", "orchestrator")
    for evidence in STAGE_EVIDENCE:
        ok(root, "advance", "--evidence", write(root, evidence))

    config = json.loads(ok(root, "orchestrate", "example").stdout)
    for tier, model_id in (("cheap", "m-cheap"), ("current", "m-current"), ("strong", "m-strong")):
        config["models"][tier]["id"] = model_id
    config["budget"]["max_tokens"] = max_tokens
    config["budget"]["max_cost_usd"] = 1_000
    ok(root, "orchestrate", "configure", "--file", write(root, "o.json", json.dumps(config)))

    write(root, "app.py", "print('x')\n")
    ok(root, "task", "prepare", "--task", "t1", "--brief", write(root, "sdd/brief.md"),
       "--files", "app.py", "--risk", "low", "--complexity", "simple",
       "--estimated-tokens", "100")
    return json.loads(ok(root, "orchestrate", "plan", "--backend", "native-host",
                         "--host", "claude").stdout)


def submit_receipt(root: Path, plan: dict, operation_id: str, agent_id: str,
                   input_tokens: int, output_tokens: int) -> subprocess.CompletedProcess[str]:
    operation = next(o for o in plan["operations"] if o["operation_id"] == operation_id)
    report = write(root, f"reports/{operation_id.replace(':', '-')}.md", "a real report\n")
    receipt = {
        "schema_version": 1,
        "plan_id": plan["plan_id"],
        "plan_hash": plan["plan_hash"],
        "operation_id": operation_id,
        "status": "complete",
        "provenance": "native_attested",
        "host": "claude",
        "agent_id": agent_id,
        "native_run_id": f"run-{agent_id}",
        "requested_model_id": operation["requested_model_id"],
        "actual_model_id": operation["requested_model_id"],
        "report_path": report,
        "telemetry": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }
    return run(root, "orchestrate", "receipt", "--file",
               write(root, f"receipt-{agent_id}.json", json.dumps(receipt)))


def status(root: Path) -> str:
    return json.loads(ok(root, "orchestrate", "status").stdout)["status"]


# --- budget ceiling -------------------------------------------------------

def test_an_overrun_is_terminal_and_blocks_review_and_integration(tmp_path: Path) -> None:
    """A run that exceeds its ceiling must stay stopped.

    Regression guard for the budget-bypass finding in
    docs/reviews/2026-09-18-sia-0.3-review.md: an overrun used to be replaceable
    by `complete`, letting a run exceed its ceiling and still pass integration.
    Each step below is an attempt to push past the overrun.
    """
    plan = project_at_execution(tmp_path, max_tokens=2_000)

    overrun = submit_receipt(tmp_path, plan, "t1:implement", "implementer", 4_000, 1_000)
    assert overrun.returncode == 0, "the overrunning receipt itself must still be recorded"
    assert status(tmp_path) == "budget-exceeded"

    review = submit_receipt(tmp_path, plan, "t1:review", "reviewer", 10, 10)
    assert review.returncode != 0, "a receipt after an overrun must be rejected"
    assert "budget-exceeded" in review.stderr
    assert status(tmp_path) == "budget-exceeded", "the overrun must not be replaced by complete"

    integration = run(tmp_path, "integration", "--evidence", write(tmp_path, "sdd/int.md"))
    assert integration.returncode != 0, "integration must not pass after an overrun"


def test_an_overrun_on_the_final_receipt_is_not_reported_complete(tmp_path: Path) -> None:
    """The precise shape of the original finding.

    When the LAST outstanding operation is the one that blows the ceiling, every
    operation is complete AND the budget is exceeded in the same transition. If
    completion is checked before the overrun, the run is reported `complete` and
    sails through integration over budget.

    The test above cannot see this: it overruns on the first receipt, while the
    review is still pending, so "all complete" is never true and the order of
    the two checks never matters. That test passed against a runtime with this
    exact bug reintroduced; this one fails against it.
    """
    plan = project_at_execution(tmp_path, max_tokens=2_000)

    within = submit_receipt(tmp_path, plan, "t1:implement", "implementer", 300, 100)
    assert within.returncode == 0
    assert status(tmp_path) != "budget-exceeded", "still within budget after the implementer"

    final_overrun = submit_receipt(tmp_path, plan, "t1:review", "reviewer", 4_000, 1_000)
    assert final_overrun.returncode == 0, "the overrunning receipt itself must be recorded"
    assert status(tmp_path) == "budget-exceeded", (
        "an overrun on the final receipt must not be reported as complete"
    )

    integration = run(tmp_path, "integration", "--evidence", write(tmp_path, "sdd/int.md"))
    assert integration.returncode != 0, "integration must not pass over budget"


def test_a_run_within_budget_completes(tmp_path: Path) -> None:
    """The other half of the budget contract.

    Without this, the overrun test would still pass if the runtime rejected
    every run, which would be a broken tool that looks safe.
    """
    plan = project_at_execution(tmp_path, max_tokens=100_000)

    assert submit_receipt(tmp_path, plan, "t1:implement", "implementer", 300, 100).returncode == 0
    assert submit_receipt(tmp_path, plan, "t1:review", "reviewer", 50, 20).returncode == 0
    assert status(tmp_path) == "complete"


# --- independent review ---------------------------------------------------

def test_an_agent_cannot_review_its_own_work(tmp_path: Path) -> None:
    plan = project_at_execution(tmp_path)

    assert submit_receipt(tmp_path, plan, "t1:implement", "same-agent", 300, 100).returncode == 0
    self_review = submit_receipt(tmp_path, plan, "t1:review", "same-agent", 50, 20)

    assert self_review.returncode != 0
    assert "different reviewer" in self_review.stderr
    assert status(tmp_path) != "complete"


# --- stage gates ----------------------------------------------------------

@pytest.mark.parametrize("command", [
    ("task", "prepare", "--task", "t", "--brief", "b", "--files", "f",
     "--risk", "low", "--complexity", "simple"),
    ("orchestrate", "plan", "--backend", "native-host", "--host", "claude"),
])
def test_an_execution_refusal_names_the_remedy(tmp_path: Path, command: tuple[str, ...]) -> None:
    """Refusing is correct before `execution`; refusing without saying what to
    do next is what made a working install look broken on first contact."""
    ok(tmp_path, "init", "--mode", "orchestrator")

    refused = run(tmp_path, *command)

    assert refused.returncode != 0
    assert "'intake'" in refused.stderr, "must name the current stage"
    assert "execution" in refused.stderr, "must name the stage it needs"
    assert "sia advance --evidence" in refused.stderr, "must name the next command"


# --- release consistency --------------------------------------------------

def test_every_version_marker_agrees() -> None:
    """Six files declare the version. Claude Code reads the plugin's to decide
    whether an installed copy is stale, so a plugin version left behind the
    package's means users never receive the update."""
    root = CLI.parent

    def json_version(relative: str, *path: str | int) -> str:
        node = json.loads((root / relative).read_text(encoding="utf-8"))
        for key in path:
            node = node[key]
        return node

    def regex_version(relative: str, pattern: str) -> str:
        import re
        match = re.search(pattern, (root / relative).read_text(encoding="utf-8"), re.MULTILINE)
        assert match, f"no version found in {relative}"
        return match.group(1)

    versions = {
        "pyproject.toml": regex_version("pyproject.toml", r'^version = "([^"]+)"'),
        "src/sia/__init__.py": regex_version("src/sia/__init__.py", r'^__version__ = "([^"]+)"'),
        "package.json": json_version("package.json", "version"),
        "extension/package.json": json_version("extension/package.json", "version"),
        ".claude-plugin/plugin.json": json_version(".claude-plugin/plugin.json", "version"),
        ".claude-plugin/marketplace.json": json_version(
            ".claude-plugin/marketplace.json", "plugins", 0, "version"),
        "plugin.json": json_version("plugin.json", "version"),
        "gemini-extension.json": json_version("gemini-extension.json", "version"),
    }

    assert len(set(versions.values())) == 1, f"version markers disagree: {versions}"


# --- configuration --------------------------------------------------------

def test_configure_rejects_the_example_placeholders(tmp_path: Path) -> None:
    """`orchestrate example` emits placeholders on purpose. Accepting one yields
    a config that reports configured but can never dispatch."""
    ok(tmp_path, "init", "--mode", "orchestrator")
    example = ok(tmp_path, "orchestrate", "example").stdout

    refused = run(tmp_path, "orchestrate", "configure", "--file", write(tmp_path, "o.json", example))

    assert refused.returncode != 0
    assert "placeholder" in refused.stderr
