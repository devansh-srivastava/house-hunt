# Media Feature Setup (Supabase Storage)

Everything required before quote media upload/view works.

## 1. Create a Supabase Storage Bucket

1. Open your Supabase project dashboard.
2. Go to Storage -> Buckets.
3. Click New bucket.
4. Bucket name: property-media (or any name you prefer).
5. Set bucket visibility to Public.
6. Create the bucket.

If you use a different bucket name, set the same name in bot/.env as SUPABASE_MEDIA_BUCKET.

## 2. Update bot/.env

Set these values in bot/.env:

```env
TELEGRAM_BOT_TOKEN=...
GEMINI_API_KEY=...
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=YOUR_SECRET_OR_SERVICE_ROLE_KEY
SUPABASE_MEDIA_BUCKET=property-media
ALLOWED_USER_ID=YOUR_TELEGRAM_NUMERIC_USER_ID
```

Notes:
- SUPABASE_KEY must be a server-side key (Secret or service_role), never a public key.
- Website uses publishable/anon key separately in website/config.js.

## 3. Run SQL Migration (property_media)

In Supabase SQL Editor, run:

```sql
CREATE TABLE IF NOT EXISTS property_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES broker_quotes(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video')),
    public_url TEXT NOT NULL,
    storage_path TEXT NOT NULL,
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

This SQL is also present in bot/schema.sql.

## 4. RLS Policy For Frontend Media Read

If RLS is enabled, allow read access for website clients:

```sql
ALTER TABLE property_media ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read on property_media"
ON property_media FOR SELECT
USING (true);
```

For storage file URLs:
- Because the bucket is Public, files are directly readable via public URL.
- Bot uploads use the server-side key, so upload writes are allowed.

## 5. Python Dependencies

Install bot requirements (includes Pillow for image compression):

```powershell
cd bot
.\venv\Scripts\activate
pip install -r requirements.txt
```

## 6. Install ffmpeg (for Video Compression)

Video compression needs ffmpeg on system PATH. If you skip this, images still compress — videos just upload at original size.

**Windows (winget):**
```powershell
winget install Gyan.FFmpeg
```

**Windows (manual):**
1. Download from https://www.gyan.dev/ffmpeg/builds/ (release essentials zip).
2. Extract and add the `bin` folder to your system PATH.
3. Verify: `ffmpeg -version`

**Optional .env toggle:**
```env
COMPRESS_MEDIA=1   # set to 0 to disable all compression
```

## 7. Restart Bot

```powershell
cd bot
.\venv\Scripts\activate
python main.py
```

## 8. Test Flow

1. Send a property text message in Telegram.
2. Bot reply includes quote short IDs like [9F2A].
3. Send a photo or video.
4. Bot compresses the media and replies with size reduction (e.g. "Compressed: 20480 KB → 2900 KB").
5. Bot uploads to Supabase Storage and saves row in property_media.
6. Run /summary and /add <quote_id> to attach media to older quotes.
7. Open website, go to a quote card, click the media button to view gallery/lightbox.

## 9. Bot Commands

- /summary: List recent quotes with short IDs.
- /add <id>: Set active quote for media uploads (20 min).
- /edit <id> field=value: Update quote fields.

Editable fields: availability, broker_name, broker_phone, facing, floor, notes, price_lakh
