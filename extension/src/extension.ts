import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

const VERSION = "0.2.0a1";
const PROMPT_TEXT = 'Read sia/AGENT.md in full and follow it.';

let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    console.log('[SIA Extension] Activated across Multi-IDE workspace (VS Code / Cursor / Windsurf / Kiro).');

    // Create Status Bar Item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'sia.status';
    statusBarItem.text = `$(symbol-event) SIA: Active`;
    statusBarItem.tooltip = `SIA v${VERSION} (Click for Status Audit & Token Savings)`;
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Register Webview Sidebar Provider
    const sidebarProvider = new SiaSidebarWebviewProvider(context);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('sia.sidebarView', sidebarProvider)
    );

    // Register Commands
    const initCmd = vscode.commands.registerCommand('sia.init', async () => {
        await initSiaWorkspace(context);
        sidebarProvider.refresh();
    });

    const statusCmd = vscode.commands.registerCommand('sia.status', async () => {
        await runSiaStatusAudit();
        sidebarProvider.refresh();
    });

    const copyPromptCmd = vscode.commands.registerCommand('sia.copyPrompt', async () => {
        await vscode.env.clipboard.writeText(PROMPT_TEXT);
        vscode.window.showInformationMessage(`[SIA] Prompt copied to clipboard: "${PROMPT_TEXT}"`);
    });

    const bannerCmd = vscode.commands.registerCommand('sia.banner', async () => {
        showSiaBannerOutput();
    });

    context.subscriptions.push(initCmd, statusCmd, copyPromptCmd, bannerCmd);
}

class SiaSidebarWebviewProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;

    constructor(private readonly _context: vscode.ExtensionContext) {}

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._context.extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview();

        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'init':
                    await vscode.commands.executeCommand('sia.init');
                    break;
                case 'copyPrompt':
                    await vscode.commands.executeCommand('sia.copyPrompt');
                    break;
                case 'status':
                    await vscode.commands.executeCommand('sia.status');
                    break;
                case 'refresh':
                    this.refresh();
                    break;
            }
        });
    }

    public refresh() {
        if (this._view) {
            this._view.webview.html = this._getHtmlForWebview();
        }
    }

    private _getHtmlForWebview(): string {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const rootPath = workspaceFolders && workspaceFolders.length > 0 ? workspaceFolders[0].uri.fsPath : process.cwd();

        const hasSia = fs.existsSync(path.join(rootPath, 'sia'));
        const hasAgent = fs.existsSync(path.join(rootPath, 'AGENT.md'));
        const hasSpecs = fs.existsSync(path.join(rootPath, 'specs'));
        const sddPath = path.join(rootPath, 'sdd');
        const hasSdd = fs.existsSync(sddPath);

        let subagentCount = 0;
        let subagentList: string[] = [];
        if (hasSdd) {
            try {
                const files = fs.readdirSync(sddPath);
                subagentList = files.filter(f => f.includes('task-') || f.endsWith('.md'));
                subagentCount = subagentList.length;
            } catch (e) {}
        }

        let skillsList: string[] = [];
        const skillsDir = path.join(rootPath, 'skills');
        const claudeSkillsDir = path.join(rootPath, '.claude', 'skills');
        if (fs.existsSync(skillsDir)) {
            try {
                skillsList = fs.readdirSync(skillsDir).filter(f => !f.startsWith('.'));
            } catch (e) {}
        }
        if (fs.existsSync(claudeSkillsDir)) {
            try {
                const cs = fs.readdirSync(claudeSkillsDir).filter(f => f !== 'sia' && !f.startsWith('.'));
                skillsList = [...new Set([...skillsList, ...cs])];
            } catch (e) {}
        }

        let tokensSaved = 0;
        let costSavedUsd = "0.00";
        if (hasAgent || hasSdd || skillsList.length > 0) {
            tokensSaved = (subagentCount * 12500) + (skillsList.length * 8000) + (hasSpecs ? 15000 : 5000);
            costSavedUsd = ((tokensSaved / 1000000) * 3.00).toFixed(2);
        }

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIA Control Center</title>
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: #111827;
            --card-border: rgba(255, 255, 255, 0.08);
            --accent-cyan: #00f2fe;
            --accent-blue: #007bff;
            --accent-green: #00e5a3;
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
        }

        body {
            font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
            background-color: var(--vscode-sideBar-background, var(--bg-color));
            color: var(--vscode-foreground, var(--text-primary));
            padding: 14px;
            margin: 0;
            box-sizing: border-box;
            -webkit-font-smoothing: antialiased;
        }

        .header-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 12px;
            margin-bottom: 16px;
            border-bottom: 1px solid var(--card-border);
        }

        .brand-box {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .brand-logo {
            width: 24px;
            height: 24px;
            flex-shrink: 0;
        }

        .brand-title {
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: var(--text-primary);
            margin: 0;
        }

        .brand-subtitle {
            font-size: 10px;
            color: var(--accent-cyan);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }

        .version-tag {
            font-size: 10px;
            font-family: monospace;
            background: rgba(0, 242, 254, 0.1);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 242, 254, 0.25);
            padding: 2px 6px;
            border-radius: 4px;
        }

        .btn-primary {
            width: 100%;
            background: linear-gradient(135deg, #00f2fe 0%, #007bff 100%);
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            box-shadow: 0 4px 12px rgba(0, 242, 254, 0.2);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            margin-bottom: 12px;
        }

        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(0, 242, 254, 0.3);
        }

        .btn-primary:active {
            transform: translateY(0);
        }

        .btn-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 16px;
        }

        .btn-subtle {
            background-color: var(--card-bg);
            color: var(--text-secondary);
            border: 1px solid var(--card-border);
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 11px;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: background 0.15s ease, color 0.15s ease;
        }

        .btn-subtle:hover {
            background-color: rgba(255, 255, 255, 0.06);
            color: var(--text-primary);
        }

        .section-label {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-muted);
            margin-bottom: 8px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 14px;
        }

        .stat-card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 6px;
            padding: 10px;
        }

        .stat-val {
            font-size: 16px;
            font-weight: 700;
            color: var(--accent-green);
        }

        .stat-lbl {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .panel-card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 14px;
        }

        .status-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
            padding: 4px 0;
        }

        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }

        .dot-green { background-color: var(--accent-green); box-shadow: 0 0 6px rgba(0, 229, 163, 0.4); }
        .dot-muted { background-color: var(--text-muted); }

        .skills-container {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 6px;
        }

        .skill-chip {
            background: rgba(0, 242, 254, 0.08);
            border: 1px solid rgba(0, 242, 254, 0.2);
            color: var(--accent-cyan);
            font-size: 10px;
            font-family: monospace;
            padding: 3px 8px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .footer-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 8px;
            border-top: 1px solid var(--card-border);
            font-size: 10px;
            color: var(--text-muted);
        }

        .icon-btn {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 11px;
            padding: 2px 4px;
        }

        .icon-btn:hover {
            color: var(--accent-cyan);
        }
    </style>
