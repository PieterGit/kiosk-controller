from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import yaml

from kiosk_overlay import __version__


def _load(path: str | Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a mapping")
    return data


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="kiosk-overlay")
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("-c", "--config", required=True)
    return ap


def main() -> None:
    args = _build_parser().parse_args()
    cfg = _load(args.config)

    # Import Gtk lazily so the base package remains importable on non-GUI systems.
    try:
        import gi  # type: ignore

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gio, GLib, Gtk  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            "kiosk-overlay requires GTK3 + PyGObject (apt install python3-gi gir1.2-gtk-3.0)"
        ) from e

    from kiosk_overlay.model import ShutdownConfirm

    bus_name = "io.github.kiosk_control"
    obj_path = "/io/github/kiosk_control"
    iface_name = bus_name

    proxy = Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION,
        Gio.DBusProxyFlags.NONE,
        None,
        bus_name,
        obj_path,
        iface_name,
        None,
    )

    overlay_cfg = cfg.get("overlay", {})
    hide_after = float(overlay_cfg.get("collapse_after_seconds", 5.0))

    views = list((cfg.get("views") or {}).keys())

    confirm = ShutdownConfirm()

    class Overlay(Gtk.Window):
        def __init__(self) -> None:
            super().__init__(title="kiosk-overlay")
            self.set_decorated(False)
            self.set_keep_above(True)
            self.stick()

            self._expanded = True
            self._last_touch = GLib.get_monotonic_time()

            self._collapsed = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            self._expanded_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

            self._btn_expand = Gtk.Button(label="⋯")
            self._btn_expand.connect("clicked", self._on_expand)
            self._collapsed.pack_start(self._btn_expand, True, True, 0)

            def add(btn: Gtk.Button) -> None:
                self._expanded_box.pack_start(btn, True, True, 0)

            btn_auto = Gtk.Button(label="Auto")
            btn_auto.connect("clicked", self._call0, "SetAuto")
            add(btn_auto)

            btn_prev = Gtk.Button(label="Prev")
            btn_prev.connect("clicked", self._call0, "Prev")
            add(btn_prev)

            btn_next = Gtk.Button(label="Next")
            btn_next.connect("clicked", self._call0, "Next")
            add(btn_next)

            for v in views:
                b = Gtk.Button(label=v)
                b.connect("clicked", self._set_view, v)
                add(b)

            self._btn_power = Gtk.Button(label="Power Off")
            self._btn_power.connect("clicked", self._power_off)
            add(self._btn_power)

            self._stack = Gtk.Stack()
            self._stack.add_named(self._expanded_box, "expanded")
            self._stack.add_named(self._collapsed, "collapsed")
            self._stack.set_visible_child_name("expanded")
            self.add(self._stack)

            GLib.timeout_add(250, self._tick)

        def _touch(self) -> None:
            self._last_touch = GLib.get_monotonic_time()
            if not self._expanded:
                self._expanded = True
                self._stack.set_visible_child_name("expanded")

        def _tick(self) -> bool:
            if self._expanded:
                idle_s = (GLib.get_monotonic_time() - self._last_touch) / 1_000_000
                if idle_s >= hide_after:
                    self._expanded = False
                    self._stack.set_visible_child_name("collapsed")
            return True

        def _on_expand(self, *_: object) -> None:
            self._touch()

        def _call0(self, _btn: Gtk.Button, method: str) -> None:
            self._touch()
            proxy.call_sync(method, None, Gio.DBusCallFlags.NONE, -1, None)
            proxy.call_sync("Wake", GLib.Variant("(s)", ("ui",)), Gio.DBusCallFlags.NONE, -1, None)

        def _set_view(self, _btn: Gtk.Button, view: str) -> None:
            self._touch()
            proxy.call_sync(
                "SetView", GLib.Variant("(s)", (view,)), Gio.DBusCallFlags.NONE, -1, None
            )
            proxy.call_sync("Wake", GLib.Variant("(s)", ("ui",)), Gio.DBusCallFlags.NONE, -1, None)

        def _power_off(self, *_: object) -> None:
            self._touch()
            now = time.time()
            if confirm.consume_if_armed(now):
                proxy.call_sync(
                    "PowerOff", GLib.Variant("(s)", ("ui",)), Gio.DBusCallFlags.NONE, -1, None
                )
                self._btn_power.set_label("Powering off…")
                self._btn_power.set_sensitive(False)
                return
            confirm.arm(now)
            self._btn_power.set_label("Confirm")
            GLib.timeout_add(3000, self._reset_power)

        def _reset_power(self) -> bool:
            self._btn_power.set_label("Power Off")
            return False

    win = Overlay()
    win.show_all()
    Gtk.main()
