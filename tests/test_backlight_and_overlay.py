from __future__ import annotations

from pathlib import Path

from kiosk_control.system.backlight import Backlight
from kiosk_overlay.model import ShutdownConfirm


def test_backlight_writes_sysfs(tmp_path: Path) -> None:
    (tmp_path / "bl_power").write_text("0", encoding="utf-8")
    (tmp_path / "brightness").write_text("0", encoding="utf-8")

    bl = Backlight(tmp_path)
    bl.set_power(False)
    assert (tmp_path / "bl_power").read_text(encoding="utf-8") == "1"

    bl.set_brightness(123)
    assert (tmp_path / "brightness").read_text(encoding="utf-8") == "123"


def test_shutdown_confirm_two_step() -> None:
    c = ShutdownConfirm()
    assert c.consume_if_armed(0.0) is False

    c.arm(now=10.0, window_seconds=3.0)
    assert c.armed(now=11.0) is True
    assert c.consume_if_armed(now=11.0) is True
    assert c.consume_if_armed(now=11.1) is False
