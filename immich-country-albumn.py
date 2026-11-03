#!/usr/bin/env python3
"""Preview or create Country YYYY albums from photos already in Immich."""

import argparse
from collections import defaultdict
from datetime import date
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

    def request(method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else None
        req = Request(base + path, data=body, method=method, headers={
            "x-api-key": key,
            "Content-Type": "application/json",
        })
        try:
            with urlopen(req, timeout=60) as response:
                return json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"{method} {path}: HTTP {error.code}") from error

    groups = defaultdict(set)
    skipped = 0
    page = 1
    while page is not None:
        result = request("POST", "/search/metadata", {
            "type": "IMAGE", "withExif": True, "page": page, "size": 500,
        })["assets"]
        for asset in result["items"]:
            country = ((asset.get("exifInfo") or {}).get("country") or "").strip()
            local_date = asset.get("localDateTime") or ""
            if not country or not local_date:
                skipped += 1
                continue
            year = date.fromisoformat(local_date[:10]).year
            groups[f"{country} {year:04d}"].add(asset["id"])
        page = result["nextPage"]
        if page is not None:
            page = int(page)

    albums = defaultdict(list)
    for album in request("GET", "/albums?shared=false"):
        albums[album["albumName"]].append(album["id"])

    print(f"Skipped {skipped} photos without a country or local date.")
    failed = False
    for name, ids in sorted(groups.items()):
        matches = albums[name]
        if len(matches) > 1:
            print(f"Skipping {name!r}: multiple owned albums have this name.", file=sys.stderr)
            failed = True
            continue

        album_id = matches[0] if matches else None
        if album_id:
            album = request("GET", f"/albums/{album_id}?withoutAssets=false")
            ids = ids.difference(asset["id"] for asset in album["assets"])

        action = "Update" if album_id else "Create"
        print(f"{action} {name!r}: {len(ids)} photos to add")
        if not apply or not ids:
            continue

        if not album_id:
            album_id = request("POST", "/albums", {"albumName": name})["id"]

        ordered_ids = sorted(ids)
        for offset in range(0, len(ordered_ids), 500):
            results = request("PUT", f"/albums/{album_id}/assets", {
                "ids": ordered_ids[offset:offset + 500],
            })
            for result in results:
                if not result["success"] and result.get("error") != "duplicate":
                    print(f"{name!r}: could not add {result['id']}: "
                          f"{result.get('error', 'unknown error')}", file=sys.stderr)
                    failed = True

    if not apply:
        print("Preview complete. Pass --apply to save changes.")
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("IMMICH_URL"),
                        help="Immich server URL (or set IMMICH_URL)")
    parser.add_argument("--apply", action="store_true", help="Create and update albums")
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
