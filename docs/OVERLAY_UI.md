# kiosk-overlay (touch UI)

`kiosk-overlay` is optional. It is built to run on Raspberry Pi OS (Wayland + labwc) as a thin, always-on-top bar.

## Buttons

- **Auto**: clear manual override
- **Prev / Next**: move in the configured playlist
- **View buttons**: select named views
- **Power Off**: shutdown Raspberry Pi (two-step confirm)

## Power off permissions

The overlay calls the controller D-Bus method `PowerOff()`.

By default the controller executes:

```bash
systemctl poweroff --no-wall
```

You must allow this without a password.

### Option A (recommended): polkit rule

Create `/etc/polkit-1/rules.d/50-kiosk-poweroff.rules`:

```js
polkit.addRule(function(action, subject) {
  if (action.id == "org.freedesktop.login1.power-off" && subject.user == "kiosk") {
    return polkit.Result.YES;
  }
});
```

### Option B: sudoers

`sudo visudo -f /etc/sudoers.d/kiosk-poweroff`:

```text
kiosk ALL=NOPASSWD: /bin/systemctl poweroff
```

Then set:

```yaml
system:
  poweroff_command: ["sudo", "-n", "systemctl", "poweroff"]
```
