#!/usr/bin/env bash
set -euxo pipefail

PY=$(python -c 'import platform,sysconfig;v="".join(platform.python_version_tuple()[:2]);t="t" if sysconfig.get_config_var("Py_GIL_DISABLED") else "";print(f"cp{v}-cp{v}{t}")')
[[ "${PY}" == cp313-cp313t || "${PY}" == cp314-cp314 || "${PY}" == cp314-cp314t ]] || exit 0

[[ "$(uname)" == Linux ]] && PLATFORM=linux_x86_64 || PLATFORM=win_amd64


BASE=https://github.com/streamlink/temp-dependency-builds-DO-NOT-USE/releases/download
DEPS=(
    'lxml-20250630-1/lxml-6.0.0'
    'brotli-20250630-1/brotli-1.1.0'
    'zstandard-20250630-1/zstandard-0.24.0.dev0'
)
DEPS_WINDOWS=(
    'cffi-20250630-1/cffi-1.17.1'
)

deps=()

for dep in "${DEPS[@]}"; do
    deps+=("${BASE}/${dep}-${PY}-${PLATFORM}.whl")
done

if [[ "${PLATFORM}" == win_amd64 ]]; then
    for dep in "${DEPS_WINDOWS[@]}"; do
        deps+=("${BASE}/${dep}-${PY}-${PLATFORM}.whl")
    done
fi

python -m pip install -U "${deps[@]}"
