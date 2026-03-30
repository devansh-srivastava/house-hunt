import io
import logging
import time

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import ALLOWED_USER_ID, TELEGRAM_BOT_TOKEN, MEDIA_UPLOADS_ENABLED, COMPRESS_MEDIA
from db import (
    find_quote_by_short_id,
    get_all_societies,
    get_all_society_names,
    get_recent_quotes,
    get_society_detail,
    save_listing,
    save_property_media,
    update_quote_fields,
)
from compress import compress_image, compress_video
from extractor import extract_listings
from storage_supabase import upload_media

logging.basicConfig(
    format="%(asctime)s | %(name)-18s | %(levelname)-7s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Application").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Updater").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.ExtBot").setLevel(logging.WARNING)

USAGE_TEXT = (
    "House Hunt Bot\n\n"
    "Send a message with broker name, phone, society, and listings.\n\n"
    "/start or /help - usage instructions\n"
    "/summary - recent quotes with IDs\n"
    "/add <id> - set active quote for media (20 min)\n"
    "/edit <id> field=value - update a quote\n"
    "/list - all saved societies\n"
    "/status Society - quotes for a society"
)

# Active quote context per user (in-memory, 20-minute TTL)
ACTIVE_QUOTE_CONTEXT: dict[int, dict] = {}
CONTEXT_TTL_SECONDS = 20 * 60


def set_active_quote(user_id: int, quote_id: str) -> dict:
    """Set active quote context for media uploads."""
    ctx = {
        "quote_id": quote_id,
        "short_id": quote_id[:4].upper(),
        "expires_at": time.time() + CONTEXT_TTL_SECONDS,
    }
    ACTIVE_QUOTE_CONTEXT[user_id] = ctx
    return ctx


def get_active_quote(user_id: int) -> dict | None:
    """Return active quote context, removing it if expired."""
    ctx = ACTIVE_QUOTE_CONTEXT.get(user_id)
    if not ctx:
        return None
    if time.time() > ctx["expires_at"]:
        del ACTIVE_QUOTE_CONTEXT[user_id]
        return None
    return ctx


def _authorized(update: Update) -> bool:
    return update.effective_user is not None and update.effective_user.id == ALLOWED_USER_ID


async def cmd_start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    await update.message.reply_text(USAGE_TEXT)


