#!/usr/bin/env bash
# Mint a principal_id bearer token for the Node API.  Usage: scripts/mint_node_token.sh [principal_id]
set -euo pipefail
PRINCIPAL="${1:-KM-1176}"
CRED="$HOME/.breathline/credentials"
mkdir -p "$CRED"; chmod 700 "$HOME/.breathline" "$CRED"
SECRET="$(python3 -c 'import secrets;print(secrets.token_urlsafe(24))')"
printf '%s' "$SECRET" > "$CRED/$PRINCIPAL.token"; chmod 600 "$CRED/$PRINCIPAL.token"
echo "minted $CRED/$PRINCIPAL.token (0600)"
echo "Atrium token (paste as localStorage.breathline_atrium_token): $PRINCIPAL:$SECRET"
