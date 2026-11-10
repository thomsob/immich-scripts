#!/bin/bash

# depends on https://pypi.org/project/osxphotos/
# and immich CLI and server running at $IMMICH_URL

IMMICH_URL="http://192.168.0.154:30041"
ROOT_FOLDER=/Volumes/nvme/check-as-off-Nov-2026
DESTINATION_FOLDER_ROOT=/Volumes/WD_BLACK/photos-export

if [ ! -d "$DESTINATION_FOLDER_ROOT" ]; then
    echo "Destination folder $DESTINATION_FOLDER_ROOT does not exist. Creating it now."
    mkdir -p "$DESTINATION_FOLDER_ROOT"
fi

if [ ! -d "$ROOT_FOLDER" ]; then
    echo "Root folder $ROOT_FOLDER does not exist. Please check the path."
    exit 1
fi

if [ -z "$IMMICH_API_KEY" ]; then
    echo "IMMICH_API_KEY environment variable is not set. Please set it before running the script."
    exit 1
fi

echo "Extracting and copying photos from $ROOT_FOLDER to Immich at $IMMICH_URL"


for LIBRARY in "$ROOT_FOLDER"/*.photoslibrary; do
    #if [[ "$LIBRARY" == *.photoslibrary ]]; then
        echo "========================="
        echo "Processing library: $LIBRARY"

        LIBRARY_NAME="${LIBRARY##*/}"
        LIBRARY_NAME="${LIBRARY_NAME%.photoslibrary}"
        DESTINATION_FOLDER="$DESTINATION_FOLDER_ROOT/$LIBRARY_NAME"
        if [ ! -d "$DESTINATION_FOLDER" ]; then
            echo "Destination folder $DESTINATION_FOLDER does not exist. Creating it now."
            mkdir -p "$DESTINATION_FOLDER"
        fi

        echo "$DESTINATION_FOLDER"

               
        # Extract and copy photos from the folder
        #osxphotos export --update --export-by-date --db "$LIBRARY" "$DESTINATION_FOLDER"
        
        # Copy the photos to the destination folder
        echo "Copying photos from $DESTINATION_FOLDER to Immich"
        immich upload -r "$DESTINATION_FOLDER" -H -a -k $IMMICH_API_KEY -u $IMMICH_URL
    #ßfi
done




