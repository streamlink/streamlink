#!/bin/sh
# Downloads a prebuilt bootstrap from a Windows build
# and injects a fresh egg into it.

SCRIPT_DIR=$(cd $(dirname $0); pwd -P)
SOURCE_DIR="$SCRIPT_DIR/.."
BUILD_DIR="$SOURCE_DIR/build"
BUILD_TARGET_DIR="$BUILD_DIR/livestreamer-$(git describe)"
DIST_DIR="$SOURCE_DIR/dist"
DIST_TARGET="$DIST_DIR/livestreamer-$(git describe)-win32.zip"
BOOTSTRAP_PATH="$BUILD_DIR/livestreamer-bootstrap.zip"
BOOTSTRAP_URL="http://livestreamer-builds.s3.amazonaws.com/livestreamer-bootstrap.zip"

if [ ! -d $BUILD_DIR ]; then
	mkdir "$BUILD_DIR"
fi

if [ -d "$BUILD_TARGET_DIR" ]; then
	rm -rf $BUILD_TARGET_DIR
fi

if [ ! -f $BOOTSTRAP_PATH ]; then
	wget -O $BOOTSTRAP_PATH $BOOTSTRAP_URL
fi

unzip -d $BUILD_TARGET_DIR $BOOTSTRAP_PATH

cd $SOURCE_DIR
NO_DEPS=1 python setup.py bdist_egg
egg=$(basename dist/*.egg)

unzip -d "$BUILD_TARGET_DIR/$egg" "dist/$egg"

cd $BUILD_DIR
zip -r $DIST_TARGET "$(basename "$BUILD_TARGET_DIR")"

cd $SCRIPT_DIR
makensis -DPROGRAM_VERSION=$(git describe) -DLIVESTREAMER_PYTHON_BBFREEZE_OUTPUT_DIR="$BUILD_TARGET_DIR" "livestreamer-win32-installer-from-bootstrap.nsi"
