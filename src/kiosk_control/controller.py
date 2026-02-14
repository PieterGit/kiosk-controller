from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kiosk_control.cdp import ChromiumKiosk
from kiosk_control.dbus_service import Callbacks, KioskInterface, serve
from kiosk_control.plugins.base import PluginContext
from kiosk_control.plugins.homeassistant import HomeAssistantConfig, HomeAssistantWsPlugin
from kiosk_control.plugins.input_activity import InputActivityConfig, InputActivityPlugin
from kiosk_control.plugins.manager import PluginManager
from kiosk_control.plugins.nightscout import NightscoutConfig, NightscoutV3SocketPlugin
from kiosk_control.policy import Decision, PolicyConfig, RuntimeState, derive_alert, evaluate
from kiosk_control.system.backlight import Backlight
from kiosk_control.system.power import PowerConfig, normalize_poweroff_command, request_poweroff


@dataclass
class Controller:
    cfg: dict[str, Any]

    def __post_init__(self) -> None:
        self.facts: dict[str, Any] = {}
        self.state = RuntimeState()
        self._current_view: str | None = None
        self._screen_on = True
        self._forced_sleep = False

        self._policy_cfg = PolicyConfig(
            idle_off_seconds=int(self.cfg["policy"]["idle_off_seconds"]),
            manual_timeout_seconds=int(self.cfg["policy"]["manual_timeout_seconds"]),
            hypo_threshold_mmol=float(self.cfg["policy"]["hypo_threshold_mmol"]),
            trending_guard_mmol=float(self.cfg["policy"]["trending_guard_mmol"]),
            falling_directions=set(self.cfg["policy"].get("falling_directions", [])),
        )

        backlight_dir = Path(self.cfg["screen"]["backlight_sysfs"])
        self._backlight = Backlight(backlight_dir)

        self._power_cfg = PowerConfig(
            poweroff_command=normalize_poweroff_command(
                self.cfg.get("system", {}).get("poweroff_command")
            )
        )

        chromium = self.cfg["chromium"]
        self._chromium = ChromiumKiosk(
            bin_path=str(chromium["bin"]),
            user_data_dir=str(chromium["user_data_dir"]),
            extra_flags=[str(x) for x in chromium.get("extra_flags", [])],
        )

        self._views: dict[str, str] = {k: str(v) for k, v in self.cfg["views"].items()}
        self._playlist: list[dict[str, Any]] = list(self.cfg["playlist"])

        self._plugins = self._build_plugins(self.cfg.get("plugins", {}))
        self._pm = PluginManager(self._plugins)

        self._bus = None

    def _build_plugins(self, plugins_cfg: dict[str, Any]) -> list[Any]:
        out: list[Any] = []

        ia = plugins_cfg.get("input_activity", {})
        if ia.get("enabled"):
            out.append(InputActivityPlugin(InputActivityConfig(device_hint=ia.get("device_hint"))))

        ha = plugins_cfg.get("homeassistant", {})
        if ha.get("enabled"):
            out.append(
                HomeAssistantWsPlugin(
                    HomeAssistantConfig(
                        ws_url=str(ha["ws_url"]),
                        token=str(ha["token"]),
                        entity_sun=str(ha["entity_sun"]),
                        entity_production_w=str(ha["entity_production_w"]),
                        entity_consumption_w=str(ha["entity_consumption_w"]),
                        min_surplus_w=float(ha.get("min_surplus_w", 0)),
                        require_sun_above_horizon=bool(ha.get("require_sun_above_horizon", True)),
                    )
                )
            )

        ns = plugins_cfg.get("nightscout", {})
        if ns.get("enabled"):
            out.append(
                NightscoutV3SocketPlugin(
                    NightscoutConfig(
                        base_url=str(ns["base_url"]),
                        access_token=str(ns["access_token"]),
                        collections=[str(x) for x in ns.get("collections", ["entries"])],
                        stale_seconds=int(ns.get("stale_seconds", 900)),
                    )
                )
            )

        return out

    def set_view(self, view: str) -> None:
        if view not in self._views:
            return
        self._forced_sleep = False
        self.state.manual_view = view
        self.state.manual_until_ts = time.time() + self._policy_cfg.manual_timeout_seconds

    def set_auto(self) -> None:
        self.state.manual_view = None
        self.state.manual_until_ts = 0.0

    def next_view(self) -> None:
        self._forced_sleep = False
        self.state.playlist_index = (self.state.playlist_index + 1) % len(self._playlist)
        self.set_view(str(self._playlist[self.state.playlist_index]["view"]))

    def prev_view(self) -> None:
        self._forced_sleep = False
        self.state.playlist_index = (self.state.playlist_index - 1) % len(self._playlist)
        self.set_view(str(self._playlist[self.state.playlist_index]["view"]))

    def wake(self, reason: str) -> None:
        self._forced_sleep = False
        self.facts["activity.last_ts"] = time.time()

    def sleep(self, reason: str) -> None:
        if self.facts.get("nightscout.alert"):
            return
        self._forced_sleep = True

    def power_off(self, reason: str) -> bool:
        return request_poweroff(self._power_cfg, reason)

    async def start(self) -> None:
        ctx = PluginContext(self.facts)
        await self._chromium.start()
        await self._pm.start_all(ctx)

        cb = Callbacks(
            set_view=self.set_view,
            set_auto=self.set_auto,
            next_view=self.next_view,
            prev_view=self.prev_view,
            wake=self.wake,
            sleep=self.sleep,
            power_off=self.power_off,
        )
        iface = KioskInterface(cb)
        self._bus = await serve(iface)

    async def stop(self) -> None:
        await self._pm.stop_all()
        self._chromium.terminate()
        if self._bus:
            self._bus.disconnect()

    async def run(self) -> None:
        await self.start()
        try:
            await self._loop()
        finally:
            await self.stop()

    async def _loop(self) -> None:
        self.facts.setdefault("activity.last_ts", time.time())
        self.state.last_switch_ts = time.time()

        while True:
            now = time.time()

            # Keep a derived alert fact available to plugins.
            self.facts["nightscout.alert"] = derive_alert(self.facts, self._policy_cfg)

            inhibit, _reasons = self._pm.screensaver_inhibit(self.facts)
            decision = evaluate(
                cfg=self._policy_cfg,
                state=self.state,
                facts=self.facts,
                views=self._views,
                playlist=self._playlist,
                screensaver_inhibit=inhibit,
                now=now,
            )

            if self._forced_sleep and not self.facts.get("nightscout.alert"):
                decision = Decision(screen_on=False, view=decision.view, why="forced_sleep")

            await self._apply(decision, now)
            await asyncio.sleep(0.25)

    async def _apply(self, decision: Decision, now: float) -> None:
        # Screen power.
        if decision.screen_on != self._screen_on:
            self._screen_on = decision.screen_on
            if decision.screen_on:
                self._backlight.set_brightness(int(self.cfg["screen"]["brightness_on"]))
                self._backlight.set_power(True)
            else:
                self._backlight.set_brightness(int(self.cfg["screen"]["brightness_dim"]))
                self._backlight.set_power(False)

        # Playlist cycling when in auto mode.
        manual_active = self.state.manual_view is not None and now < self.state.manual_until_ts
        alert = bool(self.facts.get("nightscout.alert"))
        if self._screen_on and not manual_active and not alert:
            seconds = int(self._playlist[self.state.playlist_index]["seconds"])
            if (now - self.state.last_switch_ts) >= seconds:
                self.state.playlist_index = (self.state.playlist_index + 1) % len(self._playlist)
                self.state.last_switch_ts = now

        # Navigate only if screen is on.
        if self._screen_on and decision.view != self._current_view:
            self._current_view = decision.view
            await self._chromium.navigate(self._views[decision.view])
