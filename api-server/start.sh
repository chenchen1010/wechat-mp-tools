#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a
source ./.env
set +a
exec /www/server/nodejs/v18.20.8/bin/node ./server.mjs
