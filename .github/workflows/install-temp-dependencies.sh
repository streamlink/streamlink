#!/usr/bin/env bash
set -euxo pipefail

PY=$(python -c 'import platform,sysconfig;v="".join(platform.python_version_tuple()[:2]);t="t" if sysconfig.get_config_var("Py_GIL_DISABLED") else "";print(f"cp{v}-cp{v}{t}")')
[[ "${PY}" == cp314-cp314 || "${PY}" == cp314-cp314t ]] || exit 0

[[ "$(uname)" == Linux ]] && PLATFORM=linux_x86_64 || PLATFORM=win_amd64


BASE=https://github.com/streamlink/temp-dependency-builds-DO-NOT-USE/releases/download
DEPS=()

if [[ "${PLATFORM}" == linux_x86_64 ]]; then
    DEPS+=()
elif [[ "${PLATFORM}" == win_amd64 ]]; then
    DEPS+=()
fi

if [[ "${PY}" == *t ]]; then
    DEPS+=(
        'brotli-20251007-1/brotli-1.2.0'
        'pycryptodome-20251017-1/pycryptodome-3.23.0'
    )
fi

deps=()
for dep in "${DEPS[@]}"; do
    deps+=("${BASE}/${dep}-${PY}-${PLATFORM}.whl")
done

if [[ ${#deps[@]} != 0 ]]; then
    python -m pip install -U "${deps[@]}"
fi
