import asyncio
import json
import os
import socket
import time

import websockets
from pynput.mouse import Controller


PORT = int(os.environ.get("PORT", "8080"))
GAIN = float(os.environ.get("GAIN", "1.2"))
MAX_STEP = float(os.environ.get("MAX_STEP", "60"))
FRICTION = float(os.environ.get("FRICTION", "0.12"))
DEBUG = os.environ.get("DEBUG", "0") == "1"
SELFTEST = os.environ.get("SELFTEST", "0") == "1"

mouse = Controller()


def get_local_ips() -> list[str]:
    ips: list[str] = []
    for iface_name in socket.if_nameindex():
        try:
            for fam, _, _, _, sockaddr in socket.getaddrinfo(None, 0, proto=socket.IPPROTO_TCP):
                pass  # placeholder to satisfy type checkers
        except Exception:
            pass
    # Fallback: iterate network interfaces via getaddrinfo on hostname
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None):
            if info[0] == socket.AF_INET:
                addr = info[4][0]
                if not addr.startswith("127."):
                    ips.append(addr)
    except Exception:
        pass
    return sorted(set(ips))


class Velocity:
    def __init__(self) -> None:
        self.vx = 0.0
        self.vy = 0.0

    def step(self, dx: float, dy: float) -> tuple[float, float]:
        # scale and clamp per-frame
        dx *= GAIN
        dy *= GAIN
        mag = (dx * dx + dy * dy) ** 0.5
        if mag > 0 and mag > MAX_STEP:
            s = MAX_STEP / mag
            dx *= s
            dy *= s

        # exponential smoothing
        self.vx = self.vx * (1.0 - FRICTION) + dx * FRICTION
        self.vy = self.vy * (1.0 - FRICTION) + dy * FRICTION
        return self.vx, self.vy


msgs_last_window = 0
last_move_time = time.time()


async def handler(ws: websockets.WebSocketServerProtocol):
    global msgs_last_window, last_move_time
    client = f"{ws.remote_address}"
    print(f"[py-server] Client connected: {client}")
    vel = Velocity()
    try:
        async for message in ws:
            msgs_last_window += 1
            try:
                data = json.loads(message)
            except Exception:
                continue
            dx = data.get("dx")
            dy = data.get("dy")
            if not isinstance(dx, (int, float)) or not isinstance(dy, (int, float)):
                continue
            vx, vy = vel.step(float(dx), float(dy))
            try:
                pos = mouse.position
                nx = int(round(pos[0] + vx))
                ny = int(round(pos[1] + vy))
                mouse.position = (nx, ny)
                last_move_time = time.time()
                if DEBUG:
                    print(f"[data] dx={dx:.2f} dy={dy:.2f} v=({vx:.2f},{vy:.2f}) -> ({nx},{ny})")
            except Exception as e:
                print("[py-server] Move failed:", e)
    finally:
        print(f"[py-server] Client disconnected: {client}")


async def diag_task():
    global msgs_last_window
    while True:
        await asyncio.sleep(2)
        moved_recently = (time.time() - last_move_time) < 2.0
        if msgs_last_window > 0:
            print(f"[py-server] Msgs last 2s: {msgs_last_window}{'' if moved_recently else ' (no-move)'}")
        if msgs_last_window > 10 and not moved_recently:
            print("[py-server] No cursor movement detected despite incoming data. Check Accessibility permissions (System Settings → Privacy & Security → Accessibility).")
        msgs_last_window = 0


async def selftest_task():
    if not SELFTEST:
        return
    print("[py-server] SELFTEST enabled: moving cursor slightly every 1s")
    while True:
        try:
            x, y = mouse.position
            mouse.position = (x + 1, y + 1)
            mouse.position = (x, y)
        except Exception as e:
            print("[py-server] SELFTEST move failed:", e)
        await asyncio.sleep(1)


async def main():
    ips = get_local_ips()
    print(f"[py-server] WebSocket listening on ws://0.0.0.0:{PORT}")
    if ips:
        print("[py-server] Local IPs:", ", ".join([f"ws://{ip}:{PORT}" for ip in ips]))
    print("[py-server] Env tuning: GAIN, MAX_STEP, FRICTION")

    server = await websockets.serve(handler, "0.0.0.0", PORT, max_size=None)
    try:
        await asyncio.gather(diag_task(), selftest_task(), server.wait_closed())
    finally:
        server.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[py-server] Shutting down...")


