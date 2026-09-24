"""Protocol tests for the stdio MCP server.

These launch `sia_mcp.py` as a real subprocess and talk newline-delimited
JSON-RPC to it, which is exactly what every host does. The server is started
from a directory that is NOT the project, mirroring how hosts launch it from
the plugin's install directory; the project is always reached through
project_root.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SERVER = Path(__file__).resolve().parents[1] / "sia_mcp.py"
STAGE_EVIDENCE = ("sdd/a.md", "docs/specs/s.md", "sdd/b.md", "sdd/c.md", "sdd/d.md")


class Client:
    def __init__(self, cwd: Path) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER)], cwd=cwd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self._next_id = 0

    def send(self, payload: Any) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write((payload if isinstance(payload, str) else json.dumps(payload)) + "\n")
        self.proc.stdin.flush()

    def read(self) -> dict[str, Any]:
        assert self.proc.stdout is not None
        line = self.proc.stdout.readline()
        assert line, f"server closed stdout; stderr: {self.proc.stderr.read() if self.proc.stderr else ''}"
        return json.loads(line)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        response = self.read()
        assert response["id"] == self._next_id, "responses must answer the request they belong to"
        return response

    def call(self, name: str, **arguments: Any) -> tuple[str, bool]:
        result = self.request("tools/call", {"name": name, "arguments": arguments})["result"]
        return result["content"][0]["text"], result["isError"]

    def close(self) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.close()
        self.proc.wait(timeout=10)


@pytest.fixture
def client(tmp_path: Path):
    launch_dir = tmp_path / "plugin-install-dir"   # stands in for the plugin root
    launch_dir.mkdir()
    c = Client(launch_dir)
    init = c.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "test", "version": "0"}})
    assert init["result"]["protocolVersion"] == "2025-06-18"
    c.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    yield c
    c.close()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    return root


def write(root: Path, relative: str, text: str = "evidence\n") -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return relative


# --- protocol -------------------------------------------------------------

def test_handshake_advertises_tools_and_instructions(tmp_path: Path) -> None:
    c = Client(tmp_path)
    result = c.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})["result"]
    assert result["serverInfo"]["name"] == "sia"
    assert "tools" in result["capabilities"]
    assert "project_root" in result["instructions"]
    c.close()


def test_unknown_protocol_version_gets_the_latest_supported(tmp_path: Path) -> None:
    c = Client(tmp_path)
    result = c.request("initialize", {"protocolVersion": "1999-01-01", "capabilities": {}})["result"]
    assert result["protocolVersion"] == "2025-06-18"
    c.close()


def test_notifications_get_no_reply(client: Client) -> None:
    """A reply to a notification would desynchronise every later request."""
    client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    client.send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 99}})
    assert client.request("ping")["result"] == {}   # next line read is the ping reply


def test_bad_input_is_answered_and_the_server_survives(client: Client) -> None:
    client.send("{not json")
    assert client.read()["error"]["code"] == -32700
    client.send(json.dumps([{"jsonrpc": "2.0", "id": 1, "method": "ping"}]))
    assert client.read()["error"]["code"] == -32600
    assert client.request("no/such/method")["error"]["code"] == -32601
    assert client.request("tools/call", {"name": "no_such_tool", "arguments": {}})["error"]["code"] == -32602
    assert client.request("ping")["result"] == {}, "server must still be alive"


def test_tools_list_schemas_all_require_project_root(client: Client) -> None:
    tools = client.request("tools/list")["result"]["tools"]
    assert tools, "no tools advertised"
    for tool in tools:
        assert "project_root" in tool["inputSchema"]["required"], tool["name"]
    names = {t["name"] for t in tools}
    assert "sia_orchestrate_run" not in names, "standalone run needs a human; it must stay CLI-only"


def test_stdout_carries_only_protocol(client: Client, project: Path) -> None:
    """SIA prints JSON on every command. If any of it leaked to stdout outside a
    JSON-RPC message, the next read would not parse and the host would drop the
    server."""
    client.call("sia_doctor", project_root=str(project))
    client.call("sia_init", project_root=str(project), mode="orchestrator")
    assert client.request("ping")["result"] == {}


# --- safety of project_root ----------------------------------------------

def test_a_relative_project_root_is_refused(client: Client, tmp_path: Path) -> None:
    """The server runs from the plugin's directory. A relative root would
    initialize SIA inside the plugin install, silently."""
    text, is_error = client.call("sia_init", project_root=".", mode="orchestrator")
    assert is_error and "absolute" in text
    assert not (tmp_path / "plugin-install-dir" / ".sia").exists()


def test_a_missing_project_root_is_refused(client: Client, tmp_path: Path) -> None:
    text, is_error = client.call("sia_status", project_root=str(tmp_path / "nope"))
    assert is_error and "does not exist" in text


def test_invalid_arguments_are_refused_before_running(client: Client, project: Path) -> None:
    _, bad_enum = client.call("sia_init", project_root=str(project), mode="yolo")
    _, unknown = client.call("sia_status", project_root=str(project), force=True)
    _, empty_list = client.call("sia_advance", project_root=str(project), evidence=[])
    assert bad_enum and unknown and empty_list
    assert not (project / ".sia").exists(), "nothing may run on invalid arguments"


# --- feedback tools -------------------------------------------------------

def test_feedback_tools_accept_their_documented_arguments(client: Client, project: Path) -> None:
    """The skills document these argument sets. An earlier version of the
    skills documented CLI examples that were missing required flags and would
    have failed; this runs the documented shapes for real."""
    root = str(project)
    assert not client.call("sia_init", project_root=root, mode="orchestrator")[1]

    text, err = client.call("sia_preflight", project_root=root, scope=["src/**"])
    assert not err, text
    text, err = client.call("sia_record", project_root=root, outcome="pass",
                            signal="probe", context="documented shape", severity="low")
    assert not err, text
    text, err = client.call("sia_capture", project_root=root, signal="budget-overrun",
                            context="documented shape", severity="high", error_class="cost-overrun")
    assert not err, text
    text, err = client.call("sia_convergence", project_root=root)
    assert not err, text
    assert "cost-overrun" in text, "the captured deviation must be counted"


def test_the_documented_rule_add_command_works(project: Path) -> None:
    """sia-workflow documents `rule add` as a CLI command with these flags."""
    cli = SERVER.parent / "cli.py"

    def sia(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(cli), *args], cwd=project,
                              capture_output=True, text=True)

    assert sia("init", "--mode", "orchestrator").returncode == 0
    captured = sia("--json", "capture", "--signal", "s", "--context", "c",
                   "--severity", "medium", "--error-class", "probe-class")
    assert captured.returncode == 0, captured.stderr
    event_id = json.loads(captured.stdout)["id"]

    added = sia("rule", "add", "--text", "a standing rule", "--scope", "src/**",
                "--severity", "medium", "--error-class", "probe-class", "--source-event", event_id)
    assert added.returncode == 0, added.stderr


# --- workflow end to end over MCP ----------------------------------------

def test_full_workflow_to_a_dispatch_plan(client: Client, project: Path) -> None:
    root = str(project)

    _, err = client.call("sia_init", project_root=root, mode="orchestrator")
    assert not err
    assert (project / ".sia").is_dir(), "state must land in the project, not the server's cwd"

    refusal, err = client.call("sia_task_prepare", project_root=root, task="t1",
                               brief="sdd/brief.md", files=["app.py"])
    assert err and "'intake'" in refusal and "sia advance --evidence" in refusal, \
        "the gate refusal must reach the model with its remedy intact"

    for evidence in STAGE_EVIDENCE:
        _, err = client.call("sia_advance", project_root=root, evidence=[write(project, evidence)])
        assert not err, f"advance with {evidence} failed"
    assert json.loads(client.call("sia_status", project_root=root)[0])["current_stage"] == "execution"

    example = json.loads(client.call("sia_orchestrate_example", project_root=root)[0])
    for tier, model_id in (("cheap", "m-cheap"), ("current", "m-current"), ("strong", "m-strong")):
        example["models"][tier]["id"] = model_id
    _, err = client.call("sia_orchestrate_configure", project_root=root,
                         file=write(project, "o.json", json.dumps(example)))
    assert not err

    write(project, "app.py", "print(1)\n")
    _, err = client.call("sia_task_prepare", project_root=root, task="t1",
                         brief=write(project, "sdd/brief.md"), files=["app.py"],
                         risk="high", complexity="complex", estimated_tokens=500)
    assert not err

    plan_text, err = client.call("sia_orchestrate_plan", project_root=root, backend="native-host", host="codex")
    assert not err
    plan = json.loads(plan_text)
    tiers = {o["operation_id"]: o["tier"] for o in plan["operations"]}
    assert tiers == {"t1:implement": "strong", "t1:review": "strong"}
