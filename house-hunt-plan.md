# 🏠 House Hunt Tracker — Full Build Plan

## Overview

A personal house hunting tracker with two parts:
1. **Telegram Bot** — you forward broker messages, AI extracts property data, saves to DB
2. **Website** — displays all societies, configurations, broker quotes in a clean mobile-first UI

---

## Tech Stack

| Part | Tool | Cost |
|------|------|------|
| Telegram Bot | Python + `python-telegram-bot` | Free |
| AI Extraction | Gemini 2.0 Flash (Google AI Studio) | Free |
| Database | Supabase (PostgreSQL) | Free |
| Website | React + Vite | Free |
| Bot Hosting | Railway free tier | Free |
| Website Hosting | GitHub Pages | Free |

---

## Database Schema

### `societies`
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
name TEXT NOT NULL
location TEXT
general_notes TEXT
created_at TIMESTAMP DEFAULT now()
```

### `configurations`
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
society_id UUID REFERENCES societies(id)
type TEXT NOT NULL  -- e.g. "3BHK", "2.5BHK", "2BHK"
area_sqft INTEGER
floor_range TEXT  -- e.g. "3-8"
general_notes TEXT
created_at TIMESTAMP DEFAULT now()
```

### `broker_quotes`
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
config_id UUID REFERENCES configurations(id)
broker_name TEXT
broker_phone TEXT  -- store as 91XXXXXXXXXX format
price_lakh NUMERIC
floor TEXT
facing TEXT
availability TEXT  -- e.g. "ready to move", "under construction"
notes TEXT
added_on TIMESTAMP DEFAULT now()
```

### `society_status`
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
society_id UUID REFERENCES societies(id)
status TEXT DEFAULT 'New'  -- New | Interested | Shortlisted | Visited | Not Interested
personal_notes TEXT
updated_at TIMESTAMP DEFAULT now()
```

---

## Telegram Bot — Full Behaviour

### Step 1: Set Active Broker
Before forwarding messages, you type:
```
Broker: Ramesh 98XXXXXX
```
Bot replies:
```
✅ Broker locked: Ramesh (98XXXXXX)
Forward messages now. Type "done" when finished.
```
Broker stays active for the entire session until you type `done` or set a new broker.

**Edge case:** If you forward a message without setting a broker first, bot asks:
```
⚠️ Who is this broker? Reply with name and number.
```

---

### Step 2: Forward Messages
You forward 1 or many broker messages in bulk. Bot batches all messages received within a 5-second window, then sends them together to Gemini for extraction.

---

### Step 3: AI Extraction (Gemini 2.0 Flash)

**Prompt sent to Gemini:**
```
You are a real estate data extractor. From the following broker messages, extract ALL property listings mentioned.

Active broker: {broker_name}, phone: {broker_phone}

Messages:
{all_forwarded_messages}

Return a JSON array. Each item should have:
- society_name (string)
- location (string or null)
- config (string, e.g. "3BHK")
- area_sqft (integer or null)
- price_lakh (float or null)
- floor (string or null)
- facing (string or null)
- availability (string or null)
- notes (string or null)

Return ONLY the JSON array. No explanation.
```

Gemini returns structured array even if one message has 3 societies or 5 messages have 1 society.

---

### Step 4: Society Matching
For each extracted society:
1. Bot checks existing society names in Supabase (case-insensitive exact match)
2. If match found → uses that existing society
3. If no match → creates new society automatically

> No fuzzy matching. Gemini extracts the society name as-is from the message (e.g. "Ace Aspire"), and that's what gets matched/stored.

---

### Step 5: Confirmation Card
For each extracted listing, bot sends:
```
📋 Ace Aspire — 3BHK
📐 Area: 1250 sqft
💰 Price: ₹85L
🏢 Floor: 4th
🧭 Facing: East
👤 Broker: Ramesh 98XXXXXX
📝 Notes: Ready to move

[✅ Save] [❌ Skip] [✏️ Edit]
```

If you tap **Edit**, bot asks you to send corrected details as plain text.

---

### Step 6: Save to Supabase
On confirmation:
1. Upsert society (create if new)
2. Upsert configuration under that society
3. Insert broker quote (always new row — keeps price history)
4. Website auto-reflects new data

---

