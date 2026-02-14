from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    pass


def _require(cfg: dict[str, Any], key: str) -> Any:
    if key not in cfg:
        raise ConfigError(f"Missing required config key: {key}")
    return cfg[key]


def _is_https(url: str) -> bool:
    return url.startswith("https://")


def _is_wss(url: str) -> bool:
    return url.startswith("wss://")


def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError("Top-level config must be a mapping")
    validate(data)
    return data


def validate(cfg: dict[str, Any]) -> None:
    security = cfg.get("security", {})
    allow_insecure = bool(security.get("allow_insecure", False))

    chromium = _require(cfg, "chromium")
    _require(chromium, "bin")
    _require(chromium, "user_data_dir")
    _require(chromium, "extra_flags")

    views = _require(cfg, "views")
    if not isinstance(views, dict) or not views:
        raise ConfigError("views must be a non-empty mapping")

    playlist = _require(cfg, "playlist")
    if not isinstance(playlist, list) or not playlist:
        raise ConfigError("playlist must be a non-empty list")

    for item in playlist:
        if not isinstance(item, dict):
            raise ConfigError("playlist items must be mappings")
        view = item.get("view")
        if view not in views:
            raise ConfigError(f"playlist references unknown view: {view}")
        if int(item.get("seconds", 0)) <= 0:
            raise ConfigError(f"playlist item seconds must be > 0: {item}")

    policy = _require(cfg, "policy")
    if int(policy.get("idle_off_seconds", 0)) <= 0:
        raise ConfigError("policy.idle_off_seconds must be > 0")

    screen = _require(cfg, "screen")
    _require(screen, "backlight_sysfs")

    system = cfg.get("system", {})
    if "poweroff_command" in system and (
        not isinstance(system["poweroff_command"], list) or not system["poweroff_command"]
    ):
        raise ConfigError("system.poweroff_command must be a non-empty list")

    if not allow_insecure:
        for name, url in views.items():
            if not _is_https(str(url)):
                raise ConfigError(
                    f"views.{name} must be https:// (set allow_insecure to true to bypass)"
                )

        plugins = cfg.get("plugins", {})
        ha = plugins.get("homeassistant", {})
        if ha.get("enabled"):
            ws_url = str(ha.get("ws_url", ""))
            if not _is_wss(ws_url):
                raise ConfigError(
                    "Home Assistant ws_url must be wss:// when allow_insecure is false"
                )

        ns = plugins.get("nightscout", {})
        if ns.get("enabled"):
            base_url = str(ns.get("base_url", ""))
            if not _is_https(base_url):
                raise ConfigError(
                    "Nightscout base_url must be https:// when allow_insecure is false"
                )
