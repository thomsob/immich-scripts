#!/usr/bin/env python3
"""Merge date-named album assets into monthly albums and remove source albums."""

import argparse
from datetime import datetime
from getpass import getpass
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DATE_PREFIX = re.compile(
    r"^(?:0?[1-9]|[12]\d|3[01]) "
    r"(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"(?P<year>\d{4}).*$",
    re.IGNORECASE,
)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
YEAR_MONTH_NAME = re.compile(
    r"^(?P<year>\d{4})-(?P<month>"
    r"January|February|March|April|May|June|July|August|September|October|November|December"
    r")$",
    re.IGNORECASE,
)
MONTH_YEAR_ABBREVIATION = re.compile(
    r"^(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"(?P<year>\d{4})$",
    re.IGNORECASE,
)
MONTH_NUMBERS = {
    month.casefold(): f"{number:02d}"
    for number, name in enumerate(
        ("January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"),
        start=1,
    )
    for month in (name, name[:3])
}


def target_album_name(name):
    match = YEAR_MONTH_NAME.fullmatch(name)
    if match:
        return f"{match['year']}-{MONTH_NUMBERS[match['month'].casefold()]}"

    match = MONTH_YEAR_ABBREVIATION.fullmatch(name)
    if match:
        return f"{match['year']}-{MONTH_NUMBERS[match['month'].casefold()]}"

    if ISO_DATE.fullmatch(name):
        try:
            date = datetime.strptime(name, "%Y-%m-%d")
        except ValueError:
            return None
        return date.strftime("%Y-%m")

    match = DATE_PREFIX.match(name)
    if match:
        return f"{match['month'].title()} {match['year']}"
    return None


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
                return None if method == "DELETE" else json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"{method} {path}: HTTP {error.code}") from error

    def get_album_asset_ids(album_id):
        asset_ids = set()
        page = 1
        while page is not None:
            result = request("POST", "/search/metadata", {
                "albumIds": [album_id],
                "page": page,
                "size": 1000,
            })["assets"]
            asset_ids.update(asset["id"] for asset in result["items"])
            next_page = result["nextPage"]
            page = int(next_page) if next_page is not None else None
        return asset_ids

    albums = request("GET", "/albums?isOwned=true")
    matches = sorted(
        (album for album in albums if target_album_name(album["albumName"])),
        key=lambda album: album["albumName"].casefold(),
    )
    if not matches:
        print("No owned date-named albums were found.")
        if apply:
            print("Albums deleted: 0; albums created: 0")
        else:
            print("Albums to delete: 0; albums to create: 0")
        return 0

    albums_by_name = {}
    for album in albums:
        albums_by_name.setdefault(album["albumName"], []).append(album)

    failed = False
    deleted_count = 0
    created_count = 0
    planned_deletions = 0
    planned_creations = set()
    for album in matches:
        name = album["albumName"]
        target_name = target_album_name(name)
        targets = albums_by_name.get(target_name, [])

        if len(targets) > 1:
            print(f"Skipping {name!r}: multiple owned {target_name!r} albums exist.",
                  file=sys.stderr)
            failed = True
            continue

        target = targets[0] if targets else None
        if not apply:
            planned_deletions += 1
            if target is None and album["assetCount"] > 0:
                planned_creations.add(target_name)
            action = f"add to {target_name!r}" if target else f"create {target_name!r}"
            print(f"Would {action}, move {album['assetCount']} assets from {name!r}, "
                  f"then remove the source album")
            continue

        try:
            source_ids = get_album_asset_ids(album["id"])
            if len(source_ids) != album["assetCount"]:
                raise RuntimeError(
                    f"album reports {album['assetCount']} assets but returned "
                    f"{len(source_ids)}; leaving the source album untouched"
                )

            if source_ids:
                if target is None:
                    target = request("POST", "/albums", {"albumName": target_name})
                    albums_by_name[target_name] = [target]
                    created_count += 1

                existing_ids = get_album_asset_ids(target["id"])
                ids_to_add = sorted(source_ids - existing_ids)
                for offset in range(0, len(ids_to_add), 500):
                    results = request("PUT", f"/albums/{target['id']}/assets", {
                        "ids": ids_to_add[offset:offset + 500],
                    })
                    if results is None or any(
                        not result["success"] and result.get("error") != "duplicate"
                        for result in results
                    ):
                        raise RuntimeError(f"Immich did not add all assets to {target_name!r}")

                target_ids = get_album_asset_ids(target["id"])
                if not source_ids.issubset(target_ids):
                    raise RuntimeError(
                        f"could not verify all assets in {target_name!r}; "
                        "leaving the source album untouched"
                    )

            request("DELETE", f"/albums/{album['id']}")
            deleted_count += 1
            if source_ids:
                print(f"Merged {album['assetCount']} assets from {name!r} into "
                      f"{target_name!r} and removed the source album")
            else:
                print(f"Removed empty source album {name!r}")
        except (RuntimeError, URLError, TimeoutError, KeyError, TypeError) as error:
            print(f"Could not merge {name!r}: {error}", file=sys.stderr)
            failed = True

    if not apply:
        print("Preview only. Pass --apply to merge assets into monthly albums "
              "and remove the dated albums.")
        print(f"Albums to delete: {planned_deletions}; "
              f"albums to create: {len(planned_creations)}")
    else:
        print(f"Albums deleted: {deleted_count}; albums created: {created_count}")
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