async def cmd_list(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    societies = get_all_societies()
    if not societies:
        await update.message.reply_text("No societies saved yet.")
        return

    lines = ["Saved Societies:\n"]
    for s in societies:
        status_info = s.get("society_status")
        status = "New"
        if isinstance(status_info, list) and status_info:
            status = status_info[0].get("status", "New")
        elif isinstance(status_info, dict):
            status = status_info.get("status", "New")
        lines.append(f"- {s['name']} [{status}]")
    await update.message.reply_text("\n".join(lines))


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    name = " ".join(context.args) if context.args else ""
    if not name:
        await update.message.reply_text("Usage: /status Society Name")
        return

    detail = get_society_detail(name)
    if not detail:
        await update.message.reply_text(f'No society found matching "{name}".')
        return

    society = detail["society"]
    configs = detail["configs"]
    quotes = detail["quotes"]
    lines = [f"{society['name']}\n"]

    quotes_by_config: dict[str, list[dict]] = {}
    for q in quotes:
        quotes_by_config.setdefault(q["config_id"], []).append(q)

    for cfg in configs:
        lines.append(f"-- {cfg['type']} ({cfg.get('area_sqft') or '?'} sqft) --")
        cfg_quotes = quotes_by_config.get(cfg["id"], [])
        if not cfg_quotes:
            lines.append("  No quotes yet.")
        for q in cfg_quotes:
            p = f"Rs{q['price_lakh']}L" if q.get("price_lakh") is not None else "--"
            lines.append(
                f"  {q.get('broker_name', '?')} | {p} | {q.get('floor') or '--'} fl | {q.get('facing') or '--'}"
            )
        lines.append("")
    await update.message.reply_text("\n".join(lines))


async def on_text(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    await update.message.reply_text("Processing with Gemini...")

    try:
        existing = get_all_society_names()
        result = await extract_listings(text, existing)
    except Exception as exc:
        logger.error("[MSG] Extraction failed: %s", exc)
        await update.message.reply_text(f"Extraction failed: {exc}")
        return

    broker_name = result.get("broker_name")
    broker_phone = result.get("broker_phone")
    society_name = result.get("society_name")
    listings = result.get("listings", [])

    if not broker_name or not society_name or not listings:
        await update.message.reply_text("Could not extract broker/society/listings from that message.")
        return

    saved_quotes = []
    for listing in listings:
        try:
            saved_quotes.append(save_listing(society_name, listing, broker_name, broker_phone))
        except Exception as exc:
            logger.error("[MSG] Save failed for listing: %s", exc)

    saved = len(saved_quotes)

    lines = [
        f"Saved {saved}/{len(listings)} listing(s)",
        f"Society: {society_name}",
        f"Broker: {broker_name} ({broker_phone})",
        "",
    ]

    for i, li in enumerate(listings):
        parts = [li.get("config", "?")]
        if li.get("area_sqft"):
            parts.append(f"{li['area_sqft']}sqft")
        if li.get("price_lakh") is not None:
            parts.append(f"Rs{li['price_lakh']}L")
        if li.get("floor"):
            parts.append(f"Floor {li['floor']}")
        if i < len(saved_quotes):
            parts.append(f"[{saved_quotes[i]['short_id']}]")
        lines.append("- " + " | ".join(parts))

    # Keep the most recently saved quote active for quick media uploads.
    if saved_quotes:
        ctx = set_active_quote(update.effective_user.id, saved_quotes[-1]["quote_id"])
        lines.append(f"\nActive: {ctx['short_id']} - send photos/videos to attach")

    await update.message.reply_text("\n".join(lines))


async def cmd_summary(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    quotes = get_recent_quotes(limit=20)
    if not quotes:
        await update.message.reply_text("No quotes saved yet.")
        return

    lines = ["Recent Quotes:\n"]
    for q in quotes:
        short_id = q["id"][:4].upper()
        cfg = q.get("configurations") or {}
        soc = cfg.get("societies") or {}
        parts = [
            short_id,
            soc.get("name", "?"),
            cfg.get("type", "?"),
            f"{cfg['area_sqft']}sqft" if cfg.get("area_sqft") else None,
            f"Rs{q['price_lakh']}L" if q.get("price_lakh") else None,
            q.get("broker_name", "?"),
            q["added_on"][:10] if q.get("added_on") else None,
        ]
        lines.append(" | ".join(p for p in parts if p))

    active = get_active_quote(update.effective_user.id)
    if active:
        lines.append(f"\nActive: {active['short_id']}")

    await update.message.reply_text("\n".join(lines))


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage: /add <quote_id>\n"
            "Sets active quote for media uploads (20 min).\n"
            "Run /summary to see quote IDs."
        )
        return

    short_id = args[0]
    matches = find_quote_by_short_id(short_id)
    if not matches:
        await update.message.reply_text(f"No quote found matching '{short_id}'.")
        return
    if len(matches) > 1:
        ids = ", ".join(m["id"][:4].upper() for m in matches)
        await update.message.reply_text(f"Multiple matches: {ids}\nUse a longer ID.")
        return

    ctx = set_active_quote(update.effective_user.id, matches[0]["id"])
    await update.message.reply_text(
        f"Active quote: {ctx['short_id']}\n"
        "Send photos/videos now - they will attach to this quote for 20 min."
    )


EDITABLE_FIELDS = {
    "price_lakh",
    "floor",
    "facing",
    "notes",
    "availability",
    "broker_name",
    "broker_phone",
}


async def cmd_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    args = context.args or []
    if len(args) < 2:
        fields = ", ".join(sorted(EDITABLE_FIELDS))
        await update.message.reply_text(f"Usage: /edit <quote_id> field=value ...\n\nFields: {fields}")
        return

    short_id = args[0]

    updates = {}
    for arg in args[1:]:
        if "=" not in arg:
            await update.message.reply_text(f"Invalid format: '{arg}'. Use field=value.")
            return

        field, value = arg.split("=", 1)
        if field not in EDITABLE_FIELDS:
            await update.message.reply_text(
                f"Unknown field '{field}'.\nAllowed: {', '.join(sorted(EDITABLE_FIELDS))}"
            )
            return

        if field == "price_lakh":
            try:
                value = float(value)
            except ValueError:
                await update.message.reply_text(f"Invalid number for price_lakh: {value}")
                return

        updates[field] = value

    matches = find_quote_by_short_id(short_id)
    if not matches:
        await update.message.reply_text(f"No quote found matching '{short_id}'.")
        return
    if len(matches) > 1:
        ids = ", ".join(m["id"][:4].upper() for m in matches)
        await update.message.reply_text(f"Multiple matches: {ids}\nUse a longer ID.")
        return

    update_quote_fields(matches[0]["id"], updates)
    changes = ", ".join(f"{k}={v}" for k, v in updates.items())
    await update.message.reply_text(f"Updated {matches[0]['id'][:4].upper()}: {changes}")


async def on_media(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return

    if not MEDIA_UPLOADS_ENABLED:
        await update.message.reply_text("Media uploads not configured. Set SUPABASE_MEDIA_BUCKET in .env.")
        return

    active = get_active_quote(update.effective_user.id)
    if not active:
        await update.message.reply_text(
            "No active quote. Send property details first,\n"
            "or use /summary then /add <quote_id>."
        )
        return

    if update.message.photo:
        media_type = "image"
        file_obj = update.message.photo[-1]
        ext = "jpg"
        content_type = "image/jpeg"
    elif update.message.video:
        media_type = "video"
        file_obj = update.message.video
        ext = "mp4"
        content_type = file_obj.mime_type or "video/mp4"
    else:
        return

    caption = update.message.caption or None

    # Telegram Bot API hard limit: bots can only download files ≤ 20 MB.
    # Compression happens after download, so oversized files must be rejected here.
    TG_DOWNLOAD_LIMIT = 20 * 1024 * 1024  # 20 MB in bytes
    file_size = getattr(file_obj, "file_size", None)
    if file_size and file_size > TG_DOWNLOAD_LIMIT:
        size_mb = file_size / (1024 * 1024)
        logger.warning("[MEDIA] File too large for Bot API download: %.1f MB", size_mb)
        await update.message.reply_text(
            f"File is {size_mb:.1f} MB — Telegram Bot API only allows downloading files up to 20 MB.\n"
            f"Please compress it before sending (e.g. re-encode the video to a smaller size)."
        )
        return

    await update.message.reply_text(f"Uploading {media_type}...")

    try:
        tg_file = await file_obj.get_file()
        buf = io.BytesIO()
        await tg_file.download_to_memory(out=buf)
        buf.seek(0)
        file_bytes = buf.read()
    except Exception as exc:
        logger.error("[MEDIA] Telegram download failed: %s", exc)
        await update.message.reply_text(f"Download failed: {exc}")
        return

    # ── Compress before uploading ──
    original_kb = len(file_bytes) // 1024
    if COMPRESS_MEDIA:
        if media_type == "image":
            file_bytes, content_type = compress_image(file_bytes)
            ext = "jpg"  # compressed output is always JPEG
        elif media_type == "video":
            file_bytes, content_type = compress_video(file_bytes)
        compressed_kb = len(file_bytes) // 1024
        if compressed_kb < original_kb:
            await update.message.reply_text(
                f"Compressed: {original_kb} KB → {compressed_kb} KB"
            )

    ts = int(time.time())
    unique_id = getattr(file_obj, "file_unique_id", str(ts))
    storage_path = f"quotes/{active['quote_id']}/{ts}_{unique_id}.{ext}"

    try:
        public_url = upload_media(file_bytes, storage_path, content_type)
    except Exception as exc:
        logger.error("[MEDIA] Storage upload failed: %s", exc)
        await update.message.reply_text(f"Upload failed: {exc}")
        return

    try:
        save_property_media(
            quote_id=active["quote_id"],
            media_type=media_type,
            public_url=public_url,
            storage_path=storage_path,
            telegram_file_id=file_obj.file_id,
            telegram_file_unique_id=file_obj.file_unique_id,
            caption=caption,
            uploaded_by=update.effective_user.id,
        )
    except Exception as exc:
        logger.error("[MEDIA] DB save failed: %s", exc)
        await update.message.reply_text(f"Uploaded to Storage but DB save failed: {exc}")
        return

    await update.message.reply_text(f"{media_type.title()} saved for quote {active['short_id']}")


async def _post_init(app: Application) -> None:
    logger.info("Bot is online and listening.")
    try:
        await app.bot.send_message(
            ALLOWED_USER_ID,
            "Bot is online and listening. Send /start or /help for instructions.",
        )
    except Exception as exc:
        logger.warning("Could not send startup message: %s", exc)


def main() -> None:
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(_post_init)
        .read_timeout(60)    # large media downloads can take a while
        .write_timeout(60)   # large media uploads to Telegram reply can too
        .connect_timeout(15)
        .build()
    )
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("edit", cmd_edit))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, on_media))
    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
