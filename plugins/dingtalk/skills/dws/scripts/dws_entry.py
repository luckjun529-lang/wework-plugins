"""Run the plugin entry directly, preserving argument boundaries on every OS."""

import sys
from pathlib import Path


def command(executable: str = "dws") -> list[str]:
    prefix = [
        sys.executable,
        str(Path(__file__).resolve().parents[3] / "scripts/dws.py"),
    ]
    return prefix if executable == "dws" else [*prefix, "--local-binary", executable]
