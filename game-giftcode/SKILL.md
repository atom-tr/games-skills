---
name: game-giftcode
description: >
  Manage and redeem game gift codes. Remembers which codes have been tried
  (success or error) so only new/untried codes are submitted. Supports
  browser automation via puppeteer or direct API calls.
---

# Game Gift Code Skill

## State File

All code history is stored in:
`<skill_dir>/data/codes.json`

Format:
```json
{
  "game": "game-name",
  "codes": {
    "CODE123": { "status": "success", "tried_at": "2026-06-23T08:00:00Z", "note": "" },
    "BADCODE": { "status": "error",   "tried_at": "2026-06-23T08:01:00Z", "note": "expired" },
    "NEWCODE": { "status": "pending", "tried_at": null, "note": "" }
  }
}
```

Statuses:
- `pending`  — not tried yet
- `success`  — redeemed successfully
- `error`    — tried but failed (expired / invalid / already used)
- `skip`     — manually marked to skip

## Workflow — When User Provides Codes

1. **Read state file** via `cat <skill_dir>/data/codes.json`
2. **Diff**: compare user-provided list against stored codes
3. **Report**: tell user which codes are new vs already tried
4. **Ask confirmation** before attempting new codes
5. **Try each new code** one by one using the appropriate method (see below)
6. **Update state file** immediately after each attempt (do not batch-write)

## Redeem Methods

### Method A — API (preferred if game has a redeem endpoint)

Use `curl`. Check `resources/api_examples.md` for known game APIs.

```bash
# Example structure
curl -s -X POST "https://game.example.com/api/redeem" \
  -H "Authorization: Bearer $GAME_TOKEN" \
  -d '{"code": "CODE123", "uid": "YOUR_UID"}'
```

Parse the JSON response — on success update status to `success`, on failure update to `error` with the error message as `note`.

### Method B — Browser (puppeteer via MCP)

Use the MCP puppeteer tool to:
1. Navigate to the game's redeem page
2. Fill in the code input field
3. Click submit
4. Read the result toast/alert text
5. Return result to agent for state update

Reference: `resources/puppeteer_guide.md`

## Helper Script

Use `scripts/manage_codes.py` to read/write the state file safely:

```bash
# List all codes and their status
python3 <skill_dir>/scripts/manage_codes.py list

# Add new codes (status=pending if not already tracked)
python3 <skill_dir>/scripts/manage_codes.py add CODE1 CODE2 CODE3

# Update a code's status after attempt
python3 <skill_dir>/scripts/manage_codes.py update CODE1 success "got 500 gems"
python3 <skill_dir>/scripts/manage_codes.py update CODE2 error "code expired"

# Show only new/pending codes
python3 <skill_dir>/scripts/manage_codes.py pending
```

## Rules

- **Path Resolution**: All paths specified in this skill (referenced via the `<skill_dir>` placeholder) are relative to the skill's installation directory (the directory containing `SKILL.md`). The AI agent must resolve `<skill_dir>` to the actual installation path of this skill dynamically before execution.
- **Never retry** a code with status `success` or `error` — it wastes attempts and may get account flagged
- **Always save state** after each individual attempt, not at the end of a batch
- **Rate limit**: wait 2s between each code submission to avoid being throttled
- If the game requires login credentials or tokens, ask user for them — **never hardcode secrets**
- If unsure about the redeem URL/selector, ask the user to provide it before proceeding

---

## Game Profiles

### Delta Force (Garena)

- **API endpoint**: `https://sg-act.playerinfinite.com/api/proxy/present/CdkV2/RedeemCDKey`
- **Script**: `scripts/redeem_deltaforce_api.py` — direct API, **no browser needed**
- **Signature**: `MD5(path?params&intel#!2022$act)` appended as `&s=`

**Required env vars** (from Garena auth JSON):
```bash
export DF_OPENID="8486567269679708357"       # numeric openid field
export DF_TOKEN="fbf006dac704924e09e8346..."  # token field (not channel access_token)
```

**How to get tokens**: paste the Garena auth JSON to agent — extract `openid` and `token` fields.

**Redeem a single code**:
```bash
DF_OPENID="..." DF_TOKEN="..." \
  python3 <skill_dir>/scripts/redeem_deltaforce_api.py CODEHERE
```

**Redeem a batch** (agent workflow):
```bash
# 1. Add all codes first
python3 <skill_dir>/scripts/manage_codes.py add CODE1 CODE2 CODE3

# 2. Redeem all pending codes (auto 2s delay between each)
DF_OPENID="..." DF_TOKEN="..." \
  python3 <skill_dir>/scripts/redeem_deltaforce_api.py CODE1 CODE2 CODE3
```

**API response codes**:
| code   | meaning                                |
|--------|----------------------------------------|
| 0      | ✅ success                              |
| 400054 | ❌ code does not match (invalid/wrong) |
| 400055 | ❌ already claimed by this account     |
| 400067 | ❌ redemption limit reached (code used up) |
| 400082 | ❌ game role error (wrong game_id)     |
| 300001 | ❌ not logged in (bad token/openid)    |

