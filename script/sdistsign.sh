#!/usr/bin/env bash
shopt -s nullglob
set -e

KEY_ID=2E390FA0
KEY_FILE=${SDIST_KEY_FILE:-signing.key}

version=$(python setup.py --version)
dist_dir=${STREAMLINK_DIST_DIR:-dist}
temp_keyring=$(mktemp -d) && trap "rm -rf ${temp_keyring}" EXIT || exit 255

wheel_platforms_windows=("win32" "win-amd64")

if [[ -n "${TRAVIS}" ]]; then
      openssl aes-256-cbc -K ${encrypted_eeb8b970d3a3_key} -iv ${encrypted_eeb8b970d3a3_iv} -in signing.key.enc -out "${SDIST_KEY_FILE}" -d
fi

echo "build: Installing twine and wheel" >&2
pip -q install -U setuptools twine wheel

echo "build: Building Streamlink sdist" >&2
python setup.py -q sdist --dist-dir "${dist_dir}"

echo "build: Building Streamlink wheel (universal)" >&2
python setup.py -q bdist_wheel --dist-dir "${dist_dir}"

for platform in "${wheel_platforms_windows[@]}"; do
    echo "build: Building Streamlink wheel (${platform})" >&2
    python setup.py -q bdist_wheel --plat-name "${platform}" --dist-dir "${dist_dir}"
done

if [ -f "${KEY_FILE}" ]; then
    echo "build: Signing sdist and wheel files" >&2
    gpg --homedir "${temp_keyring}" --import "${KEY_FILE}" 2>&1 > /dev/null
    for file in "${dist_dir}"/streamlink-"${version}"{.tar.gz,-*.whl}; do
        gpg --homedir "${temp_keyring}" --trust-model always --default-key "${KEY_ID}" --detach-sign --armor "${file}"
    done
else
    echo "warning: no signing key, files not signed" >&2
fi

if [[ "${DEPLOY_PYPI}" == "yes" ]]; then
    echo "build: Uploading sdist and wheel to PyPI" >&2
    twine upload --username "${PYPI_USER}" --password "${PYPI_PASSWORD}" \
        "${dist_dir}"/streamlink-"${version}"{.tar.gz,-*.whl}{,.asc}
fi
