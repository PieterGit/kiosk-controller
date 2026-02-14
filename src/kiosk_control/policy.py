from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class PolicyConfig:
    idle_off_seconds: int
    manual_timeout_seconds: int
    hypo_threshold_mmol: float
    trending_guard_mmol: float
    falling_directions: set[str]


@dataclass
class RuntimeState:
    playlist_index: int = 0
    last_switch_ts: float = 0.0
    manual_view: str | None = None
    manual_until_ts: float = 0.0


def derive_alert(facts: dict[str, Any], cfg: PolicyConfig) -> bool:
    sgv = facts.get("nightscout.sgv_mmol")
    direction = str(facts.get("nightscout.direction") or "")
    if sgv is None:
        return False
    try:
        sgv_f = float(sgv)
    except Exception:
        return False

    if sgv_f < cfg.hypo_threshold_mmol:
        return True

    return direction in cfg.falling_directions and sgv_f < (
        cfg.hypo_threshold_mmol + cfg.trending_guard_mmol
    )


@dataclass(frozen=True)
class Decision:
    screen_on: bool
    view: str
    why: str


def evaluate(
    cfg: PolicyConfig,
    state: RuntimeState,
    facts: dict[str, Any],
    views: dict[str, str],
    playlist: list[dict[str, Any]],
    screensaver_inhibit: bool,
    now: float | None = None,
) -> Decision:
    now = time.time() if now is None else now

    last_activity = float(facts.get("activity.last_ts", 0.0) or 0.0)
    idle = (now - last_activity) if last_activity else 1e9
    energy_good = bool(facts.get("ha.energy_good", False))

    alert = derive_alert(facts, cfg)
    facts["nightscout.alert"] = alert

    manual_active = state.manual_view is not None and now < state.manual_until_ts

    # Decide if the screen should be on.
    if alert:
        screen_on = True
        why = "nightscout_alert"
    elif manual_active:
        screen_on = True
        why = "manual_override"
    else:
        if energy_good:
            screen_on = True
            why = "energy_good"
        else:
            # Allow a short grace period after user interaction.
            if idle < cfg.idle_off_seconds:
                screen_on = True
                why = "recent_activity"
            elif screensaver_inhibit:
                screen_on = True
                why = "plugin_inhibit"
            else:
                screen_on = False
                why = "idle_off"

    # Decide view.
    if alert and "nightscout" in views:
        view = "nightscout"
    elif manual_active and state.manual_view in views:
        view = state.manual_view
    else:
        view = str(playlist[state.playlist_index]["view"])

    return Decision(screen_on=screen_on, view=view, why=why)
