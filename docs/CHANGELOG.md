# Changelog

## 0.0.3

- Fixed user-level runs failing with `PermissionError` when `chromium.user_data_dir` points to `/var/lib/...`.
  The config loader normalizes the path and ChromiumKiosk falls back to a user-writable XDG path.
- Updated example configuration to use a user-writable default profile path.

## 0.0.2

- Added `kiosk-overlay` package (touch bar UI) with two-step Power Off.
- Added Ruff formatter and lint configuration.
- Added import/compileall tests to catch syntax/indent regressions.
- Cleaned and minimized controller core while keeping plugin-driven screensaver inhibition.
