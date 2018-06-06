#!/usr/bin/env bash
set -e

KEY_ID=2E390FA0
KEY_FILE=${SDIST_KEY_FILE:-signing.key}

version=$(python setup.py --version)
dist_dir=${STREAMLINK_DIST_DIR:-dist}
temp_keyring=$(mktemp -d) && trap "rm -rf ${temp_keyring}" EXIT || exit 255

if [[ -n "${TRAVIS}" ]]; then
      openssl aes-256-cbc -K ${encrypted_eeb8b970d3a3_key} -iv ${encrypted_eeb8b970d3a3_iv} -in signing.key.enc -out "${SDIST_KEY_FILE}" -d
fi

echo "build: Installing twine and wheel" >&2
pip -q install -U setuptools twine wheel

echo "build: Building streamlink sdist and wheel" >&2
python setup.py -q sdist bdist_wheel --dist-dir "${dist_dir}"

if [ -f "${KEY_FILE}" ]; then
    echo "build: Signing sdist and wheel files" >&2
    gpg --homedir "${temp_keyring}" --import "${KEY_FILE}" 2>&1 > /dev/null
    gpg --homedir "${temp_keyring}" --trust-model always --default-key "${KEY_ID}" --detach-sign --armor "${dist_dir}/streamlink-${version}.tar.gz"
    gpg --homedir "${temp_keyring}" --trust-model always --default-key "${KEY_ID}" --detach-sign --armor "${dist_dir}/streamlink-${version}-py2.py3-none-any.whl"
else
    echo "warning: no signing key, files not signed" >&2
fi

if [[ "${DEPLOY_PYPI}" == "yes" ]]; then
    echo "build: Uploading sdist and wheel to PyPI" >&2
    twine upload --username "${PYPI_USER}" --password "${PYPI_PASSWORD}" \
        "${dist_dir}/streamlink-${version}.tar.gz" \
        "${dist_dir}/streamlink-${version}.tar.gz.asc"
    twine upload --username "${PYPI_USER}" --password "${PYPI_PASSWORD}" \
        "${dist_dir}/streamlink-${version}-py2.py3-none-any.whl" \
        "${dist_dir}/streamlink-${version}-py2.py3-none-any.whl.asc"
fi