from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class ShutdownConfirm:
    armed_until_ts: float = 0.0

    def arm(self, now: float | None = None, window_seconds: float = 3.0) -> None:
        now = time.time() if now is None else now
        self.armed_until_ts = now + window_seconds

    def armed(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return now < self.armed_until_ts

    def consume_if_armed(self, now: float | None = None) -> bool:
        if self.armed(now):
            self.armed_until_ts = 0.0
            return True
        return False
