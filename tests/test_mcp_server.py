"""Protocol tests for the stdio MCP server.

These launch `sia_mcp.py` as a real subprocess and talk newline-delimited
JSON-RPC to it, which is exactly what every host does. The server is started
from a directory that is NOT the project, mirroring how hosts launch it from
the plugin's install directory; the project is always reached through
project_root.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
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


# --- tool annotations -----------------------------------------------------

def test_every_tool_declares_annotations(client: Client) -> None:
    """Undeclared annotations default to destructive and open-world under the
    MCP spec, which makes hosts demand approval for a harmless status check."""
    for tool in client.request("tools/list")["result"]["tools"]:
        hints = tool.get("annotations")
        assert hints, f"{tool['name']} declares no annotations"
        assert hints["openWorldHint"] is False, f"{tool['name']}: SIA never touches the network"
        if hints["readOnlyHint"]:
            assert hints["destructiveHint"] is False, f"{tool['name']}: read-only cannot be destructive"


def fingerprint(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted((root / ".sia").rglob("*")) if p.is_file()}


# Valid arguments for every tool, for a fresh orchestrator project at `intake`.
# The read-only test must use these: a call rejected by argument validation
# never runs, so it trivially "writes nothing" and proves nothing. An earlier
# version of this test made exactly that mistake and passed with a writing tool
# mislabelled as read-only.
VALID_ARGS: dict[str, dict[str, Any]] = {
    "sia_preflight": {"scope": ["src/**"]},
    "sia_advance": {"evidence": ["sdd/intake.md"]},
    "sia_owner": {"stage": "plan", "to": "sia"},
    "sia_record": {"outcome": "pass", "signal": "s", "context": "c", "severity": "low"},
    "sia_capture": {"signal": "s", "context": "c", "severity": "low", "error_class": "e"},
    "sia_rule_learn": {"text": "t", "user_quote": "q"},
    "sia_rule_retire": {"id": "rule-x", "reason": "r"},
}
VALIDATION_ERRORS = ("missing required argument", "unknown argument", "must be", "needs at least")


def test_tools_labelled_read_only_really_write_nothing(client: Client, project: Path) -> None:
    """A read-only label is a promise hosts act on by skipping approval. If a
    tool labelled read-only ever writes, this catches it."""
    root = str(project)
    assert not client.call("sia_init", project_root=root, mode="orchestrator")[1]
    write(project, "sdd/intake.md")

    read_only = [t["name"] for t in client.request("tools/list")["result"]["tools"]
                 if t["annotations"]["readOnlyHint"]]
    assert read_only, "expected some read-only tools"

    for name in read_only:
        before = fingerprint(project)
        text, _ = client.call(name, project_root=root, **VALID_ARGS.get(name, {}))
        assert not text.startswith(VALIDATION_ERRORS), (
            f"{name} was rejected on its arguments, so it never ran and the check "
            f"proves nothing: {text}")
        assert fingerprint(project) == before, f"{name} is labelled read-only but changed .sia/"


def test_doctor_on_a_fresh_project_is_a_result_not_an_error(client: Client, project: Path) -> None:
    """Before sia_init, doctor's checks fail -- which is the expected finding.
    Reporting it as a tool error made a Codex agent stop at step one."""
    text, is_error = client.call("sia_doctor", project_root=str(project))
    assert not is_error, text
    report = json.loads(text)
    assert report["ok"] is False
    assert any(c["name"] == "initialized" and c["ok"] is False for c in report["checks"])


# --- the shipped launcher in .mcp.json -------------------------------------
#
# Hosts disagree on how an MCP server learns where its plugin lives. Codex
# 0.136.0 was probed: it expands no variable in MCP arguments, sets no PLUGIN_*
# environment, and starts the server with cwd = the user's project. The launcher
# in .mcp.json therefore locates the plugin itself. These tests run that exact
# launcher, read from the shipped file, under each host's conditions.

REPO = SERVER.parent
LITERAL = "${CLAUDE_PLUGIN_ROOT}"   # what Codex passes through unexpanded


def shipped_launcher() -> tuple[str, list[str]]:
    server = json.loads((REPO / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["sia"]
    return server["command"], server["args"]


def launch(args: list[str], cwd: Path, home: Path) -> subprocess.Popen[str]:
    """Start the launcher with a clean environment: no PLUGIN_* variables."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home)}
    return subprocess.Popen([sys.executable, *args], cwd=cwd, env=env, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def handshake(proc: subprocess.Popen[str]) -> dict[str, Any]:
    assert proc.stdin and proc.stdout
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                 "params": {"protocolVersion": "2025-06-18", "capabilities": {}}}) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    proc.stdin.close()
    proc.wait(timeout=10)
    assert line, f"no handshake; stderr: {proc.stderr.read() if proc.stderr else ''}"
    return json.loads(line)


