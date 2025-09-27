# Mac Cursor WebSocket Server

Node.js server that receives `dx, dy` deltas over WebSocket and moves the macOS cursor using `robotjs`.

## Setup

1. Install deps

```bash
cd mac-cursor-server
npm install
```

2. Grant Accessibility permission to Terminal/Node so cursor movement is allowed:
   - System Settings → Privacy & Security → Accessibility → enable your terminal app (Terminal, iTerm, Cursor) and Node if listed.

## Run

```bash
npm start
# or
PORT=8080 GAIN=1.2 MAX_STEP=60 FRICTION=0.12 DEBUG=1 npm start
```

The server listens on `ws://0.0.0.0:8080` by default.

### Env tuning
- `GAIN`: scale multiplier on incoming deltas
- `MAX_STEP`: per-frame clamp on pixels
- `FRICTION`: smoothing factor for velocity integrator (0..1)
- `DEBUG=1`: logs each message with resulting cursor pos


