# Cross-Platform Cursor WebSocket Server

Python server that receives `dx, dy` deltas over WebSocket and moves the cursor using `pynput` for cross-platform compatibility (Windows, macOS, Linux).

## Setup

1. Install Python dependencies

```bash
cd mac-cursor-server
pip install -r requirements.txt
```

2. Grant system permissions for cursor control:
   - **macOS**: System Settings → Privacy & Security → Accessibility → enable your terminal app (Terminal, iTerm, Cursor) and Python if listed
   - **Linux**: May require running with appropriate permissions or adding user to input group
   - **Windows**: Usually works without additional permissions

## Run

### Option 1: Using the run script (recommended)

```bash
./run.sh
# or with environment variables
DEBUG=1 SELFTEST=1 PORT=8081 ./run.sh
```

### Option 2: Direct Python execution

```bash
python cursor_server.py
# or with environment variables
PORT=8080 GAIN=1.2 MAX_STEP=60 FRICTION=0.12 DEBUG=1 python cursor_server.py
```

The server listens on `ws://0.0.0.0:8080` by default.

### Environment tuning

- `PORT`: WebSocket server port (default: 8080)
- `GAIN`: scale multiplier on incoming deltas (default: 1.2)
- `MAX_STEP`: per-frame clamp on pixels (default: 60)
- `FRICTION`: smoothing factor for velocity integrator 0..1 (default: 0.12)
- `DEBUG=1`: logs each message with resulting cursor pos
- `SELFTEST=1`: jiggles cursor every second to test permissions

## Cross-Platform Compatibility

This Python version works on:

- **Windows** (tested on Windows 10/11)
- **macOS** (tested on macOS 10.14+)
- **Linux** (tested on Ubuntu, should work on most distributions)

## Legacy Node.js Version

The original Node.js version using `robotjs` is available in `index.js` but is Mac-specific and has dependency issues on newer systems.
