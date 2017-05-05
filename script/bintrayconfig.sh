#!/usr/bin/env bash
#
# Script to generate bintray config for nightly builds
#

build_dir="$(pwd)/build"
nsis_dir="${build_dir}/nsis"
# get the dist directory from an environment variable, but default to the build/nsis directory
dist_dir="${STREAMLINK_INSTALLER_DIST_DIR:-$nsis_dir}"

# TODO: extract this common version detection code in to a separate function
STREAMLINK_VERSION_PLAIN=$(python setup.py --version)
# For travis nightly builds generate a version number with commit hash
if [ -n "${TRAVIS_BRANCH}" ] && [ -z "${TRAVIS_TAG}" ]; then
    STREAMLINK_VI_VERSION="${STREAMLINK_VERSION_PLAIN}.${TRAVIS_BUILD_NUMBER}"
    STREAMLINK_INSTALLER="streamlink-${STREAMLINK_VERSION_PLAIN}-${TRAVIS_BUILD_NUMBER}-${TRAVIS_COMMIT:0:7}"
    STREAMLINK_VERSION="${STREAMLINK_VERSION_PLAIN}+${TRAVIS_COMMIT:0:7}"
else
    STREAMLINK_VI_VERSION="${STREAMLINK_VERSION_PLAIN}.${TRAVIS_BUILD_NUMBER:-0}"
    STREAMLINK_VERSION="${STREAMLINK_VERSION_PLAIN}"
    STREAMLINK_INSTALLER="streamlink-${STREAMLINK_VERSION}"
fi

cat > "${build_dir}/bintray-latest.json" <<EOF
{
  "package": {
    "subject": "streamlink",
    "repo": "streamlink-nightly",
    "name": "streamlink"
  },

  "version": {
    "name": "latest",
    "released": "$(date +'%Y-%m-%d')",
    "desc": "Latest version of the installer (${STREAMLINK_VERSION})"
  },

  "files": [
    {
      "includePattern": "${dist_dir}/${STREAMLINK_INSTALLER}.exe",
      "uploadPattern": "streamlink-latest.exe",
      "matrixParams": {
        "override": 1,
        "publish": 1
      }
    }
  ],

  "publish": true
}
EOF

echo "Wrote Bintray config to: ${build_dir}/bintray-latest.json"

cat > "${build_dir}/bintray-nightly.json" <<EOF
{
  "package": {
    "subject": "streamlink",
    "repo": "streamlink-nightly",
    "name": "streamlink"
  },

  "version": {
    "name": "$(date +'%Y.%m.%d')",
    "released": "$(date +'%Y-%m-%d')",
    "desc": "Streamlink Nightly based on ${STREAMLINK_VERSION}"
  },

  "files": [
    {
      "includePattern": "${dist_dir}/${STREAMLINK_INSTALLER}.exe",
      "uploadPattern": "streamlink-${STREAMLINK_VERSION_PLAIN}-$(date +'%Y%m%d').exe",
      "matrixParams": {
        "override": 1,
        "publish": 1
      }
    }
  ],

  "publish": true
}
EOF

echo "Wrote Bintray config to: ${build_dir}/bintray-nightly.json"
