
SOURCE_DIR="/Volumes/data/immich/"
DESTINATION_DIR="/Volumes/8GB/Photos/immich/"

rsync -rltvh --delete --size-only --progress --stats \
--exclude=".DS_Store" \
  --exclude="._*" \
  --exclude=".Spotlight-V100" \
  --exclude=".Trashes" \
  --exclude="@eaDir" \
"$SOURCE_DIR" "$DESTINATION_DIR"
