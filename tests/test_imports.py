from __future__ import annotations

import compileall
import importlib
from pathlib import Path


def test_compileall_src() -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    ok = compileall.compile_dir(str(src), quiet=1)
    assert ok


def test_import_packages() -> None:
    importlib.import_module("kiosk_control")
    importlib.import_module("kiosk_control.cli")
    importlib.import_module("kiosk_control.config")
    importlib.import_module("kiosk_control.cdp")
    importlib.import_module("kiosk_control.policy")
    importlib.import_module("kiosk_overlay")
    importlib.import_module("kiosk_overlay.model")
