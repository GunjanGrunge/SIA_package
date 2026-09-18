"""
SIA (Self-Improving Agents) - Terminal Startup & Status Banner
===============================================================
Compact, elegant startup banner in the style of modern developer CLIs (Claude Code).
Features the official Hexagonal Prism 'S' vector mark in Electric Cyan,
engine detection, working directory verification, and SIA project status audit.
"""

import os
import sys
import argparse
from pathlib import Path

# Electric Cyan Color Palette
CYAN = "\033[38;2;0;242;254m"
BOLD_CYAN = "\033[1m\033[38;2;0;242;254m"
DIM = "\033[38;2;120;135;155m"
GREEN = "\033[38;2;0;229;163m"
YELLOW = "\033[38;2;255;191;0m"
RED = "\033[38;2;255;75;75m"
RESET = "\033[0m"

VERSION = "0.2.0"

def is_color_enabled() -> bool:
    return not bool(os.environ.get("NO_COLOR")) and sys.stdout.isatty()

def detect_host_engine() -> str:
    """Detect active coding assistant host environment/engine"""
    if os.environ.get("CLAUDE_CODE") or os.environ.get("CLAUDE_CODE_ENTRY"):
        return "Claude Code (Terminal)"
    elif os.environ.get("ANTIGRAVITY_IDE") or "antigravity" in sys.executable.lower():
        return "Antigravity IDE"
    elif os.environ.get("CODEX_CLI") or os.environ.get("CODEX_SESSION"):
        return "Codex CLI"
    elif "cursor" in os.environ.get("PATH", "").lower():
        return "Cursor / Host Agent"
    else:
        return "Generic Host Engine (Claude/Codex/Antigravity)"

def verify_working_directory() -> tuple[str, bool]:
    """Verify if execution directory is inside target project root or hidden workingtree"""
    cwd = os.getcwd()
    is_workingtree = ".claude/workingtree" in cwd.replace("\\", "/") or "scratch/" in cwd.replace("\\", "/")
    return cwd, not is_workingtree

# Official High-Definition Hexagonal Prism 'S' Vector Mark
HEX_PRISM_MARK = [
    "         ⣠⣴⣶⣄       ",
    "      ⢀⣴⣾⣿⣿⣿⣿⣿⣦⣄    ",
    "    ⣠⣾⣿⣿⡿⠋⠁ ⠙⠿⣿⣿⣷⣦⡀  ",
    "  ⣴⣿⣿⣿⠟⠉ ⢀⣠⣄  ⠈⠛⣿⣿⣿⡗ ",
    "  ⣿⣿⣯⡀  ⠐⢿⣿⣿⣷⣤⡀⠐⢿⣿⡟ ",
    "  ⠙⢿⣿⣿⣷⣄  ⠈⠻⣿⣿⣿⣦⣀⠉   ",
    "    ⠙⠻⣿⣿⣷⣦⡀  ⠙⢿⣿⣿⣷⣄⡀ ",
    "   ⢠⣷⣄⠈⠻⢿⣿⣿⣶⣄  ⠉⠻⣿⣿⣿ ",
    "  ⢠⣿⣿⣿⠃  ⠙⠿⡿⠟⠁ ⢀⣤⣾⣿⣿ ",
    "  ⠘⠻⣿⣿⣿⣦⣄    ⣠⣶⣿⣿⡿⠛⠁ ",
    "     ⠙⠿⣿⣿⣷⣦⣴⣾⣿⣿⠟⠋     ",
    "       ⠈⠛⢿⣿⣿⡿⠋⠁      "
]

def get_claude_code_banner(version=VERSION, cwd=None) -> str:
    """Centered compact splash screen in vibrant Electric Cyan (Claude Code style)"""
    if cwd is None:
        cwd, is_valid_root = verify_working_directory()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]

    engine = detect_host_engine()
    c = BOLD_CYAN if is_color_enabled() else ""
    cyan_reg = CYAN if is_color_enabled() else ""
    d = DIM if is_color_enabled() else ""
    g = GREEN if is_color_enabled() else ""
    r = RESET if is_color_enabled() else ""

    lines = [""]
    for row in HEX_PRISM_MARK:
        lines.append(f"        {c}{row}{r}")

    lines.append("")
    lines.append(f"              {c}SIA{r} {d}v{version}{r}")
    lines.append(f"         {cyan_reg}Self-Improving Agents{r}")
    lines.append("")
    lines.append(f"      {c}•{r} Engine           : {g}{engine}{r}")
    lines.append(f"      {c}•{r} Loop Engineering : {g}active{r}")
    lines.append(f"      {c}•{r} Security Gate    : {g}armed{r}")
    lines.append(f"      {c}•{r} Human Gates      : {d}questioning & approval{r}")
    lines.append(f"      {c}•{r} Directory        : {d}{cwd}{r}")
    lines.append("")
    return "\n".join(lines)

