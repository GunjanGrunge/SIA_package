"""
SIA (Self-Improving Agents) - Terminal Startup Banner
====================================================
Compact, elegant startup banner in the style of modern developer CLIs (Claude Code).
Features the official Hexagonal Prism 'S' vector mark in Electric Cyan.
"""

import os
import sys
import argparse

# Electric Cyan Color Palette
CYAN = "\033[38;2;0;242;254m"
BOLD_CYAN = "\033[1m\033[38;2;0;242;254m"
DIM = "\033[38;2;120;135;155m"
GREEN = "\033[38;2;0;229;163m"
RESET = "\033[0m"

def is_color_enabled() -> bool:
    return not bool(os.environ.get("NO_COLOR")) and sys.stdout.isatty()

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

def get_claude_code_banner(version="0.1.0-alpha", cwd=None) -> str:
    """Centered compact splash screen in vibrant Electric Cyan (Claude Code style)"""
    if cwd is None:
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]

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
    lines.append(f"      {c}•{r} Loop Engineering : {g}active{r}")
    lines.append(f"      {c}•{r} Security Gate    : {g}armed{r}")
    lines.append(f"      {c}•{r} Human Gates      : {d}questioning & approval{r}")
    lines.append(f"      {c}•{r} Directory        : {d}{cwd}{r}")
    lines.append("")
    return "\n".join(lines)

def get_inline_banner(version="0.1.0-alpha", cwd=None) -> str:
    """Inline side-by-side compact banner in Electric Cyan"""
    if cwd is None:
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]

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
        f"    {c}•{r} loop: {g}active{r}  {d}•{r}  security: {g}armed{r}",
        f"    {c}•{r} cwd: {d}{cwd}{r}",
        "",
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

def print_banner(inline=False, version="0.1.0-alpha"):
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
    parser = argparse.ArgumentParser(description="SIA Terminal Startup Banner")
    parser.add_argument("--inline", action="store_true", help="Display inline side-by-side instead of centered stacked")
    parser.add_argument("--save-txt", type=str, default=None, help="Save plain-text banner to file")
    args = parser.parse_args()

    if args.save_txt:
        os.environ["NO_COLOR"] = "1"
        content = get_inline_banner() if args.inline else get_claude_code_banner()
        # Do NOT call .strip() as it removes the leading indentation of line 1!
        content_clean = content.strip("\r\n") + "\n"
        with open(args.save_txt, "w", encoding="utf-8") as f:
            f.write(content_clean)
        print(f"Saved banner to {args.save_txt}")
    else:
        print_banner(inline=args.inline)

if __name__ == "__main__":
    main()
