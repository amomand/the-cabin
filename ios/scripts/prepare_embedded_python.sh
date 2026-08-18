#!/bin/sh
set -eu

# Reproducibly prepare the BeeWare CPython runtime and pure-Python HTTP stack.
# The 115 MB framework and generated app payload stay outside git.

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
IOS_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
REPO_DIR=$(CDPATH='' cd -- "$IOS_DIR/.." && pwd)
RUNTIME_DIR="$IOS_DIR/EmbeddedPython"
CACHE_DIR="$RUNTIME_DIR/cache"
ARCHIVE_NAME="Python-3.13-iOS-support.b14.tar.gz"
ARCHIVE_URL="https://github.com/beeware/Python-Apple-support/releases/download/3.13-b14/$ARCHIVE_NAME"
ARCHIVE_SHA256="8b5cb76ef8d8a2946052479358eeec9d54b4496cb60920e175ec1489b5cf7963"
# Version- and hash-pinned pure-Python wheels; pip refuses anything that does
# not match, whether downloaded here or supplied through CABIN_WHEELHOUSE.
REQUIREMENTS_FILE="$IOS_DIR/requirements-ios.txt"

mkdir -p "$CACHE_DIR"
ARCHIVE_PATH=${CABIN_PYTHON_ARCHIVE:-"$CACHE_DIR/$ARCHIVE_NAME"}
if [ ! -f "$ARCHIVE_PATH" ]; then
    curl --fail --location --retry 3 --output "$ARCHIVE_PATH" "$ARCHIVE_URL"
fi

ACTUAL_SHA256=$(shasum -a 256 "$ARCHIVE_PATH" | awk '{print $1}')
if [ "$ACTUAL_SHA256" != "$ARCHIVE_SHA256" ]; then
    echo "Embedded Python archive checksum mismatch" >&2
    exit 1
fi

STAGING_DIR=$(mktemp -d "${TMPDIR:-/tmp}/the-cabin-python.XXXXXX")
trap 'rm -rf "$STAGING_DIR"' EXIT INT TERM
tar -xzf "$ARCHIVE_PATH" -C "$STAGING_DIR"
if [ ! -f "$STAGING_DIR/Python.xcframework/Info.plist" ]; then
    echo "Embedded Python archive did not contain Python.xcframework" >&2
    exit 1
fi

mkdir -p "$RUNTIME_DIR/Python.xcframework"
rsync -a --delete \
    "$STAGING_DIR/Python.xcframework/" \
    "$RUNTIME_DIR/Python.xcframework/"

WHEEL_DIR="$STAGING_DIR/wheels"
mkdir -p "$WHEEL_DIR"
if [ -n "${CABIN_WHEELHOUSE:-}" ]; then
    rsync -a "$CABIN_WHEELHOUSE/" "$WHEEL_DIR/"
else
    python3 -m pip download \
        --disable-pip-version-check \
        --only-binary=:all: \
        --no-deps \
        --require-hashes \
        --dest "$WHEEL_DIR" \
        --requirement "$REQUIREMENTS_FILE"
fi

if find "$WHEEL_DIR" -type f -name '*.whl' ! -name '*-none-any.whl' | grep -q .; then
    echo "Embedded dependency set contains a platform wheel" >&2
    exit 1
fi

PACKAGE_STAGE="$STAGING_DIR/app_packages"
python3 -m pip install \
    --disable-pip-version-check \
    --no-compile \
    --no-deps \
    --no-index \
    --require-hashes \
    --find-links "$WHEEL_DIR" \
    --target "$PACKAGE_STAGE" \
    --requirement "$REQUIREMENTS_FILE"

if find "$PACKAGE_STAGE" -type f \( -name '*.so' -o -name '*.dylib' \) | grep -q .; then
    echo "Embedded dependency set contains a native extension" >&2
    exit 1
fi
if find "$PACKAGE_STAGE" -maxdepth 1 \( -iname 'openai*' -o -iname 'pydantic*' \) | grep -q .; then
    echo "OpenAI SDK or pydantic leaked into the embedded dependency set" >&2
    exit 1
fi

mkdir -p "$RUNTIME_DIR/app_packages"
rsync -a --delete "$PACKAGE_STAGE/" "$RUNTIME_DIR/app_packages/"

APP_STAGE="$STAGING_DIR/app"
mkdir -p "$APP_STAGE"
rsync -a --exclude '__pycache__' --exclude '*.pyc' "$REPO_DIR/game" "$APP_STAGE/"
rsync -a --exclude '__pycache__' --exclude '*.pyc' "$REPO_DIR/server" "$APP_STAGE/"
cp "$REPO_DIR/config.json.example" "$APP_STAGE/config.json"
mkdir -p "$RUNTIME_DIR/app"
rsync -a --delete "$APP_STAGE/" "$RUNTIME_DIR/app/"

printf '%s\n' \
    "Python Apple Support: 3.13-b14" \
    "Archive SHA256: $ARCHIVE_SHA256" \
    "Model transport: direct-httpx (no OpenAI SDK or pydantic-core)" \
    > "$RUNTIME_DIR/PREPARED.txt"

echo "Prepared embedded Python at $RUNTIME_DIR"
