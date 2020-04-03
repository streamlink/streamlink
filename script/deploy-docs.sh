#!/usr/bin/env bash
shopt -s nullglob
set -eo pipefail

[[ -n "${GITHUB_ACTIONS}" ]] || exit 1

ROOT=$(realpath "$(dirname "$(readlink -f "${0}")")/..")

DOCS_REPO=${DOCS_REPO:-streamlink/streamlink.github.io}
DOCS_BRANCH=${DOCS_BRANCH:-master}
DOCS_USER=${DOCS_USER:-streamlink-bot}
DOCS_EMAIL=${DOCS_EMAIL:-streamlink-bot@users.noreply.github.com}
KEY_FILE=${DOCS_KEY_FILE:-"${ROOT}/docs.key"}
KEY_FILE_ENC=${KEY_FILE}.gpg

SOURCE=${DOCS_DIR:-"${ROOT}/docs/_build/html"}
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


if ! [[ -s "${SOURCE}/index.html" ]]; then
    echo Missing or empty index.html
    exit 1
fi

if ! [[ -f "${KEY_FILE}" ]]; then
    echo Decrypting documentation deploy key
    gpg --quiet --batch --yes --decrypt \
        --passphrase="${DOCS_KEY_PASSPHRASE}" \
        --output "${KEY_FILE}" \
        "${KEY_FILE_ENC}"
    chmod 600 "${KEY_FILE}"
fi
# make sure that no SSH config file and that the docs deploy key is used by git
export GIT_SSH_COMMAND="ssh -F /dev/null -i '${KEY_FILE}'"


echo Creating temporary directory
TEMP=$(mktemp -d) && trap "rm -rf ${TEMP}" EXIT || exit 255
cd "${TEMP}"


echo Cloning repository...
git clone \
    --depth=1 \
    --origin=origin \
    --branch="${DOCS_BRANCH}" \
    "git@github.com:${DOCS_REPO}.git" \
    .

echo Deleting all files stored in \'${DEST}\' file list
for file in $(cat "${DEST}/${FILELIST}" || echo ""); do
    rm "${file}" || true
done

echo Copying new files into \'${DEST}\'
mkdir --parents "${DEST}"
cp --archive "${SOURCE}/." "${DEST}/"

echo Building a new file list in \'${DEST}\'
( cd "${SOURCE}"; find . -type f | sort | sed "s/^\\.\//${DEST}\//" > "${TEMP}/${DEST}/${FILELIST}" )

if git diff-index --quiet HEAD --; then
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
git push origin "${DOCS_BRANCH}"

echo Done
