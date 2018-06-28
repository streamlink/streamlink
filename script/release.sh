#!/usr/bin/env bash

script=$(basename -- "$0")
temp_dir=$(mktemp -d) && trap "rm -rf ${temp_dir}" EXIT || exit 255

usage() {
    echo "usage: $script [OPTIONS]" >&2
}

help() {
    usage
    cat <<EOF >&2

Helper script for performing a release of Streamlink.
Options can be specified on the command line, or the user will
be prompted to enter the required options.

General options:
  -h, --help
    Show this help message and exit.

  -u, --upstream REPO
    Set the upstream repo (streamlink/streamlink)

  -o, --origin REPO
    Set the users fork of the upstream repo (gituser/streamlink)

  -v, --version VERSION
    Set the new version number.
EOF
}

test_getopt() {
    getopt --test > /dev/null
    if [[ $? -ne 4 ]]; then
        echo "An updated version of getopt is required (gnu-getopt)." >&2
        return 1
    fi
}

test_available() {
    which $1 > /dev/null
    return $?
}

columns() {
  cols=$(tput cols)
  echo $((cols > 80 ? 80 : cols))
}

error() {
  cols=$(columns)
  tput hpa $((cols - 6))
  echo -e "\e[39m[\e[31mFAIL\e[39m]"
}

success() {
  cols=$(columns)
  tput hpa $((cols - 4))
  echo -e "\e[39m[\e[32mOK\e[39m]"
}

changelog() {
  temp_changes=$(mktemp) && trap "rm -rf ${temp_changes}" EXIT || exit 255
  date=$(date -u +"%Y-%m-%d")
  shortlog=$(git shortlog --email --no-merges --pretty=%s ${1}..)

  echo -e "\n## streamlink $2 ($date)\n\n!! WRITE RELEASE NOTES HERE !!\n\n\`\`\`text\n${shortlog}\n\`\`\`\n" > "${temp_changes}"

  sed -i "/# Changelog/ r ${temp_changes}" "CHANGELOG.md"
  return $?
}

check_changelog() {
  grep "WRITE RELEASE NOTES HERE" "CHANGELOG.md" >/dev/null
  if [[ "$?" == "0" ]]; then
    echo "fatal: CHANGELOG.md contains the template text" >&2
    return 1
  fi
  return 0
}

action() {
  local msg temp_log
  msg=$1
  temp_log=$(mktemp) && trap "rm -rf ${temp_log}" EXIT || exit 255

  echo -n "$msg "
  shift

  "$@" 2> "${temp_log}" 1>&2 && success || (error; cat "${temp_log}"; exit 1)

  return $?
}

test_getopt || exit 255

# setup getopts
OPTIONS=hu:o:v:
LONGOPTIONS=help,upstream:,origin:,version:
PARSED=$(getopt --options $OPTIONS --longoptions=$LONGOPTIONS --name "$0" -- "$@")
if [[ $? -ne 0 ]]; then
    usage
    exit 2
fi

# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

# now enjoy the options in order and nicely split until we see --
while true; do
    case "$1" in
        -h|--help)
            help
            exit 0
            ;;
        -u|--upstream)
            upstream="$2"
            shift 2
            ;;
        -o|--origin)
            origin="$2"
            shift 2
            ;;
        -v|--version)
            version="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Programming error"
            exit 3
            ;;
    esac
done

echo -e "Streamlink Release Script\n"
action "User has git installed" test_available git

if [ -z "$upstream" ]; then
    echo -n "Upstream repo [streamlink/streamlink]: "
    read upstream
    if [ -z "$upstream" ]; then
        upstream="streamlink/streamlink"
    fi
fi

if [ -z "$origin" ]; then
    echo -n "Fork repo [$USER/streamlink]: "
    read origin
    if [ -z "$origin" ]; then
        origin="$USER/streamlink"
    fi
fi

while [ -z "$version" ]; do
    echo -n "New version number: "
    read version
done

action "Cloning ${upstream}..." git clone -q "ssh://git@github.com/${upstream}.git" "${temp_dir}"

pushd "${temp_dir}" >/dev/null

dirty_version=$(python setup.py --version)
current_version="${dirty_version%%+*}"

action "Adding ${origin} as origin" git remote set-url origin "git@github.com:${origin}.git" || exit 1
action "Adding release-${version} branch" git checkout -b "release-${version}" || exit 1

action "Updating CHANGELOG.md (${current_version}..HEAD}" changelog "${current_version}" "${version}" || exit 1

# launch editor to edit the file
"${VISUAL:-"${EDITOR:-vi}"}" "CHANGELOG.md"

action "Check CHANGELOG.md was updated" check_changelog || exit 1

action "Commit CHANGELOG.md to release-${version} branch" git commit CHANGELOG.md -m "Release ${version}" || exit 1
action "Push release-${version} branch to ${origin}" git push origin "release-${version}" || exit 1

popd >/dev/null
