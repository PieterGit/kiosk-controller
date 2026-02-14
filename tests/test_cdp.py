from __future__ import annotations

from pathlib import Path

from kiosk_control.cdp import parse_devtools_active_port


def test_parse_devtools_active_port_token(tmp_path: Path) -> None:
    (tmp_path / "DevToolsActivePort").write_text("12345\nABCDEF\n", encoding="utf-8")
    assert parse_devtools_active_port(tmp_path) == "ws://127.0.0.1:12345/devtools/browser/ABCDEF"


def test_parse_devtools_active_port_path(tmp_path: Path) -> None:
    (tmp_path / "DevToolsActivePort").write_text("9222\n/devtools/browser/XYZ\n", encoding="utf-8")
    assert parse_devtools_active_port(tmp_path) == "ws://127.0.0.1:9222/devtools/browser/XYZ"
