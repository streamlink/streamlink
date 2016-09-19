#!/bin/sh

if [ $TRAVIS_SECURE_ENV_VARS != "true" ]; then
	exit 0
fi

if [ $TRAVIS_PYTHON_VERSION != "2.7" ]; then
	exit 0
fi

# "git describe" seems to somtimes exit with "fatal: No names found, cannot
# describe anything.", this makes sure we have tag information fetched.
git fetch --unshallow

sh win32/build-with-bootstrap.sh
cd dist/

if [ $TRAVIS_BRANCH = "develop" ]; then
	cp *zip livestreamer-latest-win32.zip
	cp *exe livestreamer-latest-win32-setup.exe
fi

for file in ./{*.exe,*.zip}; do
	~/bin/artifacts upload --target-paths "/" "$file"
done