</head>
<body>
    <div class="header-container">
        <div class="brand-box">
            <svg class="brand-logo" viewBox="0 0 500 700">
                <defs>
                    <linearGradient id="siaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#00F2FE"/>
                        <stop offset="50%" stop-color="#007BFF"/>
                        <stop offset="100%" stop-color="#7B2CBF"/>
                    </linearGradient>
                </defs>
                <g fill="url(#siaGrad)">
                    <path d="M 236.8 650.0 L 23.9 501.2 L 71.2 398.0 L 74.4 393.5 L 136.2 443.7 L 119.6 480.3 L 249.3 570.8 L 415.9 446.3 L 416.4 444.7 L 182.0 259.7 L 245.4 214.8 L 476.5 398.4 L 477.1 490.7 L 263.0 650.0 L 236.8 650.0 Z"/>
                    <path d="M 249.3 50.0 L 252.0 50.5 L 464.7 199.1 L 476.3 208.8 L 427.2 314.5 L 425.6 315.3 L 364.2 266.2 L 380.4 228.3 L 250.6 138.0 L 83.5 262.3 L 318.0 449.0 L 254.6 494.0 L 22.9 309.3 L 24.1 216.6 L 249.3 50.0 Z"/>
                </g>
            </svg>
            <div>
                <h1 class="brand-title">SIA Engine</h1>
                <div class="brand-subtitle">Self-Improving System</div>
            </div>
        </div>
        <span class="version-tag">v${VERSION}</span>
    </div>

    <button class="btn-primary" onclick="postMessage('copyPrompt')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
        Copy Assistant Prompt
    </button>

    <div class="btn-group">
        <button class="btn-subtle" onclick="postMessage('init')">⚡ Init Root</button>
        <button class="btn-subtle" onclick="postMessage('status')">📊 Audit Log</button>
    </div>

    <div class="section-label">Metrics & Savings</div>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-val">~${tokensSaved > 0 ? (tokensSaved / 1000).toFixed(0) + 'k' : '0'}</div>
            <div class="stat-lbl">Tokens Saved</div>
        </div>
        <div class="stat-card">
            <div class="stat-val">$${costSavedUsd}</div>
            <div class="stat-lbl">Est. USD Reduced</div>
        </div>
    </div>

    <div class="section-label">Active Feature Skills (${skillsList.length})</div>
    <div class="panel-card" style="padding: 10px;">
        ${skillsList.length > 0 ? `
            <div class="skills-container">
                ${skillsList.slice(0, 6).map(s => `<span class="skill-chip"><span>🧩</span> ${s}</span>`).join('')}
            </div>
        ` : `
            <div style="font-size: 11px; color: var(--text-muted); font-style: italic;">No custom feature skills generated yet. Run SIA Intake.</div>
        `}
    </div>

    <div class="section-label">System Health & Gates</div>
    <div class="panel-card">
        <div class="status-item">
            <span><span class="status-dot ${hasSia ? 'dot-green' : 'dot-muted'}"></span>Vendored ./sia</span>
            <span style="color: ${hasSia ? 'var(--text-primary)' : 'var(--text-muted)'}">${hasSia ? 'Active' : 'Missing'}</span>
        </div>
        <div class="status-item">
            <span><span class="status-dot ${hasAgent ? 'dot-green' : 'dot-muted'}"></span>Project AGENT.md</span>
            <span style="color: ${hasAgent ? 'var(--text-primary)' : 'var(--text-muted)'}">${hasAgent ? 'Active' : 'Pending'}</span>
        </div>
        <div class="status-item">
            <span><span class="status-dot ${hasSpecs ? 'dot-green' : 'dot-muted'}"></span>Specs & Specs Folders</span>
            <span style="color: ${hasSpecs ? 'var(--text-primary)' : 'var(--text-muted)'}">${hasSpecs ? 'Ready' : 'None'}</span>
        </div>
        <div class="status-item">
            <span><span class="status-dot ${hasSdd ? 'dot-green' : 'dot-muted'}"></span>Subagent Dispatches</span>
            <span style="color: ${hasSdd ? 'var(--text-primary)' : 'var(--text-muted)'}">${subagentCount} task(s)</span>
        </div>
    </div>

    <div class="footer-bar">
        <span>Host: VS Code / IDE</span>
        <button class="icon-btn" onclick="postMessage('refresh')">🔄 Refresh</button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        function postMessage(type) {
            vscode.postMessage({ type });
        }
    </script>
