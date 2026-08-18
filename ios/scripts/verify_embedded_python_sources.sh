#!/bin/sh
set -eu

REPO_DIR=${1:?repository root is required}
PAYLOAD_DIR=${2:?prepared app payload is required}

stale=false
for source_dir in game server; do
    if ! diff -qr -x '__pycache__' -x '*.pyc' \
        "$REPO_DIR/$source_dir" "$PAYLOAD_DIR/$source_dir" >/dev/null; then
        stale=true
    fi
done
if ! cmp -s "$REPO_DIR/config.json.example" "$PAYLOAD_DIR/config.json"; then
    stale=true
fi

if [ "$stale" = true ]; then
    echo "Embedded Python payload is stale; run ios/scripts/refresh_embedded_sources.sh (or prepare_embedded_python.sh if the runtime is not prepared)" >&2
    exit 1
fi
