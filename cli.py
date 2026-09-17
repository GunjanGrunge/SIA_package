"""
SIA (Self-Improving Agents) - Unified Python CLI & Plugin Launcher
====================================================================
Provides `sia init`, `sia status`, `pip install sia-agent`, and `pipx` CLI tooling.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from banner import print_status_audit, print_banner, VERSION

PACKAGE_ROOT = Path(__file__).resolve().parent

def print_help():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(f"""
\033[1m\033[38;2;0;242;254mSIA (Self-Improving Agents) Python CLI v{VERSION}\033[0m

\033[36mUsage:\033[0m
  sia init       Initialize SIA in current project (vendors sia/ & sets up discovery shims)
  sia status     Run SIA project audit, check active skills & token savings
  sia banner     Display terminal launch banner
  sia --help     Show this help guide

\033[36mQuickstart:\033[0m
  1. Run \033[32msia init\033[0m inside your target project directory.
  2. Tell your assistant: \033[33m"Read sia/AGENT.md and follow it."\033[0m
  3. Verify status anytime with \033[32msia status\033[0m.
""")

def init_sia():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print_banner()
    cwd = Path.cwd().resolve()
    sia_target = cwd / "sia"

    print(f"\033[36m[SIA]\033[0m Initializing SIA v{VERSION} in project root: \033[33m{cwd}\033[0m")

    if cwd != PACKAGE_ROOT.resolve():
        sia_target.mkdir(parents=True, exist_ok=True)
        items_to_copy = ['AGENT.md', 'BANNER.txt', 'CHANGELOG.md', 'INSTALL.md', 'README.md', 'USAGE.md', 'VALIDATION.md', 'banner.py', 'capture-interface.md', 'guides', 'integrations']
        for item in items_to_copy:
            src = PACKAGE_ROOT / item
            dest = sia_target / item
            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dest)
        print("\033[32m✔ Vendored SIA files copied to ./sia/\033[0m")
    else:
        print("\033[32m✔ Currently in SIA package repository root.\033[0m")

    # Update .gitignore
    gitignore_path = cwd / ".gitignore"
    gitignore_content = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    if "sia/" not in gitignore_content:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n# Vendored SIA (Self Improving Agents) tooling\nsia/\n")
        print("\033[32m✔ Added sia/ to .gitignore\033[0m")
    else:
        print("\033[32m✔ .gitignore already configured for sia/\033[0m")

    # Set up Claude Code discovery shim
    claude_skills_dir = cwd / ".claude" / "skills" / "sia"
    claude_skills_dir.mkdir(parents=True, exist_ok=True)
    shim_src = PACKAGE_ROOT / "integrations" / "claude-code" / "SKILL.md"
    shim_dest = claude_skills_dir / "SKILL.md"
    if shim_src.exists():
        shutil.copy2(shim_src, shim_dest)
        print("\033[32m✔ Installed Claude Code discovery shim at .claude/skills/sia/SKILL.md\033[0m")

    print("\n\033[1m\033[32mSIA successfully initialized!\033[0m")
    print("Tell your assistant: \033[1m\033[33m\"Read sia/AGENT.md and follow it.\"\033[0m\n")

def main():
    parser = argparse.ArgumentParser(description="SIA Python CLI & Plugin Launcher", add_help=False)
    parser.add_argument("command", nargs="?", default="help", help="Command: init, status, banner, help")
    parser.add_argument("--help", "-h", action="store_true", help="Show help message")
    parser.add_argument("--status", "--check", action="store_true", help="Run status audit")
    args, unknown = parser.parse_known_args()

    cmd = args.command.lower() if args.command else "help"

    if args.help or cmd in ["help", "--help", "-h"]:
        print_help()
    elif args.status or cmd in ["status", "check", "--status", "--check"]:
        print_status_audit()
    elif cmd == "init":
        init_sia()
    elif cmd == "banner":
        print_banner()
    else:
        print_help()

if __name__ == "__main__":
    main()
