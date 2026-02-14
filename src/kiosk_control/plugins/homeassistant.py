from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

import websockets

from kiosk_control.plugins.base import Plugin, PluginContext


@dataclass(frozen=True)
class HomeAssistantConfig:
    ws_url: str
    token: str
    entity_sun: str
    entity_production_w: str
    entity_consumption_w: str
    min_surplus_w: float
    require_sun_above_horizon: bool


def _to_float(val: Any) -> float | None:
    try:
        return float(val)
    except Exception:
        return None


class HomeAssistantWsPlugin(Plugin):
    name = "homeassistant"

    def __init__(self, cfg: HomeAssistantConfig):
        self._cfg = cfg
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._ctx: PluginContext | None = None
        self._msg_id = 0

    async def start(self, ctx: PluginContext) -> None:
        self._ctx = ctx
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    def _update_energy_good(self) -> None:
        assert self._ctx
        prod = _to_float(self._ctx.facts.get("ha.production_w"))
        cons = _to_float(self._ctx.facts.get("ha.consumption_w"))
        sun = str(self._ctx.facts.get("ha.sun_state") or "")

        if prod is None or cons is None:
            self._ctx.set_fact("ha.energy_good", False)
            return

        surplus = prod - cons
        sun_ok = True
        if self._cfg.require_sun_above_horizon:
            sun_ok = sun == "above_horizon"
        self._ctx.set_fact("ha.energy_good", sun_ok and surplus >= self._cfg.min_surplus_w)

    async def _run(self) -> None:
        assert self._ctx
        self._ctx.set_fact("ha.connected", False)
        async with websockets.connect(self._cfg.ws_url, ping_interval=20, ping_timeout=20) as ws:
            # auth_required
            raw = await ws.recv()
            msg = json.loads(raw)
            if msg.get("type") != "auth_required":
                raise RuntimeError("Unexpected HA websocket handshake")

            await ws.send(json.dumps({"type": "auth", "access_token": self._cfg.token}))

            raw = await ws.recv()
            msg = json.loads(raw)
            if msg.get("type") != "auth_ok":
                raise RuntimeError("Home Assistant auth failed")

            self._ctx.set_fact("ha.connected", True)
            self._msg_id += 1
            await ws.send(
                json.dumps(
                    {"id": self._msg_id, "type": "subscribe_events", "event_type": "state_changed"}
                )
            )

            while not self._stop.is_set():
                raw = await ws.recv()
                msg = json.loads(raw)
                if msg.get("type") != "event":
                    continue
                ev = msg.get("event", {})
                if ev.get("event_type") != "state_changed":
                    continue

                data = ev.get("data", {})
                entity = data.get("entity_id")
                new_state = (data.get("new_state") or {}).get("state")

                if entity == self._cfg.entity_sun:
                    self._ctx.set_fact("ha.sun_state", new_state)
                elif entity == self._cfg.entity_production_w:
                    v = _to_float(new_state)
                    if v is not None:
                        self._ctx.set_fact("ha.production_w", v)
                elif entity == self._cfg.entity_consumption_w:
                    v = _to_float(new_state)
                    if v is not None:
                        self._ctx.set_fact("ha.consumption_w", v)
                else:
                    continue

                self._update_energy_good()

    def screensaver_inhibit(self, facts: dict[str, Any]) -> tuple[bool, str]:
        if facts.get("ha.energy_good"):
            return True, "ha.energy_good"
        return False, ""
