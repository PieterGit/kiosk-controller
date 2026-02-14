from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from kiosk_control.plugins.base import Plugin, PluginContext


@dataclass(frozen=True)
class NightscoutConfig:
    base_url: str
    access_token: str
    collections: list[str]
    stale_seconds: int


def mgdl_to_mmol(mgdl: float) -> float:
    return mgdl / 18.0


class NightscoutV3SocketPlugin(Plugin):
    name = "nightscout"

    def __init__(self, cfg: NightscoutConfig):
        self._cfg = cfg
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._ctx: PluginContext | None = None

    async def start(self, ctx: PluginContext) -> None:
        self._ctx = ctx
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    def _apply_entry_doc(self, doc: dict[str, Any]) -> None:
        if not self._ctx:
            return
        sgv = doc.get("sgv")
        if sgv is None:
            return
        try:
            sgv_f = float(sgv)
        except Exception:
            return
        self._ctx.set_fact("nightscout.sgv_mgdl", sgv_f)
        self._ctx.set_fact("nightscout.sgv_mmol", mgdl_to_mmol(sgv_f))
        self._ctx.set_fact("nightscout.direction", str(doc.get("direction") or ""))
        self._ctx.set_fact("nightscout.date", doc.get("date") or doc.get("dateString"))
        self._ctx.set_fact("nightscout.last_update_ts", time.time())
        self._ctx.set_fact("nightscout.stale", False)

    async def _watch_stale(self) -> None:
        assert self._ctx
        while not self._stop.is_set():
            last = float(self._ctx.facts.get("nightscout.last_update_ts", 0.0) or 0.0)
            stale = (time.time() - last) > self._cfg.stale_seconds if last else True
            self._ctx.set_fact("nightscout.stale", stale)
            await asyncio.sleep(5)

    async def _run(self) -> None:
        try:
            import socketio  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("python-socketio is required for nightscout plugin") from e

        assert self._ctx
        self._ctx.set_fact("nightscout.connected", False)
        stale_task = asyncio.create_task(self._watch_stale())

        sio = socketio.AsyncClient(reconnection=True, reconnection_attempts=0)
        ns = "/storage"

        @sio.event(namespace=ns)
        async def connect() -> None:  # noqa: ANN001
            self._ctx.set_fact("nightscout.connected", True)
            await sio.emit(
                "subscribe",
                {"accessToken": self._cfg.access_token, "collections": self._cfg.collections},
                namespace=ns,
            )

        @sio.event(namespace=ns)
        async def disconnect() -> None:  # noqa: ANN001
            self._ctx.set_fact("nightscout.connected", False)

        async def on_storage_event(data: dict[str, Any]) -> None:
            if str(data.get("colName")) != "entries":
                return
            doc = data.get("doc")
            if isinstance(doc, dict):
                self._apply_entry_doc(doc)

        sio.on("create", handler=on_storage_event, namespace=ns)
        sio.on("update", handler=on_storage_event, namespace=ns)

        # Per Nightscout APIv3 docs, use base URL without /api/v3, connect to /storage namespace.
        await sio.connect(self._cfg.base_url, namespaces=[ns])

        try:
            while not self._stop.is_set():
                await asyncio.sleep(0.5)
        finally:
            stale_task.cancel()
            with suppress(asyncio.CancelledError):
                await stale_task
            await sio.disconnect()

    def screensaver_inhibit(self, facts: dict[str, Any]) -> tuple[bool, str]:
        if facts.get("nightscout.alert"):
            return True, "nightscout.alert"
        return False, ""