def fake_codex_install(home: Path, version: str, target: Path) -> None:
    slot = home / ".codex" / "plugins" / "cache" / "some-marketplace" / "sia" / version
    slot.parent.mkdir(parents=True, exist_ok=True)
    slot.symlink_to(target, target_is_directory=True)


def decoy_plugin(tmp: Path, name: str) -> Path:
    """A plugin root whose server refuses to start, so choosing it is visible."""
    root = tmp / name
    root.mkdir()
    (root / "sia_mcp.py").write_text("import sys; sys.exit('decoy chosen: " + name + "')\n")
    return root


def test_the_launcher_uses_a_root_the_host_substituted(tmp_path: Path) -> None:
    """Claude Code expands ${CLAUDE_PLUGIN_ROOT}, so the real path arrives."""
    command, args = shipped_launcher()
    assert command == "python3"
    substituted = [a if a != LITERAL else str(REPO) for a in args]
    result = handshake(launch(substituted, cwd=tmp_path, home=tmp_path / "empty-home"))
    assert result["result"]["serverInfo"]["name"] == "sia"


def test_the_launcher_finds_a_codex_install_when_nothing_is_substituted(tmp_path: Path) -> None:
    """Codex: literal ${...}, empty environment, cwd = project. Only the cache
    can reveal where the plugin is."""
    _, args = shipped_launcher()
    assert LITERAL in args, "the launcher must still offer the Claude Code variable"
    home, project = tmp_path / "home", tmp_path / "project"
    project.mkdir()
    fake_codex_install(home, "0.3.1", REPO)

    result = handshake(launch(args, cwd=project, home=home))
    assert result["result"]["serverInfo"]["name"] == "sia"


def test_the_launcher_picks_the_highest_version_numerically(tmp_path: Path) -> None:
    """Sorted as text, 0.9.0 comes after 0.10.0 and the older plugin would load."""
    _, args = shipped_launcher()
    home, project = tmp_path / "home", tmp_path / "project"
    project.mkdir()
    fake_codex_install(home, "0.10.0", REPO)
    fake_codex_install(home, "0.9.0", decoy_plugin(tmp_path, "old-0.9.0"))

    result = handshake(launch(args, cwd=project, home=home))
    assert result["result"]["serverInfo"]["name"] == "sia"


