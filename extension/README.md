# SIA VS Code & Multi-IDE Extension

**Self-Improving Agents (SIA)** native IDE extension for **VS Code**, **Cursor**, **Windsurf**, **Kiro**, and any VSIX-compatible environment.

## 🚀 Features

- **1-Click Project Initialization**: Right-click project root or press `Ctrl+Shift+P` -> `SIA: Initialize SIA in Project Root`.
- **Automatic Shims**: Installs shims for Claude Code (`.claude/skills/sia/`), Cursor (`.cursor/rules/sia.mdc`), and VS Code AI.
- **Clipboard Prompt Copy**: Automatically copies `"Read sia/AGENT.md in full and follow it."` to your clipboard.
- **Live Status Bar Badge**: Displays real-time SIA status, active feature skills, and token savings metrics in the status bar.
- **Status Audit & Banner Output**: View token savings and project health anytime via Command Palette.

## 📦 Installation Options

### Option 1: Install VSIX Package Directly
1. Download `sia-vscode-extension-0.3.0.vsix` from [GitHub Releases](https://github.com/GunjanGrunge/SIA_package/releases).
2. Open **VS Code**, **Cursor**, **Windsurf**, or **Kiro**.
3. Open Extensions view (`Ctrl+Shift+X` / `Cmd+Shift+X`).
4. Click the `...` menu in the top right -> **Install from VSIX...**
5. Select `sia-vscode-extension-0.3.0.vsix`.

### Option 2: CLI Installation
```bash
# For VS Code
code --install-extension sia-vscode-extension-0.3.0.vsix

# For Cursor
cursor --install-extension sia-vscode-extension-0.3.0.vsix

# For Windsurf
windsurf --install-extension sia-vscode-extension-0.3.0.vsix
```

## 🎮 Available Commands

- `SIA: Initialize SIA in Project Root` (`sia.init`)
- `SIA: Run Status Audit & Token Savings` (`sia.status`)
- `SIA: Copy Assistant Prompt to Clipboard` (`sia.copyPrompt`)
- `SIA: Display Terminal Launch Banner` (`sia.banner`)
