import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import ALLOWED_USER_ID, TELEGRAM_BOT_TOKEN
from db import get_all_societies, get_all_society_names, get_society_detail, save_listing
from extractor import extract_listings

logging.basicConfig(
    format="%(asctime)s | %(name)-18s | %(levelname)-7s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Application").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Updater").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.ExtBot").setLevel(logging.WARNING)


def _authorized(update: Update) -> bool:
    return update.effective_user is not None and update.effective_user.id == ALLOWED_USER_ID


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    await update.message.reply_text(
        "House Hunt Bot\n\n"
        "Send one message with broker name, phone, society, and listings.\n\n"
        "/list -- all saved societies\n"
        "/status Society Name -- quotes for a society",
    )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            lines.append(f"  {q.get('broker_name','?')} | {p} | {q.get('floor') or '--'} fl | {q.get('facing') or '--'}")
        lines.append("")
    await update.message.reply_text("\n".join(lines))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    saved = 0
    for listing in listings:
        try:
            save_listing(society_name, listing, broker_name, broker_phone)
            saved += 1
        except Exception as exc:
            logger.error("[MSG] Save failed for listing: %s", exc)

    # Build confirmation
    lines = [f"Saved {saved}/{len(listings)} listing(s)", f"Society: {society_name}", f"Broker: {broker_name} ({broker_phone})", ""]
    for li in listings:
        parts = [li.get("config", "?")]
        if li.get("area_sqft"):
            parts.append(f"{li['area_sqft']}sqft")
        if li.get("price_lakh") is not None:
            parts.append(f"Rs{li['price_lakh']}L")
        if li.get("floor"):
            parts.append(f"Floor {li['floor']}")
        lines.append("- " + " | ".join(parts))

    await update.message.reply_text("\n".join(lines))


async def _post_init(app: Application) -> None:
    logger.info("Bot is online and listening.")
    try:
        await app.bot.send_message(ALLOWED_USER_ID, "Bot is online and listening.")
    except Exception as exc:
        logger.warning("Could not send startup message: %s", exc)


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(_post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
