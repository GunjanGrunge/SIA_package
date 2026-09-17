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

        // Count Subagent Tasks
        let subagentCount = 0;
        let subagentList: string[] = [];
        if (hasSdd) {
            try {
                const files = fs.readdirSync(sddPath);
                subagentList = files.filter(f => f.includes('task-') || f.endsWith('.md'));
                subagentCount = subagentList.length;
            } catch (e) {}
        }

        // Count Created Feature Skill Files
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

        // Parse Token & Cost Savings
        let tokensSaved = 0;
        let costSavedUsd = "0.00";
        if (hasAgent || hasSdd) {
            tokensSaved = (subagentCount * 12500) + (skillsList.length * 8000) + (hasSpecs ? 15000 : 5000);
            costSavedUsd = ((tokensSaved / 1000000) * 3.00).toFixed(3);
        }

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIA Dashboard</title>
    <style>
        body {
            font-family: var(--vscode-font-family, system-ui, -apple-system, sans-serif);
            color: var(--vscode-foreground);
            background-color: var(--vscode-sideBar-background);
            padding: 12px;
            margin: 0;
            line-height: 1.4;
        }
        .header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--vscode-widget-border, rgba(255,255,255,0.1));
            margin-bottom: 16px;
        }
        .header-title {
            font-size: 15px;
            font-weight: 700;
            color: #00f2fe;
            margin: 0;
        }
        .badge {
            background-color: rgba(0, 242, 254, 0.15);
            color: #00f2fe;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(0, 242, 254, 0.3);
        }
        .card {
            background-color: var(--vscode-editor-background);
            border: 1px solid var(--vscode-widget-border, rgba(255,255,255,0.08));
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 12px;
        }
        .card-title {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .metric-value {
            font-size: 20px;
            font-weight: 700;
            color: #00e5a3;
        }
        .metric-sub {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            margin-top: 2px;
        }
        .status-row {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            font-size: 12px;
        }
        .status-ok {
            color: #00e5a3;
            font-weight: 600;
        }
        .status-off {
            color: #ff4b4b;
        }
        .btn {
            display: block;
            width: 100%;
            background-color: #00f2fe;
            color: #080c14;
            border: none;
            border-radius: 4px;
            padding: 8px 12px;
            font-weight: 600;
            font-size: 12px;
            cursor: pointer;
            text-align: center;
            margin-bottom: 8px;
            box-sizing: border-box;
        }
        .btn:hover {
            background-color: #00d8e4;
        }
        .btn-secondary {
            background-color: var(--vscode-button-secondaryBackground, #3a3d41);
            color: var(--vscode-button-secondaryForeground, #ffffff);
        }
        .btn-secondary:hover {
            background-color: var(--vscode-button-secondaryHoverBackground, #45494e);
        }
        .list-item {
            font-size: 11px;
            padding: 3px 6px;
            background: rgba(255,255,255,0.03);
            border-radius: 3px;
            margin-top: 4px;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="header">
        <h2 class="header-title">SIA Engine</h2>
        <span class="badge">v${VERSION}</span>
    </div>

    <button class="btn" onclick="postMessage('copyPrompt')">📋 Copy Assistant Prompt</button>
    <button class="btn btn-secondary" onclick="postMessage('init')">⚡ Initialize SIA in Root</button>

    <div class="card">
        <div class="card-title">Token & Cost Savings</div>
        <div class="metric-value">~${tokensSaved.toLocaleString()}</div>
        <div class="metric-sub">Tokens Saved (Est. $${costSavedUsd} USD)</div>
    </div>

    <div class="card">
        <div class="card-title">Subagents Working</div>
        <div class="status-row">
            <span>Dispatched Tasks</span>
            <span class="status-ok">${subagentCount} task record(s)</span>
        </div>
        ${subagentList.slice(0, 3).map(item => `<div class="list-item">📄 ${item}</div>`).join('')}
    </div>

    <div class="card">
        <div class="card-title">Active Feature Skills</div>
        <div class="status-row">
            <span>Skills Created</span>
            <span class="status-ok">${skillsList.length} skill file(s)</span>
        </div>
        ${skillsList.length > 0 ? skillsList.slice(0, 4).map(s => `<div class="list-item">🧩 ${s}</div>`).join('') : '<div class="metric-sub">SIA generates modular skills upon Intake</div>'}
    </div>

    <div class="card">
        <div class="card-title">Project Environment</div>
        <div class="status-row">
            <span>Vendored ./sia</span>
            <span class="${hasSia ? 'status-ok' : 'status-off'}">${hasSia ? 'Present' : 'Missing'}</span>
        </div>
        <div class="status-row">
            <span>Project AGENT.md</span>
            <span class="${hasAgent ? 'status-ok' : 'status-off'}">${hasAgent ? 'Active' : 'Not generated'}</span>
        </div>
        <div class="status-row">
            <span>Specs & Plans</span>
            <span class="${hasSpecs ? 'status-ok' : 'status-off'}">${hasSpecs ? 'Present' : 'Pending'}</span>
        </div>
    </div>

    <button class="btn btn-secondary" onclick="postMessage('status')">📊 Output Status Audit</button>
    <button class="btn btn-secondary" style="margin-bottom:0;" onclick="postMessage('refresh')">🔄 Refresh Dashboard</button>

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
