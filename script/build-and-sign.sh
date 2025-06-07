#!/usr/bin/env bash
shopt -s nullglob
set -e


ROOT=$(git rev-parse --show-toplevel 2>/dev/null || realpath "$(dirname "$(readlink -f "${0}")")/..")
DIST=${STREAMLINK_DIST_DIR:-"${ROOT}/dist"}

WHEEL_PLATFORMS=("win32" "win-amd64")

SIGNING_KEY_FILE="${SIGNING_KEY_FILE:-"${ROOT}/signing.key.enc"}"


# ----


log() {
    echo >&2 "build:" "${@}"
}

warn() {
    log "WARNING:" "${@}"
}

err() {
    log "ERROR:" "${@}"
    exit 1
}


# ----


pushd "${ROOT}"


check_deps() {
    local dep
    for dep in build wheel versioningit; do
        if ! python -m pip -q show "${dep}"; then
            err "Missing python package: ${dep}"
        fi
    done
}

get_version() {
    log "Reading version string"
    VERSION=$(python -m versioningit)
}

build() {
    mkdir -p "${DIST}"

    log "Building Streamlink sdist and generic wheel"
    python -m build --outdir "${DIST}" --sdist --wheel

    # see custom build-system override in pyproject.toml
    for platform in "${WHEEL_PLATFORMS[@]}"; do
        log "Building Streamlink platform-specific wheel for ${platform}"
        python -m build --outdir "${DIST}" --wheel --config-setting="--build-option=--plat-name=${platform}"
    done
}

sign() {
    [[ -z "${SIGNING_KEY_PASSPHRASE}" ]] && { warn "Empty SIGNING_KEY_PASSPHRASE, not signing built files"; exit; }
    [[ -z "${SIGNING_KEY_ID}" ]] && err "Missing SIGNING_KEY_ID"

    local tmp
    # shellcheck disable=SC2064
    tmp=$(mktemp -d) && trap "rm -rf '${tmp}'" EXIT || exit 255

    log "Decrypting signing key"
    gpg --quiet \
        --batch \
        --yes \
        --decrypt \
        --passphrase-fd 0 \
        --output "${tmp}/signing.key" \
        "${SIGNING_KEY_FILE}" \
        <<< "${SIGNING_KEY_PASSPHRASE}"

    log "Signing sdist and wheel files"
    gpg --homedir "${tmp}" --import "${tmp}/signing.key" >/dev/null 2>&1
    for file in "${DIST}"/streamlink-"${VERSION}"{.tar.gz,-*.whl}; do
        gpg --homedir "${tmp}" \
            --trust-model always \
            --default-key "${SIGNING_KEY_ID}" \
            --detach-sign \
            --armor \
            --yes \
            "${file}"
    done
}


check_deps
get_version
build
sign
