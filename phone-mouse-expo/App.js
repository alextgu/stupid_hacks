import { StatusBar } from 'expo-status-bar';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View, TextInput, Button, SafeAreaView, Platform, ScrollView, Switch } from 'react-native';
import { Gyroscope, Accelerometer } from 'expo-sensors';

export default function App() {
  const [address, setAddress] = useState('');
  const [connected, setConnected] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [gyro, setGyro] = useState({ x: 0, y: 0, z: 0 });
  const [accel, setAccel] = useState({ x: 0, y: 0, z: 0 });
  const [sensitivity, setSensitivity] = useState('1.0');
  const [lastDelta, setLastDelta] = useState({ dx: 0, dy: 0 });
  const [debug, setDebug] = useState(false);
  const wsRef = useRef(null);
  const debugRef = useRef(false);
  const gyroRef = useRef({ x: 0, y: 0, z: 0 });

  useEffect(() => {
    debugRef.current = debug;
  }, [debug]);

  // Sensor setup
  useEffect(() => {
    Gyroscope.setUpdateInterval(16); // ~60Hz
    Accelerometer.setUpdateInterval(50); // ~20Hz, optional
    const gsub = Gyroscope.addListener((g) => {
      gyroRef.current = g;
      setGyro(g);
    });
    const asub = Accelerometer.addListener((a) => setAccel(a));
    return () => {
      gsub && gsub.remove();
      asub && asub.remove();
    };
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) {
      try { wsRef.current.close(); } catch { /* noop */ }
      wsRef.current = null;
    }
    if (!address) return;

    const url = address.startsWith('ws://') || address.startsWith('wss://') ? address : `ws://${address}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };
    ws.onclose = () => {
      setConnected(false);
      setStreaming(false);
    };
    ws.onerror = () => {
      setConnected(false);
      setStreaming(false);
    };
    ws.onmessage = (event) => {
      if (!debugRef.current) return;
      try {
        const payload = JSON.parse(event.data);
        console.log('Server message', payload);
      } catch (err) {
        console.log('Server message', event.data);
      }
    };
  }, [address]);

  const disconnect = useCallback(() => {
    setStreaming(false);
    setConnected(false);
    if (wsRef.current) {
      try { wsRef.current.close(); } catch {}
      wsRef.current = null;
    }
  }, []);

  // Motion → delta mapping
  const computeDelta = useCallback((g) => {
    // Use yaw rate (z) to steer horizontal, pitch rate (x) for vertical
    // Normalize and clamp to reduce spikes
    const gainX = 100; // px per rad/s at 60hz → per frame delta
    const gainY = 110;
    const clamp = 80;

    let dx = g.z * gainX * (1 / 60);
    let dy = -g.x * gainY * (1 / 60);

    const dead = 0.01;
    const deadify = (v) => (Math.abs(v) < dead ? 0 : v);
    dx = deadify(dx);
    dy = deadify(dy);

    const sens = Number(sensitivity || '1');
    dx *= sens;
    dy *= sens;

    const mag = Math.hypot(dx, dy);
    if (mag > clamp && mag > 0) {
      const s = clamp / mag;
      dx *= s;
      dy *= s;
    }
    return { dx, dy };
  }, [sensitivity]);

  // Send loop throttled to ~60Hz; we already have 60Hz gyro
  useEffect(() => {
    if (!streaming) return;
    const id = setInterval(() => {
      const { dx, dy } = computeDelta(gyroRef.current);
      setLastDelta({ dx, dy });
      try {
        if (debugRef.current) {
          console.log('Delta', { dx, dy });
        }
        const socket = wsRef.current;
        if (connected && socket?.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ dx, dy, timestamp: Date.now() }));
        }
      } catch (err) {
        console.warn('Failed to handle delta', err);
      }
    }, 16);
    return () => clearInterval(id);
  }, [streaming, connected, computeDelta]);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        try { wsRef.current.close(); } catch { /* noop */ }
      }
    };
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Phone → Mac Cursor</Text>
      <View style={styles.row}>
        <TextInput
          style={styles.input}
          placeholder="Server address (ws://192.168.1.10:8080)"
          value={address}
          onChangeText={setAddress}
          autoCapitalize="none"
          keyboardType="numbers-and-punctuation"
        />
      </View>

      <View style={styles.row}>
        {!connected ? (
          <Button title="Connect" onPress={connect} />
        ) : (
          <Button title="Disconnect" onPress={disconnect} />
        )}
      </View>

      <View style={styles.row}>
        <Button
          title={streaming ? 'Stop Streaming' : 'Start Streaming'}
          onPress={() => setStreaming((s) => !s)}
          disabled={!connected}
        />
      </View>

      <View style={styles.row}>
        <Text style={{ marginRight: 8 }}>Sensitivity</Text>
        <TextInput
          style={[styles.input, { width: 100 }]}
          value={sensitivity}
          onChangeText={setSensitivity}
          keyboardType="decimal-pad"
        />
      </View>

      <View style={styles.row}>
        <Text style={{ marginRight: 8 }}>Debug Log</Text>
        <Switch value={debug} onValueChange={setDebug} />
      </View>

      <ScrollView style={styles.readout}>
        <Text style={[styles.mono, styles.readoutLine]}>Gyro: x={gyro.x.toFixed(3)} y={gyro.y.toFixed(3)} z={gyro.z.toFixed(3)}</Text>
        <Text style={[styles.mono, styles.readoutLine]}>Accel: x={accel.x.toFixed(3)} y={accel.y.toFixed(3)} z={accel.z.toFixed(3)}</Text>
        <Text style={[styles.mono, styles.readoutLine]}>Delta: dx={lastDelta.dx.toFixed(3)} dy={lastDelta.dy.toFixed(3)}</Text>
        <Text style={[styles.mono, styles.readoutLine]}>Status: {connected ? 'Connected' : 'Disconnected'} | {streaming ? 'Streaming' : 'Idle'}</Text>
      </ScrollView>

      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'stretch',
    justifyContent: 'flex-start',
    padding: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: '600',
    marginBottom: 16,
    textAlign: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    backgroundColor: '#fafafa',
  },
  readout: {
    marginTop: 16,
  },
  readoutLine: { marginBottom: 6 },
  mono: {
    fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }),
  },
});
