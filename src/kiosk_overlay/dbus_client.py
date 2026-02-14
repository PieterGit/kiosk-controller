from __future__ import annotations

from dataclasses import dataclass

from dbus_next.aio import MessageBus

BUS = "io.github.kiosk_control"
OBJ = "/io/github/kiosk_control"


@dataclass
class KioskDbusClient:
    bus: MessageBus
    iface: object

    @classmethod
    async def connect(cls) -> KioskDbusClient:
        bus = await MessageBus().connect()
        introspection = await bus.introspect(BUS, OBJ)
        obj = bus.get_proxy_object(BUS, OBJ, introspection)
        iface = obj.get_interface(BUS)
        return cls(bus=bus, iface=iface)

    async def set_view(self, view: str) -> None:
        await self.iface.call_set_view(view)

    async def set_auto(self) -> None:
        await self.iface.call_set_auto()

    async def next(self) -> None:
        await self.iface.call_next()

    async def prev(self) -> None:
        await self.iface.call_prev()

    async def wake(self, reason: str = "ui") -> None:
        await self.iface.call_wake(reason)

    async def sleep(self, reason: str = "ui") -> None:
        await self.iface.call_sleep(reason)

    async def power_off(self, reason: str = "ui") -> bool:
        return bool(await self.iface.call_power_off(reason))

    async def close(self) -> None:
        self.bus.disconnect()
