#!/usr/bin/env bash
# Execute this at the base of the streamlink repo.
# Requires: sphinx

if [ "$#" -ne 1 ] ; then
    echo "Path to streamlink.github.io repo is required."
    exit 1
fi

DOCS_REPO_PATH="$1"

make --directory=docs html

# remove old files
rm "$DOCS_REPO_PATH/"*.html -f
rm "$DOCS_REPO_PATH/"*.js -f
rm "$DOCS_REPO_PATH/"*.inv -f
rm "$DOCS_REPO_PATH/_sources" -fr
rm "$DOCS_REPO_PATH/_static" -fr

# copy new files
cp -R docs/_build/html/* "$DOCS_REPO_PATH/"

echo "All the files were successfully built and copied."
