"""Generate the MCP launcher configs: .mcp.json and mcp.json.

Run from the repository root:  python3 tools/gen_mcp_config.py

Two files, identical content, because hosts disagree on the name:
  .mcp.json  Claude Code; Codex 0.136.0 (verified to ignore mcp.json)
  mcp.json   Kiro and the Agent Plugins portable format

tests/test_mcp_server.py asserts both files equal this script's output, so they
cannot drift from each other or from this source.

Hosts also disagree on how an MCP server learns where its plugin is installed.
Claude Code expands ${CLAUDE_PLUGIN_ROOT} in arguments. Codex 0.136.0 was
probed: no variable expansion, no PLUGIN_* environment, cwd = the user's
project. Kiro documents no variable at all. So the launcher is inline Python --
it cannot live in a file, because locating that file is the problem -- and
tries, in order:

  1. a root the host substituted into argv (Claude Code),
  2. CLAUDE_PLUGIN_ROOT / PLUGIN_ROOT from the environment,
  3. Codex's plugin cache, highest installed version first,
  4. Kiro's powers directory, at most four levels deep -- a recursive search
     would walk every installed power's files, node_modules included, on
     every server start,
  5. Gemini CLI's extensions directory.

It deliberately never looks in its working directory. Codex starts the server
with cwd = the user's project, so an untrusted repository containing a file
named sia_mcp.py would otherwise have its code executed the moment the host
started the server. Only host-provided paths and host-managed install
directories are trusted.

If every candidate fails it exits with a diagnostic on stderr -- what it was
given and where it looked -- which hosts surface in their MCP logs. stdout is
never written: hosts read it as protocol.
"""
from __future__ import annotations

import json
from pathlib import Path

LAUNCHER = """\
import glob, os, runpy, sys
def usable(p):
    return bool(p) and '${' not in p and os.path.isfile(os.path.join(p, 'sia_mcp.py'))
def version(p):
    try:
        return tuple(int(x) for x in os.path.basename(os.path.normpath(p)).split('.'))
    except ValueError:
        return ()
home = os.path.expanduser('~')
candidates = sys.argv[1:] + [os.environ.get(k, '') for k in ('CLAUDE_PLUGIN_ROOT', 'PLUGIN_ROOT')]
candidates += sorted(glob.glob(os.path.join(home, '.codex', 'plugins', 'cache', '*', 'sia', '*')), key=version, reverse=True)
for depth in range(1, 5):
    candidates += [os.path.dirname(p) for p in glob.glob(os.path.join(home, '.kiro', 'powers', *['*'] * depth, 'sia_mcp.py'))]
candidates += [os.path.join(home, '.gemini', 'extensions', 'sia')]
root = next((p for p in candidates if usable(p)), None)
if root is None:
    sys.exit('sia: cannot locate the plugin root. argv=%r cwd=%r tried=%r' % (sys.argv[1:], os.getcwd(), candidates))
runpy.run_path(os.path.join(root, 'sia_mcp.py'), run_name='__main__')
"""

CONFIG = {
    "mcpServers": {
        "sia": {
            "command": "python3",
            "args": ["-c", LAUNCHER, "${CLAUDE_PLUGIN_ROOT}"],
        }
    }
}

FILES = (".mcp.json", "mcp.json")


def render() -> str:
    return json.dumps(CONFIG, indent=2) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in FILES:
        (root / name).write_text(render(), encoding="utf-8")
        print("wrote", name)


if __name__ == "__main__":
    main()
