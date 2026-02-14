from __future__ import annotations

import pytest

from kiosk_control.config import ConfigError, validate


def test_https_enforced_by_default() -> None:
    cfg = {
        "security": {"allow_insecure": False},
        "chromium": {"bin": "chromium", "user_data_dir": "/tmp/x", "extra_flags": []},
        "views": {"a": "http://example"},
        "playlist": [{"view": "a", "seconds": 10}],
        "policy": {
            "idle_off_seconds": 1,
            "manual_timeout_seconds": 1,
            "hypo_threshold_mmol": 5,
            "trending_guard_mmol": 0.5,
        },
        "screen": {"backlight_sysfs": "/tmp"},
    }
    with pytest.raises(ConfigError):
        validate(cfg)


def test_allow_insecure_allows_http() -> None:
    cfg = {
        "security": {"allow_insecure": True},
        "chromium": {"bin": "chromium", "user_data_dir": "/tmp/x", "extra_flags": []},
        "views": {"a": "http://example"},
        "playlist": [{"view": "a", "seconds": 10}],
        "policy": {
            "idle_off_seconds": 1,
            "manual_timeout_seconds": 1,
            "hypo_threshold_mmol": 5,
            "trending_guard_mmol": 0.5,
        },
        "screen": {"backlight_sysfs": "/tmp"},
    }
    validate(cfg)
