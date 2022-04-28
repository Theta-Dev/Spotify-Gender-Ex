#!/bin/bash
set -e
cd -- "$( dirname -- "${BASH_SOURCE[0]}" )"

TARGET_DIR="/path/to/webroot"

mkdir -p GenderEx

docker run -v $(pwd)/GenderEx:/GenderEx -v /etc/localtime:/etc/localtime:ro -u 1000:1000 --env-file gex.env --rm thetadev256/spotify-gender-ex:latest

rm -rf GenderEx/tmp

if compgen -G 'GenderEx/output/*.apk' > /dev/null; then
    mv GenderEx/output/*.apk ${TARGET_DIR}
fi

# Only keep latest 4 apk files
ls ${TARGET_DIR}/*.apk -t | tail -n +5 | xargs --no-run-if-empty rm
