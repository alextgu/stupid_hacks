"""WebSocket server that applies incoming motion deltas to the mouse pointer."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict
import math

from pynput import mouse
try:
    from websockets.exceptions import ConnectionClosed
    from websockets.server import WebSocketServerProtocol, serve
except ImportError as exc:  # pragma: no cover - optional dependency guard
    raise ImportError(
        "websockets package is required for the mouse_control server. Install via 'pip install websockets'."
    ) from exc

LOGGER = logging.getLogger(__name__)


class MouseServerError(RuntimeError):
    """Raised when the WebSocket mouse server cannot be initialised."""


@dataclass(slots=True)
class MotionEnvelope:
    """Normalised cursor delta payload."""

    dx: float
    dy: float
    raw_east: float
    raw_north: float


class MotionWebSocketServer:
    """Receive JSON deltas over WebSocket and move the system cursor."""

    def __init__(
        self,
        *,
        host: str = "0.0.0.0",
        port: int = 8080,
        gain: float = 1.0,
        max_step: float = 120.0,
        deadzone: float = 0.004,
    ) -> None:
        if port <= 0 or port > 65535:
            raise ValueError("port must be between 1 and 65535")
        if gain <= 0:
            raise ValueError("gain must be positive")
        if max_step <= 0:
            raise ValueError("max_step must be positive")
        if deadzone < 0:
            raise ValueError("deadzone cannot be negative")

        try:
            self._mouse = mouse.Controller()
        except OSError as exc:
            raise MouseServerError(
                "Unable to access mouse controller. Ensure accessibility permissions are granted."
            ) from exc

        self._host = host
        self._port = port
        self._gain = gain
        self._max_step = max_step
        self._deadzone = deadzone

    async def run(self) -> None:
        LOGGER.info("Starting WebSocket server on ws://%s:%s", self._host, self._port)
        async with serve(self._handle_client, self._host, self._port):
            await asyncio.Future()

    async def _handle_client(self, websocket: WebSocketServerProtocol) -> None:
        peer = getattr(websocket, "remote_address", None)
        LOGGER.info("Client connected: %s", peer)
        accum_dx = 0.0
        accum_dy = 0.0
        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": "hello",
                        "message": "mouse_control server ready",
                        "gain": self._gain,
                        "maxStep": self._max_step,
                    }
                )
            )
        except Exception:  # pragma: no cover - send failure is non critical
            LOGGER.debug("Failed to send hello to client", exc_info=True)

        try:
            async for raw in websocket:
                payload = self._parse_message(raw)
                if payload is None:
                    continue
                accum_dx += payload.dx
                accum_dy += payload.dy

                move_dx = int(round(accum_dx))
                move_dy = int(round(accum_dy))

                if move_dx == 0 and move_dy == 0:
                    continue

                accum_dx -= move_dx
                accum_dy -= move_dy

                LOGGER.debug(
                    "Moving cursor by (%s, %s) (raw meters east=%.3f north=%.3f)",
                    move_dx,
                    move_dy,
                    payload.raw_east,
                    payload.raw_north,
                )
                await asyncio.to_thread(self._mouse.move, move_dx, move_dy)
        except ConnectionClosed:
            LOGGER.info("Client disconnected: %s", peer)
        except Exception:  # pragma: no cover - unexpected handler failure
            LOGGER.exception("Unhandled exception while processing client %s", peer)

    def _parse_message(self, raw: Any) -> MotionEnvelope | None:
        data: Dict[str, Any]
        if isinstance(raw, (bytes, bytearray)):
            try:
                raw = raw.decode("utf-8")
            except UnicodeDecodeError:
                LOGGER.debug("Dropping non UTF-8 payload: %s", raw)
                return None

        if isinstance(raw, str):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                LOGGER.debug("Dropping non-JSON payload: %s", raw)
                return None
        elif isinstance(raw, dict):
            data = raw  # websockets won't provide dict, but allow for tests
        else:
            LOGGER.debug("Dropping unsupported payload type: %s", type(raw))
            return None

        try:
            dx_raw = float(data.get("dx", 0.0))
            dy_raw = float(data.get("dy", 0.0))
        except (TypeError, ValueError):
            LOGGER.debug("Payload dx/dy are not numeric: %s", data)
            return None

        raw_meters = data.get("meters") or {}
        raw_east = float(raw_meters.get("east", 0.0)) if isinstance(raw_meters, dict) else 0.0
        raw_north = float(raw_meters.get("north", 0.0)) if isinstance(raw_meters, dict) else 0.0

        dx = self._normalise(dx_raw)
        dy = self._normalise(dy_raw)

        if dx == 0.0 and dy == 0.0:
            return None

        return MotionEnvelope(dx=dx, dy=dy, raw_east=raw_east, raw_north=raw_north)

    def _normalise(self, value: float) -> float:
        if math.isnan(value) or math.isinf(value):
            return 0.0

        if abs(value) < self._deadzone:
            return 0.0

        value *= self._gain
        value = max(-self._max_step, min(self._max_step, value))
        return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a WebSocket server that maps motion deltas to cursor movement",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host/IP to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument(
        "--gain",
        type=float,
        default=1.0,
        help="Multiplier applied to incoming deltas (default: 1.0)",
    )
    parser.add_argument(
        "--max-step",
        type=float,
        default=120.0,
        help="Clamp per-message cursor movement in pixels (default: 120)",
    )
    parser.add_argument(
        "--deadzone",
        type=float,
        default=0.004,
        help="Ignore deltas whose absolute value is below this threshold (default: 0.004)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (-v for info, -vv for debug)",
    )
    return parser


def configure_logging(verbose: int) -> None:
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args.verbose)

    try:
        server = MotionWebSocketServer(
            host=args.host,
            port=args.port,
            gain=args.gain,
            max_step=args.max_step,
            deadzone=args.deadzone,
        )
    except (ValueError, MouseServerError) as exc:
        LOGGER.error("%s", exc)
        return 1

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        LOGGER.info("Interrupted by user")
    return 0


__all__ = ["MotionWebSocketServer", "MotionEnvelope", "MouseServerError", "main"]


