# kiosk-control 0.0.2

Policy-driven kiosk for Raspberry Pi OS:

- Runs Chromium in kiosk mode.
- Switches pages using Chrome DevTools Protocol (CDP).
- Plugin architecture for data sources (Nightscout API v3 Socket.IO, Home Assistant WebSocket, input activity, etc.).
- Screen/backlight control via `/sys/class/backlight`.
- Local control API over D-Bus.
- Optional touch overlay UI (`kiosk-overlay`) with a Power Off button.

## Project layout

- `src/kiosk_control/` – controller + plugin framework
- `src/kiosk_overlay/` – touch overlay UI (Wayland layer-shell, optional)
- `configs/` – example configs
- `docs/` – setup, architecture, and agent context
- `tests/` – unit tests

## Quick start (development)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,nightscout,input]"
pytest
ruff format .
ruff check .
```

## Raspberry Pi OS (Bookworm) setup

See `docs/SETUP_RPI_OS_BOOKWORM.md`.

## Security

The default stance is HTTPS/WSS only. See `docs/SECURITY_TLS.md`.
