# iPhone → Mac Cursor Prototype

Move your Mac cursor by moving your iPhone. The iPhone streams gyroscope deltas over WebSocket; the Mac applies them with robotjs.

## Projects
- `mac-cursor-server/`: Node.js WebSocket server controlling cursor
- `phone-mouse-expo/`: Expo client streaming motion deltas

## Prerequisites
- macOS with Accessibility permission for your terminal/Node
- Node 18+ (server), Node 20 recommended for Expo
- iPhone with Expo Go app
- Same Wi‑Fi network for both devices

## Setup

### 1) Start the server
```
cd mac-cursor-server
npm install
npm start
```
The server prints local URLs like `ws://192.168.x.x:8080`.

If cursor doesn’t move, enable: System Settings → Privacy & Security → Accessibility → allow your terminal (Terminal/iTerm/Cursor) and Node.

Optional env tuning:
```
PORT=8080 GAIN=1.2 MAX_STEP=60 FRICTION=0.12 DEBUG=1 npm start
```

### 2) Run the Expo client
```
cd ../phone-mouse-expo
npm install
npx expo install expo-sensors
npm start
```
Open in Expo Go on your iPhone.

In the app:
- Enter the server IP and port (from server logs)
- Tap Connect, then Start Streaming

## Troubleshooting
- Ensure phone and Mac are on same subnet (e.g., 192.168.1.*)
- Try disabling VPNs/firewalls
- Verify server logs show client connection
- Toggle `DEBUG=1` on server for detailed logs

## Tuning Notes
- Client maps yaw (z) → horizontal, pitch (x) → vertical (inverted)
- Client clamps per-frame deltas; server applies smoothing and friction
- Adjust client gains in `phone-mouse-expo/App.js`; server gain/friction via env
