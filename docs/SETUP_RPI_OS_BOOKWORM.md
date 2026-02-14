# Raspberry Pi OS (Bookworm) setup

This assumes Raspberry Pi OS Desktop (Wayland + labwc).

## 1) OS updates

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

## 2) Packages

```bash
sudo apt install -y chromium python3-venv python3-pip
```

Optional (overlay UI):

```bash
sudo apt install -y python3-gi gir1.2-gtk-3.0 gir1.2-gtk-layer-shell-0.1
```

Optional (idle detection):

```bash
sudo apt install -y python3-evdev
sudo usermod -aG input $USER
sudo reboot
```

## 3) Backlight permissions (official 7" display)

Create a group and allow writing to backlight sysfs:

```bash
sudo groupadd -f backlight
sudo usermod -aG backlight $USER

sudo tee /etc/udev/rules.d/90-backlight.rules >/dev/null <<'RULE'
SUBSYSTEM=="backlight", GROUP="backlight", MODE="0664"
RULE

sudo udevadm control --reload-rules
sudo udevadm trigger
```

## 4) Install kiosk-control

```bash
mkdir -p ~/kiosk-control
cd ~/kiosk-control
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[nightscout,input]"
```

## 5) Configure

Copy and edit:

```bash
cp configs/example.full.yaml config.yaml
```

Set URLs to HTTPS and supply tokens.

## 6) Autostart with labwc

Create `~/.config/labwc/autostart`:

```sh
#!/bin/sh
cd $HOME/kiosk-control
. .venv/bin/activate
kiosk-control run -c $HOME/kiosk-control/config.yaml &
kiosk-overlay -c $HOME/kiosk-control/config.yaml &
```

Make executable:

```bash
chmod +x ~/.config/labwc/autostart
```

## 7) Allow power off button

Recommended: create a polkit rule to allow your kiosk user to power off.
Alternative: `sudoers` NOPASSWD for `systemctl poweroff`.

See `docs/OVERLAY_UI.md`.
