import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function spawnPython(args = [], options = {}) {
  const modulePath = path.join(__dirname, '..');
  const venvPython = process.env.PYTHON || 'python3';

  const proc = spawn(venvPython, ['-m', 'mouse_control.server', ...args], {
    cwd: modulePath,
    stdio: 'inherit',
    ...options,
  });

  proc.on('close', (code) => {
    if (code !== 0) {
      console.error(`mouse_control server exited with code ${code}`);
    }
  });

  return proc;
}

export function startServer(argv = []) {
  return spawnPython(argv);
}

export function stopServer(processHandle) {
  if (!processHandle || processHandle.killed) return;
  processHandle.kill();
}

export default {
  startServer,
  stopServer,
};


