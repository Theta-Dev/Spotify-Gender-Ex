#!/bin/bash
set -e
cd -- "$( dirname -- "${BASH_SOURCE[0]}" )"

TARGET_DIR="/path/to/webroot"

mkdir -p GenderEx

docker run -v $(pwd)/GenderEx:/GenderEx -u 1000:1000 --env-file gex.env --rm thetadev256/spotify-gender-ex:latest

rm -r GenderEx/tmp
mv GenderEx/output/*.apk ${TARGET_DIR}

# Only keep latest 4 apk files
ls ${TARGET_DIR}/*.apk -t | tail -n +5 | xargs rm
