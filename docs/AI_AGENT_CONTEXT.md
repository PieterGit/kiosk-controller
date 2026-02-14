# AI agent context (ChatGPT / Claude)

This repository is designed to be edited by coding agents.

## Hard invariants

1. **HTTPS/WSS only by default.**
   - If `security.allow_insecure` is `false` (default), all URLs must be `https://` and WebSockets must be `wss://`.

2. **Screen saver must be plugin-driven.**
   - Do not hardcode “Nightscout” or “Home Assistant” special-cases in the policy.
   - Plugins decide whether the screen saver is inhibited via `Plugin.screensaver_inhibit(facts)`.

3. **Keep tests fast and offline.**
   - Unit tests must not require real network endpoints, a real D-Bus session, or a GUI.

4. **Formatting and linting.**
   - Use Ruff.
   - `ruff format .` then `ruff check .` must pass.

## Standard dev loop

```bash
pip install -e ".[dev,nightscout,input]"
ruff format .
ruff check .
pytest
```

## What is OK to mock

- Socket.IO and HA WebSocket traffic
- CDP transport
- Backlight sysfs writes
- Poweroff commands
