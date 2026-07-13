#!/usr/bin/env python3
"""
redeem_deltaforce_api.py — Delta Force (Garena) gift code redeemer via direct API
No browser needed. Uses the playerinfinite API with HMAC-MD5 signature.

Usage:
  python3 redeem_deltaforce_api.py <CODE>
  python3 redeem_deltaforce_api.py CODE1 CODE2 CODE3

Env vars (required):
  DF_OPENID   — openid from Garena auth (numeric, e.g. 8486567269679708357)
  DF_TOKEN    — token from Garena auth (hex string)

Exit codes:
  0 = success or already redeemed
  1 = code invalid/expired/limit reached
  2 = auth/script error
"""

import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from urllib.parse import urlencode

# ── Constants ──────────────────────────────────────────────────────────────────
API_BASE   = "https://sg-act.playerinfinite.com"
API_PATH   = "/api/proxy/present/CdkV2/RedeemCDKey"
SIGN_SALT  = "&intel#!2022$act"
APP_ID     = "10005"
CHANNEL    = "10"
GAME_ID    = "30150"

# ── Auth from env ──────────────────────────────────────────────────────────────
OPENID = os.environ.get("DF_OPENID", "")
TOKEN  = os.environ.get("DF_TOKEN",  "")

if not OPENID or not TOKEN:
    print("[ERROR] Set DF_OPENID and DF_TOKEN env vars before running.", file=sys.stderr)
    print("  export DF_OPENID='8486567269679708357'", file=sys.stderr)
    print("  export DF_TOKEN='fbf006dac704924e09e8346dde18e673642603fb'", file=sys.stderr)
    sys.exit(2)


def build_signed_url(code: str) -> str:
    """Build the full API URL with u, a, ts query params and MD5 signature s."""
    ts  = str(int(time.time()))
    u   = str(uuid.uuid4())

    # Params injected into URL (matches browser behavior)
    query = urlencode({
        "cdkey":        code,
        "channel":      CHANNEL,
        "game_id":      GAME_ID,
        "gameid":       GAME_ID,
        "openid":       OPENID,
        "token":        TOKEN,
        "account_type": "1",
        "lang_type":    "vi",
        "u":            u,
        "a":            APP_ID,
        "ts":           ts,
    })

    path_with_query = f"{API_PATH}?{query}"
    sign_input      = path_with_query + SIGN_SALT
    s               = hashlib.md5(sign_input.encode()).hexdigest()

    return f"{API_BASE}{path_with_query}&s={s}"


def redeem(code: str) -> dict:
    """Call the API and return parsed JSON response."""
    url = build_signed_url(code)
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "-H", "Accept: application/json",
            "-H", "Origin: https://redeem.df.garena.sg",
            "-H", "Referer: https://redeem.df.garena.sg/",
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "-d", json.dumps({"role_info": {"game_id": GAME_ID}}),
            "--max-time", "15",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def classify(resp: dict) -> tuple[str, str]:
    """
    Returns (status, note) where status is 'success' | 'error' | 'unknown'.
    API code reference (code_type=1 = auth/system, code_type=2 = business logic):
      0        → success
      300001   → not logged in
      400067   → redemption limit reached (code already used by enough players)
      400082   → game role error
      other 4x → invalid / expired / already claimed by this account
    """
    code = resp.get("code", -1)
    msg  = resp.get("msg", "")

    if code == 0:
        return "success", msg or "redeemed successfully"
    elif code in (400067,):
        # Limit reached = code is valid but slots full (treat as error, not retry)
        return "error", f"[{code}] {msg}"
    elif code == 300001:
        return "error", f"[{code}] auth error — check DF_OPENID / DF_TOKEN"
    else:
        return "error", f"[{code}] {msg}"


def main():
    codes = [c.strip().upper() for c in sys.argv[1:] if c.strip()]
    if not codes:
        print("Usage: python3 redeem_deltaforce_api.py CODE1 [CODE2 ...]")
        sys.exit(1)

    manage = [
        "python3",
        os.path.join(os.path.dirname(__file__), "manage_codes.py"),
    ]

    # Load existing states to avoid retrying success or error codes
    state_file = os.path.join(os.path.dirname(__file__), "../data/codes.json")
    tracked = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state_data = json.load(f)
                tracked = {k.upper(): v for k, v in state_data.get("codes", {}).items()}
        except Exception as e:
            print(f"[*] Warning: Could not load state file {state_file}: {e}", file=sys.stderr)

    first_run = True
    for code in codes:
        # Case-insensitive check
        if code in tracked:
            status = tracked[code].get("status")
            if status in ("success", "error"):
                # Check if the error note is something we should retry (e.g. auth error)
                note = tracked[code].get("note", "")
                if "auth error" not in note.lower() and "curl failed" not in note.lower():
                    print(f"[SKIP] {code} is already {status}: {note}")
                    continue

        if not first_run:
            time.sleep(2)   # rate-limit: 2s between requests
        first_run = False

        print(f"\n[*] Redeeming: {code}")
        try:
            resp   = redeem(code)
            status, note = classify(resp)
            symbol = "✓" if status == "success" else "✗"
            print(f"[{symbol}] {code}: {note}")
            print(f"    raw: {resp}")

            # Update state file
            subprocess.run(manage + ["update", code, status, note], check=False)

        except Exception as e:
            print(f"[!] {code}: script error — {e}", file=sys.stderr)
            subprocess.run(manage + ["update", code, "error", str(e)], check=False)


if __name__ == "__main__":
    main()
