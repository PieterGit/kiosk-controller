from __future__ import annotations

import os
from pathlib import Path


def default_user_data_dir(app_name: str = "kiosk-control") -> Path:
    """Return a user-writable Chromium profile directory.

    Rationale:
    - user services (systemd --user, labwc autostart) typically run unprivileged
    - /var/lib/... defaults cause PermissionError for most users

    Uses XDG_STATE_HOME when available, else ~/.local/state.
    """

    base = os.environ.get("XDG_STATE_HOME")
    if base:
        root = Path(base)
    else:
        root = Path.home() / ".local" / "state"
    return root / app_name / "chrome-profile"
