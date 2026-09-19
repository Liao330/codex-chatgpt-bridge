#!/usr/bin/env bash
# Relay self-check for the Codex C2C bridge.
# Verifies: the client tunnel is listening, Funnel points at it, and the bridge answers.
# Exit 0 = healthy. Any failure prints FAIL lines and exits 1.
#
#   c2c-relay-selfcheck.sh [port]
#
# Install as a systemd timer (see deploy/c2c-relay-selfcheck.{service,timer}).
set -uo pipefail

PORT="${1:-8081}"
TAG="c2c-relay-selfcheck"
FAIL=0

note() { logger -t "$TAG" "$*" 2>/dev/null || true; echo "$(date -Is) $*"; }

if ss -lnt 2>/dev/null | grep -q "127.0.0.1:$PORT "; then
  note "OK   tunnel port 127.0.0.1:$PORT is listening"
else
  note "FAIL tunnel port 127.0.0.1:$PORT is not listening (client machine offline?)"
  FAIL=1
fi

if tailscale funnel status 2>/dev/null | grep -q "127.0.0.1:$PORT"; then
  note "OK   funnel proxies to 127.0.0.1:$PORT"
else
  note "FAIL funnel is not pointing at 127.0.0.1:$PORT"
  FAIL=1
fi

HEALTH="$(curl -s -m 10 "http://127.0.0.1:$PORT/health" 2>/dev/null || true)"
if printf '%s' "$HEALTH" | grep -q '"status":"ok"'; then
  note "OK   bridge health: $(printf '%s' "$HEALTH" | head -c 120)"
else
  note "FAIL bridge health probe returned: ${HEALTH:-<no response>}"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  note "PASS all checks"
else
  note "RESULT degraded - see FAIL lines above"
fi
exit "$FAIL"
