from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method

# dbus-next uses signature strings ("s", "b") in annotations.
# Ruff tries to treat these as Python types.


BUS_NAME = "io.github.kiosk_control"
OBJ_PATH = "/io/github/kiosk_control"


@dataclass(frozen=True)
class Callbacks:
    set_view: Callable[[str], None]
    set_auto: Callable[[], None]
    next_view: Callable[[], None]
    prev_view: Callable[[], None]
    wake: Callable[[str], None]
    sleep: Callable[[str], None]
    power_off: Callable[[str], bool]


class KioskInterface(ServiceInterface):
    def __init__(self, cb: Callbacks):
        super().__init__(BUS_NAME)
        self._cb = cb

    @method()
    def SetView(self, view: "s") -> "b":  # noqa: N802
        self._cb.set_view(view)
        return True

    @method()
    def SetAuto(self) -> "b":  # noqa: N802
        self._cb.set_auto()
        return True

    @method()
    def Next(self) -> "b":  # noqa: N802
        self._cb.next_view()
        return True

    @method()
    def Prev(self) -> "b":  # noqa: N802
        self._cb.prev_view()
        return True

    @method()
    def Wake(self, reason: "s") -> "b":  # noqa: N802
        self._cb.wake(reason)
        return True

    @method()
    def Sleep(self, reason: "s") -> "b":  # noqa: N802
        self._cb.sleep(reason)
        return True

    @method()
    def PowerOff(self, reason: "s") -> "b":  # noqa: N802
        return bool(self._cb.power_off(reason))


async def serve(iface: KioskInterface) -> MessageBus:
    bus = await MessageBus().connect()
    bus.export(OBJ_PATH, iface)
    await bus.request_name(BUS_NAME)
    return bus
