#!/bin/sh

if [ $TRAVIS_PYTHON_VERSION != "2.7" ]; then
	exit 0
fi

# "git describe" seems to somtimes exit with "fatal: No names found, cannot
# describe anything.", this makes sure we have tag information fetched.
git fetch --unshallow

sh win32/build-with-bootstrap.sh
cd dist/
cp *zip livestreamer-latest-win32.zip
travis-artifacts upload --path *zip --target-path ""
