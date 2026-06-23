#!/usr/bin/env python3
"""
manage_codes.py — Game Gift Code state manager
Usage:
  manage_codes.py list
  manage_codes.py add <code> [<code> ...]
  manage_codes.py update <code> <status> [<note>]
  manage_codes.py pending
  manage_codes.py stats
"""

import json
import sys
import os
from datetime import datetime, timezone

STATE_FILE = os.path.join(os.path.dirname(__file__), "../data/codes.json")
VALID_STATUSES = {"pending", "success", "error", "skip"}


def load_state() -> dict:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    if not os.path.exists(STATE_FILE):
        return {"game": "unknown", "codes": {}}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_list(state: dict):
    codes = state.get("codes", {})
    if not codes:
        print("No codes tracked yet.")
        return
    print(f"Game: {state.get('game', 'unknown')}")
    print(f"{'CODE':<30} {'STATUS':<10} {'TRIED_AT':<22} NOTE")
    print("-" * 80)
    for code, info in sorted(codes.items()):
        tried = info.get("tried_at") or "-"
        note  = info.get("note") or ""
        print(f"{code:<30} {info['status']:<10} {tried:<22} {note}")


def cmd_add(state: dict, codes: list[str]):
    added, skipped = [], []
    for code in codes:
        code = code.strip().upper()
        if not code:
            continue
        if code in state["codes"]:
            skipped.append(code)
        else:
            state["codes"][code] = {"status": "pending", "tried_at": None, "note": ""}
            added.append(code)
    save_state(state)
    if added:
        print(f"Added ({len(added)}): {', '.join(added)}")
    if skipped:
        print(f"Already tracked ({len(skipped)}): {', '.join(skipped)}")


def cmd_update(state: dict, code: str, status: str, note: str = ""):
    code = code.strip().upper()
    if status not in VALID_STATUSES:
        print(f"ERROR: invalid status '{status}'. Choose from: {', '.join(VALID_STATUSES)}", file=sys.stderr)
        sys.exit(1)
    if code not in state["codes"]:
        # Auto-add if not tracked yet
        state["codes"][code] = {"status": "pending", "tried_at": None, "note": ""}
    state["codes"][code]["status"] = status
    state["codes"][code]["tried_at"] = now_iso()
    state["codes"][code]["note"] = note
    save_state(state)
    print(f"Updated: {code} -> {status}" + (f" ({note})" if note else ""))


def cmd_pending(state: dict):
    pending = [c for c, v in state.get("codes", {}).items() if v["status"] == "pending"]
    if not pending:
        print("No pending codes.")
    else:
        print(f"Pending ({len(pending)}):")
        for c in sorted(pending):
            print(f"  {c}")


def cmd_stats(state: dict):
    from collections import Counter
    counts = Counter(v["status"] for v in state.get("codes", {}).values())
    total = sum(counts.values())
    print(f"Game  : {state.get('game', 'unknown')}")
    print(f"Total : {total}")
    for status in ["success", "error", "pending", "skip"]:
        print(f"  {status:<10}: {counts.get(status, 0)}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()
    state = load_state()

    if command == "list":
        cmd_list(state)
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
