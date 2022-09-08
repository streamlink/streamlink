#!/usr/bin/env bash

[[ "$CI" = true ]] || [[ -n "$GITHUB_ACTIONS" ]] || [[ -n "$VIRTUAL_ENV" ]] || exit 1

set -ex

python -m pip install --disable-pip-version-check --upgrade pip setuptools
python -m pip install --upgrade -r dev-requirements.txt
# https://github.com/streamlink/streamlink/issues/4021
python -m pip install brotli
# Temporary custom lxml wheel for cp311 on Windows: https://github.com/streamlink/streamlink/pull/4806#issue-1364468477
[[ "$(uname)" != "Linux" ]] \
  && [[ "$(python -V)" =~ "Python 3.11."* ]] \
  && python -m pip install https://github.com/streamlink/temp-wheel-for-lxml-cp311-win-amd64/releases/download/lxml-4.9.1-1/lxml-4.9.1-cp311-cp311-win_amd64.whl \
  || true
python -m pip install -e .
