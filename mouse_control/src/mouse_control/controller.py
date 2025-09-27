"""Core logic for moving the mouse with keyboard input."""

from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Iterable, Tuple

from pynput import keyboard, mouse


LOGGER = logging.getLogger(__name__)


class MouseControlError(RuntimeError):
    """Raised when mouse control cannot be initialised."""


class MouseController:
    """Listen for WASD key presses and move the mouse accordingly."""

    _DIRECTION_VECTORS: Dict[str, Tuple[int, int]] = {
        "w": (0, -1),
        "a": (-1, 0),
        "s": (0, 1),
        "d": (1, 0),
    }

    def __init__(self, *, step: int = 20, interval: float = 0.04) -> None:
        if step <= 0:
            raise ValueError("step must be a positive integer")
        if interval <= 0:
            raise ValueError("interval must be positive")

        try:
            self._mouse = mouse.Controller()
        except OSError as exc:  # Accessibility permission missing on macOS.
            raise MouseControlError(
                "Unable to access mouse controller. Ensure accessibility permissions are granted."
            ) from exc

        self._listener = keyboard.Listener(
            on_press=self._handle_press, on_release=self._handle_release
        )

        self._step = step
        self._interval = interval
        self._pressed: set[str] = set()
        self._lock = threading.Lock()
        self._movement_thread: threading.Thread | None = None
        self._running = threading.Event()

    def run(self) -> None:
        """Start listening for keyboard events and block until stopped."""

        LOGGER.info(
            "Starting mouse control: step=%s interval=%ss", self._step, self._interval
        )
        self._running.set()
        self._movement_thread = threading.Thread(
            target=self._movement_loop, name="mouse-control-loop", daemon=True
        )
        self._movement_thread.start()

        try:
            with self._listener:
                self._listener.join()
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop listening and movement."""

        if not self._running.is_set():
            return

        LOGGER.info("Stopping mouse control")
        self._running.clear()
        self._listener.stop()
        if self._movement_thread and self._movement_thread.is_alive():
            self._movement_thread.join(timeout=self._interval * 3)

    def _handle_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if key == keyboard.Key.esc:
            LOGGER.info("ESC pressed; shutting down")
            self.stop()
            return

        char = self._normalise_key(key)
        if char is None:
            return

        with self._lock:
            if char not in self._pressed:
                LOGGER.debug("Key down: %s", char)
            self._pressed.add(char)

    def _handle_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        char = self._normalise_key(key)
        if char is None:
            return

        with self._lock:
            if char in self._pressed:
                LOGGER.debug("Key up: %s", char)
            self._pressed.discard(char)

    def _movement_loop(self) -> None:
        while self._running.is_set():
            dx, dy = self._calculate_delta()
            if dx or dy:
                try:
                    self._mouse.move(dx, dy)
                except OSError as exc:
                    LOGGER.error("Mouse move failed: %s", exc)
                    self.stop()
                    return
            time.sleep(self._interval)

    def _calculate_delta(self) -> Tuple[int, int]:
        with self._lock:
            active = list(self._pressed)

        dx = dy = 0
        for key in active:
            vector = self._DIRECTION_VECTORS.get(key)
            if vector:
                vx, vy = vector
                dx += vx
                dy += vy

        if dx == 0 and dy == 0:
            return 0, 0

        return dx * self._step, dy * self._step

    @staticmethod
    def _normalise_key(key: keyboard.Key | keyboard.KeyCode) -> str | None:
        if isinstance(key, keyboard.KeyCode) and key.char:
            return key.char.lower()
        return None


def pressed_keys_to_vector(keys: Iterable[str]) -> Tuple[int, int]:
    """Utility for tests: calculate the resulting movement vector for keys."""

    dx = dy = 0
    for key in keys:
        vector = MouseController._DIRECTION_VECTORS.get(key.lower())
        if not vector:
            continue
        vx, vy = vector
        dx += vx
        dy += vy
    return dx, dy

