"""
Supabase database operations.
Singleton client — one connection for the bot's lifetime.
"""
import logging

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_db() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("[DB] Supabase client initialized → %s", SUPABASE_URL)
    return _client


# ── Societies ────────────────────────────────────────────

def get_all_society_names() -> list[str]:
    """Return all existing society names (for Gemini fuzzy matching)."""
    res = get_db().table("societies").select("name").execute()
    return [r["name"] for r in res.data]


def find_society(name: str) -> dict | None:
    res = get_db().table("societies").select("*").ilike("name", name).execute()
    return res.data[0] if res.data else None


def create_society(name: str) -> dict:
    db = get_db()
    society = db.table("societies").insert({"name": name}).execute().data[0]
    db.table("society_status").insert(
        {"society_id": society["id"], "status": "New"}
    ).execute()
    logger.info("[DB] Created society '%s' (id=%s)", name, society["id"])
    return society


def find_or_create_society(name: str) -> dict:
    return find_society(name) or create_society(name)


# ── Configurations ───────────────────────────────────────

def find_config(society_id: str, config_type: str) -> dict | None:
    res = (
        get_db()
        .table("configurations")
        .select("*")
        .eq("society_id", society_id)
        .ilike("type", config_type)
        .execute()
    )
    return res.data[0] if res.data else None


def create_config(society_id: str, config_type: str, area_sqft: int | None) -> dict:
    row = {"society_id": society_id, "type": config_type}
    if area_sqft:
        row["area_sqft"] = area_sqft
    config = get_db().table("configurations").insert(row).execute().data[0]
    logger.info("[DB] Created config '%s' for society %s", config_type, society_id)
    return config


def find_or_create_config(society_id: str, config_type: str, area_sqft: int | None) -> dict:
    return find_config(society_id, config_type) or create_config(society_id, config_type, area_sqft)


# ── Broker Quotes ────────────────────────────────────────

def insert_quote(config_id: str, broker_name: str | None, broker_phone: str | None,
                 price_lakh: float | None, floor: str | None, facing: str | None,
                 notes: str | None) -> dict:
    optional = {
        "broker_name": broker_name, "broker_phone": broker_phone,
        "price_lakh": price_lakh, "floor": floor, "facing": facing, "notes": notes,
    }
    row = {"config_id": config_id, **{k: v for k, v in optional.items() if v is not None}}
    quote = get_db().table("broker_quotes").insert(row).execute().data[0]
    logger.info("[DB] Inserted quote → config=%s | broker=%s | ₹%sL", config_id, broker_name, price_lakh)
    return quote


# ── Save pipeline ────────────────────────────────────────

def save_listing(society_name: str, listing: dict, broker_name: str, broker_phone: str) -> dict:
    """Find/create society → find/create config → insert quote. Returns quote info dict."""
    society = find_or_create_society(society_name)
    config = find_or_create_config(society["id"], listing["config"], listing.get("area_sqft"))
    quote = insert_quote(
        config_id=config["id"],
        broker_name=broker_name,
        broker_phone=broker_phone,
        price_lakh=listing.get("price_lakh"),
        floor=listing.get("floor"),
        facing=listing.get("facing"),
        notes=listing.get("notes"),
    )
    logger.info("[DB] Saved → '%s' / '%s'", society["name"], listing["config"])
    return {
        "quote_id": quote["id"],
        "short_id": quote["id"][:4].upper(),
        "society_name": society["name"],
        "config_type": listing["config"],
    }


# ── Queries (for /list and /status) ──────────────────────

def get_all_societies() -> list[dict]:
    return (
        get_db()
        .table("societies")
        .select("*, society_status(status)")
        .order("created_at", desc=True)
        .execute()
        .data
    )


def get_society_detail(name: str) -> dict | None:
    society = find_society(name)
    if not society:
        return None
    db = get_db()
    configs = db.table("configurations").select("*").eq("society_id", society["id"]).execute().data
    config_ids = [c["id"] for c in configs]
    quotes = []
    if config_ids:
        quotes = (
            db.table("broker_quotes").select("*")
            .in_("config_id", config_ids)
            .order("added_on", desc=True)
            .execute().data
        )
    return {"society": society, "configs": configs, "quotes": quotes}


# ── Property Media ───────────────────────────────────

def save_property_media(quote_id: str, media_type: str, public_url: str,
                        storage_path: str, telegram_file_id: str | None,
                        telegram_file_unique_id: str | None, caption: str | None,
                        uploaded_by: int | None) -> dict:
    """Insert a media row linked to a broker quote."""
    row = {
        "quote_id": quote_id,
        "media_type": media_type,
        "public_url": public_url,
        "storage_path": storage_path,
    }
    if telegram_file_id:
        row["telegram_file_id"] = telegram_file_id
    if telegram_file_unique_id:
        row["telegram_file_unique_id"] = telegram_file_unique_id
    if caption:
        row["caption"] = caption
    if uploaded_by:
        row["uploaded_by"] = uploaded_by
    media = get_db().table("property_media").insert(row).execute().data[0]
    logger.info("[DB] Saved media → quote=%s | type=%s", quote_id[:8], media_type)
    return media


# ── Quote Operations (for /summary, /edit, /add) ────

def get_recent_quotes(limit: int = 20) -> list[dict]:
    """Fetch recent quotes with nested society name and config type."""
    return (
        get_db()
        .table("broker_quotes")
        .select("id, broker_name, price_lakh, floor, facing, added_on, "
                "configurations(type, area_sqft, societies(name))")
        .order("added_on", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def find_quote_by_short_id(short_id: str) -> list[dict]:
    """Find quotes whose UUID starts with the given prefix (case-insensitive)."""
    short_id = short_id.lower().strip()
    # Fetch recent quotes and filter by prefix in Python (fine for personal use)
    res = (
        get_db()
        .table("broker_quotes")
        .select("id, broker_name, broker_phone, price_lakh, floor, facing, "
                "notes, availability, config_id, added_on")
        .order("added_on", desc=True)
        .limit(100)
        .execute()
    )
    return [q for q in res.data if q["id"].startswith(short_id)]


def update_quote_fields(quote_id: str, updates: dict) -> None:
    """Update specific fields on a broker quote."""
    get_db().table("broker_quotes").update(updates).eq("id", quote_id).execute()
    logger.info("[DB] Updated quote %s: %s", quote_id[:8], updates)
