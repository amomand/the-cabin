#!/bin/sh
set -eu

# Xcode build phase: select and embed the prepared runtime slice, then install
# its standard library and process extension modules into signed frameworks.

PYTHON_XCFRAMEWORK="$PROJECT_DIR/EmbeddedPython/Python.xcframework"
if [ "$EFFECTIVE_PLATFORM_NAME" = "-iphonesimulator" ]; then
    PYTHON_SLICE="ios-arm64_x86_64-simulator"
elif [ "$EFFECTIVE_PLATFORM_NAME" = "-iphoneos" ]; then
    PYTHON_SLICE="ios-arm64"
else
    echo "Unsupported embedded-Python platform: $EFFECTIVE_PLATFORM_NAME" >&2
    exit 1
fi

if [ -z "${EXPANDED_CODE_SIGN_IDENTITY:-}" ]; then
    export EXPANDED_CODE_SIGN_IDENTITY="-"
    export EXPANDED_CODE_SIGN_IDENTITY_NAME="Ad Hoc"
fi

mkdir -p "$CODESIGNING_FOLDER_PATH/Frameworks/Python.framework"
rsync -a --delete \
    "$PYTHON_XCFRAMEWORK/$PYTHON_SLICE/Python.framework/" \
    "$CODESIGNING_FOLDER_PATH/Frameworks/Python.framework/"
# Xcode supplies OTHER_CODE_SIGN_FLAGS as a shell-style list of flags.
# shellcheck disable=SC2086
/usr/bin/codesign \
    --force \
    --sign "$EXPANDED_CODE_SIGN_IDENTITY" \
    ${OTHER_CODE_SIGN_FLAGS:-} \
    --timestamp=none \
    --preserve-metadata=identifier,entitlements,flags \
    --generate-entitlement-der \
    "$CODESIGNING_FOLDER_PATH/Frameworks/Python.framework"

mkdir -p "$CODESIGNING_FOLDER_PATH/app" "$CODESIGNING_FOLDER_PATH/app_packages"
rsync -a --delete \
    "$PROJECT_DIR/EmbeddedPython/app/" \
    "$CODESIGNING_FOLDER_PATH/app/"
rsync -a --delete \
    "$PROJECT_DIR/EmbeddedPython/app_packages/" \
    "$CODESIGNING_FOLDER_PATH/app_packages/"

# shellcheck source=/dev/null
. "$PYTHON_XCFRAMEWORK/build/utils.sh"
install_python EmbeddedPython/Python.xcframework app app_packages
