# Puppeteer Browser Automation Guide

## When to use
Use puppeteer MCP when the game does NOT have a public API and requires
login + browser interaction to redeem codes.

## General Flow (via MCP puppeteer tools)

1. `puppeteer_navigate` → go to game redeem page
2. `puppeteer_fill` → fill the code input field (provide CSS selector)
3. `puppeteer_click` → click the submit button
4. `puppeteer_evaluate` → read result text from page (toast, alert, modal)
5. Parse result → update code status via manage_codes.py

## What to ask the user before starting
- Game redeem page URL (e.g. `https://game.com/gift`)
- CSS selector for code input field
- CSS selector for submit button
- CSS selector or text to read the result from
- Login credentials (if page requires auth) — store as env vars, never in state file

## Example Selectors (common patterns)
```
input[placeholder*="code"]   → code input
input[name="code"]           → code input (by name)
button[type="submit"]        → submit button
.toast-message               → result toast
.modal-body                  → result modal
```

## Rate Limiting
Wait at least 2000ms between each code submission:
- Use `puppeteer_evaluate` with `setTimeout` or just instruct agent to pause