def get_inline_banner(version=VERSION, cwd=None) -> str:
    """Inline side-by-side compact banner in Electric Cyan"""
    if cwd is None:
        cwd, is_valid_root = verify_working_directory()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]

    engine = detect_host_engine()
    c = BOLD_CYAN if is_color_enabled() else ""
    cyan_reg = CYAN if is_color_enabled() else ""
    d = DIM if is_color_enabled() else ""
    g = GREEN if is_color_enabled() else ""
    r = RESET if is_color_enabled() else ""

    side_text = [
        "",
        "",
        f"    {c}SIA{r} {d}v{version}{r}",
        f"    {cyan_reg}Self-Improving Agents{r}",
        "",
        f"    {c}•{r} engine: {g}{engine}{r}",
        f"    {c}•{r} loop: {g}active{r}  {d}•{r}  security: {g}armed{r}",
        f"    {c}•{r} cwd: {d}{cwd}{r}",
        "",
        "",
        "",
        ""
    ]

    lines = [""]
    for i in range(len(HEX_PRISM_MARK)):
        l = f"{c}{HEX_PRISM_MARK[i]}{r}"
        s = side_text[i]
        lines.append(f"  {l}{s}")
    lines.append("")
    return "\n".join(lines)

def print_status_audit():
    """Print comprehensive SIA project status, modular skills, and token savings"""
    c = BOLD_CYAN if is_color_enabled() else ""
    d = DIM if is_color_enabled() else ""
    g = GREEN if is_color_enabled() else ""
    y = YELLOW if is_color_enabled() else ""
    r = RESET if is_color_enabled() else ""

    cwd, is_root_valid = verify_working_directory()
    engine = detect_host_engine()

    print(f"\n{c}=== SIA Status & Project Audit ==={r}")
    print(f"SIA Version   : {g}{VERSION}{r}")
    print(f"Host Engine   : {g}{engine}{r}")
    print(f"Working Dir   : {d}{cwd}{r} {'[' + g + 'OK: Project Root' + r + ']' if is_root_valid else '[' + y + 'WARN: Isolated Sandbox' + r + ']'}")

    # Check for project AGENT.md
    agent_file = Path("AGENT.md")
    if agent_file.exists():
        print(f"Project AGENT : {g}Present ({agent_file.stat().st_size} bytes){r}")
    else:
        print(f"Project AGENT : {y}Not generated yet (Run SIA Intake){r}")

    # Inspect skills directory
    skills_dir = Path("skills")
    modular_skills = list(skills_dir.glob("*/SKILL.md")) if skills_dir.exists() else []
    print(f"Modular Skills: {g}{len(modular_skills)} active feature skill(s){r}")
    for s in modular_skills:
        print(f"  - {d}{s}{r}")

    # Inspect SDD records
    sdd_dir = Path("sdd")
    if sdd_dir.exists():
        progress_file = sdd_dir / "progress.md"
        manifest_file = sdd_dir / "skill-manifest.md"
        print(f"Execution Gate: {g}SDD records active{r}")
        if progress_file.exists():
            print(f"Progress Log   : {d}{progress_file}{r}")
        if manifest_file.exists():
            print(f"Skill Manifest : {d}{manifest_file}{r}")
    else:
        print(f"Execution Gate: {d}No active plan execution in sdd/{r}")

    print(f"Token Accounting: {g}Active (Tracking Tokens Used & Baseline Context Savings){r}")
    print(f"{c}===================================={r}\n")

def print_banner(inline=False, version=VERSION):
    """Main API function to print the banner to stdout"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if inline:
        print(get_inline_banner(version=version))
    else:
        print(get_claude_code_banner(version=version))

def main():
    parser = argparse.ArgumentParser(description="SIA Terminal Startup Banner & Status Audit")
    parser.add_argument("--inline", action="store_true", help="Display inline side-by-side instead of centered stacked")
    parser.add_argument("--status", "--check", action="store_true", help="Print current SIA project status, modular skills & token savings")
    parser.add_argument("--save-txt", type=str, default=None, help="Save plain-text banner to file")
    args = parser.parse_args()

    if args.status:
        print_status_audit()
        return

    if args.save_txt:
        os.environ["NO_COLOR"] = "1"
        content = get_inline_banner() if args.inline else get_claude_code_banner()
        content_clean = content.strip("\r\n") + "\n"
        # Replace actual directory with <current project directory> placeholder for release distribution
        cwd, _ = verify_working_directory()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        content_clean = content_clean.replace(cwd, "<current project directory>")
        with open(args.save_txt, "w", encoding="utf-8") as f:
            f.write(content_clean)
        print(f"Saved banner to {args.save_txt}")
    else:
        print_banner(inline=args.inline)

if __name__ == "__main__":
    main()
