from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import websockets

from .paths import default_user_data_dir


class CdpError(RuntimeError):
    pass


def parse_devtools_active_port(profile_dir: str | Path) -> str:
    """Return the browser-level CDP websocket URL from DevToolsActivePort."""

    p = Path(profile_dir) / "DevToolsActivePort"
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(lines) < 2:
        raise CdpError("DevToolsActivePort missing endpoint line")

    port = int(lines[0])
    endpoint = lines[1]
    if endpoint.startswith("ws://") or endpoint.startswith("wss://"):
        return endpoint
    if endpoint.startswith("/devtools/"):
        return f"ws://127.0.0.1:{port}{endpoint}"
    if endpoint.startswith("devtools/"):
        return f"ws://127.0.0.1:{port}/{endpoint}"
    # Most builds write a token that is appended to /devtools/browser/<token>
    return f"ws://127.0.0.1:{port}/devtools/browser/{endpoint}"


@dataclass
class _Cmd:
    id: int
    fut: asyncio.Future


class CdpClient:
    def __init__(self, ws_url: str):
        self._ws_url = ws_url
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._next_id = 0
        self._pending: dict[int, asyncio.Future] = {}

    async def connect(self) -> None:
        self._ws = await websockets.connect(self._ws_url, ping_interval=20, ping_timeout=20)
        asyncio.create_task(self._reader())

    async def _reader(self) -> None:
        assert self._ws
        async for raw in self._ws:
            msg = json.loads(raw)
            if "id" in msg and msg["id"] in self._pending:
                fut = self._pending.pop(msg["id"])
                if "error" in msg:
                    fut.set_exception(CdpError(str(msg["error"])))
                else:
                    fut.set_result(msg.get("result"))

    async def call(
        self, method: str, params: dict[str, Any] | None = None, session_id: str | None = None
    ) -> Any:
        self._next_id += 1
        cmd_id = self._next_id
        msg: dict[str, Any] = {"id": cmd_id, "method": method}
        if params:
            msg["params"] = params
        if session_id:
            msg["sessionId"] = session_id

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending[cmd_id] = fut
        assert self._ws
        await self._ws.send(json.dumps(msg))
        return await fut


class ChromiumKiosk:
    """Start Chromium and provide a single controllable page via CDP."""

    def __init__(self, bin_path: str, user_data_dir: str, extra_flags: list[str]):
        self._bin_path = bin_path
        self._user_data_dir = user_data_dir.strip()
        self._extra_flags = extra_flags
        self._proc: subprocess.Popen | None = None
        self._cdp: CdpClient | None = None
        self._session_id: str | None = None

    async def start(self) -> None:
        self._ensure_profile_dir()
        cmd = [self._bin_path, f"--user-data-dir={self._user_data_dir}"] + list(self._extra_flags)
        self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for DevToolsActivePort file.
        dtap = Path(self._user_data_dir) / "DevToolsActivePort"
        for _ in range(200):
            if dtap.exists() and dtap.stat().st_size > 0:
                break
            await asyncio.sleep(0.1)
        if not dtap.exists():
            raise CdpError("DevToolsActivePort was not created")

        ws_url = parse_devtools_active_port(self._user_data_dir)
        self._cdp = CdpClient(ws_url)
        await self._cdp.connect()

        await self._cdp.call("Target.setDiscoverTargets", {"discover": True})
        targets = await self._cdp.call("Target.getTargets")
        page = next((t for t in targets.get("targetInfos", []) if t.get("type") == "page"), None)
        if not page:
            raise CdpError("No page target found")

        attached = await self._cdp.call(
            "Target.attachToTarget", {"targetId": page["targetId"], "flatten": True}
        )
        self._session_id = attached["sessionId"]
        await self._cdp.call("Page.enable", session_id=self._session_id)

    def _ensure_profile_dir(self) -> None:
        """Create Chromium profile directory, with safe fallback for user runs.

        If the configured profile path is not writable (common when config uses
        /var/lib/..), fall back to a user-writable XDG path.
        """

        log = logging.getLogger(__name__)

        p = Path(self._user_data_dir).expanduser()
        if _needs_user_fallback(p):
            fallback = default_user_data_dir()
            log.warning(
                "chromium.user_data_dir is not writable (%s). Falling back to %s",
                p,
                fallback,
            )
            self._user_data_dir = str(fallback)
            p = fallback
        p.mkdir(parents=True, exist_ok=True)


def _needs_user_fallback(profile_dir: Path) -> bool:
    # Root can create /var/lib locations; user services typically cannot.
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return False

    # Find nearest existing parent and test writability.
    parent = profile_dir
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent

    try:
        return not os.access(parent, os.W_OK)
    except Exception:
        return True

    async def navigate(self, url: str) -> None:
        if not self._cdp or not self._session_id:
            raise CdpError("ChromiumKiosk not started")
        await self._cdp.call("Page.navigate", {"url": url}, session_id=self._session_id)

    def terminate(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
