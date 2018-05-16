#!/usr/bin/env bash
#
# Script to generate bintray config for nightly builds
#

build_dir="$(pwd)/build"
nsis_dir="${build_dir}/nsis"
# get the dist directory from an environment variable, but default to the build/nsis directory
dist_dir="${STREAMLINK_INSTALLER_DIST_DIR:-$nsis_dir}"

# TODO: extract this common version detection code in to a separate function
# For travis nightly builds generate a version number with commit hash
STREAMLINK_VERSION=$(python setup.py --version)
STREAMLINK_VERSION_PLAIN="${STREAMLINK_VERSION%%+*}"
STREAMLINK_INSTALLER="streamlink-${STREAMLINK_VERSION/\+/_}"


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

# update repo to full clone and get the tags
git fetch --unshallow
git fetch --tags
latest_tag=$(git describe --tags --abbrev=0)
tag_changes_json=$(git log ${latest_tag}..HEAD --no-merges --pretty=format:" * [\`%h\`](https://github.com/streamlink/streamlink/commit/%H) %s" | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/"/\\"/g')
echo "{\"bintray\": {\"content\": \"**This build includes the following changes since [v${latest_tag}](https://github.com/streamlink/streamlink/releases/tag/${latest_tag})**\n\n${tag_changes_json}\"}}" > "${build_dir}/bintray-changelog.json"

echo "Wrote changelog to ${build_dir}/bintray-changelog.json"
