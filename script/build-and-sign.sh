#!/usr/bin/env bash
shopt -s nullglob
set -e


if ! python -m pip -q show "build"; then
    echo >&2 "build: missing dependency 'build'"
    exit 1
fi


KEY_ID=${SIGNING_KEY_ID:-2E390FA0}
KEY_FILE=${SIGNING_KEY_FILE:-signing.key}
KEY_FILE_ENC=${KEY_FILE}.gpg

version=$(python setup.py --version)
dist_dir=${STREAMLINK_DIST_DIR:-dist}

wheel_platforms_windows=("win32" "win-amd64")

mkdir -p "${dist_dir}"

echo >&2 "build: Building Streamlink sdist"
python -m build --outdir "${dist_dir}" --sdist

echo >&2 "build: Building Streamlink wheel"
python -m build --outdir "${dist_dir}" --wheel

for platform in "${wheel_platforms_windows[@]}"; do
    echo >&2 "build: Building Streamlink wheel (${platform})"
    python -m build --outdir "${dist_dir}" --wheel --config-setting="--build-option=--plat-name=${platform}"
done


if [[ "${CI}" = true ]] || [[ -n "${GITHUB_ACTIONS}" ]]; then
    echo >&2 "build: Decrypting signing key"
    gpg --quiet --batch --yes --decrypt \
        --passphrase-fd 0 \
        --output "${KEY_FILE}" \
        "${KEY_FILE_ENC}" \
        <<< "${RELEASE_KEY_PASSPHRASE}"
fi

if ! [[ -f "${KEY_FILE}" ]]; then
    echo >&2 "warning: No signing key, files not signed"
else
    echo >&2 "build: Signing sdist and wheel files"
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
