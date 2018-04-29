#!/usr/bin/env bash
set -e
# Update the Bintray release

old_date=$(date +"%Y.%m.%d" -d "30 days ago")
build_dir="$(pwd)/build"
api_base="https://api.bintray.com/packages/streamlink/streamlink-nightly/streamlink"
current_api_url="${api_base}/versions/$(date +'%Y.%m.%d')/release_notes"
files_api_url="${api_base}/files"
versions_api_url="${api_base}/versions"

curl -u "${BINTRAY_USER}:${BINTRAY_KEY}" -H "Content-Type: application/json" -d @"${build_dir}/bintray-changelog.json" "${current_api_url}"

echo "Deleting versions older than ${old_date}..."
versions=$(curl -s -u "${BINTRAY_USER}:${BINTRAY_KEY}" "${files_api_url}" | jq -r '.[].version')

for version in $versions; do
    if [[ "$version" < "$old_date" ]]; then
        curl -s -u "${BINTRAY_USER}:${BINTRAY_KEY}" -X DELETE "${versions_api_url}/${version}" -o /dev/null && echo "Deleted version: ${version}"
    fi
done
