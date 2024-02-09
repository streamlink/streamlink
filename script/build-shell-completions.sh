#!/usr/bin/env bash
set -e

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || realpath "$(dirname "$(readlink -f "${0}")")/..")

DIST="${ROOT}/completions"
PYTHON_DEPS=(streamlink_cli shtab)

declare -A COMPLETIONS=(
  [bash]="streamlink"
  # ZSH requires the file to be prefixed with an underscore
  [zsh]="_streamlink"
)

for dep in "${PYTHON_DEPS[@]}"; do
  python -c "import ${dep}" 2>&1 >/dev/null \
    || { echo >&2 "${dep} could not be found in your python environment"; exit 1; }
done

for shell in "${!COMPLETIONS[@]}"; do
  mkdir -p "${DIST}/${shell}"
  dist="${DIST}/${shell}/${COMPLETIONS[${shell}]}"
  python -m shtab \
    "--shell=${shell}" \
    --error-unimportable \
    streamlink_cli._parser.get_parser \
    > "${dist}"
  echo "Completions for ${shell} written to ${dist}"
done
