# 🤖 House Hunt — Telegram Bot Plan

---

## Overview

Personal Telegram bot: forward broker messages → Gemini extracts property data → saved to Supabase → website auto-reflects.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Bot Framework | `python-telegram-bot` v22.x |
| AI Backend | Google Gemini 2.5 Flash (`google-genai` SDK) |
| Database | Supabase PostgreSQL (`supabase-py`) |
| Language | Python 3.11+ |

---

## Bot Files

```
bot/
├── main.py           # Entry point — handlers, batching, confirmation cards
├── extractor.py      # Gemini extraction + prompt + retry
├── db.py             # Supabase CRUD
├── session.py        # In-memory broker session state
├── config.py         # Env vars + constants
├── schema.sql        # DB migration — run in Supabase SQL Editor
├── requirements.txt
└── .env.example
```

---

## User Flow

1. **Set broker:** `Broker: Ramesh 9876543210` → session starts
2. **Forward messages:** any text/WhatsApp forwards → buffered for 5 seconds
3. **AI extraction:** all buffered messages sent to Gemini in 1 call → JSON array
4. **Confirmation cards:** each listing shown with [Save] [Skip] [Edit] buttons
5. **Save:** society → config → broker quote written to Supabase
6. **Done:** type `done` to clear broker session

## Commands

| Command | Action |
|---------|--------|
| `/start` | Welcome + usage instructions |
| `/list` | Show all saved societies with status |
| `/status SocietyName` | Show all configs & quotes for a society |
| `Broker: Name Phone` | Set active broker |
| `done` | Clear active broker |

---

## Message Batching

Timer-based approach (PTB JobQueue pattern):
- Each forwarded message resets a 5-second timer
- When silence hits, all buffered messages go to Gemini in ONE call
- 10 rapid forwards = 1 API call

---

## Gemini Extraction

- System prompt: "real estate data extractor for Indian property markets"
- Structured JSON output (`response_mime_type="application/json"`)
- Low temperature (0.1) for factual accuracy
- Handles: Hindi/English, lakhs/crores, BHK variations, multi-listing messages
- Retry with exponential backoff on 429 errors

---

## Edge Cases

| Case | Handling |
|------|---------|
| No broker set | Prompt user to set one |
| Empty Gemini result | "No listings found" |
| Duplicate society | Case-insensitive match, reuses existing |
| Duplicate config | Reuses existing, adds new quote (price history) |
| Non-real-estate text | Gemini returns `[]`, bot says no listings |
| 429 rate limit | Exponential backoff, max 3 retries |
| Double-tap Save | Message already edited on first tap, second is harmless |

---

## Testing Checklist

- [ ] `Broker: Test 9999999999` → session created
- [ ] Forward single message → confirmation card with correct data
- [ ] Forward 5 messages rapidly → all batched → cards appear
- [ ] Tap Save → data in Supabase
- [ ] Tap Skip → no DB write
- [ ] Tap Edit → send correction → new card
- [ ] `done` → session cleared
- [ ] `/list` → all societies
- [ ] `/status Ace Aspire` → quotes for that society
- [ ] Non-real-estate text → "no listings found"
- [ ] Other users ignored
