#!/usr/bin/env bash
set -euxo pipefail

PY=$(python -c 'import platform,sysconfig;v="".join(platform.python_version_tuple()[:2]);t="t" if sysconfig.get_config_var("Py_GIL_DISABLED") else "";print(f"cp{v}-cp{v}{t}")')
[[ "${PY}" == cp314-cp314t || "${PY}" == cp315-cp315 ]] || exit 0

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

if [[ "${PY}" == cp314-cp314t ]]; then
    DEPS+=(
        "${BASE}/brotli-20260523-1/brotli-1.2.0-${PY}-${PLATFORM}.whl"
        "${BASE}/pycryptodome-20260610-1/pycryptodome-3.23.0-${PY}-${PLATFORM}.whl"
    )

elif [[ "${PY}" == cp315-cp315 ]]; then
    DEPS+=(
        "${BASE}/brotli-20260523-1/brotli-1.2.0-${PY}-${PLATFORM}.whl"
        "${BASE}/lxml-20260523-1/lxml-6.1.1-${PY}-${PLATFORM}.whl"
    )
    if [[ "${PLATFORM}" == win_amd64 ]]; then
        DEPS+=(
            "${BASE}/cffi-20260523-1/cffi-2.0.0-${PY}-${PLATFORM}.whl"
        )
    fi
fi


if [[ ${#DEPS[@]} != 0 ]]; then
    uv pip install -U "${DEPS[@]}"
fi
