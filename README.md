# immich-scripts
a selection of scripts to manage an Immich library

## List albums

`list-albums.py` prints each album's name and Immich asset count (including
videos). It includes owned and shared albums.

```sh
export IMMICH_URL="https://your-immich-server"
export IMMICH_API_KEY="your-api-key"
python3 list-albums.py
```

Alternatively, pass the server URL with `--url`; if `IMMICH_API_KEY` is not
set, the script prompts for the API key.

## Delete `IMG_` albums

`delete-img-albums.py` targets owned albums whose names begin with the exact
prefix `IMG_`. It previews matches by default. Review the list, then pass
`--apply` to delete the albums. This uses Immich's album-delete endpoint only;
the photos and videos in those albums are kept.

```sh
python3 delete-img-albums.py
python3 delete-img-albums.py --apply
```

It uses the same `IMMICH_URL` and `IMMICH_API_KEY` settings as `list-albums.py`.

## Find thumbnails and small images

`find_thumbnail_albums.py` scans image assets and previews album updates by
default. It identifies thumbnail-like images by a thumbnail suffix in the
filename (`thumb`, `thumbnail`, `preview`, or `small`) or dimensions no larger
than 512 pixels on either side. A thumbnail is considered to have a clear
original match only when exactly one non-thumbnail has the same normalized
filename stem. Matched thumbnails go into `to-be-deleted`; thumbnails without
a unique match go into `possible-to-be-deleted`. All images smaller than
1,000,000 bytes go into `small images album`, including any thumbnails.

Review the preview, then pass `--apply` to create or update those albums. The
script does not delete assets.

```sh
python3 find_thumbnail_albums.py
python3 find_thumbnail_albums.py --apply
```

It uses the same `IMMICH_URL` and `IMMICH_API_KEY` settings as `list-albums.py`.

## Delete date-prefixed albums

`delete-date-albums.py` targets owned albums whose names start with a date in
`D MMM YYYY` or `DD MMM YYYY` format, such as `1 Mar 2024` or
`01 Mar 2024 holiday`, as well as exact `YYYY-MM-DD` names such as
`2024-03-01`, and `YYYY-{month-name}` names such as `1970-January`. Month names
are case-insensitive. It also targets exact `MMM YYYY` albums such as
`Jan 1970`. It previews matches by default. With `--apply`, it adds each
dated album's photos and videos to the corresponding `MMM YYYY` album for
`D MMM YYYY`/`DD MMM YYYY` names, or `YYYY-MM` album for ISO dates,
month-name albums, and abbreviated month-year albums (creating it if needed),
verifies the assets are present there, then removes the dated album. If a move
cannot be verified, the source album is left in place.

```sh
python3 delete-date-albums.py
python3 delete-date-albums.py --apply
```

It uses the same `IMMICH_URL` and `IMMICH_API_KEY` settings as `list-albums.py`.
