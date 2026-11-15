// Serve _site with the Python stdlib server on a free local port (8100-8899).
import { spawn } from 'node:child_process';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function free(port) {
  return new Promise((ok) => {
    const s = net.createServer();
    s.once('error', () => ok(false));
    s.listen(port, '127.0.0.1', () => s.close(() => ok(true)));
  });
}

export async function serve() {
  let port = 0;
  for (let i = 0; i < 50 && !port; i++) {
    const p = 8100 + Math.floor(Math.random() * 800);
    if (await free(p)) port = p;
  }
  if (!port) throw new Error('no free port');
  const proc = spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1', '--directory', path.join(root, '_site')], { stdio: 'ignore' });
  const url = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 50; i++) {
    try { if ((await fetch(url + '/')).ok) break; } catch { /* retry */ }
    await new Promise((r) => setTimeout(r, 100));
  }
  return { url, port, stop: () => proc.kill() };
}
