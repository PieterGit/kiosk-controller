from __future__ import annotations

import time

from kiosk_control.policy import PolicyConfig, RuntimeState, derive_alert, evaluate


def test_alert_threshold() -> None:
    cfg = PolicyConfig(
        idle_off_seconds=120,
        manual_timeout_seconds=10,
        hypo_threshold_mmol=5.0,
        trending_guard_mmol=0.5,
        falling_directions={"SingleDown"},
    )
    facts = {"nightscout.sgv_mmol": 4.9, "nightscout.direction": "Flat"}
    assert derive_alert(facts, cfg) is True


def test_trending_guard() -> None:
    cfg = PolicyConfig(
        idle_off_seconds=120,
        manual_timeout_seconds=10,
        hypo_threshold_mmol=5.0,
        trending_guard_mmol=0.5,
        falling_directions={"SingleDown"},
    )
    facts = {"nightscout.sgv_mmol": 5.3, "nightscout.direction": "SingleDown"}
    assert derive_alert(facts, cfg) is True


def test_idle_off_when_no_inhibit() -> None:
    cfg = PolicyConfig(
        idle_off_seconds=120,
        manual_timeout_seconds=10,
        hypo_threshold_mmol=5.0,
        trending_guard_mmol=0.5,
        falling_directions=set(),
    )
    state = RuntimeState(playlist_index=0)
    now = time.time()
    facts = {"activity.last_ts": now - 9999, "ha.energy_good": False}
    decision = evaluate(
        cfg,
        state,
        facts,
        views={"a": "https://x", "nightscout": "https://n"},
        playlist=[{"view": "a", "seconds": 10}],
        screensaver_inhibit=False,
        now=now,
    )
    assert decision.screen_on is False
