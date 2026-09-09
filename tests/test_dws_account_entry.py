import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "plugins/dingtalk"
sys.path.insert(0, str(ROOT / "scripts"))
import dws


class PublicEntryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        capabilities = self.home / "capabilities"
        capabilities.mkdir()
        (capabilities / "manifest.json").write_text(
            json.dumps(
                {
                    "plugins": {
                        "dingtalk": {
                            "managed": True,
                            "enabled": True,
                            "store_path": str(ROOT),
                            "installed_plugin_id": 41,
                        }
                    }
                }
            )
        )
        self.calls = []
        self.reply = {"stdout": '{"result":"business-result"}'}
        self.status = 200
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                fixture.calls.append(
                    (
                        self.path,
                        json.loads(
                            self.rfile.read(int(self.headers["Content-Length"]))
                        ),
                    )
                )
                self.send_response(fixture.status)
                self.end_headers()
                self.wfile.write(json.dumps(fixture.reply).encode())

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.environment = {
            **os.environ,
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "DWS_CONFIG_DIR": str(self.home / ".dws"),
            "WEGENT_EXECUTOR_HOME": str(self.home),
            "WEGENT_PLUGIN_AUTH_MODE": "cloud",
            "WEGENT_PLUGIN_AUTH_BROKER": f"http://127.0.0.1:{self.server.server_port}/v1/run",
            "WEGENT_PLUGIN_AUTH_BROKER_TOKEN": "a" * 64,
        }
        self.environment.pop("WEGENT_DWS_RESOLVING", None)

    def invoke(self, args, environment=None):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/dws.py"), *args],
            env=environment or self.environment,
            text=True,
            capture_output=True,
            timeout=10,
        )

    def test_cloud_command_preserves_arguments_and_only_returns_business_output(self):
        arguments = [
            "todo",
            "task",
            "get",
            "--task-id",
            "value & echo unwanted",
            "--account-id",
            "corp:alice",
        ]
        result = self.invoke(arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"result": "business-result"})
        path, body = self.calls[0]
        self.assertEqual(path, "/v1/run")
        self.assertEqual(body["args"], arguments[:-2])
        self.assertEqual(body["account_id"], "corp:alice")
        self.assertEqual(body["installed_plugin_id"], 41)
        self.assertEqual(
            set(body),
            {
                "installed_plugin_id",
                "connector_slug",
                "account_id",
                "args",
                "working_directory",
            },
        )

    def test_cloud_failures_never_start_local_install_or_login(self):
        self.status = 400
        self.reply = {"error": "plugin_auth_device_not_granted"}
        result = self.invoke(["todo", "task", "get"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("plugin_auth_device_not_granted", result.stdout)
        self.assertFalse((self.home / ".dws").exists())
        environment = {
            **self.environment,
            "WEGENT_PLUGIN_AUTH_BROKER": "https://untrusted.invalid/v1/run",
        }
        result = self.invoke(["auth", "login"], environment)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("untrusted.invalid", result.stdout + result.stderr)
        self.assertEqual(len(self.calls), 1)

    def test_managed_readiness_checks_the_platform_without_starting_local_auth(self):
        result = self.invoke(["plugin-health"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls[0][1]["args"], ["account-status"])
        self.assertFalse((self.home / ".dws").exists())

    def test_detached_local_account_uses_the_broker_without_source_credentials(self):
        receipts = self.home / ".dws/wegent-transfers"
        receipts.mkdir(parents=True)
        (receipts / ("b" * 64 + ".json")).write_text(
            json.dumps({"version": 1, "state": "detached", "fingerprint": "c" * 64})
        )
        result = self.invoke(
            ["todo", "task", "get"],
            {**self.environment, "WEGENT_PLUGIN_AUTH_MODE": "local"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls), 1)

    def test_unmigrated_local_account_keeps_the_existing_cli(self):
        with patch.dict(
            os.environ,
            {**self.environment, "WEGENT_PLUGIN_AUTH_MODE": "local"},
            clear=True,
        ), patch.object(dws, "run_local", return_value=7) as local:
            self.assertEqual(dws.main(["todo", "task", "get"]), 7)
        local.assert_called_once_with(["todo", "task", "get"], None)
        self.assertEqual(self.calls, [])

    def test_aborted_transfer_does_not_mark_the_new_source_as_managed(self):
        receipts = self.home / ".dws/wegent-transfers"
        receipts.mkdir(parents=True)
        (receipts / ("b" * 64 + ".json")).write_text(
            json.dumps({"version": 1, "state": "aborted", "fingerprint": "c" * 64})
        )
        with patch.dict(
            os.environ,
            {**self.environment, "WEGENT_PLUGIN_AUTH_MODE": "local"},
            clear=True,
        ), patch.object(dws, "run_local", return_value=0) as local:
            self.assertEqual(dws.main(["todo", "task", "get"]), 0)
        local.assert_called_once()
        self.assertEqual(self.calls, [])

    def test_local_binary_override_cannot_bypass_a_cloud_grant(self):
        result = self.invoke(["--local-binary", "/untrusted/dws", "todo", "get"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("plugin_auth_invalid_command", result.stdout)
        self.assertEqual(self.calls, [])

    def test_account_selection_rejects_duplicates_and_empty_values(self):
        for arguments in (
            ["--account-id"],
            ["--account-id="],
            ["--account-id=a", "--account-id=b"],
        ):
            self.assertEqual(self.invoke(arguments).returncode, 1)
        self.assertEqual(self.calls, [])

    def test_helper_subprocess_uses_the_same_public_entry(self):
        helper = ROOT / "skills/dws/scripts/todo_batch_create.py"
        code = "import sys;sys.path.insert(0,sys.argv[1]);from todo_batch_create import run_dws;assert run_dws(['todo','task','get']) == {'result':'business-result'}"
        result = subprocess.run(
            [sys.executable, "-c", code, str(helper.parent)],
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls[0][1]["connector_slug"], "dingtalk")

    def test_native_adapter_requires_matching_artifact_metadata(self):
        spec = importlib.util.spec_from_file_location(
            "dws_native_adapter", ROOT / "scripts/account-auth.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        scripts = self.home / "plugin/scripts"
        directory = scripts / "native/linux-amd64"
        directory.mkdir(parents=True)
        binary = directory / "dws-account-auth"
        binary.write_bytes(b"synthetic-binary")
        metadata = binary.with_name(binary.name + ".json")
        value = {
            "nativeProtocolVersion": 1,
            "target": "linux/amd64",
            "binarySha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        }
        metadata.write_text(json.dumps(value))
        with patch.object(
            module, "__file__", str(scripts / "account-auth.py")
        ), patch.object(module.platform, "system", return_value="Linux"), patch.object(
            module.platform, "machine", return_value="x86_64"
        ):
            self.assertEqual(module.companion(), binary.resolve())
            binary.write_bytes(b"changed-binary")
            with self.assertRaises(ValueError):
                module.companion()


if __name__ == "__main__":
    unittest.main()
