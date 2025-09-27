import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export function startServer(args = []) {
  const python = process.env.PYTHON || 'python3';
  const projectRoot = path.join(__dirname, '..');
  const proc = spawn(python, ['-m', 'mouse_control.server', ...args], {
    cwd: projectRoot,
    stdio: 'inherit',
  });
  proc.on('exit', (code, signal) => {
    if (code && code !== 0) {
      console.error(`mouse_control.server exited with code ${code}`);
    } else if (signal) {
      console.warn(`mouse_control.server terminated via signal ${signal}`);
    }
  });
  return proc;
}

export function stopServer(proc) {
  if (!proc || proc.killed) return;
  proc.kill();
}

export default { startServer, stopServer };


