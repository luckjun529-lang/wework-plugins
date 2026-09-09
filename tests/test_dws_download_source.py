"""Execute the installer resolver without network requests or user installation."""

import os
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/dingtalk/scripts/install-dws.sh"


class DwsDownloadSourceTests(unittest.TestCase):
    def resolve(self, mirror, system="Linux", arch="x86_64"):
        shell = shutil.which("sh")
        self.assertIsNotNone(shell, "A POSIX shell is required for installer tests")
        functions = SCRIPT.read_text().split("\nif DWS_EXECUTABLE=", 1)[0]
        harness = functions + '''
uname() {
    if [ "$1" = "-s" ]; then printf '%s\\n' "$TEST_SYSTEM";
    else printf '%s\\n' "$TEST_ARCH"; fi
}
resolve_release
printf '%s\\n' "$DWS_ARCHIVE_URL" "$DWS_EXPECTED_SHA"
'''
        environment = dict(os.environ, TEST_SYSTEM=system, TEST_ARCH=arch)
        environment.pop("DWS_DOWNLOAD_BASE_URL", None)
        if mirror is not None:
            environment["DWS_DOWNLOAD_BASE_URL"] = mirror
        return subprocess.run([shell], input=harness, text=True, capture_output=True,
                              env=environment, timeout=10)

    def test_mirror_changes_only_source_and_preserves_all_pinned_checksums(self):
        for system, arch, asset in (
            ("Linux", "x86_64", "linux-amd64"),
            ("Linux", "aarch64", "linux-arm64"),
            ("Darwin", "x86_64", "darwin-amd64"),
            ("Darwin", "arm64", "darwin-arm64"),
        ):
            with self.subTest(system=system, arch=arch):
                upstream = self.resolve(None, system, arch)
                mirror = self.resolve("https://artifacts.example.test/dws/", system, arch)
                self.assertEqual(upstream.returncode, 0, upstream.stderr)
                self.assertEqual(mirror.returncode, 0, mirror.stderr)
                url, checksum = mirror.stdout.splitlines()
                self.assertEqual(url, f"https://artifacts.example.test/dws/v1.0.58/dws-{asset}.tar.gz")
                self.assertEqual(checksum, upstream.stdout.splitlines()[1])

    def test_invalid_sources_fail_without_falling_back_to_github(self):
        for source in ("http://mirror.test", "https://user:password@mirror.test",
                       "https://mirror.test?token=value", "https://mirror.test#fragment",
                       "https://mirror.test\nhttps://other.test", "https://mirror.test\n",
                       "https://mirror.test/$(command)"):
            with self.subTest(source=source):
                result = self.resolve(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("github.com", result.stdout)
                self.assertNotIn("password", result.stderr)

    def test_unconfigured_source_remains_the_pinned_upstream_release(self):
        result = self.resolve(None)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0],
                         "https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/download/v1.0.58/dws-linux-amd64.tar.gz")


if __name__ == "__main__":
    unittest.main()
