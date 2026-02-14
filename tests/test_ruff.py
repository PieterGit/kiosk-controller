from __future__ import annotations

import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not installed")
def test_ruff_format_and_check() -> None:
    subprocess.run(["ruff", "format", "--check", "."], check=True)  # noqa: S603
    subprocess.run(["ruff", "check", "."], check=True)  # noqa: S603
