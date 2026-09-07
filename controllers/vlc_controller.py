"""VLC HTTP controller using VLC's own hotkey actions.

The gesture layer never simulates keyboard input. It asks VLC's HTTP/Lua
interface to execute the same internal actions that VLC binds to its hotkeys.
This makes volume and long jumps follow the user's actual VLC hotkey/jump-size
settings instead of duplicating them in Python.
"""
from __future__ import annotations

import base64
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from requests.exceptions import RequestException

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class VLCStatus:
    connected: bool
    state: str = "unknown"
    volume: int = 0
    time_seconds: float = 0.0
    length_seconds: float = 0.0


class VLCController:
    """Reliable VLC Lua-HTTP controller with optional auto-start."""

    STATUS_PATH = "/requests/status.json"

    # Values accepted by VLC's HTTP `key` command. These map to VLC's
    # internal key-* actions, not to OS-level keyboard injection.
    HOTKEY_ACTIONS = {
        "volume_up": "vol-up",
        "volume_down": "vol-down",
        "long_forward": "jump+long",
        "long_backward": "jump-long",
    }

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4000,
        password: str = "vlc123",
        timeout: float = 1.5,
        reconnect_interval: float = 2.0,
        executable: str | Path | None = r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        auto_start: bool = True,
        startup_timeout: float = 8.0,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.password = password
        self.timeout = float(timeout)
        self.reconnect_interval = float(reconnect_interval)
        self.executable = Path(executable) if executable else None
        self.auto_start = bool(auto_start)
        self.startup_timeout = float(startup_timeout)

        self.base_url = f"http://{self.host}:{self.port}"
        self.status_url = f"{self.base_url}{self.STATUS_PATH}"

        self._session = requests.Session()
        token = base64.b64encode(f":{self.password}".encode()).decode()
        self._session.headers.update(
            {
                "Authorization": f"Basic {token}",
                "User-Agent": "Gesture-VLC-Controller/Final",
            }
        )

        self._connected = False
        self._last_connection_attempt = 0.0
        self._process: subprocess.Popen[str] | None = None
        self._last_status = VLCStatus(False)
        self._last_error: str | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def connect(self, force: bool = False) -> bool:
        now = time.monotonic()
        if not force and now - self._last_connection_attempt < self.reconnect_interval:
            return self._connected

        self._last_connection_attempt = now
        if self._probe():
            return True

        if self.auto_start and self.executable and self.executable.exists():
            if self._process is None or self._process.poll() is not None:
                self._start_vlc()

            deadline = time.monotonic() + self.startup_timeout
            while time.monotonic() < deadline:
                if self._probe():
                    return True
                time.sleep(0.15)

        self._connected = False
        return False

    def reconnect(self) -> bool:
        return self.connect(force=True)

    def _probe(self) -> bool:
        try:
            response = self._session.get(self.status_url, timeout=self.timeout)
            if response.status_code == 401:
                self._last_error = "VLC authentication failed"
                self._connected = False
                return False
            response.raise_for_status()
            self._last_status = self._parse_status(response.json())
            self._connected = True
            self._last_error = None
            return True
        except (RequestException, ValueError) as exc:
            self._last_error = str(exc)
            self._connected = False
            return False

    def _start_vlc(self) -> None:
        if not self.executable:
            return

        command = [
            str(self.executable),
            "--extraintf=http",
            "--http-host=127.0.0.1",
            f"--http-port={self.port}",
            f"--http-password={self.password}",
        ]

        LOGGER.info("Starting VLC: %s", self.executable)
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError as exc:
            self._process = None
            self._last_error = str(exc)
            LOGGER.error("Failed to start VLC: %s", exc)

    def _command(self, command: str, **params: Any) -> bool:
        params = dict(params)
        params["command"] = command

        try:
            response = self._session.get(
                self.status_url,
                params=params,
                timeout=self.timeout,
            )
            if response.status_code == 401:
                self._connected = False
                self._last_error = "VLC authentication failed"
                LOGGER.error("VLC authentication failed.")
                return False

            response.raise_for_status()

            try:
                self._last_status = self._parse_status(response.json())
            except ValueError:
                pass

            self._connected = True
            self._last_error = None
            LOGGER.info(
                "VLC HTTP COMMAND SUCCESS: %s params=%s",
                command,
                params,
            )
            return True

        except RequestException as exc:
            self._connected = False
            self._last_error = str(exc)
            LOGGER.error(
                "VLC HTTP COMMAND FAILED: %s | %s",
                command,
                exc,
            )
            return False

    def _hotkey(self, action_name: str) -> bool:
        val = self.HOTKEY_ACTIONS[action_name]
        # VLC's Lua interface maps `command=key&val=...` to its internal
        # key-* action. requests performs the required URL encoding, including
        # encoding '+' as %2B for jump+long.
        return self._command("key", val=val)

    # --- Basic playback ---
    def play(self) -> bool:
        return self._command("pl_play")

    def pause(self) -> bool:
        return self._command("pl_pause")

    def stop(self) -> bool:
        return self._command("pl_stop")

    def next_track(self) -> bool:
        return self._command("pl_next")

    def previous_track(self) -> bool:
        return self._command("pl_previous")

    # --- VLC-native hotkey actions ---
    def volume_up(self) -> bool:
        """Run VLC's configured Volume up action."""
        return self._hotkey("volume_up")

    def volume_down(self) -> bool:
        """Run VLC's configured Volume down action."""
        return self._hotkey("volume_down")

    def long_forward(self) -> bool:
        """Run VLC's configured Long forward jump action."""
        return self._hotkey("long_forward")

    def long_backward(self) -> bool:
        """Run VLC's configured Long backwards jump action."""
        return self._hotkey("long_backward")

    # Backward-compatible names for the previous state-machine API.
    def seek_forward(self, seconds: int = 10) -> bool:
        return self.long_forward()

    def seek_backward(self, seconds: int = 10) -> bool:
        return self.long_backward()

    def get_status(self) -> VLCStatus:
        try:
            response = self._session.get(self.status_url, timeout=self.timeout)
            response.raise_for_status()
            status = self._parse_status(response.json())
            self._last_status = status
            self._connected = True
            self._last_error = None
            return status
        except (RequestException, ValueError) as exc:
            self._connected = False
            self._last_error = str(exc)
            return VLCStatus(False)

    @staticmethod
    def _parse_status(data: dict[str, Any]) -> VLCStatus:
        try:
            volume = int(data.get("volume", 0))
        except (TypeError, ValueError):
            volume = 0

        try:
            current_time = float(data.get("time", 0.0))
        except (TypeError, ValueError):
            current_time = 0.0

        try:
            length = float(data.get("length", 0.0))
        except (TypeError, ValueError):
            length = 0.0

        return VLCStatus(
            connected=True,
            state=str(data.get("state", "unknown")),
            volume=volume,
            time_seconds=current_time,
            length_seconds=length,
        )

    def close(self) -> None:
        self._session.close()
