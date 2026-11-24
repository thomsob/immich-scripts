#!/usr/bin/env python3
"""Find thumbnail-like images and add review candidates to Immich albums."""

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


THUMBNAIL_MAX_DIMENSION = 512
SMALL_IMAGE_MAX_BYTES = 1_000_000
ALBUM_NAMES = {
    "matched": "to-be-deleted",
    "unmatched": "possible-to-be-deleted",
    "small": "small images album",
}
THUMBNAIL_SUFFIX = re.compile(
    r"(?:[._ -](?:thumb(?:nail)?|preview|small))+$",
    re.IGNORECASE,
)


def image_dimensions(asset):
    width = asset.get("width")
    height = asset.get("height")
    if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
        return width, height
    return None


def is_named_thumbnail(asset):
    stem = Path(asset["originalFileName"]).stem
    return THUMBNAIL_SUFFIX.search(stem) is not None


def is_thumbnail(asset, max_dimension=THUMBNAIL_MAX_DIMENSION):
    dimensions = image_dimensions(asset)
    return is_named_thumbnail(asset) or (
        dimensions is not None and max(dimensions) <= max_dimension
    )


def normalized_stem(asset):
    stem = Path(asset["originalFileName"]).stem
    return THUMBNAIL_SUFFIX.sub("", stem).casefold()


def find_thumbnail_matches(assets, max_dimension=THUMBNAIL_MAX_DIMENSION):
    """Return each thumbnail ID mapped to its sole obvious original ID, if any."""
    assets_by_stem = {}
    for asset in assets:
        assets_by_stem.setdefault(normalized_stem(asset), []).append(asset)

    matches = {}
    for thumbnail in assets:
        if not is_thumbnail(thumbnail, max_dimension):
            continue

        candidates = [
            asset
            for asset in assets_by_stem[normalized_stem(thumbnail)]
            if asset["id"] != thumbnail["id"] and not is_thumbnail(asset, max_dimension)
        ]
        matches[thumbnail["id"]] = candidates[0]["id"] if len(candidates) == 1 else None
    return matches


def find_small_images(assets):
    return {
        asset["id"]
        for asset in assets
        if int(asset["fileSizeInByte"]) < SMALL_IMAGE_MAX_BYTES
    }


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

    assets = []
    page = 1
    while page is not None:
        result = request("POST", "/search/metadata", {
            "type": "IMAGE",
            "page": page,
            "size": 1000,
        })["assets"]
        assets.extend(result["items"])
        next_page = result["nextPage"]
        page = int(next_page) if next_page is not None else None

    matches = find_thumbnail_matches(assets)
    assets_by_id = {asset["id"]: asset for asset in assets}
    groups = {
        ALBUM_NAMES["matched"]: {
            asset_id for asset_id, match_id in matches.items() if match_id is not None
        },
        ALBUM_NAMES["unmatched"]: {
            asset_id for asset_id, match_id in matches.items() if match_id is None
        },
        ALBUM_NAMES["small"]: find_small_images(assets),
    }

    for asset_id, match_id in sorted(
        matches.items(), key=lambda item: assets_by_id[item[0]]["originalFileName"].casefold()
    ):
        thumbnail = assets_by_id[asset_id]["originalFileName"]
        if match_id is None:
            print(f"Possible thumbnail: {thumbnail!r} (no unique original match)")
        else:
            original = assets_by_id[match_id]["originalFileName"]
            print(f"Matched thumbnail: {thumbnail!r} -> {original!r}")

    albums = {}
    for album in request("GET", "/albums?shared=false"):
        albums.setdefault(album["albumName"], []).append(album["id"])

    failed = False
    for album_name, asset_ids in groups.items():
        existing_albums = albums.get(album_name, [])
        if len(existing_albums) > 1:
            print(f"Skipping {album_name!r}: multiple owned albums have that name.",
                  file=sys.stderr)
            failed = True
            continue

        album_id = existing_albums[0] if existing_albums else None
        if album_id:
            existing_ids = set()
            page = 1
            while page is not None:
                result = request("POST", "/search/metadata", {
                    "albumIds": [album_id],
                    "page": page,
                    "size": 1000,
                })["assets"]
                existing_ids.update(asset["id"] for asset in result["items"])
                next_page = result["nextPage"]
                page = int(next_page) if next_page is not None else None
        else:
            existing_ids = set()

        ids_to_add = sorted(asset_ids - existing_ids)
        print(f"{album_name!r}: {len(ids_to_add)} image(s) to add")
        if not apply or not ids_to_add:
            continue

        try:
            if album_id is None:
                album_id = request("POST", "/albums", {"albumName": album_name})["id"]
                albums[album_name] = [album_id]

            for offset in range(0, len(ids_to_add), 500):
                results = request("PUT", f"/albums/{album_id}/assets", {
                    "ids": ids_to_add[offset:offset + 500],
                })
                if any(
                    not result["success"] and result.get("error") != "duplicate"
                    for result in results
                ):
                    raise RuntimeError(f"Immich did not add all images to {album_name!r}")

            verify_ids = set()
            page = 1
            while page is not None:
                result = request("POST", "/search/metadata", {
                    "albumIds": [album_id],
                    "page": page,
                    "size": 1000,
                })["assets"]
                verify_ids.update(asset["id"] for asset in result["items"])
                next_page = result["nextPage"]
                page = int(next_page) if next_page is not None else None
            if not asset_ids.issubset(verify_ids):
                raise RuntimeError(f"Could not verify all images in {album_name!r}")
        except (RuntimeError, URLError, TimeoutError, KeyError, TypeError) as error:
            print(f"Could not update {album_name!r}: {error}", file=sys.stderr)
            failed = True

    if not apply:
        print("Preview only. Pass --apply to add these images to the albums.")
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
    except (RuntimeError, URLError, TimeoutError, ValueError, KeyError, TypeError) as error:
        print(f"Immich request or response error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
