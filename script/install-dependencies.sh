#!/usr/bin/env bash

[[ "$CI" = true ]] || [[ -n "$GITHUB_ACTIONS" ]] || [[ -n "$VIRTUAL_ENV" ]] || exit 1

set -ex

python -m pip install --disable-pip-version-check --upgrade pip setuptools

# temporary dependency workarounds
[[ "$(python -V)" =~ 3.12. && "$(uname)" != Linux ]] \
  && python -m pip install --upgrade --force-reinstall \
    'https://github.com/streamlink/temp-dependency-builds-DO-NOT-USE/releases/download/cffi-20230923-1/cffi-1.15.1-cp312-cp312-win_amd64.whl'

python -m pip install --upgrade -r dev-requirements.txt
# https://github.com/streamlink/streamlink/issues/4021
python -m pip install brotli
python -m pip install -e .
