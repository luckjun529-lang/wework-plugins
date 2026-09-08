# Managed DWS download source

The installers accept `DWS_DOWNLOAD_BASE_URL` for a trusted HTTPS artifact mirror.
The mirror must preserve the pinned release archives byte-for-byte and expose:

```text
<base>/v1.0.58/dws-darwin-amd64.tar.gz
<base>/v1.0.58/dws-darwin-arm64.tar.gz
<base>/v1.0.58/dws-linux-amd64.tar.gz
<base>/v1.0.58/dws-linux-arm64.tar.gz
<base>/v1.0.58/dws-windows-amd64.zip
```

Configure the variable in the executor/container environment. Both POSIX and
PowerShell installers retain their pinned SHA-256 hashes and fail when the
selected mirror fails or returns a different archive. URLs containing embedded
credentials, query strings, or fragments are rejected.

For cloud images, preinstall the verified binary and set `DWS_BINARY_PATH` to its
absolute path. Existing binary discovery and version-specific installation cache
run before any download. This avoids first-task downloads entirely.

Without the variable the installer still uses GitHub. No company mirror is
provisioned or configured by this change. The variable names an artifact base,
not a generic GitHub proxy or a Gitee repository page.

Account authentication is separate from binary distribution. DWS 1.0.58 rejects
portable export on Windows and on macOS when using its default Keychain backend;
do not reset authentication, copy only app.json, or claim cross-platform auth
migration merely because the binary was installed successfully.
