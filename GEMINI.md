# Workspace Skill Instructions

Whenever an `agy` session is started in this workspace directory, automatically load and follow the **`game-giftcode`** skill located at:
- `game-giftcode/SKILL.md` (or `.gemini/skills/game-giftcode/SKILL.md`)

This skill manages, tracks, and redeems game gift codes, remembers code history in `data/codes.json`, and handles Delta Force (Garena) API redemptions.

### Command Execution Rules
- Commands starting with `python3 game-giftcode/scripts/manage_codes.py` (or `python3 <skill_dir>/scripts/manage_codes.py`) are pre-approved for execution in this workspace.
