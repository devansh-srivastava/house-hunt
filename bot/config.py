"""
Central config — loads env vars and defines constants.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

ALLOWED_USER_ID = int(os.environ["ALLOWED_USER_ID"])

GEMINI_MODEL = "gemini-2.5-flash"

# ── Supabase Storage (for quote photos/videos) ──
# Uses the same SUPABASE_URL + SUPABASE_KEY credentials as database writes.
SUPABASE_MEDIA_BUCKET = os.environ.get("SUPABASE_MEDIA_BUCKET", "property-media").strip()

# Media uploads are enabled when a bucket name is configured.
MEDIA_UPLOADS_ENABLED = bool(SUPABASE_MEDIA_BUCKET)

# ── Media Compression ──
# Set to False in .env (COMPRESS_MEDIA=0) to skip compression.
COMPRESS_MEDIA = os.environ.get("COMPRESS_MEDIA", "1").strip() not in ("0", "false", "no")
