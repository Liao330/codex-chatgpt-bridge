#!/usr/bin/env bash
# One-click relay setup for the Codex C2C bridge.
# Runs on a Linux VM (Debian/Ubuntu). Exposes a local port through Tailscale Funnel.
#
#   sudo bash relay-setup.sh --port 8081 --hostname codex-c2c-vps
#
# The client keeps  <relay>:127.0.0.1:<port>  wired to its local bridge with an
# SSH reverse tunnel (scripts/vps-tunnel.ps1).
set -euo pipefail

PORT=8081
HOSTNAME_ARG="codex-c2c-vps"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --hostname) HOSTNAME_ARG="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done

echo "== installing tailscale"
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
tailscale version | head -1

echo "== starting tailscaled"
systemctl enable --now tailscaled

echo "== joining the tailnet"
if ! tailscale status >/dev/null 2>&1; then
  tailscale up --hostname="$HOSTNAME_ARG"
fi
tailscale status | head -3

echo "== enabling HTTPS certificates for the tailnet (may already be on)"
tailscale cert "$(tailscale status --json | sed -n 's/.*"DNSName": *"\([^"]*\)".*/\1/p' | head -1)" >/dev/null 2>&1 || \
  echo "   open https://login.tailscale.com/admin/dns and enable HTTPS Certificates, then re-run"

echo "== publishing port $PORT through Funnel"
tailscale funnel --bg "$PORT" || {
  echo
  echo "Enable Funnel for this tailnet, then re-run this script:"
  echo "  tailscale funnel --bg $PORT"
  exit 1
}

echo
echo "== done. Public URL:"
tailscale funnel status | head -6
echo
echo "Client next step: point scripts/vps-tunnel.ps1 at this host (ssh alias) and run"
echo "  deploy/install-client.ps1 -WorkspacePath <path>"