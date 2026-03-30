# House Hunt Media Feature Plan (Images + Videos)

## 1. Goal

Add media support with minimal code changes:

- After a quote is saved from a property text message, follow-up photos and videos should attach to that specific quote.
- Every quote should have a user-visible quote ID in Telegram summary output.
- Telegram commands should allow selecting a quote, editing that quote, and then attaching media to it.
- Media files should be uploaded to Cloudflare R2.
- Media metadata and public link should be saved in Supabase.
- Website should show a Media button on each quote card and open a media view where:
  - images can be opened large and browsed like a slider
  - videos are playable in-page
- Do not use Gemini for media handling.

## 2. Keep It Simple (Design Choice)

For v1, attach media directly to broker_quotes.id (quote-level mapping), and use explicit quote selection commands.

Simple deterministic rule:

- The bot stores ACTIVE_QUOTE_CONTEXT per user for 20 minutes.
- You can change active quote explicitly from Telegram using a command.
- Media always maps to the resolved active quote; no AI guesswork.

Quote ID strategy (minimal schema change):

- Keep existing broker_quotes.id UUID as source of truth.
- Show short quote ID in Telegram as first 4 chars of UUID, for example 9F2A.
- Commands accept full UUID or short ID prefix. If prefix matches multiple rows, bot asks for a longer ID.

## 3. Free and Low-Cost Approach

Recommended stack:

- Uploads: Cloudflare R2 Standard storage (via S3 API)
- Metadata: Supabase Postgres table only (store URLs, keys, type)
- Frontend delivery: read public media URLs directly

Why this is cheapest and simplest:

- R2 Standard free allowance includes 10 GB-month storage, 1M Class A ops, 10M Class B ops monthly.
- R2 egress to Internet is free.
- No extra backend service needed for upload because the bot already runs server-side and can upload directly.
- Supabase stores only metadata rows, not binary media files.

Important guardrail:

- Use R2 Standard class for v1. Do not use Infrequent Access for this use case.

## 4. Current Baseline (Already in Repo)

- Bot saves text-extracted listings in:
  - bot/main.py
  - bot/db.py
  - bot/extractor.py
- Schema exists for societies, configurations, broker_quotes in:
  - bot/schema.sql
- Website renders society detail and quote cards in:
  - website/app.js
  - website/index.html
  - website/style.css

## 5. Data Model Changes (Supabase)

Add one new table in bot/schema.sql:

```sql
CREATE TABLE IF NOT EXISTS property_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES broker_quotes(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video')),
    public_url TEXT NOT NULL,
    r2_key TEXT NOT NULL,
    telegram_file_id TEXT,
    telegram_file_unique_id TEXT,
    caption TEXT,
    uploaded_by BIGINT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_property_media_quote_created
ON property_media (quote_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_property_media_quote_unique_file
ON property_media (quote_id, telegram_file_unique_id)
WHERE telegram_file_unique_id IS NOT NULL;
```

Reasoning:

- quote_id gives exact mapping to the quote card the user intended.
- media_type supports mixed gallery rendering.
- unique index prevents duplicate save on repeated forwards.

## 6. Bot Changes (Minimal)

### 6.1 Files to Update

- bot/requirements.txt
- bot/config.py
- bot/.env.example
- bot/db.py
- bot/main.py

### 6.2 New File

- bot/storage_r2.py

### 6.3 Environment Variables

Add:

- R2_ACCOUNT_ID
- R2_ACCESS_KEY_ID
- R2_SECRET_ACCESS_KEY
- R2_BUCKET
- R2_PUBLIC_BASE_URL

R2_PUBLIC_BASE_URL should be your public bucket domain base, for example custom domain or r2.dev base.

### 6.4 Upload Service

In bot/storage_r2.py:

- Create singleton boto3 S3 client with endpoint:
  - https://<ACCOUNT_ID>.r2.cloudflarestorage.com
- Add upload helper:
  - upload_media(content_bytes, key, content_type) -> public_url

Object key pattern:

- quotes/{quote_id}/{yyyy}/{mm}/{timestamp}_{telegram_unique_id}.{ext}

### 6.5 Quote Selection and Active Context (20 Minutes)

Add very small in-memory map in bot/main.py:

- ACTIVE_QUOTE_CONTEXT[user_id] = {
  - quote_id
  - short_id
  - expires_at
}

Set active quote after each successful quote save in on_text.

Context TTL: 20 minutes.

When one message contains multiple listings:

- Bot shows one-line summary for each saved quote including short ID.
- Bot sets last saved quote as active by default.
- User can switch active quote explicitly with command.

If no context:

- Reply with guidance: use /summary then /add <quote_id>.

### 6.6 Telegram Commands

Keep command count small and practical:

- /start
  - Show usage and media mapping rules.
- /summary
  - List recent quotes in one line each, for example:
    - 9F2A1C7B | Logix Blossom | 3BHK | 1250sqft | Rs85L | Ramesh | 24 Mar
- /add <quote_id>
  - Set active quote for the next 20 minutes.
  - Use this before sending image or video for older quote.
- /edit <quote_id> field=value field=value ...
  - Update specific quote fields directly from Telegram.
  - Supported fields in v1: price_lakh, floor, facing, notes, availability, broker_name, broker_phone.

