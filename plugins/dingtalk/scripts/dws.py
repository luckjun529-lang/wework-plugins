#!/usr/bin/env python3
"""Public DWS entry: business metadata goes to the shared native broker."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from wegent_plugin_auth import AuthError, run_account_command

ROOT = Path(__file__).resolve().parents[1]


def account_arguments(arguments: list[str]) -> tuple[str | None, list[str]]:
    account = None
    forwarded = []
    index = 0
    while index < len(arguments):
        value = arguments[index]
        if value == "--":
            forwarded.extend(arguments[index:])
            break
        if value == "--account-id" or value.startswith("--account-id="):
            if account is not None:
                raise AuthError("plugin_auth_account_selection_required")
            if value == "--account-id":
                index += 1
                if index >= len(arguments):
                    raise AuthError("plugin_auth_account_selection_required")
                account = arguments[index]
            else:
                account = value.split("=", 1)[1]
            if not account.strip() or len(account) > 256:
                raise AuthError("plugin_auth_account_selection_required")
        else:
            forwarded.append(value)
        index += 1
    return account, forwarded


def source_is_managed() -> bool:
    """Receipts are public handoff metadata; never inspect the DWS token store."""
    directory = Path(os.environ.get("DWS_CONFIG_DIR") or Path.home() / ".dws")
    receipts = directory / "wegent-transfers"
    if not receipts.exists():
        return False
    # Once handoff started, uncertainty must not trigger another local login.
    if receipts.is_symlink() or not receipts.is_dir():
        raise AuthError("plugin_auth_reconnect_required")
    for path in receipts.glob("*.json"):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
            raise AuthError("plugin_auth_reconnect_required")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("version") != 1 or value.get("state") not in {
                "prepared",
                "detached",
                "aborted",
            }:
                raise ValueError
        except (ValueError, AttributeError):
            raise AuthError("plugin_auth_reconnect_required") from None
        if value["state"] == "aborted":
            continue
        return True
    return False


def local_environment() -> dict[str, str]:
    environment = dict(os.environ)
    # A user may put this public wrapper on PATH. Installer probes must reject
    # it rather than recursively discovering another copy of the same wrapper.
    environment["WEGENT_DWS_RESOLVING"] = "1"
    return environment


def run_local(arguments: list[str], executable: str | None = None) -> int:
    environment = local_environment()
    if arguments == ["plugin-health"]:
        command = (
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts/local-dws-ready.ps1"),
            ]
            if os.name == "nt"
            else ["/bin/sh", str(ROOT / "scripts/local-dws-ready.sh")]
        )
        return subprocess.call(command, env=environment)
    if executable is not None:
        return subprocess.call([executable, *arguments], env=environment)
    if os.name == "nt":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts/install-dws.ps1"),
            "-PrintPath",
        ]
    else:
        command = ["/bin/sh", str(ROOT / "scripts/install-dws.sh")]
    result = subprocess.run(
        command, env=environment, stdout=subprocess.PIPE, text=True, check=False
    )
    if result.returncode:
        return result.returncode
    lines = result.stdout.strip().splitlines()
    if not lines or not Path(lines[-1]).is_file():
        raise AuthError("plugin_auth_runtime_unsupported")
    return subprocess.call([lines[-1], *arguments], env=environment)


def main(arguments: list[str]) -> int:
    try:
        if os.environ.get("WEGENT_DWS_RESOLVING") == "1":
            return 126
        executable = None
        if arguments[:1] == ["--local-binary"]:
            if len(arguments) < 3:
                raise AuthError("plugin_auth_invalid_command")
            executable, arguments = arguments[1], arguments[2:]
        account, arguments = account_arguments(arguments)
        if (
            os.environ.get("WEGENT_PLUGIN_AUTH_MODE") == "cloud"
            or account is not None
            or source_is_managed()
        ):
            if executable is not None:
                raise AuthError("plugin_auth_invalid_command")
            if arguments == ["plugin-health"]:
                arguments = ["account-status"]
            sys.stdout.write(
                run_account_command(ROOT, "dingtalk", arguments, account_id=account)
            )
            return 0
        return run_local(arguments, executable)
    except AuthError as error:
        print(json.dumps({"error": str(error)}))
        return 1
    except (OSError, ValueError):
        print(json.dumps({"error": "plugin_auth_execution_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
