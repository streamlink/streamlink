#!/usr/bin/env bash
shopt -s nullglob
set -e


for dep in setuptools wheel; do
    if ! python -m pip -q show "${dep}"; then
        echo "build: missing dependency '${dep}'" >&2;
        exit 1;
    fi
done


KEY_ID=${SIGNING_KEY_ID:-2E390FA0}
KEY_FILE=${SIGNING_KEY_FILE:-signing.key}
KEY_FILE_ENC=${KEY_FILE}.gpg

version=$(python setup.py --version)
dist_dir=${STREAMLINK_DIST_DIR:-dist}

wheel_platforms_windows=("win32" "win-amd64")

mkdir -p "${dist_dir}"

echo "build: Building Streamlink sdist" >&2
python setup.py sdist --dist-dir "${dist_dir}"

echo "build: Building Streamlink bdist_wheel" >&2
python setup.py bdist_wheel --dist-dir "${dist_dir}"

for platform in "${wheel_platforms_windows[@]}"; do
    echo "build: Building Streamlink bdist_wheel (${platform})" >&2
    python setup.py bdist_wheel --plat-name "${platform}" --dist-dir "${dist_dir}"
done


if [[ "${CI}" = true ]] || [[ -n "${GITHUB_ACTIONS}" ]]; then
    echo "build: Decrypting signing key" >&2
    gpg --quiet --batch --yes --decrypt \
        --passphrase="${RELEASE_KEY_PASSPHRASE}" \
        --output "${KEY_FILE}" \
        "${KEY_FILE_ENC}"
fi

if ! [[ -f "${KEY_FILE}" ]]; then
    echo "warning: No signing key, files not signed" >&2
else
    echo "build: Signing sdist and wheel files" >&2
    temp_keyring=$(mktemp -d) && trap "rm -rf ${temp_keyring}" EXIT || exit 255
    gpg --homedir "${temp_keyring}" --import "${KEY_FILE}" 2>&1 >/dev/null
    for file in "${dist_dir}"/streamlink-"${version}"{.tar.gz,-*.whl}; do
        gpg --homedir "${temp_keyring}" \
            --trust-model always \
            --default-key "${KEY_ID}" \
            --detach-sign \
            --armor \
            "${file}"
    done
fi
