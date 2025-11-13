"""Serial keypad helper for Mopii-style devices."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class SerialKeypad:
    """Non-blocking reader for a keypad that sends ASCII digits over serial."""

    port: str
    baudrate: int = 9600
    timeout_s: float = 0.0
    encoding: str = "ascii"

    def __post_init__(self) -> None:
        try:
            import serial  # type: ignore
        except ImportError as exc:  # pragma: no cover - runtime environment specific
            raise RuntimeError(
                "pyserial is required for SerialKeypad support. Install it via 'pip install pyserial'."
            ) from exc

        self._serial_module = serial
        self._device = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout_s,
        )
        self._buffer = ""

    def close(self) -> None:
        """Close the underlying serial port."""

        try:
            self._device.close()
        except Exception:
            pass

    def poll(self, allowed_keys: Iterable[str]) -> Optional[str]:
        """Return the first allowed key pressed since the last poll."""

        allowed = set(allowed_keys)
        if not allowed:
            return None
        self._buffer += self._read_all()
        if not self._buffer:
            return None
        for idx, char in enumerate(self._buffer):
            if char in allowed:
                self._buffer = self._buffer[idx + 1 :]
                return char
        # keep buffer trimmed to avoid unbounded growth
        if len(self._buffer) > 128:
            self._buffer = self._buffer[-64:]
        return None

    def wait_for_key(self, allowed_keys: Iterable[str], max_wait: float) -> Optional[str]:
        """Block (with polling) up to ``max_wait`` seconds for one of the allowed keys."""

        deadline = time.monotonic() + max_wait
        while time.monotonic() <= deadline:
            key = self.poll(allowed_keys)
            if key is not None:
                return key
            time.sleep(0.01)
        return None

    def _read_all(self) -> str:
        """Read and decode any bytes currently waiting on the serial buffer."""

        try:
            waiting = self._device.in_waiting
        except Exception:
            waiting = 0
        if not waiting:
            return ""
        try:
            data = self._device.read(waiting)
        except Exception:
            return ""
        if not data:
            return ""
        return data.decode(self.encoding, errors="ignore")


__all__ = ["SerialKeypad"]
