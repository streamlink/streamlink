#!/usr/bin/env bash

[[ "$CI" = true ]] || [[ -n "$GITHUB_ACTIONS" ]] || [[ -n "$VIRTUAL_ENV" ]] || exit 1

set -ex

python -m pip install --disable-pip-version-check --upgrade pip setuptools
python -m pip install --upgrade -r dev-requirements.txt
python -m pip install 'pycountry==19.8.18;python_version<"3.0"'
python -m pip install 'pycountry;python_version>="3.0"'
python -m pip install -e .
