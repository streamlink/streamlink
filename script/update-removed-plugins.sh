#!/usr/bin/env bash
set -eo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || realpath "$(dirname "$(readlink -f "${0}")")/..")
DIR_PLUGINS="${ROOT}/src/streamlink/plugins/"
FILE_REMOVED="${DIR_PLUGINS}/.removed"

# ----

[[ -d "${DIR_PLUGINS}" ]] || { echo >&2 "Missing directory: ${DIR_PLUGINS}"; exit 1; }
[[ -f "${FILE_REMOVED}" ]] || { echo >&2 "Missing file: ${FILE_REMOVED}"; exit 1; }

get_plugin_names() {
    grep -E '\.py$' | LC_ALL=C sort -u | xargs -I@ basename @ .py
}

header=$(sed -e '/^[^#;]/d' "${FILE_REMOVED}")
content=$(
    `# Only show plugin names which are unique to the first list` \
    comm -23 --nocheck-order \
        `# Find all deleted and renamed files in the plugins directory` \
        <(git log --diff-filter=DR --name-status --pretty=tformat: "${DIR_PLUGINS}" | cut -f2 | get_plugin_names) \
        `# Find all current plugin names` \
        <(find "${DIR_PLUGINS}" -type f | get_plugin_names)
)

cat >"${FILE_REMOVED}" <<EOF
${header}
${content}
EOF