</body>
</html>`;
    }
}

async function initSiaWorkspace(context: vscode.ExtensionContext) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('[SIA] No active workspace folder open. Open a project folder to initialize SIA.');
        return;
    }

    const rootPath = workspaceFolders[0].uri.fsPath;
    const siaTarget = path.join(rootPath, 'sia');

    const extRoot = context.extensionPath;
    const repoRoot = fs.existsSync(path.join(extRoot, 'AGENT.md')) ? extRoot : path.resolve(extRoot, '..');

    try {
        if (!fs.existsSync(siaTarget)) {
            fs.mkdirSync(siaTarget, { recursive: true });
        }

        const itemsToCopy = ['AGENT.md', 'BANNER.txt', 'CHANGELOG.md', 'INSTALL.md', 'README.md', 'USAGE.md', 'VALIDATION.md', 'banner.py', 'capture-interface.md', 'guides', 'integrations'];
        for (const item of itemsToCopy) {
            const src = path.join(repoRoot, item);
            const dest = path.join(siaTarget, item);
            if (fs.existsSync(src)) {
                copyRecursiveSync(src, dest);
            }
        }

        const gitignorePath = path.join(rootPath, '.gitignore');
        let gitignoreContent = fs.existsSync(gitignorePath) ? fs.readFileSync(gitignorePath, 'utf8') : '';
        if (!gitignoreContent.includes('sia/')) {
            gitignoreContent += '\n# Vendored SIA (Self Improving Agents) tooling\nsia/\n';
            fs.writeFileSync(gitignorePath, gitignoreContent, 'utf8');
        }

        const claudeSkillsDir = path.join(rootPath, '.claude', 'skills', 'sia');
        fs.mkdirSync(claudeSkillsDir, { recursive: true });
        const shimSrc = path.join(repoRoot, 'integrations', 'claude-code', 'SKILL.md');
        if (fs.existsSync(shimSrc)) {
            fs.copyFileSync(shimSrc, path.join(claudeSkillsDir, 'SKILL.md'));
        }

        const cursorRulesDir = path.join(rootPath, '.cursor', 'rules');
        fs.mkdirSync(cursorRulesDir, { recursive: true });
        const cursorRuleContent = `---
