import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

const VERSION = "0.3.0";
const PROMPT_TEXT = 'Read sia/AGENT.md in full and follow it.';

let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    console.log('[SIA Extension] Activated across Multi-IDE workspace (VS Code / Cursor / Windsurf / Kiro).');

    // Create Status Bar Item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'sia.status';
    statusBarItem.text = `$(symbol-event) SIA: Active`;
    statusBarItem.tooltip = `SIA v${VERSION} (Click for authoritative CLI orchestration status)`;
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

        const hasSia = fs.existsSync(path.join(rootPath, '.sia'));
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

        const formattedTokens = hasSia ? "CLI ledger" : "—";
        const costStatus = hasSia ? "actual / calc / est" : "—";

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIA Control Center</title>
    <style>
        :root {
            --bg-color: #0c1017;
            --card-bg: #121824;
            --card-border: rgba(255, 255, 255, 0.08);
            --cyan-accent: #38bdf8;
            --purple-accent: #c084fc;
            --green-accent: #34d399;
            --text-main: #f3f4f6;
            --text-sub: #9ca3af;
            --text-muted: #6b7280;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--vscode-sideBar-background, var(--bg-color));
            color: var(--vscode-foreground, var(--text-main));
            padding: 16px 14px;
            font-size: 13px;
            line-height: 1.4;
            -webkit-font-smoothing: antialiased;
        }

        /* Top Header Area */
        .header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 20px;
        }

        .brand-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .sia-logo-svg {
            width: 44px;
            height: 32px;
            flex-shrink: 0;
        }

        .header-titles {
            display: flex;
            flex-direction: column;
        }

        .engine-title {
            font-size: 17px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.2px;
            line-height: 1.2;
        }

        .engine-subtitle {
            font-size: 9.5px;
            font-weight: 700;
            color: #94a3b8;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-top: 1px;
        }

        .engine-motto {
            font-size: 8.5px;
            font-weight: 600;
            color: #64748b;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            margin-top: 2px;
        }

        .version-badge {
            font-size: 10px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            color: #94a3b8;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.12);
            padding: 3px 8px;
            border-radius: 6px;
        }

        /* Primary Action Button */
        .btn-primary-prompt {
            width: 100%;
            background: linear-gradient(135deg, #0284c7 0%, #4f46e5 50%, #7c3aed 100%);
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 11px 16px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35);
            transition: all 0.15s ease;
            margin-bottom: 12px;
        }

        .btn-primary-prompt:hover {
            opacity: 0.95;
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(79, 70, 229, 0.45);
        }

        /* 2-Column Action Cards */
        .action-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 22px;
        }

        .action-card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 10px 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.15s ease;
        }

        .action-card:hover {
            background-color: rgba(255, 255, 255, 0.05);
            border-color: rgba(255, 255, 255, 0.16);
        }

        .action-left {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 500;
            color: var(--text-main);
        }

        .action-arrow {
            color: var(--text-muted);
            font-size: 12px;
        }

        /* Section Dividers */
        .section-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
        }

        .section-title {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            color: #64748b;
            white-space: nowrap;
        }

        .section-line {
            flex-grow: 1;
            height: 1px;
            background-color: var(--card-border);
        }

        .section-icon {
            color: #64748b;
            display: flex;
            align-items: center;
        }

        /* Metrics Cards */
        .metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 22px;
        }

        .metric-card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .metric-icon-box {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .metric-number {
            font-size: 20px;
            font-weight: 700;
            line-height: 1.1;
        }

        .metric-label {
            font-size: 11px;
            color: var(--text-sub);
            margin-top: 2px;
        }

        /* Feature Skills Pills */
        .skills-box {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 22px;
        }

        .skills-wrapper {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }

        .skill-pill {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #e2e8f0;
            font-size: 11px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            padding: 4px 10px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .skill-icon {
            color: #94a3b8;
            display: flex;
            align-items: center;
        }

        /* System Health Panel */
        .health-panel {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 24px;
        }

        .health-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 14px;
            font-size: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }

        .health-row:last-child {
            border-bottom: none;
        }

        .health-left {
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--text-main);
        }

        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }

        .ind-active {
            background-color: var(--green-accent);
            box-shadow: 0 0 8px rgba(52, 211, 153, 0.5);
        }

        .ind-muted {
            background-color: #475569;
        }

        .health-val-active {
            color: var(--green-accent);
            font-weight: 500;
        }

        .health-val-muted {
            color: #64748b;
        }

        /* Footer */
        .footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
            color: #64748b;
            padding-top: 4px;
        }

        .footer-left {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .footer-refresh {
            background: none;
            border: none;
            color: #64748b;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            transition: color 0.15s ease;
        }

        .footer-refresh:hover {
            color: var(--cyan-accent);
        }
    </style>
</head>
<body>
    <!-- Top Header -->
    <div class="header">
        <div class="brand-left">
            <svg class="brand-logo" viewBox="0 0 500 700" style="width: 34px; height: 44px; flex-shrink: 0;">
                <defs>
                    <linearGradient id="siaMarkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#00F2FE"/>
                        <stop offset="50%" stop-color="#007BFF"/>
                        <stop offset="100%" stop-color="#7B2CBF"/>
                    </linearGradient>
                </defs>
                <g fill="url(#siaMarkGrad)">
                    <path d="M 236.8 650.0 L 23.9 501.2 L 71.2 398.0 L 74.4 393.5 L 136.2 443.7 L 119.6 480.3 L 249.3 570.8 L 415.9 446.3 L 416.4 444.7 L 182.0 259.7 L 245.4 214.8 L 476.5 398.4 L 477.1 490.7 L 263.0 650.0 L 236.8 650.0 Z"/>
                    <path d="M 249.3 50.0 L 252.0 50.5 L 464.7 199.1 L 476.3 208.8 L 427.2 314.5 L 425.6 315.3 L 364.2 266.2 L 380.4 228.3 L 250.6 138.0 L 83.5 262.3 L 318.0 449.0 L 254.6 494.0 L 22.9 309.3 L 24.1 216.6 L 249.3 50.0 Z"/>
                </g>
            </svg>
            <div class="header-titles">
                <h1 class="engine-title"><span style="color:#ffffff; font-weight:800; margin-right:4px;">SIA</span> Engine</h1>
                <div class="engine-subtitle">SELF-IMPROVING SYSTEM</div>
                <div class="engine-motto">ASK | VERIFY | PROTECT | IMPROVE</div>
            </div>
        </div>
        <span class="version-badge">v${VERSION}</span>
    </div>

    <!-- Main Copy Prompt CTA -->
    <button class="btn-primary-prompt" onclick="postMessage('copyPrompt')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
        Copy Assistant Prompt
    </button>

    <!-- 2-Column Action Grid -->
    <div class="action-grid">
        <div class="action-card" onclick="postMessage('init')">
            <div class="action-left">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                <span>Init Root</span>
            </div>
            <span class="action-arrow">›</span>
        </div>
        <div class="action-card" onclick="postMessage('status')">
            <div class="action-left">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#c084fc" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                <span>Audit Log</span>
            </div>
            <span class="action-arrow">›</span>
        </div>
    </div>

    <!-- Metrics & Savings -->
    <div class="section-header">
        <span class="section-title">METRICS & SAVINGS</span>
        <div class="section-line"></div>
        <div class="section-icon">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        </div>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-icon-box">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
            </div>
            <div>
                <div class="metric-number" style="color: #38bdf8;">${formattedTokens}</div>
                <div class="metric-label">Token Usage</div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-icon-box">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c084fc" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h.01M18 12h.01"/></svg>
            </div>
            <div>
                <div class="metric-number" style="color: #c084fc;">${costStatus}</div>
                <div class="metric-label">Telemetry Quality</div>
            </div>
        </div>
    </div>

    <!-- Active Feature Skills -->
    <div class="section-header">
        <span class="section-title">ACTIVE FEATURE SKILLS (${skillsList.length})</span>
        <div class="section-line"></div>
        <div class="section-icon">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
        </div>
    </div>

    <div class="skills-box">
        ${skillsList.length > 0 ? `
            <div class="skills-wrapper">
                ${skillsList.slice(0, 8).map(s => `
                    <div class="skill-pill">
                        <span class="skill-icon">
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                        </span>
                        <span>${s}</span>
                    </div>
                `).join('')}
            </div>
        ` : `
            <div style="font-size: 11px; color: var(--text-muted); font-style: italic;">No custom feature skills generated yet. Run SIA Intake.</div>
        `}
    </div>

    <!-- System Health & Gates -->
    <div class="section-header">
        <span class="section-title">SYSTEM HEALTH & GATES</span>
        <div class="section-line"></div>
        <div class="section-icon">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
    </div>

    <div class="health-panel">
        <div class="health-row">
            <div class="health-left">
                <span class="status-indicator ${hasSia ? 'ind-active' : 'ind-muted'}"></span>
                <span>Runtime ./.sia</span>
            </div>
            <span class="${hasSia ? 'health-val-active' : 'health-val-muted'}">${hasSia ? 'Active' : 'Missing'}</span>
        </div>
        <div class="health-row">
            <div class="health-left">
                <span class="status-indicator ${hasAgent ? 'ind-active' : 'ind-muted'}"></span>
                <span>Project AGENT.md</span>
            </div>
            <span class="${hasAgent ? 'health-val-active' : 'health-val-muted'}">${hasAgent ? 'Active' : 'Pending'}</span>
        </div>
        <div class="health-row">
            <div class="health-left">
                <span class="status-indicator ${hasSpecs ? 'ind-active' : 'ind-muted'}"></span>
                <span>Specs & Specs Folders</span>
            </div>
            <span class="${hasSpecs ? 'health-val-active' : 'health-val-muted'}">${hasSpecs ? 'Ready' : 'None'}</span>
        </div>
        <div class="health-row">
            <div class="health-left">
                <span class="status-indicator ${hasSdd ? 'ind-active' : 'ind-muted'}"></span>
                <span>Subagent Dispatches</span>
            </div>
            <span class="${hasSdd ? 'health-val-active' : 'health-val-muted'}">${subagentCount} task(s)</span>
        </div>
    </div>

    <!-- Footer -->
    <div class="footer">
        <div class="footer-left">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
            <span>Host: VS Code / IDE</span>
        </div>
        <button class="footer-refresh" onclick="postMessage('refresh')">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
            Refresh
        </button>
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

async function initSiaWorkspace(_context: vscode.ExtensionContext) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('[SIA] No active workspace folder open. Open a project folder to initialize SIA.');
        return;
    }

    const rootPath = workspaceFolders[0].uri.fsPath;
    try {
        await execFileAsync('python', ['-m', 'sia', '--root', rootPath, 'init', '--mode', 'orchestrator']);
        await vscode.env.clipboard.writeText('Run `sia next --json` and follow the persisted SIA stage.');
        vscode.window.showInformationMessage(
            `[SIA] Persistent runtime v${VERSION} initialized in ${path.basename(rootPath)}. Install host adapters explicitly with the SIA CLI.`
        );
        statusBarItem.text = `$(check) SIA: v${VERSION}`;
    } catch (err: any) {
        vscode.window.showErrorMessage(
            `[SIA Error] Initialization failed. Install sia-package==${VERSION} and run sia init. ${err.message}`
        );
    }
}

async function runSiaStatusAudit() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    const rootPath = workspaceFolders && workspaceFolders.length > 0 ? workspaceFolders[0].uri.fsPath : process.cwd();
    const outputChannel = vscode.window.createOutputChannel('SIA Status Audit');
    outputChannel.clear();
    try {
        const result = await execFileAsync('python', ['-m', 'sia', '--root', rootPath, 'status']);
        outputChannel.appendLine(result.stdout.trim());
    } catch (err: any) {
        outputChannel.appendLine(`SIA status unavailable. Install sia-package==${VERSION} and initialize this workspace.`);
        outputChannel.appendLine(err.message);
    }
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
