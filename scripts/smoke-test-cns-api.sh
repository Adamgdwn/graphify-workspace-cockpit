#!/usr/bin/env bash
# Smoke-test the Graphify CNS API. Requires the server to already be running.
# Usage: BASE_URL=http://localhost:8001 ./scripts/smoke-test-cns-api.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"

echo "Smoke-testing Graphify CNS API at $BASE_URL"

result=$(curl -sf "$BASE_URL/health")
status=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])")
if [ "$status" != "ok" ]; then
  echo "FAIL: health check returned status=$status"
  exit 1
fi
echo "PASS: /health -> $result"

echo "Smoke tests passed."
