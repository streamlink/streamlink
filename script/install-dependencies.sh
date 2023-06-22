#!/usr/bin/env bash

[[ "$CI" = true ]] || [[ -n "$GITHUB_ACTIONS" ]] || [[ -n "$VIRTUAL_ENV" ]] || exit 1

set -ex

python -m pip install --disable-pip-version-check --upgrade pip setuptools
python -m pip install --upgrade -r dev-requirements.txt

# install a custom-built lxml wheel for the py312 CI runner until an official one is available
[[ "${GITHUB_ACTIONS}" && "$(uname)" == Linux && "$(python -V)" =~ 3.12. ]] \
  && python -m pip install --require-hashes -r /dev/stdin <<EOF
    https://github.com/streamlink/temp-lxml-wheel-DO-NOT-USE/releases/download/lxml-ec0b59b-1/lxml-5.0.0a0-cp312-cp312-linux_x86_64.whl \
      --hash=sha256:b2049d4dfc3fba2d8bb998f909ee98c183cb02b8a277ea8ef323238c88aac744
EOF

# https://github.com/streamlink/streamlink/issues/4021
python -m pip install brotli
python -m pip install -e .
