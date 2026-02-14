from __future__ import annotations

import argparse
import asyncio

from kiosk_control import __version__
from kiosk_control.config import load
from kiosk_control.controller import Controller


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="kiosk-control")
    ap.add_argument("--version", action="version", version=__version__)

    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run the kiosk controller")
    run.add_argument("-c", "--config", required=True)

    return ap


def main() -> None:
    args = _build_parser().parse_args()
    if args.cmd == "run":
        cfg = load(args.config)
        ctl = Controller(cfg)
        asyncio.run(ctl.run())
