from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass
class PluginContext:
    facts: dict[str, Any]

    def set_fact(self, key: str, value: Any) -> None:
        self.facts[key] = value


class Plugin(abc.ABC):
    """A plugin produces facts and can inhibit screensaver."""

    name: str

    @abc.abstractmethod
    async def start(self, ctx: PluginContext) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        return None

    def screensaver_inhibit(self, facts: dict[str, Any]) -> tuple[bool, str]:
        return False, ""
