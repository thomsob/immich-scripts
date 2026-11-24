#!/bin/bash

# depends on https://pypi.org/project/osxphotos/
# and immich CLI and server running at $IMMICH_URL

IMMICH_URL="http://192.168.0.154:30041"
ROOT_FOLDER=/Users/brian/Downloads/
DESTINATION_FOLDER_ROOT=/Volumes/WD_BLACK/photos-export

if [ ! -d "$ROOT_FOLDER" ]; then
    echo "Root folder $ROOT_FOLDER does not exist. Please check the path."
    exit 1
fi

if [ -z "$IMMICH_API_KEY" ]; then
    echo "IMMICH_API_KEY environment variable is not set. Please set it before running the script."
    exit 1
fi

echo "Copying photos from $ROOT_FOLDER to Immich at $IMMICH_URL"


for LIBRARY in "$ROOT_FOLDER"/*; do
        echo "========================="
       
        echo "Copying photos from $LIBRARY to Immich"
        immich upload -r "$LIBRARY" -H -a -k $IMMICH_API_KEY -u $IMMICH_URL
    #ßfi
done




