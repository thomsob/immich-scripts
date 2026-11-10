#!/usr/bin/env python3
"""List Immich albums and the number of assets in each."""

import argparse
from getpass import getpass
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def run(url, key):
    base = url.rstrip("/")
    if not base.endswith("/api"):
        base += "/api"

    request = Request(base + "/albums", headers={
        "x-api-key": key,
        "Content-Type": "application/json",
    })
    try:
        with urlopen(request, timeout=60) as response:
            albums = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"GET /albums: HTTP {error.code}") from error

    print("Album\tAssets")
    print("Found albums: " + str(len(albums)))
    #for album in sorted(albums, key=lambda item: item["albumName"].casefold()):
    #    print(f"{album['albumName']}\t{album['assetCount']}")

    # export to CSV
    with open("albums.csv", "w") as f:
        f.write("Album,Assets\n")
        for album in sorted(albums, key=lambda item: item["albumName"].casefold()):
            f.write(f"{album['albumName']},{album['assetCount']}\n")    


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("IMMICH_URL"),
                        help="Immich server URL (or set IMMICH_URL)")
    args = parser.parse_args()
    if not args.url or not args.url.startswith(("https://", "http://")):
        parser.error("provide an HTTP(S) Immich URL using --url or IMMICH_URL")
    key = os.environ.get("IMMICH_API_KEY") or getpass("Immich API key: ")
    if not key.strip():
        parser.error("an Immich API key is required")
    try:
        run(args.url, key.strip())
    except (RuntimeError, URLError, TimeoutError, ValueError, KeyError) as error:
        print(f"Immich request or response error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
