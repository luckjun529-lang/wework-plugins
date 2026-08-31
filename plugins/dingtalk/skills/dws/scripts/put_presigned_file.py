#!/usr/bin/env python3
"""Upload one local file to an HTTP(S) presigned URL with PUT.

The request deliberately omits Content-Type unless --content-type is supplied.
This keeps DingTalk Minutes uploads compatible with their signed-request rules.
"""

from __future__ import annotations

import argparse
import http.client
import sys
from pathlib import Path
from urllib.parse import urlsplit


def upload(url: str, file_path: Path, content_type: str | None) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("the presigned URL must use http or https")

    target = parsed.path or "/"
    if parsed.query:
        target = f"{target}?{parsed.query}"

    payload = file_path.read_bytes()
    connection_type = (
        http.client.HTTPSConnection
        if parsed.scheme == "https"
        else http.client.HTTPConnection
    )
    connection = connection_type(parsed.hostname, parsed.port, timeout=180)
    try:
        connection.putrequest("PUT", target)
        connection.putheader("Content-Length", str(len(payload)))
        if content_type is not None:
            connection.putheader("Content-Type", content_type)
        connection.endheaders(payload)
        response = connection.getresponse()
        response_body = response.read(512).decode("utf-8", "replace")
        if not 200 <= response.status < 300:
            raise RuntimeError(
                f"upload failed with HTTP {response.status}: {response_body}"
            )
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="presigned HTTP(S) PUT URL")
    parser.add_argument("file", help="local file to upload")
    parser.add_argument(
        "--content-type",
        help="optional Content-Type header; omit for DingTalk Minutes uploads",
    )
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.is_file():
        parser.error(f"file does not exist or is not readable: {file_path}")

    try:
        upload(args.url, file_path, args.content_type)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"upload failed: {error}", file=sys.stderr)
        return 1
    print("upload complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
