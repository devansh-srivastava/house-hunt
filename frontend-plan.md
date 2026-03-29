# 🏠 House Hunt — Frontend Plan
---

## Tech

| What | How |
|------|-----|
| Structure | Single `index.html` |
| Styling | Single `style.css` |
| Logic | Single `app.js` |
| Supabase | `@supabase/supabase-js` via CDN (esm.sh) |
| Routing | Hash-based (`#/` = home, `#/society/{id}` = detail) |
| Hosting | GitHub Pages (static files, no build) |

---

## Design Direction

**Vibe:** Clean, minimal, Gen Z — like a Notion page or a modern notes app.

### Colors
| Role | Color |
|------|-------|
| Background | `#FAFAF8` — warm off-white |
| Card background | `#FFFFFF` with subtle border |
| Text primary | `#1A1A1A` |
| Text secondary | `#6B7280` — muted gray |
| Accent | `#2563EB` — calm blue (links, active states) |
| Status: New | `#E5E7EB` — light gray chip |
| Status: Interested | `#DBEAFE` — light blue chip |
| Status: Shortlisted | `#FEF3C7` — light amber chip |
| Status: Visited | `#D1FAE5` — light green chip |
| Status: Not Interested | `#FEE2E2` — light red chip |

### Typography
- Font: `Inter` (Google Fonts) — clean, modern, great on mobile
- Society names: 16px semi-bold
- Body/details: 14px regular
- Labels/dates: 12px, muted gray

### General Rules
- Rounded corners (8px) on cards
- Subtle `box-shadow` on cards — no hard borders
- Generous padding inside cards (16px)
- 12px gap between cards
- No icons unless absolutely needed (keep it text-driven)
- WhatsApp button = green pill button, large enough to tap

---

## Layout

### View 1: Home (Society List)

```
┌─────────────────────────────┐
│  🏠 House Hunt              │  ← simple text header
├─────────────────────────────┤
│  [Search societies...]      │  ← sticky on scroll
├─────────────────────────────┤
│  All · Interested · Short-  │  ← filter chips (horizontal scroll OK)
│  listed · Visited           │
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ Ace Aspire              │ │  ← society name (bold)
│ │ Greater Noida West      │ │  ← location (muted)
│ │ 2BHK  3BHK              │ │  ← config tags (small pills)
│ │ Interested    24 Mar    │ │  ← status chip + last updated
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ Prateek Grand City      │ │
│ │ Siddharth Vihar         │ │
│ │ 3BHK                    │ │
│ │ New             22 Mar  │ │
│ └─────────────────────────┘ │
│         ...                 │
└─────────────────────────────┘
```

**Data shown per card:**
- `societies.name`
- `societies.location`
- Config types from `configurations.type` (deduplicated tags)
- `society_status.status`
- Latest `broker_quotes.added_on` for "last updated"

**Interactions:**
- Type in search → filters cards by society name (client-side, instant)
- Tap a filter chip → filters by status
- Tap a card → navigates to `#/society/{id}`

---

### View 2: Society Detail

```
┌─────────────────────────────┐
│  ← Back                     │  ← goes to #/
├─────────────────────────────┤
│  Ace Aspire                 │  ← society name (large)
│  Greater Noida West         │  ← location
│                             │
│  Status: [Interested ▾]     │  ← dropdown, saves on change
│                             │
│  Notes:                     │
│  ┌─────────────────────────┐│
│  │ Good society, park      ││  ← editable textarea
│  │ facing available        ││     saves on blur (lose focus)
│  └─────────────────────────┘│
├─────────────────────────────┤
│  ┌──────┐ ┌──────┐         │
│  │ 3BHK │ │ 2BHK │         │  ← config tabs/pills
│  └──────┘ └──────┘         │
├─────────────────────────────┤
│  3BHK — 1250 sqft          │  ← selected config header
│                             │
│ ┌─────────────────────────┐ │
│ │ Ramesh · 98XXXXXXXX     │ │  ← broker quote card
│ │ ₹85L · 4th Floor · East │ │
│ │ Ready to move            │ │
│ │ 24 Mar 2025              │ │
│ │ [💬 WhatsApp]            │ │  ← green button
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ Sunil · 99XXXXXXXX      │ │  ← another quote, same config
│ │ ₹82L · 6th Floor · West │ │
│ │ Under construction       │ │
│ │ 20 Mar 2025              │ │
│ │ [💬 WhatsApp]            │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

**Data flow:**
- Fetch society by ID → show name, location
- Fetch `society_status` for this society → show status dropdown + notes
- Fetch all `configurations` for this society → render config pills
- First config selected by default
- Fetch `broker_quotes` for selected config → render quote cards sorted by `added_on` desc

**Interactions:**
- Change status dropdown → upsert to `society_status` table
- Edit notes → save on blur to `society_status` table
- Tap config pill → switch quotes shown
- Tap WhatsApp → opens `https://wa.me/{broker_phone}`
- Back button → go to `#/`

---

## Supabase Queries (what the JS will do)

### Home page load
```sql
-- Get all societies with their status and configs
SELECT s.*, ss.status, ss.updated_at
FROM societies s
LEFT JOIN society_status ss ON ss.society_id = s.id
ORDER BY ss.updated_at DESC NULLS LAST
```
Then for config tags, one query:
```sql
SELECT society_id, type FROM configurations
```
Group client-side by `society_id`.

### Society detail page
```sql
-- Society info
SELECT * FROM societies WHERE id = ?

-- Status
SELECT * FROM society_status WHERE society_id = ?

-- Configs
SELECT * FROM configurations WHERE society_id = ?

-- Quotes for selected config
SELECT * FROM broker_quotes WHERE config_id = ? ORDER BY added_on DESC
```

### Writes
```sql
-- Upsert status (on dropdown change or notes edit)
UPSERT INTO society_status (society_id, status, personal_notes, updated_at)
VALUES (?, ?, ?, now())
```

---

## File Structure

```
website/
├── index.html      # Single HTML file, both views
├── style.css       # All styles
├── config.js       # Public runtime Supabase config
├── app.js          # All logic (~200 lines)
└── README.md       # How to set up Supabase URL/key
```

**No build step.** Supabase config lives in `config.js`. Use the public Publishable key when available, or legacy anon if not. Do not put Secret or service_role in the frontend.

---

## Mobile-First Rules

- Max-width `480px` for content area (centered on desktop)
- Cards fill full width on mobile
- Touch targets minimum 44px height
- WhatsApp button: full-width green pill, 48px tall
- Search bar: full-width, sticky top
- No hover-only interactions — everything works with tap
- Status dropdown: native `<select>` — works great on mobile
- Notes: native `<textarea>` — mobile keyboard friendly

---

## Build Order

1. Create `index.html` with both views (home + detail) as `<section>` blocks, toggled via JS
2. Create `style.css` — full styling, mobile-first
3. Create `app.js` — Supabase client, hash router, data fetch, render functions
4. Test locally (just open `index.html` in browser — needs a local server for ES modules)
5. Deploy to GitHub Pages