Optional convenience (same minimal logic):

- If media is sent as reply to a bot quote summary line, use that quote_id directly.

This avoids Gemini and avoids complex session-state architecture.

### 6.7 Telegram Media Detection

Add handler for media in bot/main.py:

- filters.PHOTO
- filters.VIDEO

Detection rules:

- if message.photo exists -> media_type = image
  - pick highest resolution: message.photo[-1]
- if message.video exists -> media_type = video
- read caption if present

Download and upload flow:

1. Get Telegram file from media object.
2. Download bytes to memory.
3. Build R2 key.
4. Upload to R2.
5. Insert row in property_media via db.py.
6. Reply confirmation with quote summary and media type.

No Gemini calls in this path.

### 6.8 DB Functions in bot/db.py

Add:

- save_property_media(...)
- get_quote_media(quote_id)
- get_recent_quotes(limit)
- update_quote_fields(quote_id, patch)
- resolve_quote_id(input_id, recent_quotes)

Keep all current save pipeline untouched.

## 7. Website Changes

### 7.1 Files to Update

- website/app.js
- website/index.html
- website/style.css

### 7.2 UX (Simple)

In society detail page quote cards:

- Add a Media button on each quote card.
- Button opens a dedicated media view (or full-screen modal) for that specific quote.

Media view behavior:

- Show tabs: All, Photos, Videos.
- Grid of thumbnails/cards.
- Click image -> open lightbox and browse next or previous.
- Video cards render with native video controls.

Keep interaction minimal and mobile-friendly.

### 7.3 Data Fetch

Query table property_media by quote_id ordered by created_at desc.

Use existing frontend Supabase client setup. No additional backend required.

## 8. Edge Cases and Rules

- Media before any quote context: reject with clear guidance.
- Context expired: ask user to resend quote text, then media.
- Bot restart: context map clears (acceptable in v1; simplest behavior).
- Duplicate file forwarded again: ignored by unique constraint.
- Album uploads: each photo or video saved as separate row.
- Two quotes then media for first quote: use /add <first_quote_id> before upload.
- Ambiguous short quote ID: bot asks for longer ID.
- /edit with invalid field: bot returns allowed fields list.

## 9. Security Notes

- Keep R2 write credentials only in bot env, never in frontend.
- Frontend only receives already-public URLs.
- If frontend cannot read property_media due RLS or grants, mirror the same policy style used by current tables.

## 10. Rollout Plan (Small Iterations)

1. Schema + env + R2 upload helper
2. Bot commands: /summary, /add, /edit + quote ID resolution
3. Bot media handler + active-quote mapping
4. Quote card media button + gallery view
5. Testing and polish

## 11. Test Checklist

- Send one quote text, then one photo: photo appears for that quote.
- Send one video after same quote: video appears and plays.
- Send two quotes A and B, then run /add A, then send media: media maps to A.
- Run /summary: verify one-line rows with quote IDs are shown.
- Run /edit <id> price_lakh=84 floor=6th: verify quote row updated.
- Send multiple images: all show in gallery and can be browsed.
- Click image: opens large view and can slide.
- Send media with no recent quote text: bot rejects with helpful message.
- Verify the media opened from one quote card does not show media from other quotes.
- Verify existing text extraction and save flow still works unchanged.

## 12. Media Compression (Before Upload)

All compression runs in bot/compress.py, called automatically in on_media before upload.

### 12.1 Image Compression

- Library: Pillow (pip package)
- Steps:
  1. Skip if file is already under 500 KB.
  2. Resize longest side to max 1920 px (keep aspect ratio).
  3. Convert to RGB, save as JPEG with quality 82, optimize=True.
  4. If still over 1.0 MB, lower quality in steps of 5 down to 60.
  5. If compressed is larger than original, keep original.
- Typical result: 20 MB photo → 1.0 MB, visually similar.

### 12.2 Video Compression

- Tool: ffmpeg (must be installed on system PATH)
- Command: `ffmpeg -i input -vf scale='min(1280,iw)':-2 -c:v libx264 -crf 28 -preset fast -c:a aac -b:a 96k -movflags +faststart -y output`
- Steps:
  1. Skip if file is already under 500 KB.
  2. Skip if ffmpeg is not installed (graceful fallback, no crash).
  3. Write to temp file, run ffmpeg, read output.
  4. If output is bigger than original, keep original.
  5. Clean up temp files always.
  6. 2-minute timeout safety cap per video.
- Typical result: 20 MB short video → 3–6 MB. Short clips can reach 2–3 MB.

### 12.3 Config Toggle

- COMPRESS_MEDIA env var (default: 1 = enabled).
- Set COMPRESS_MEDIA=0 in .env to disable compression.

### 12.4 Telegram Feedback

- After compression, bot sends: `Compressed: 20480 KB → 2900 KB`
- Only shown when size actually decreased.

## 13. Expected Code Footprint

Approximate impact:

- 2 new python files (storage_r2.py or storage_supabase.py, compress.py)
- 5 bot file edits
- 3 frontend file edits
- 1 schema migration block

This stays low-risk and aligned with your minimal-change preference.