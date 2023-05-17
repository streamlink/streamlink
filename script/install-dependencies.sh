#!/usr/bin/env bash

[[ "$CI" = true ]] || [[ -n "$GITHUB_ACTIONS" ]] || [[ -n "$VIRTUAL_ENV" ]] || exit 1

set -ex

python -m pip install --disable-pip-version-check --upgrade pip setuptools
python -m pip install --upgrade -r dev-requirements.txt

# install a custom-built lxml wheel for the py312 CI runner until an official one is available
[[ "${GITHUB_ACTIONS}" && "$(uname)" == Linux && "$(python -V)" =~ 3.12. ]] \
  && python -m pip install --require-hashes -r /dev/stdin <<EOF
    https://github.com/streamlink/temp-lxml-wheel-DO-NOT-USE/releases/download/lxml-c6b7e62-1/lxml-5.0.0a0-cp312-cp312-linux_x86_64.whl \
      --hash=sha256:52c42777484b9ab5dbc604583d007048a7d1e7cb0fd101ac063972da1b8e50fb
EOF

# https://github.com/streamlink/streamlink/issues/4021
python -m pip install brotli
python -m pip install -e .
