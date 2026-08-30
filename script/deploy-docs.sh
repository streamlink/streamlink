#!/usr/bin/env bash
shopt -s nullglob
set -eo pipefail

[[ -n "${GITHUB_ACTIONS}" ]] || [[ -n "${DOCS_DEPLOY_TOKEN}" ]] || exit 1

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || realpath "$(dirname "$(readlink -f "${0}")")/..")

DOCS_DIR=${DOCS_DIR:-"${ROOT}/docs/_build/html"}
DOCS_REPO=${DOCS_REPO:-streamlink/streamlink.github.io}
DOCS_BRANCH=${DOCS_BRANCH:-master}
DOCS_USER=${DOCS_USER:-streamlinkbot}
DOCS_EMAIL=${DOCS_EMAIL:-streamlinkbot@users.noreply.github.com}

FILELIST=".doctr-files"

if [[ "${GITHUB_REF}" =~ ^refs/tags/ ]]; then
    WHAT="tag"
    NAME="${GITHUB_REF/#refs\/tags\//}"
    DEST="."
else
    WHAT="branch"
    NAME="${GITHUB_REF/#refs\/heads\//}"
    DEST="latest"
fi


if ! [[ -s "${DOCS_DIR}/index.html" ]]; then
    echo Missing or empty index.html
    exit 1
fi


echo Creating temporary directory
TEMP=$(mktemp -d) && trap "rm -rf ${TEMP}" EXIT || exit 255
cd "${TEMP}"


echo Cloning repository...
git clone \
    --depth=1 \
    --origin=origin \
    --branch="${DOCS_BRANCH}" \
    "https://github.com/${DOCS_REPO}.git" \
    .

echo Deleting all files stored in \'${DEST}\' file list
cat "${DEST}/${FILELIST}" | xargs realpath -- | awk -v P="$(pwd)" '$0 ~ P "/" {print $0}' | xargs rm --force --

echo Copying new files into \'${DEST}\'
mkdir --parents "${DEST}"
cp --archive "${DOCS_DIR}/." "${DEST}/"

echo Building a new file list in \'${DEST}\'
( cd "${DOCS_DIR}"; find . -type f | LC_ALL=C sort | sed "s/^\\.\//${DEST}\//" > "${TEMP}/${DEST}/${FILELIST}" )

if [[ -z "$(git status --porcelain)" ]]; then
    echo No changes to be committed. Exiting...
    exit 0
fi

echo Staging changes
git add --all

echo Committing changes
git config --local user.name "${DOCS_USER}"
git config --local user.email "${DOCS_EMAIL}"
cat << EOM | git commit -F-
Update docs from Github build ${GITHUB_RUN_NUMBER}

of ${GITHUB_REPOSITORY}

The docs were built from the ${WHAT} '${NAME}' against the commit
${GITHUB_SHA}

https://github.com/${GITHUB_REPOSITORY}/commit/${GITHUB_SHA:0:7}
https://github.com/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}
EOM

echo Pushing changes
git config --unset 'http.https://github.com/.extraheader' || true
git remote set-url --push origin "https://${DOCS_USER}:${DOCS_DEPLOY_TOKEN}@github.com/${DOCS_REPO}.git"
git push origin "${DOCS_BRANCH}"

echo Done
