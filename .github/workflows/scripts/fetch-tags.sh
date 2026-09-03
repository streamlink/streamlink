#!/usr/bin/env bash
set -euxo pipefail

TARGET_DEPTH=300
CURRENT_DEPTH=$(git rev-list --count HEAD)

if [[ $(git rev-parse --is-shallow-repository) == "true" && CURRENT_DEPTH -lt TARGET_DEPTH ]]; then
  git fetch --no-tags --deepen=$((TARGET_DEPTH - CURRENT_DEPTH))
fi

# Fetch only the tags within our shallow-clone depth (set to 300 commits by @actions/checkout),
# so we can avoid fetching the entire repo, as it includes a BLOB that was committed years ago:
# 1. Query the remote
# 2. Filter peeled/annotated tags and reformat output
# 3. Query clone for known commit data
# 4. Filter out tags with unknown commit data (tags outside our fetch depth)
# 5. Fetch tags, so `git describe --tags` will work (assuming the fetch depth is large enough)
git ls-remote --tags origin \
  | awk '{ sub(/\^\{\}$/, "", $2); t[$2] = $1 } END { for (r in t) print t[r], "+" r ":" r }' \
  | git cat-file --buffer --batch-check='%(rest)' \
  | sed -n '/ missing$/!p' \
  | git fetch origin --stdin

git describe --tags --long --dirty
