#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/matic-macos ]]; then
  bash scripts/setup-macos.sh
fi
printf '\nIn the Matic app: Settings > Connectivity > Add another user > Pairing mode.\nKeep your Mac near the robot.\nPress Return when ready.\n'
read -r
.venv/bin/matic-macos pair || result=$?
printf '\nPress Return to close.\n'
read -r
exit "${result:-0}"
