#!/usr/bin/env python3
"""Delete owned Immich albums whose names start with IMG_."""

import argparse
from getpass import getpass
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def run(url, key, apply):
    base = url.rstrip("/")
    if not base.endswith("/api"):
        base += "/api"

    def request(method, path):
        req = Request(base + path, method=method, headers={
            "x-api-key": key,
            "Content-Type": "application/json",
        })
        try:
            with urlopen(req, timeout=60) as response:
                return json.load(response) if method == "GET" else None
        except HTTPError as error:
            raise RuntimeError(f"{method} {path}: HTTP {error.code}") from error

    albums = request("GET", "/albums?isOwned=true")
    matches = sorted(
        (album for album in albums if album["albumName"].startswith("20140825")),       
        key=lambda album: album["albumName"].casefold(),
    )
    if not matches:
        print("No owned albums ending with '.jpg' were found.")
        return 0

    failed = False
    for album in matches:
        name = album["albumName"]
        if not apply:
            print(f"Would delete album {name!r} ({album['assetCount']} assets; assets will be kept)")
            continue
        try:
            request("DELETE", f"/albums/{album['id']}")
            print(f"Deleted album {name!r} ({album['assetCount']} assets; assets were kept)")
        except (RuntimeError, URLError, TimeoutError) as error:
            print(f"Could not delete album {name!r}: {error}", file=sys.stderr)
            failed = True

    if not apply:
        print("Preview only. Pass --apply to delete these albums; their photos and videos will be kept.")
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("IMMICH_URL"),
                        help="Immich server URL (or set IMMICH_URL)")
    parser.add_argument("--apply", action="store_true", help="Delete matching albums")
    args = parser.parse_args()
    if not args.url or not args.url.startswith(("https://", "http://")):
        parser.error("provide an HTTP(S) Immich URL using --url or IMMICH_URL")
    key = os.environ.get("IMMICH_API_KEY") or getpass("Immich API key: ")
    if not key.strip():
        parser.error("an Immich API key is required")
    try:
        return run(args.url, key.strip(), args.apply)
    except (RuntimeError, URLError, TimeoutError, ValueError, KeyError) as error:
        print(f"Immich request or response error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
