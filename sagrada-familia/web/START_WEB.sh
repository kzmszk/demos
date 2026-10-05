#!/usr/bin/env bash
set -euo pipefail
web_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$web_root/serve.py" --open-browser "$@"
