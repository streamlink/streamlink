#!/usr/bin/env bash

[[ "$CI" = true ]] || [[ -n "$GITHUB_ACTIONS" ]] || [[ -n "$VIRTUAL_ENV" ]] || exit 1

set -ex

python -m pip install --disable-pip-version-check --upgrade pip setuptools
python -m pip install --upgrade -r dev-requirements.txt
python -m pip install pycountry
# temporary windows python 3.10 fix for missing 'lxml 4.6.3' wheel
# https://github.com/streamlink/streamlink/issues/3971
python -m pip install "https://github.com/back-to/tmp_wheel/raw/b237059b18110ca298e191340eebb6eb0aef8827/lxml-4.6.3-cp310-cp310-win_amd64.whl; \
    '3.10' <= python_version \
    and 'Windows' == platform_system \
    and ('AMD64' == platform_machine or 'x86_64' == platform_machine)"
python -m pip install "https://github.com/back-to/tmp_wheel/raw/b237059b18110ca298e191340eebb6eb0aef8827/lxml-4.6.3-cp310-cp310-win32.whl; \
    '3.10' <= python_version \
    and 'Windows' == platform_system \
    and ('AMD64' != platform_machine and 'x86_64' != platform_machine)"
python -m pip install -e .
