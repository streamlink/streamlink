#!/usr/bin/env bash
shopt -s nullglob
set -e


version=$(python setup.py --version)
dist_dir=${STREAMLINK_DIST_DIR:-dist}


if [[ "${1}" = "-n" ]] || [[ "${1}" = "--dry-run" ]]; then
    echo "deploy: dry-run (${version})" >&2
    for file in "${dist_dir}"/streamlink-"${version}"{.tar.gz,-*.whl}{,.asc}; do
        echo "${file}" >&2
    done

else
    if ! python -m pip -q show twine; then
        echo "deploy: missing dependency 'twine'" >&2
        exit 1
    fi

    if [[ -z "${PYPI_USER}" ]] || [[ -z "${PYPI_PASSWORD}" ]]; then
        echo "deploy: missing PYPI_USER or PYPI_PASSWORD env var" >&2
        exit 1
    fi

    echo "deploy: Uploading files to PyPI (${version})" >&2
    twine upload \
        --username "${PYPI_USER}" \
        --password "${PYPI_PASSWORD}" \
        "${dist_dir}"/streamlink-"${version}"{.tar.gz,-*.whl}{,.asc}
fi
