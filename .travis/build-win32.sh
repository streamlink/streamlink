#!/bin/sh

if [ $TRAVIS_PYTHON_VERSION != "2.7" ]; then
	exit 0
fi

sh win32/build-with-bootstrap.sh
cd dist/
travis-artifacts upload --path *zip --target-path ""
