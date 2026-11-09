#!/usr/bin/env python3
"""
redeem_deltaforce_api.py — Delta Force (Garena) gift code redeemer via direct API
No browser needed. Uses the playerinfinite API with HMAC-MD5 signature.

Usage:
  python3 redeem_deltaforce_api.py <CODE>
  python3 redeem_deltaforce_api.py CODE1 CODE2 CODE3

Env vars (required):
  DF_OPENID   — openid from Garena auth (numeric, e.g. <YOUR_OPENID>)
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
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlencode

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
    print("  PowerShell : $env:DF_OPENID='<YOUR_OPENID>'; $env:DF_TOKEN='<YOUR_TOKEN>'", file=sys.stderr)
    print("  CMD        : set DF_OPENID=<YOUR_OPENID> && set DF_TOKEN=<YOUR_TOKEN>", file=sys.stderr)
    print("  Bash       : export DF_OPENID='<YOUR_OPENID>' DF_TOKEN='<YOUR_TOKEN>'", file=sys.stderr)
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
    req = urllib.request.Request(
        url,
        data=json.dumps({"role_info": {"game_id": GAME_ID}}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://redeem.df.garena.sg",
            "Referer": "https://redeem.df.garena.sg/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            ),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        if body:
            try:
                return json.loads(body)
            except Exception:
                pass
        raise RuntimeError(f"HTTP {e.code}: {e.reason}")
    except Exception as e:
        # Fallback to curl if urllib encounters an unexpected network/ssl error
        try:
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
            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)
        except Exception:
            pass
        raise e


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
    codes = [c.strip() for c in sys.argv[1:] if c.strip()]
    if not codes:
        print("Usage: python redeem_deltaforce_api.py CODE1 [CODE2 ...]")
        print("       python redeem_deltaforce_api.py pending    # auto-redeem all pending codes")
        sys.exit(1)

    manage = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), "manage_codes.py"),
    ]

    # If user passed 'pending', query manage_codes.py for all untried codes
    if len(codes) == 1 and codes[0].lower() == "pending":
        res = subprocess.run(manage + ["pending"], capture_output=True, text=True, check=False)
        pending_codes = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("Pending") and not line.startswith("No pending"):
                pending_codes.append(line)
        if not pending_codes:
            print("[*] No pending codes found to redeem.")
            sys.exit(0)
        codes = pending_codes
        print(f"[*] Found {len(codes)} pending codes to redeem: {', '.join(codes)}")

    # Load existing states to avoid retrying success or error codes
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    state_file = (
        os.environ.get("CODES_STATE_FILE")
        or os.environ.get("CODES_FILE")
        or os.path.join(base_dir, "data/codes_state.json")
    )
    if not os.path.exists(state_file) and os.path.exists(os.path.join(base_dir, "data/codes.json")):
        if not os.environ.get("CODES_STATE_FILE") and not os.environ.get("CODES_FILE"):
            state_file = os.path.join(base_dir, "data/codes.json")

    tracked = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
                tracked = state_data.get("codes", {})
        except Exception as e:
            print(f"[*] Warning: Could not load state file {state_file}: {e}", file=sys.stderr)

    first_run = True
    for code in codes:
        # Case-insensitive lookup check in tracked codes
        matched_key = next((k for k in tracked if k.upper() == code.upper()), None)
        if matched_key:
            status = tracked[matched_key].get("status")
            if status in ("success", "error"):
                # Check if the error note is something we should retry (e.g. auth error)
                note = tracked[matched_key].get("note", "")
                if "auth error" not in note.lower() and "curl failed" not in note.lower():
                    print(f"[SKIP] {code} (matches tracked {matched_key}) is already {status}: {note}")
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
