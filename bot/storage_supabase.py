"""
Supabase Storage upload helper.
Uploads photo/video bytes to a public bucket and returns the public URL.
"""
import logging

from config import SUPABASE_MEDIA_BUCKET
from db import get_db

logger = logging.getLogger(__name__)


def upload_media(content_bytes: bytes, storage_path: str, content_type: str) -> str:
    """Upload bytes to Supabase Storage and return the public URL."""
    storage = get_db().storage.from_(SUPABASE_MEDIA_BUCKET)

    # storage3 accepts raw bytes but not io.BytesIO in this installed version.
    storage.upload(
        storage_path,
        content_bytes,
        {"content-type": content_type, "upsert": "false"},
    )

    # supabase-py may return either a URL string or a dict depending on version.
    public = storage.get_public_url(storage_path)
    if isinstance(public, str):
        url = public
    elif isinstance(public, dict):
        data = public.get("data") if isinstance(public.get("data"), dict) else public
        url = data.get("publicUrl") or data.get("publicURL") or str(public)
    else:
        url = str(public)

    logger.info("[STORAGE] Uploaded %s (%d bytes)", storage_path, len(content_bytes))
    return url