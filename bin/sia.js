#!/usr/bin/env node
/**
 * SIA (Self-Improving Agents) - Node.js CLI & Plugin Launcher
 * ==========================================================
 * Provides `npx sia-agent init`, `npx sia-agent status`, and CLI tooling.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const VERSION = "0.2.0-alpha.1";
const PACKAGE_ROOT = path.resolve(__dirname, '..');

function printHelp() {
  console.log(`
\x1b[1m\x1b[38;2;0;242;254mSIA (Self-Improving Agents) CLI v${VERSION}\x1b[0m

\x1b[36mUsage:\x1b[0m
  npx sia-agent init       Initialize SIA in current project (vendors sia/ & sets up discovery shims)
  npx sia-agent status     Run SIA project audit, check active skills & token savings
  npx sia-agent banner     Display terminal launch banner
  npx sia-agent --help     Show this help guide

\x1b[36mQuickstart:\x1b[0m
  1. Run \x1b[32mnpx sia-agent init\x1b[0m inside your target project directory.
  2. Tell your assistant: \x1b[33m"Read sia/AGENT.md and follow it."\x1b[0m
  3. Verify status anytime with \x1b[32mnpx sia-agent status\x1b[0m.
`);
}

function initSia() {
  const cwd = process.cwd();
  const siaTarget = path.join(cwd, 'sia');
  const bannerPy = fs.existsSync(path.join(PACKAGE_ROOT, 'banner.py')) ? path.join(PACKAGE_ROOT, 'banner.py') : null;
  if (bannerPy) {
    try { execSync(`python "${bannerPy}"`, { stdio: 'inherit' }); } catch (e) {
      try { execSync(`python3 "${bannerPy}"`, { stdio: 'inherit' }); } catch (e2) {}
    }
  }

  console.log(`\x1b[36m[SIA]\x1b[0m Initializing SIA v${VERSION} in project root: \x1b[33m${cwd}\x1b[0m`);

  // Copy SIA files to target ./sia if not already inside package repo
  if (path.resolve(cwd) !== PACKAGE_ROOT) {
    if (!fs.existsSync(siaTarget)) {
      fs.mkdirSync(siaTarget, { recursive: true });
    }

    const itemsToCopy = ['AGENT.md', 'BANNER.txt', 'CHANGELOG.md', 'INSTALL.md', 'README.md', 'USAGE.md', 'VALIDATION.md', 'banner.py', 'capture-interface.md', 'guides', 'integrations'];
    for (const item of itemsToCopy) {
      const src = path.join(PACKAGE_ROOT, item);
      const dest = path.join(siaTarget, item);
      if (fs.existsSync(src)) {
        fs.cpSync(src, dest, { recursive: true });
      }
    }
    console.log(`\x1b[32m✔ Vendored SIA files copied to ./sia/\x1b[0m`);
  } else {
    console.log(`\x1b[32m✔ Currently in SIA package repository root.\x1b[0m`);
  }

  // Update .gitignore
  const gitignorePath = path.join(cwd, '.gitignore');
  let gitignoreContent = fs.existsSync(gitignorePath) ? fs.readFileSync(gitignorePath, 'utf8') : '';
  if (!gitignoreContent.includes('sia/')) {
    gitignoreContent += '\n# Vendored SIA (Self Improving Agents) tooling\nsia/\n';
    fs.writeFileSync(gitignorePath, gitignoreContent, 'utf8');
    console.log(`\x1b[32m✔ Added sia/ to .gitignore\x1b[0m`);
  } else {
    console.log(`\x1b[32m✔ .gitignore already configured for sia/\x1b[0m`);
  }

  // Set up Claude Code discovery shim
  const claudeSkillsDir = path.join(cwd, '.claude', 'skills', 'sia');
  if (!fs.existsSync(claudeSkillsDir)) {
    fs.mkdirSync(claudeSkillsDir, { recursive: true });
  }
  const shimSrc = path.join(PACKAGE_ROOT, 'integrations', 'claude-code', 'SKILL.md');
  const shimDest = path.join(claudeSkillsDir, 'SKILL.md');
  if (fs.existsSync(shimSrc)) {
    fs.copyFileSync(shimSrc, shimDest);
    console.log(`\x1b[32m✔ Installed Claude Code discovery shim at .claude/skills/sia/SKILL.md\x1b[0m`);
  }

  console.log(`\n\x1b[1m\x1b[32mSIA successfully initialized!\x1b[0m`);
  console.log(`Tell your assistant: \x1b[1m\x1b[33m"Read sia/AGENT.md and follow it."\x1b[0m\n`);
}

function runStatus() {
  const cwd = process.cwd();
  const bannerPy = fs.existsSync(path.join(cwd, 'sia', 'banner.py')) 
    ? path.join(cwd, 'sia', 'banner.py') 
    : path.join(PACKAGE_ROOT, 'banner.py');

  try {
    execSync(`python "${bannerPy}" --status`, { stdio: 'inherit' });
  } catch (err) {
    try {
      execSync(`python3 "${bannerPy}" --status`, { stdio: 'inherit' });
    } catch (err3) {
      console.log(`\n\x1b[1m\x1b[36m=== SIA Status Audit ===\x1b[0m`);
      console.log(`Version    : ${VERSION}`);
      console.log(`Directory  : ${cwd}`);
      console.log(`AGENT.md   : ${fs.existsSync(path.join(cwd, 'AGENT.md')) ? 'Present' : 'Not generated yet'}`);
      console.log(`========================\n`);
    }
  }
}

function main() {
  const args = process.argv.slice(2);
  const command = args[0] ? args[0].toLowerCase() : 'help';

  switch (command) {
    case 'init':
      initSia();
      break;
    case 'status':
    case 'check':
    case '--status':
    case '--check':
      runStatus();
      break;
    case 'banner':
      runStatus();
      break;
    case 'help':
    case '--help':
    case '-h':
    default:
      printHelp();
      break;
  }
}

main();
