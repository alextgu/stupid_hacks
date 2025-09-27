# Phone Mouse (Expo)

Simple Expo app that streams gyroscope-based deltas over WebSocket to move a Mac cursor.

## Setup

```
cd phone-mouse-expo
npm install
npx expo install expo-sensors
```

Make sure your iPhone and Mac are on the same Wi‑Fi network.

## Run

```
npm run ios
# or start the dev server and use Expo Go
npm start
```

In the app:
- Enter your Mac's IP and the server port (default 8080)
- Tap Connect
- Tap Start Streaming

You should see gyro and accel readouts and connection status.

## Notes
- Gyro mapping: yaw (z) -> horizontal, pitch (x) -> vertical (inverted)
- Gains and deadzone are tuned conservatively; tweak in App.js if needed
