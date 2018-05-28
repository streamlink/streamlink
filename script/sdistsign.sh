#!/usr/bin/env bash

KEY_ID=2E390FA0
KEY_FILE=${SDIST_KEY_FILE:-signing.key}

dist_dir=${STREAMLINK_DIST_DIR:-dist}
temp_keyring=$(mktemp -d) && trap "rm -rf ${temp_keyring}" EXIT || exit 255


python setup.py sdist --dist-dir "${dist_dir}" >/dev/null

gpg --homedir "${temp_keyring}" --import "${KEY_FILE}" 
gpg --homedir "${temp_keyring}" --trust-model always --default-key ${KEY_ID} --detach-sign --armor "${dist_dir}/streamlink-${TRAVIS_TAG}.tar.gz"
