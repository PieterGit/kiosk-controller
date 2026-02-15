from __future__ import annotations

from pathlib import Path

from kiosk_control.config import normalize
from kiosk_control.paths import default_user_data_dir


def test_normalize_strips_user_data_dir_whitespace() -> None:
    cfg = {
        "chromium": {"user_data_dir": "  /tmp/profile  "},
        "views": {"a": "https://example.test  "},
        "playlist": [{"view": "a", "seconds": 10}],
        "policy": {"idle_off_seconds": 120},
        "screen": {"backlight_sysfs": "/tmp"},
    }
    normalize(cfg)
    assert cfg["chromium"]["user_data_dir"] == "/tmp/profile"
    assert cfg["views"]["a"] == "https://example.test"


def test_default_user_data_dir_is_user_writable() -> None:
    p = default_user_data_dir()
    # Must not default to system locations like /var/lib.
    assert str(p).startswith(str(Path.home()))


def test_normalize_sets_default_user_data_dir_when_missing() -> None:
    cfg = {
        "chromium": {"bin": "chromium", "extra_flags": []},
        "views": {"a": "https://example.test"},
        "playlist": [{"view": "a", "seconds": 10}],
        "policy": {"idle_off_seconds": 120},
        "screen": {"backlight_sysfs": "/tmp"},
    }
    normalize(cfg)
    assert "user_data_dir" in cfg["chromium"]
    assert str(cfg["chromium"]["user_data_dir"]).startswith(str(Path.home()))
