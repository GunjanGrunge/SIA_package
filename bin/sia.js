#!/usr/bin/env node
/** Compatibility launcher for the canonical Python `sia-package` runtime. */
const { spawnSync } = require('child_process');

const args = ['-m', 'sia', ...process.argv.slice(2)];
const candidates = process.platform === 'win32' ? ['python', 'py'] : ['python3', 'python'];
let lastError = null;

for (const executable of candidates) {
  const result = spawnSync(executable, args, { stdio: 'inherit' });
  if (!result.error) {
    process.exit(result.status === null ? 1 : result.status);
  }
  lastError = result.error;
}

console.error('SIA requires Python and `python -m pip install "git+https://github.com/GunjanGrunge/SIA_package"`.');
if (lastError) console.error(lastError.message);
process.exit(1);
