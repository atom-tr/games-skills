# Known Game API Examples

## Genshin Impact / HoYoverse
- Redeem URL: `https://sg-hk4e-api.hoyoverse.com/common/apicdkey/api/webExchangeCdkey`
- Params: `uid`, `region`, `game_biz`, `cdkey`, `lang`
- Auth: requires `cookie_token` + `account_id` from browser cookies

## Generic REST pattern
```bash
curl -s -X POST "https://<game-api>/redeem" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"code\": \"$CODE\", \"uid\": \"$UID\"}"
```

## Notes
- Ask user to provide: game name, redeem URL, auth token/cookie, player UID
- Parse response for success/error keywords, then update state accordingly
