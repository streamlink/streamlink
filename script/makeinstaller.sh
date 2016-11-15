#!/usr/bin/env bash
# Execute this at the base of the streamlink repo.

set -e # stop on error

STREAMLINK_VERSION=$(python -c 'import streamlink; print(streamlink.__version__)')
STREAMLINK_INSTALLER="streamlink-${STREAMLINK_VERSION}"

# For travis nightly builds generate a version number with commit hash
if [ -n "${TRAVIS_BRANCH}" ] && [ -z "${TRAVIS_TAG}" ]; then
    STREAMLINK_INSTALLER="streamlink-${STREAMLINK_VERSION}-${TRAVIS_BUILD_NUMBER}-${TRAVIS_COMMIT:0:7}"
    STREAMLINK_VERSION="${STREAMLINK_VERSION}+${TRAVIS_COMMIT:0:7}"
fi

build_dir="$(pwd)/build"
# get the dist directory from an environment variable, but default to the build/nsis directory
dist_dir="${STREAMLINK_INSTALLER_DIST_DIR:-$(pwd)/build/nsis}"
mkdir -p "${build_dir}" "${dist_dir}"

echo "Building ${STREAMLINK_INSTALLER} (v${STREAMLINK_VERSION})..." 1>&2

cat > build/streamlink.cfg <<EOF
[Application]
name=Streamlink
version=${STREAMLINK_VERSION}
entry_point=streamlink_cli.main:main

[Python]
version=3.5.2
format=bundled

[Include]
packages=requests
         streamlink
         streamlink_cli

files=../win32/rtmpdump > \$INSTDIR

[Command streamlink]
entry_point=streamlink_cli.main:main

[Build]
directory=nsis
installer_name=${dist_dir}/${STREAMLINK_INSTALLER}.exe
EOF

echo "Building Python 3 installer" 1>&2
pynsist build/streamlink.cfg

# Make a copy of this build for the "latest" nightly
if [ -n "${TRAVIS_BRANCH}" ] && [ -z "${TRAVIS_TAG}" ]; then
    cp "${dist_dir}/${STREAMLINK_INSTALLER}.exe" "${dist_dir}/streamlink-latest.exe"
fi

echo "Success!" 1>&2
echo "The installer should be in ${dist_dir}." 1>&2
