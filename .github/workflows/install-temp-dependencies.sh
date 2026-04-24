#!/usr/bin/env bash
set -euxo pipefail

PY=$(python -c 'import platform,sysconfig;v="".join(platform.python_version_tuple()[:2]);t="t" if sysconfig.get_config_var("Py_GIL_DISABLED") else "";print(f"cp{v}-cp{v}{t}")')
[[ "${PY}" == cp314-cp314 || "${PY}" == cp314-cp314t ]] || exit 0

if [[ "$(uname)" == Linux ]]; then
    PLATFORM=linux_x86_64
elif [[ "$(uname)" == Darwin ]]; then
    PLATFORM=macosx_10_15_universal2
elif [[ "$(uname)" == MINGW64_NT* ]]; then
    PLATFORM=win_amd64
else
    exit 1
fi


BASE=https://github.com/streamlink/temp-dependency-builds-DO-NOT-USE/releases/download
DEPS=()

# individual platform dependencies
if [[ "${PLATFORM}" == linux_x86_64 ]]; then
    DEPS+=()
elif [[ "${PLATFORM}" == macosx_10_15_universal2 ]]; then
    DEPS+=()
elif [[ "${PLATFORM}" == win_amd64 ]]; then
    DEPS+=()
fi

# no-GIL / free-threaded dependencies
if [[ "${PY}" == *t ]]; then
    DEPS+=(
        'brotli-20260424-1/brotli-1.2.0'
        'pycryptodome-20260424-1/pycryptodome-3.24.0b0'
    )
fi

if [[ ${#DEPS[@]} != 0 ]]; then
    deps=()
    for dep in "${DEPS[@]}"; do
        deps+=("${BASE}/${dep}-${PY}-${PLATFORM}.whl")
    done

    python -m pip install -U "${deps[@]}"
fi