### Bot Commands Summary
| Command | Action |
|--------|--------|
| `Broker: Name Number` | Set active broker for session |
| `done` | Clear active broker |
| `/list` | Show all societies saved so far |
| `/status Ace Aspire` | Show all quotes for a society |
| Forward any text | Triggers extraction flow |

---

## Website — UI Spec

### Stack
- React 19 + Vite
- Supabase JS client (reads directly from DB)
- Mobile-first layout
- Deployed on GitHub Pages (static build)

> ⚠️ No backend needed — React reads Supabase directly via public anon key with Row Level Security disabled (personal use only).

---

### Page 1: Society List (Home)

- Search bar at top — filter by society name
- Filter chips: `All | Interested | Shortlisted | Visited`
- Each society = one card showing:
  - Society name + location
  - Available configs as tags: `2BHK` `3BHK` `2.5BHK`
  - Status badge: `New / Interested / Shortlisted / Visited`
  - Last updated date
- Tap card → go to Society Detail page

---

### Page 2: Society Detail

- Society name + location at top
- Status dropdown (you can change status here)
- Personal notes field (editable inline)
- Config cards in a row: `3BHK` | `2BHK` | etc.
- Tap config → expands to show all broker quotes for that config

---

### Broker Quote Card (inside config)
```
Ramesh · 98XXXXXX
₹85L · 1250 sqft · 4th Floor · East Facing
Ready to move
Added: 24 Mar 2025

[💬 WhatsApp]
```
- **WhatsApp button** opens: `https://wa.me/91XXXXXXXXXX`
- Multiple quotes shown in chronological order (price history visible)

---

### Mobile-First Rules
- Cards stack vertically on mobile
- WhatsApp button large enough to tap easily
- No horizontal scroll
- Sticky search bar on home

---

## Rate Limit Handling (Gemini Free Tier)

- Free tier: 15 requests/minute, 1M tokens/day
- Bot queues messages with a 4-second delay between Gemini calls
- For bulk forwards (10 messages), all batched into ONE Gemini call → uses only 1 request
- Daily limit will not realistically be hit for personal use

---

## Project Folder Structure

```
house-hunt/
├── bot/
│   ├── main.py               # Telegram bot entry point
│   ├── extractor.py          # Gemini extraction logic
│   ├── db.py                 # Supabase read/write
│   ├── session.py            # Active broker session management
│   └── requirements.txt
│
├── website/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx      # Society list
│   │   │   └── Society.jsx   # Society detail
│   │   ├── components/
│   │   │   ├── SocietyCard.jsx
│   │   │   ├── ConfigCard.jsx
│   │   │   └── BrokerQuote.jsx
│   │   └── supabaseClient.js
│   ├── index.html
│   └── vite.config.js
│
└── README.md
```

---

## Environment Variables

### Bot (`bot/.env`)
```
TELEGRAM_BOT_TOKEN=
GEMINI_API_KEY=
SUPABASE_URL=
# Use the server-side key here.
# Prefer Secret. If your project only shows legacy keys, use service_role.
SUPABASE_KEY=
ALLOWED_USER_ID=
```

### Website
Use `website/config.js` for public frontend config.

For local dev and deploys, fill in:
```
window.HOUSE_HUNT_CONFIG = {
  supabaseUrl: '',
  supabaseKey: '',
}
```
> Use the new Publishable key when available. If your project only shows legacy keys, use anon. This key is public and safe to expose in a static site. GitHub Pages just serves the static files.

---

## Build Order for Agent

1. Set up Supabase — create all 4 tables with schema above
2. Build `db.py` — all Supabase read/write functions
3. Build `extractor.py` — Gemini extraction with exact prompt above
4. Build `session.py` — broker session state management
5. Build `main.py` — Telegram bot wiring everything together
6. Build React website — mobile-first, Home page first, then Society detail
8. Deploy bot to Railway, website to GitHub Pages

---

## Key Constraints to Respect

- Never overwrite broker quotes — always insert new row (price history)
- Broker phone stored as `91XXXXXXXXXX` (no spaces, no dashes)
- WhatsApp links use format: `https://wa.me/{broker_phone}`
- Website is read and write. but always ask when you submit a change from the website.
- Gemini prompt must return pure JSON array, no markdown
- Batch all messages from same session into one Gemini call