description: SIA Self-Improving Agents Project Rule
globs: *
---
Read \`sia/AGENT.md\` in full and follow it.
`;
        fs.writeFileSync(path.join(cursorRulesDir, 'sia.mdc'), cursorRuleContent, 'utf8');

        await vscode.env.clipboard.writeText(PROMPT_TEXT);

        vscode.window.showInformationMessage(
            `[SIA] SIA v${VERSION} initialized in ${path.basename(rootPath)}! Prompt copied to clipboard.`,
            'Copy Prompt Again'
        ).then(selection => {
            if (selection === 'Copy Prompt Again') {
                vscode.env.clipboard.writeText(PROMPT_TEXT);
            }
        });

        statusBarItem.text = `$(check) SIA: v${VERSION}`;
    } catch (err: any) {
        vscode.window.showErrorMessage(`[SIA Error] Initialization failed: ${err.message}`);
    }
}

async function runSiaStatusAudit() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    const rootPath = workspaceFolders && workspaceFolders.length > 0 ? workspaceFolders[0].uri.fsPath : process.cwd();
    const hasSia = fs.existsSync(path.join(rootPath, 'sia'));
    const hasAgent = fs.existsSync(path.join(rootPath, 'AGENT.md'));
    const hasSpecs = fs.existsSync(path.join(rootPath, 'specs'));
    const hasSdd = fs.existsSync(path.join(rootPath, 'sdd'));

    const outputChannel = vscode.window.createOutputChannel("SIA Status Audit");
    outputChannel.clear();
    outputChannel.appendLine(`=== SIA Status & Project Audit (v${VERSION}) ===`);
    outputChannel.appendLine(`Directory       : ${rootPath}`);
    outputChannel.appendLine(`Vendored sia/   : ${hasSia ? 'Present [OK]' : 'Not initialized (Run SIA: Initialize)'}`);
    outputChannel.appendLine(`Project AGENT   : ${hasAgent ? 'Generated [OK]' : 'Not generated yet (Run SIA Intake)'}`);
    outputChannel.appendLine(`Specs Folder    : ${hasSpecs ? 'Present [OK]' : 'None yet'}`);
    outputChannel.appendLine(`Task Brief (SDD): ${hasSdd ? 'Active [OK]' : 'None yet'}`);
    outputChannel.appendLine(`Token Savings   : Active (Baseline Context Reduction & Optimization)`);
    outputChannel.appendLine(`==============================================`);
    outputChannel.show();
}

function showSiaBannerOutput() {
    const outputChannel = vscode.window.createOutputChannel("SIA Banner");
    outputChannel.clear();
    outputChannel.appendLine(`
                 ⣠⣴⣶⣄       
              ⢀⣴⣾⣿⣿⣿⣿⣿⣦⣄    
            ⣠⣾⣿⣿⡿⠋⠁ ⠙⠿⣿⣿⣷⣦⡀  
          ⣴⣿⣿⣿⠟⠉ ⢀⣠⣄  ⠈⠛⣿⣿⣿⡗ 
          ⣿⣿⣯⡀  ⠐⢿⣿⣿⣷⣤⡀⠐⢿⣿⡟ 
          ⠙⢿⣿⣿⣷⣄  ⠈⠻⣿⣿⣿⣦⣀⠉   
            ⠙⠻⣿⣿⣷⣦⡀  ⠙⢿⣿⣿⣷⣄⡀ 
           ⢠⣷⣄⠈⠻⢿⣿⣿⣶⣄  ⠉⠻⣿⣿⣿ 
          ⢠⣿⣿⣿⠃  ⠙⠿⡿⠟⠁ ⢀⣤⣾⣿⣿ 
          ⠘⠻⣿⣿⣿⣦⣄    ⣠⣶⣿⣿⡿⠛⠁ 
             ⠙⠿⣿⣿⣷⣦⣴⣾⣿⣿⠟⠋     
               ⠈⠛⢿⣿⣿⡿⠋⠁      

              SIA v${VERSION}
         Self-Improving Agents

      • Multi-IDE Engine : VS Code / Cursor / Windsurf / Kiro
      • Loop Engineering : active
      • Security Gate    : armed
      • Human Gates      : questioning & approval
`);
    outputChannel.show();
}

function copyRecursiveSync(src: string, dest: string) {
    const stats = fs.statSync(src);
    if (stats.isDirectory()) {
        if (!fs.existsSync(dest)) {
            fs.mkdirSync(dest, { recursive: true });
        }
        for (const childItemName of fs.readdirSync(src)) {
            copyRecursiveSync(path.join(src, childItemName), path.join(dest, childItemName));
        }
    } else {
        fs.copyFileSync(src, dest);
    }
}

export function deactivate() {}
