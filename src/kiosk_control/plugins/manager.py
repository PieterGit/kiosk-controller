from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from kiosk_control.plugins.base import Plugin, PluginContext


@dataclass
class PluginManager:
    plugins: list[Plugin]

    async def start_all(self, ctx: PluginContext) -> None:
        await asyncio.gather(*(p.start(ctx) for p in self.plugins))

    async def stop_all(self) -> None:
        await asyncio.gather(*(p.stop() for p in self.plugins), return_exceptions=True)

    def screensaver_inhibit(self, facts: dict[str, Any]) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        for p in self.plugins:
            inhibit, reason = p.screensaver_inhibit(facts)
            if inhibit:
                reasons.append(reason or p.name)
        return bool(reasons), reasons
