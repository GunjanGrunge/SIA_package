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

    // Register Commands
    const initCmd = vscode.commands.registerCommand('sia.init', async () => {
        await initSiaWorkspace(context);
    });

    const statusCmd = vscode.commands.registerCommand('sia.status', async () => {
        await runSiaStatusAudit();
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

async function initSiaWorkspace(context: vscode.ExtensionContext) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('[SIA] No active workspace folder open. Open a project folder to initialize SIA.');
        return;
    }

    const rootPath = workspaceFolders[0].uri.fsPath;
    const siaTarget = path.join(rootPath, 'sia');

    // Package root (extension bundled location or parent)
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

        // Configure .gitignore
        const gitignorePath = path.join(rootPath, '.gitignore');
        let gitignoreContent = fs.existsSync(gitignorePath) ? fs.readFileSync(gitignorePath, 'utf8') : '';
        if (!gitignoreContent.includes('sia/')) {
            gitignoreContent += '\n# Vendored SIA (Self Improving Agents) tooling\nsia/\n';
            fs.writeFileSync(gitignorePath, gitignoreContent, 'utf8');
        }

        // Install Claude Code discovery shim (.claude/skills/sia/SKILL.md)
        const claudeSkillsDir = path.join(rootPath, '.claude', 'skills', 'sia');
        fs.mkdirSync(claudeSkillsDir, { recursive: true });
        const shimSrc = path.join(repoRoot, 'integrations', 'claude-code', 'SKILL.md');
        if (fs.existsSync(shimSrc)) {
            fs.copyFileSync(shimSrc, path.join(claudeSkillsDir, 'SKILL.md'));
        }

        // Install Cursor discovery rule (.cursor/rules/sia.mdc)
        const cursorRulesDir = path.join(rootPath, '.cursor', 'rules');
        fs.mkdirSync(cursorRulesDir, { recursive: true });
        const cursorRuleContent = `---
description: SIA Self-Improving Agents Project Rule
globs: *
---
Read \`sia/AGENT.md\` in full and follow it.
`;
        fs.writeFileSync(path.join(cursorRulesDir, 'sia.mdc'), cursorRuleContent, 'utf8');

        // Copy prompt to clipboard
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
