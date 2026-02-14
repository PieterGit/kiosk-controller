from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class PowerConfig:
    poweroff_command: list[str]


def normalize_poweroff_command(raw: object) -> list[str]:
    """Return a safe default if config is missing or invalid."""

    if not isinstance(raw, list) or not raw:
        return ["systemctl", "poweroff", "--no-wall"]
    return [str(x) for x in raw]


def request_poweroff(cfg: PowerConfig, reason: str) -> bool:
    """Attempt to power off.

    Returns True if the command was started.
    """

    env = os.environ.copy()
    env["KIOSK_POWEROFF_REASON"] = reason
    try:
        subprocess.Popen(list(cfg.poweroff_command), env=env)  # noqa: S603,S607
        return True
    except Exception:
        return False
