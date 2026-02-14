# Architecture

## Components

- **kiosk-control**: the controller daemon.
  - Starts Chromium.
  - Connects to Chromium using CDP.
  - Runs plugins to produce a shared `facts` dict.
  - Runs a policy engine over `facts` + local state (manual override, idle timer).
  - Acts on decisions (navigate, backlight power/brightness).
  - Exposes D-Bus methods for manual selection and poweroff.

- **kiosk-overlay**: optional touch UI.
  - Always-on-top bar (Wayland layer-shell).
  - Buttons for next/prev, view selection, auto mode, and Power Off.
  - Talks to the controller over D-Bus.

## Data flow

Plugins write facts, controller reads facts:

- `facts["nightscout"]` – latest CGM value and an `alert` boolean
- `facts["energy"]` – production/consumption and `energy_good` boolean
- `facts["activity"]` – last input timestamp

The policy engine returns:

- `desired_view` (name)
- `screen_on` (bool)
- `why` (short string for logs)

## Screensaver inhibition

Each plugin can request “do not turn the screen off” by returning:

```python
inhibit, reason = plugin.screensaver_inhibit(facts)
```

The controller aggregates inhibitors; the policy uses the aggregated value.

Reasoning:
- Prevents business rules from being hardcoded to specific plugins.
- Lets you add future plugins (doorbell, calendar, alarm) without touching core policy.
