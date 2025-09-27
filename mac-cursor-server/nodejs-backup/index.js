const WebSocket = require('ws');
const robot = require('robotjs');

const PORT = process.env.PORT ? Number(process.env.PORT) : 8080;

// RobotJS initial config: smooth mouse, high speed to keep up with streaming
robot.setMouseDelay(0);

// Basic gain and smoothing parameters
let gain = process.env.GAIN ? Number(process.env.GAIN) : 1.2; // overall scale
let maxStep = process.env.MAX_STEP ? Number(process.env.MAX_STEP) : 60; // px per frame cap
let friction = process.env.FRICTION ? Number(process.env.FRICTION) : 0.12; // exponential smoothing

// Velocity integrator for smoothing
let vx = 0;
let vy = 0;

// Diagnostics
let msgs = 0;
let lastPos = robot.getMousePos();
setInterval(() => {
  const nowPos = robot.getMousePos();
  const moved = nowPos.x !== lastPos.x || nowPos.y !== lastPos.y;
  if (!moved && msgs > 10) {
    console.warn('[server] No cursor movement detected despite incoming data. Check Accessibility permissions.');
  }
  if (msgs > 0) {
    console.log(`[server] Msgs last 2s: ${msgs}${moved ? '' : ' (no-move)'}`);
  }
  msgs = 0;
  lastPos = nowPos;
}, 2000);

const wss = new WebSocket.Server({ port: PORT });

console.log(`[server] WebSocket listening on ws://0.0.0.0:${PORT}`);
try {
  const os = require('os');
  const nets = os.networkInterfaces();
  const addrs = [];
  Object.values(nets).forEach((ifs) => {
    (ifs || []).forEach((i) => {
      if (i.family === 'IPv4' && !i.internal) addrs.push(i.address);
    });
  });
  if (addrs.length) {
    console.log(`[server] Local IPs: ${addrs.map((a) => `ws://${a}:${PORT}`).join(', ')}`);
  }
} catch {}
console.log('[server] Env tuning: GAIN, MAX_STEP, FRICTION');

wss.on('connection', (ws, req) => {
  const client = `${req.socket.remoteAddress}:${req.socket.remotePort}`;
  console.log(`[server] Client connected: ${client}`);

  ws.on('message', (message) => {
    msgs++;
    try {
      const data = JSON.parse(message.toString());
      if (!data || typeof data.dx !== 'number' || typeof data.dy !== 'number') {
        return;
      }

      // Apply gain and clamp per-frame step
      let dx = data.dx * gain;
      let dy = data.dy * gain;

      const stepMag = Math.hypot(dx, dy);
      if (stepMag > maxStep && stepMag > 0) {
        const scale = maxStep / stepMag;
        dx *= scale;
        dy *= scale;
      }

      // Exponential smoothing on velocity
      vx = vx * (1 - friction) + dx * friction;
      vy = vy * (1 - friction) + dy * friction;

      const pos = robot.getMousePos();
      const nextX = Math.round(pos.x + vx);
      const nextY = Math.round(pos.y + vy);

      robot.moveMouse(nextX, nextY);

      if (process.env.DEBUG === '1') {
        console.log(`[data] dx=${dx.toFixed(2)} dy=${dy.toFixed(2)} | v=(${vx.toFixed(2)}, ${vy.toFixed(2)}) -> (${nextX}, ${nextY})`);
      }
    } catch (e) {
      console.error('[server] Failed to process message:', e);
    }
  });

  ws.on('close', () => {
    console.log(`[server] Client disconnected: ${client}`);
  });
});

// Optional: SELFTEST jiggles the cursor to verify Accessibility permissions
if (process.env.SELFTEST === '1') {
  console.log('[server] SELFTEST enabled: moving cursor slightly every 1s');
  setInterval(() => {
    const pos = robot.getMousePos();
    robot.moveMouse(pos.x + 1, pos.y + 1);
    robot.moveMouse(pos.x, pos.y);
  }, 1000);
}

process.on('SIGINT', () => {
  console.log('\n[server] Shutting down...');
  wss.close();
  process.exit(0);
});


