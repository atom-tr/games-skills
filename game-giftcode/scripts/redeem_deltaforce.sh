#!/usr/bin/env bash
# redeem_deltaforce.sh — Wrapper to redeem a Delta Force (Garena) gift code
# and update the state file automatically.
#
# Usage:
#   ./redeem_deltaforce.sh <CODE>
#
# Env vars:
#   GARENA_COOKIE   — cookie string from browser (required for headless mode)
#
# Example:
#   GARENA_COOKIE="token=abc123" ./redeem_deltaforce.sh DFakaonikou

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANAGE="python3 $SKILL_DIR/scripts/manage_codes.py"
NODE_SCRIPT="$SKILL_DIR/scripts/redeem_deltaforce.js"

CODE="${1:-}"
if [[ -z "$CODE" ]]; then
  echo "Usage: $0 <CODE>" >&2
  exit 1
fi

# Check if already tried
STATUS=$(python3 "$SKILL_DIR/scripts/manage_codes.py" list 2>/dev/null \
  | awk -v code="$CODE" '$1 == code {print $2}')

if [[ "$STATUS" == "success" ]]; then
  echo "[SKIP] $CODE already redeemed successfully."
  exit 0
elif [[ "$STATUS" == "error" ]]; then
  echo "[SKIP] $CODE already tried and failed. Use 'update' to force retry."
  exit 1
fi

# Register as pending if not tracked yet
$MANAGE add "$CODE" 2>/dev/null || true

echo "[*] Attempting to redeem: $CODE"

# Run puppeteer script — capture output
set +e
OUTPUT=$(cd "$SKILL_DIR" && node "$NODE_SCRIPT" "$CODE" 2>&1)
EXIT_CODE=$?
set -e

echo "$OUTPUT"

# Update state based on exit code
if [[ $EXIT_CODE -eq 0 ]]; then
  NOTE=$(echo "$OUTPUT" | grep -o '\[result\] .*' | sed 's/\[result\] //' | head -1)
  $MANAGE update "$CODE" success "$NOTE"
elif [[ $EXIT_CODE -eq 1 ]]; then
  NOTE=$(echo "$OUTPUT" | grep -o '\[result\] .*' | sed 's/\[result\] //' | head -1)
  $MANAGE update "$CODE" error "$NOTE"
else
  $MANAGE update "$CODE" error "script error (exit $EXIT_CODE)"
  echo "[FATAL] Script error — check output above." >&2
  exit 2
fi
