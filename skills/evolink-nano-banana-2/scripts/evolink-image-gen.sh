#!/usr/bin/env bash
# One durable task per --output. Re-run identical arguments to resume polling.
set -euo pipefail
exec python3 "$(dirname "$0")/evolink_image.py" "$@"
