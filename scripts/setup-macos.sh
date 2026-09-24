#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin ]]; then
  echo 'This launcher is for macOS.' >&2; exit 1
fi
matic_python=''
for candidate in "${MATIC_PYTHON:-}" python3.14 python3.13 python3.12 python3.11 python3 "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"; do
  [[ -n "$candidate" ]] || continue
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3,11))' 2>/dev/null; then
    matic_python="$candidate"; break
  fi
done
if [[ -z "$matic_python" ]]; then
  echo 'Install Python 3.11+ from python.org, or set MATIC_PYTHON to its executable.' >&2; exit 1
fi
"$matic_python" -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -e '.[ble]'
echo 'Setup complete. Run: .venv/bin/matic-macos doctor'
