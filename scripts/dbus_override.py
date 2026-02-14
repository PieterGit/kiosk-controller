#!/usr/bin/env python3
"""Small helper for manual overrides via the controller's D-Bus API."""

import argparse
import asyncio

from dbus_next.aio import MessageBus

BUS = "io.github.kiosk_control"
OBJ = "/io/github/kiosk_control"


async def call(method: str, arg: str | None) -> None:
    bus = await MessageBus().connect()
    introspection = await bus.introspect(BUS, OBJ)
    obj = bus.get_proxy_object(BUS, OBJ, introspection)
    iface = obj.get_interface(BUS)

    if method == "set-view":
        assert arg
        await iface.call_set_view(arg)
    elif method == "auto":
        await iface.call_set_auto()
    elif method == "next":
        await iface.call_next()
    elif method == "prev":
        await iface.call_prev()
    elif method == "wake":
        await iface.call_wake("cli")
    elif method == "sleep":
        await iface.call_sleep("cli")
    elif method == "poweroff":
        await iface.call_power_off("cli")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "cmd",
        choices=["set-view", "auto", "next", "prev", "wake", "sleep", "poweroff"],
    )
    ap.add_argument("arg", nargs="?")
    args = ap.parse_args()
    asyncio.run(call(args.cmd, args.arg))


if __name__ == "__main__":
    main()