def minimal_plugin(at: Path) -> Path:
    """A real, runnable copy of the plugin's server -- just sia_mcp.py and src/.
    Symlinking the whole repo would drag node_modules into directory scans."""
    at.mkdir(parents=True)
    shutil.copy(REPO / "sia_mcp.py", at / "sia_mcp.py")
    shutil.copytree(REPO / "src", at / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    return at


def test_both_config_files_match_their_generator() -> None:
    """Claude Code and Codex read .mcp.json; Kiro reads mcp.json. They must not
    drift from each other or from tools/gen_mcp_config.py."""
    spec = importlib.util.spec_from_file_location("gen", REPO / "tools" / "gen_mcp_config.py")
    gen = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(gen)
    for name in (".mcp.json", "mcp.json"):
        assert (REPO / name).read_text(encoding="utf-8") == gen.render(), (
            f"{name} is stale: run python3 tools/gen_mcp_config.py")


@pytest.mark.parametrize("layout", [
    ("some-registry", "sia"),
    ("GunjanGrunge", "SIA_package", "main"),
])
def test_the_launcher_finds_a_kiro_power(tmp_path: Path, layout: tuple[str, ...]) -> None:
    """Kiro documents no plugin-root variable and no install location, so the
    launcher searches its powers directory. Two plausible depths are covered."""
    _, args = shipped_launcher()
    home, project = tmp_path / "home", tmp_path / "project"
    project.mkdir()
    minimal_plugin(home.joinpath(".kiro", "powers", *layout))

    result = handshake(launch(args, cwd=project, home=home))
    assert result["result"]["serverInfo"]["name"] == "sia"


def test_the_launcher_never_runs_code_from_its_working_directory(tmp_path: Path) -> None:
    """Security. Codex starts the server with cwd = the user's project. If the
    launcher trusted its working directory, opening an untrusted repository that
    contains a file named sia_mcp.py would execute that file automatically."""
    _, args = shipped_launcher()
    project = tmp_path / "untrusted-repo"
    project.mkdir()
    marker = tmp_path / "PWNED"
    (project / "sia_mcp.py").write_text(f"open({str(marker)!r}, 'w').write('ran')\n")

    proc = launch(args, cwd=project, home=tmp_path / "empty-home")
    proc.communicate(timeout=10)

    assert not marker.exists(), "the launcher executed a sia_mcp.py from the project directory"
    assert proc.returncode != 0


def test_a_non_ascii_project_path_survives_a_legacy_encoding(tmp_path: Path) -> None:
    """Windows decodes piped stdin with its legacy code page. Under Windows
    Python, a project at ...\\José_日本 arrived as ...\\JosÃ©_æ—¥æœ¬ and SIA said
    it did not exist. PYTHONIOENCODING=cp1252 reproduces that on any OS."""
    project = tmp_path / "José_日本"
    project.mkdir()
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    proc = subprocess.Popen([sys.executable, str(SERVER)], cwd=tmp_path, env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "sia_init", "arguments": {"project_root": str(project), "mode": "orchestrator"}}},
    ]
    # Raw UTF-8, as a Node host's JSON.stringify sends it -- not \\u escapes.
    payload = "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in messages).encode("utf-8")
    out, err = proc.communicate(payload, timeout=30)

    lines = [line for line in out.split(b"\n") if line.strip()]
    assert not any(line.endswith(b"\r") for line in lines), "protocol lines must end in \\n, not \\r\\n"
    reply = json.loads(lines[-1])["result"]
    assert reply["isError"] is False, reply["content"][0]["text"]
    assert (project / ".sia").is_dir()


def test_the_launcher_fails_loudly_and_keeps_stdout_clean(tmp_path: Path) -> None:
    """With no way to find the plugin it must exit with a reason on stderr, and
    write nothing to stdout, which the host reads as protocol."""
    _, args = shipped_launcher()
    project = tmp_path / "project"
    project.mkdir()
    proc = launch(args, cwd=project, home=tmp_path / "empty-home")
    stdout, stderr = proc.communicate(timeout=10)
    assert proc.returncode != 0
    assert stdout == ""
    assert "cannot locate the plugin root" in stderr


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


# --- learned rules over MCP ------------------------------------------------

def test_rules_can_be_learned_listed_and_retired_over_mcp(client: Client, project: Path) -> None:
    """Previously `rule add` was CLI-only, so in Codex or Kiro an agent could not
    turn a correction into a rule at all."""
    root = str(project)
    assert not client.call("sia_init", project_root=root, mode="orchestrator")[1]

    text, err = client.call("sia_rule_learn", project_root=root, text="Keep replies short.",
                            user_quote="your answers are too long")
    assert not err, text
    learned = json.loads(text)

    listed = json.loads(client.call("sia_rule_list", project_root=root)[0])
    assert [r["id"] for r in listed] == [learned["id"]]

    assert not client.call("sia_rule_retire", project_root=root, id=learned["id"], reason="done")[1]
    assert json.loads(client.call("sia_rule_list", project_root=root)[0]) == []


def test_a_gated_preflight_is_a_result_not_an_error(client: Client, project: Path) -> None:
    """A medium rule makes preflight exit 2 until acknowledged. Reported as a tool
    error, an agent reads "SIA broke" and may skip the rules it returned."""
    root = str(project)
    client.call("sia_init", project_root=root, mode="orchestrator")
    client.call("sia_rule_learn", project_root=root, text="Ask before touching infra/.",
                user_quote="never change infra without asking me", scope="infra/**", severity="medium")

    text, err = client.call("sia_preflight", project_root=root, scope=["infra/app.ts"])
    assert not err, text
    report = json.loads(text)
    assert report["clear"] is False and report["relevant_rules"]


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
