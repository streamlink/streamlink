#!/usr/bin/env bash

if [ "$TRAVIS_BRANCH" != "master" ] || [ "$BUILD_DOCS" != "yes" ] || [ "$TRAVIS_SECURE_ENV_VARS" == "false" ] || [ "$TRAVIS_PULL_REQUEST" != "false" ] ; then
    exit 0
fi

DOCS_REPO_NAME="streamlink.github.io"
DOCS_REPO_URL="git@github.com:streamlink/streamlink.github.io.git"
DOCS_KEY="deploy-key"
DOCS_USER="Travis CI"

# deal with private key
openssl aes-256-cbc -K $encrypted_25fada573976_key -iv $encrypted_25fada573976_iv -in "$DOCS_KEY.enc" -out "$DOCS_KEY" -d
chmod 600 "$DOCS_KEY"
eval `ssh-agent -s`
ssh-add "$DOCS_KEY"

# clone the repo
git clone "$DOCS_REPO_URL" "$DOCS_REPO_NAME"
bash script/makedocs.sh "$DOCS_REPO_NAME"

# git config
cd "$DOCS_REPO_NAME"
git config user.name "$DOCS_USER"
git config user.email "<>"
git add --all
# Check if anythhing changed, and if it's the case, push to origin/master.
if git commit -m 'update docs' -m "Commit: https://github.com/streamlink/streamlink/commit/$TRAVIS_COMMIT" ; then
    git push origin master
fi

exit 0
