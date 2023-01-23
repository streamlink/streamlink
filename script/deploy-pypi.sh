#!/usr/bin/env bash
shopt -s nullglob
set -e


version=$(python setup.py --version)
dist_dir=${STREAMLINK_DIST_DIR:-dist}


if [[ "${1}" = "-n" ]] || [[ "${1}" = "--dry-run" ]]; then
    echo >&2 "deploy: dry-run (${version})"
    for file in "${dist_dir}"/streamlink-"${version}"{.tar.gz,-*.whl}{,.asc}; do
        echo >&2 "${file}"
    done

else
    if ! python -m pip -q show twine; then
        echo >&2 "deploy: missing dependency 'twine'"
        exit 1
    fi

    if [[ -z "${PYPI_USER}" ]] || [[ -z "${PYPI_PASSWORD}" ]]; then
        echo >&2 "deploy: missing PYPI_USER or PYPI_PASSWORD env var"
        exit 1
    fi

    echo >&2 "deploy: Uploading files to PyPI (${version})"
    twine upload \
        --username "${PYPI_USER}" \
        --password "${PYPI_PASSWORD}" \
        "${dist_dir}"/streamlink-"${version}"{.tar.gz,-*.whl}{,.asc}
fi
