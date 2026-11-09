#!/usr/bin/env python3
"""
manage_codes.py — Game Gift Code state & codelist manager
Supports 2-file architecture:
  - Codelist: data/codelist.txt (shared list of codes)
  - State   : data/codes_state.json (per-user/account redemption status)

Usage:
  manage_codes.py list
  manage_codes.py check <code> [<code> ...]
  manage_codes.py add <code> [<code> ...]
  manage_codes.py update <code> <status> [<note>]
  manage_codes.py pending
  manage_codes.py stats
"""

import json
import sys
import os
from datetime import datetime, timezone

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CODELIST_FILE = os.environ.get("CODELIST_FILE") or os.path.join(BASE_DIR, "data/codelist.txt")

# State file resolution: CODES_STATE_FILE -> CODES_FILE -> data/codes_state.json -> data/codes.json
STATE_FILE = (
    os.environ.get("CODES_STATE_FILE")
    or os.environ.get("CODES_FILE")
    or os.path.join(BASE_DIR, "data/codes_state.json")
)
if not os.path.exists(STATE_FILE) and os.path.exists(os.path.join(BASE_DIR, "data/codes.json")):
    if not os.environ.get("CODES_STATE_FILE") and not os.environ.get("CODES_FILE"):
        STATE_FILE = os.path.join(BASE_DIR, "data/codes.json")

VALID_STATUSES = {"pending", "success", "error", "skip"}


def load_codelist() -> list[str]:
    codes = []
    seen = set()
    if os.path.exists(CODELIST_FILE):
        with open(CODELIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.upper() not in seen:
                    seen.add(line.upper())
                    codes.append(line)
    return codes


def save_codelist(codes: list[str]):
    os.makedirs(os.path.dirname(CODELIST_FILE), exist_ok=True)
    existing = load_codelist()
    seen = {c.upper() for c in existing}
    new_codes = []
    for c in codes:
        c_clean = c.strip()
        if c_clean and c_clean.upper() not in seen:
            seen.add(c_clean.upper())
            new_codes.append(c_clean)

    if new_codes or not os.path.exists(CODELIST_FILE):
        all_codes = existing + new_codes
        with open(CODELIST_FILE, "w", encoding="utf-8") as f:
            f.write("# Delta Force Gift Codes\n")
            for c in all_codes:
                f.write(f"{c}\n")


def load_state() -> dict:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    if not os.path.exists(STATE_FILE):
        return {"game": "Delta Force", "codes": {}}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"game": "Delta Force", "codes": {}}


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_all_codes_merged(state: dict) -> dict[str, dict]:
    """Combines codelist.txt and state file into a unified dict."""
    merged = {}
    codelist = load_codelist()
    state_codes = state.get("codes", {})

    # Add codelist entries (default status: pending)
    for c in codelist:
        merged[c] = {"status": "pending", "tried_at": None, "note": ""}

    # Overlay with actual tracking state (case-insensitive key mapping)
    codelist_map = {c.upper(): c for c in codelist}
    for c, info in state_codes.items():
        matched_key = codelist_map.get(c.upper(), c)
        merged[matched_key] = info

    return merged


def cmd_list(state: dict):
    merged = get_all_codes_merged(state)
    if not merged:
        print("No codes tracked yet.")
        return
    print(f"Game: {state.get('game', 'Delta Force')}")
    print(f"{'CODE':<30} {'STATUS':<10} {'TRIED_AT':<22} NOTE")
    print("-" * 80)
    for code, info in sorted(merged.items()):
        tried = info.get("tried_at") or "-"
        note = info.get("note") or ""
        print(f"{code:<30} {info.get('status', 'pending'):<10} {tried:<22} {note}")


def cmd_add(state: dict, codes: list[str]):
    merged = get_all_codes_merged(state)
    existing_upper = {k.upper() for k in merged}
    added, skipped = [], []

    for code in codes:
        code_str = code.strip()
        if not code_str:
            continue
        if code_str.upper() in existing_upper:
            skipped.append(code_str)
        else:
            state.setdefault("codes", {})[code_str] = {
                "status": "pending",
                "tried_at": None,
                "note": "",
            }
            existing_upper.add(code_str.upper())
            added.append(code_str)

    if added:
        save_state(state)
        save_codelist(added)
        print(f"Added ({len(added)}): {', '.join(added)}")
    if skipped:
        print(f"Already tracked ({len(skipped)}): {', '.join(skipped)}")


def cmd_update(state: dict, code: str, status: str, note: str = ""):
    code = code.strip()
    if status not in VALID_STATUSES:
        print(f"ERROR: invalid status '{status}'. Choose from: {', '.join(VALID_STATUSES)}", file=sys.stderr)
        sys.exit(1)

    state.setdefault("codes", {})
    # Match existing casing if present
    matched_key = next((k for k in state["codes"] if k.upper() == code.upper()), code)
    state["codes"][matched_key] = {
        "status": status,
        "tried_at": now_iso(),
        "note": note,
    }
    save_state(state)
    save_codelist([matched_key])
    print(f"Updated: {matched_key} -> {status}" + (f" ({note})" if note else ""))


def cmd_pending(state: dict):
    merged = get_all_codes_merged(state)
    pending = [c for c, v in merged.items() if v.get("status") == "pending"]
    if not pending:
        print("No pending codes.")
    else:
        print(f"Pending ({len(pending)}):")
        for c in sorted(pending):
            print(f"  {c}")


def cmd_stats(state: dict):
    from collections import Counter
    merged = get_all_codes_merged(state)
    counts = Counter(v.get("status", "pending") for v in merged.values())
    total = len(merged)
    print(f"Game  : {state.get('game', 'Delta Force')}")
    print(f"Total : {total}")
    for status in ["success", "error", "pending", "skip"]:
        print(f"  {status:<10}: {counts.get(status, 0)}")


def cmd_check(state: dict, codes: list[str]):
    merged = get_all_codes_merged(state)
    existing_upper = {k.upper(): (k, v) for k, v in merged.items()}
    print(f"{'CODE':<30} {'STATUS':<10} {'TRIED_AT':<22} NOTE")
    print("-" * 80)
    for code in codes:
        code_str = code.strip()
        if not code_str:
            continue
        if code_str.upper() in existing_upper:
            orig_key, info = existing_upper[code_str.upper()]
            tried = info.get("tried_at") or "-"
            note = info.get("note") or ""
            print(f"{orig_key:<30} {info.get('status', 'pending'):<10} {tried:<22} {note}")
        else:
            print(f"{code_str:<30} {'NOT_FOUND':<10} {'-':<22} -")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()
    state = load_state()

    if command == "list":
        cmd_list(state)
    elif command == "check":
        if len(sys.argv) < 3:
            print("Usage: manage_codes.py check <code> [<code> ...]")
            sys.exit(1)
        cmd_check(state, sys.argv[2:])
    elif command == "add":
        if len(sys.argv) < 3:
            print("Usage: manage_codes.py add <code> [<code> ...]")
            sys.exit(1)
        cmd_add(state, sys.argv[2:])
    elif command == "update":
        if len(sys.argv) < 4:
            print("Usage: manage_codes.py update <code> <status> [<note>]")
            sys.exit(1)
        note = sys.argv[4] if len(sys.argv) > 4 else ""
        cmd_update(state, sys.argv[2], sys.argv[3], note)
    elif command == "pending":
        cmd_pending(state)
    elif command == "stats":
        cmd_stats(state)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
