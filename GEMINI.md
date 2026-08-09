# Workspace Skill Instructions

Whenever an `agy` session is started in this workspace directory, automatically load and follow the **`game-giftcode`** skill located at:
- `game-giftcode/SKILL.md` (or `.gemini/skills/game-giftcode/SKILL.md`)

This skill manages, tracks, and redeems game gift codes, remembers code history in `data/codes.json`, and handles Delta Force (Garena) API redemptions.

### Command Execution Rules
- Commands starting with `python3 game-giftcode/scripts/manage_codes.py` (or `python3 <skill_dir>/scripts/manage_codes.py`) are pre-approved for execution in this workspace.
- Commands running `python3 game-giftcode/scripts/redeem_deltaforce_api.py` (or `python3 <skill_dir>/scripts/redeem_deltaforce_api.py`), including when prefixed with `DF_OPENID` and `DF_TOKEN` environment variables, are pre-approved for execution in this workspace.

### Multi-User State Tracking Rule
- If the user running this skill is not the author, ensure their code history is saved in a separate directory or via `CODES_FILE` (e.g. `export CODES_FILE="/path/to/my_codes.json"`) so they can independently track their own used gift codes.

