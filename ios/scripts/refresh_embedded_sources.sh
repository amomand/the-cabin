#!/bin/sh
set -eu

# Re-sync only the shared Python payload (game/, server/, config.json.example)
# into the prepared embedded runtime. This is the fast path after editing
# shared engine code; the framework and wheels are left alone, so the runtime
# must already have been prepared by prepare_embedded_python.sh.

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
IOS_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
REPO_DIR=$(CDPATH='' cd -- "$IOS_DIR/.." && pwd)
RUNTIME_DIR="$IOS_DIR/EmbeddedPython"

if [ ! -f "$RUNTIME_DIR/PREPARED.txt" ] \
    || [ ! -f "$RUNTIME_DIR/Python.xcframework/Info.plist" ] \
    || [ ! -d "$RUNTIME_DIR/app_packages" ]; then
    echo "Embedded Python runtime is not prepared; run ios/scripts/prepare_embedded_python.sh first" >&2
    exit 1
fi

STAGING_DIR=$(mktemp -d "${TMPDIR:-/tmp}/the-cabin-python-app.XXXXXX")
trap 'rm -rf "$STAGING_DIR"' EXIT INT TERM

APP_STAGE="$STAGING_DIR/app"
mkdir -p "$APP_STAGE"
rsync -a --exclude '__pycache__' --exclude '*.pyc' "$REPO_DIR/game" "$APP_STAGE/"
rsync -a --exclude '__pycache__' --exclude '*.pyc' "$REPO_DIR/server" "$APP_STAGE/"
cp "$REPO_DIR/config.json.example" "$APP_STAGE/config.json"
mkdir -p "$RUNTIME_DIR/app"
rsync -a --delete "$APP_STAGE/" "$RUNTIME_DIR/app/"

echo "Refreshed embedded app payload at $RUNTIME_DIR/app"
