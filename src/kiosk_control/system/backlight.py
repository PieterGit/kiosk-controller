from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Backlight:
    sysfs_dir: Path

    @property
    def _bl_power(self) -> Path:
        return self.sysfs_dir / "bl_power"

    @property
    def _brightness(self) -> Path:
        return self.sysfs_dir / "brightness"

    def set_power(self, on: bool) -> None:
        # Kernel backlight uses bl_power = 0 for on, 1 for off (often).
        self._bl_power.write_text("0" if on else "1", encoding="utf-8")

    def set_brightness(self, value: int) -> None:
        self._brightness.write_text(str(int(value)), encoding="utf-8")
