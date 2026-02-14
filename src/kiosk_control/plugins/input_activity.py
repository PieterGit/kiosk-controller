from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from kiosk_control.plugins.base import Plugin, PluginContext


@dataclass(frozen=True)
class InputActivityConfig:
    device_hint: str | None


class InputActivityPlugin(Plugin):
    name = "input_activity"

    def __init__(self, cfg: InputActivityConfig):
        self._cfg = cfg
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self, ctx: PluginContext) -> None:
        try:
            import evdev  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("evdev is required for input_activity plugin") from e

        def match(dev: Any) -> bool:
            if not self._cfg.device_hint:
                return True
            ident = f"{dev.name} {dev.phys} {dev.path}".lower()
            return self._cfg.device_hint.lower() in ident

        devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
        chosen = next((d for d in devices if match(d)), None)
        if not chosen:
            raise RuntimeError("No input device matched device_hint")

        async def loop() -> None:
            ctx.set_fact("activity.last_ts", time.time())
            async for _ in chosen.async_read_loop():
                ctx.set_fact("activity.last_ts", time.time())
                if self._stop.is_set():
                    break

        self._task = asyncio.create_task(loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
