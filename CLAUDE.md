# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A CLI tool that pulls live data from a Zscaler tenant via OneAPI and sends it to Claude for security analysis. It is not a web app or service — it runs interactively in the terminal.

## Setup & Running

```bash
# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, ZSCALER_CLIENT_ID, ZSCALER_CLIENT_SECRET, ZSCALER_CLOUD, ZSCALER_VANITY_DOMAIN

# Run
python main.py
```

## Architecture

```
main.py               — CLI entrypoint: menu loop, orchestration, report saving
src/auth.py           — ZscalerAuth: OAuth2 client_credentials flow, auto token refresh
src/zscaler_client.py — ZscalerClient: thin HTTP wrapper around ZIA/ZPA/ZDX REST endpoints
src/analyst.py        — ZscalerAnalyst: sends Zscaler JSON + question to Claude, streams response
logs/                 — JSON reports saved after each analysis (timestamp_label.json)
```

**Data flow:** `main.py` calls a `ZscalerClient` fetcher → raw JSON is passed to `ZscalerAnalyst.analyze()` → Claude streams the response to stdout → result is saved to `logs/`.

## Key Design Points

- `ZscalerAuth.token` is a lazy property — it fetches/refreshes automatically on access, no manual token management needed. Token URL uses `ZSCALER_VANITY_DOMAIN`, not `ZSCALER_CLOUD`.
- `ZscalerClient` only implements ZIA endpoints in the interactive menu; ZPA/ZDX methods exist on the class but are not wired to menu items yet. ZPA methods require a `customer_id` parameter that has no UI to collect it.
- The custom question flow (`[c]` in menu) exposes `get_blocked_destinations` as an extra data source not available in the numbered menu.
- `ZscalerAnalyst` streams by default (`stream=True`). Pass `stream=False` for non-interactive use.
- The model is hardcoded to `claude-opus-4-6` in [src/analyst.py](src/analyst.py).
- Large payloads (>50k estimated tokens) trigger a warning but are still sent.
- `prompt()` in `main.py` is an EOF-safe wrapper around `input()` — it returns `None` instead of raising on piped/non-interactive use. All user input goes through it.

## Credentials

| Variable | Where to find it |
|---|---|
| `ZSCALER_CLIENT_ID` / `ZSCALER_CLIENT_SECRET` | Zscaler Admin > API > API Key Management |
| `ZSCALER_CLOUD` | Zscaler Admin > About (e.g. `zscalerthree.net`) |
| `ZSCALER_VANITY_DOMAIN` | Zscaler Admin > Authentication > Authentication Profile (e.g. `yourcompany.zslogin.net`) |
