"""
Kamalim kanal boti — kunlik AI post generatsiyasi va admin tasdiqlash oqimi.

Ish jarayoni:
1. Har kuni 11:58 (Asia/Tashkent) da bot post generatsiya qiladi
   (Gemini + Google Search grounding orqali matn, Gemini image model orqali rasm)
2. Admin'ga (ADMIN_CHAT_ID) rasm + caption + "Qabul qilish"/"Qaytadan" tugmalari bilan yuboradi
3. "Qabul qilish" bosilsa -> kanalga yuboriladi
4. "Qaytadan" bosilsa -> yangi post generatsiya qilib, yana o'sha tugmalar bilan yuboriladi
5. 2 daqiqa ichida javob bo'lmasa -> avtomatik kanalga yuboriladi (12:00 da)
"""

import asyncio
import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from content import generate_post

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@sadaf_media_1")
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Tashkent")
APPROVAL_WINDOW_SECONDS = int(os.environ.get("APPROVAL_WINDOW_SECONDS", "120"))
POST_HOUR = int(os.environ.get("POST_HOUR", "11"))
POST_MINUTE = int(os.environ.get("POST_MINUTE", "58"))

ACCEPT_CB = "accept_post"
REGEN_CB = "regen_post"

APPROVAL_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("✅ Qabul qilish", callback_data=ACCEPT_CB),
            InlineKeyboardButton("🔄 Qaytadan", callback_data=REGEN_CB),
        ]
    ]
)


@dataclass
class PendingPost:
    """Hozirgi tasdiqlanishi kutilayotgan post holati."""

    topic: str
    caption: str
    image_bytes: bytes
    photo_message_id: Optional[int] = None
    text_message_id: Optional[int] = None
    decided: bool = False
    timeout_task: Optional[asyncio.Task] = field(default=None, repr=False)


# Global holat — bir vaqtda faqat bitta pending post bo'ladi
pending: Optional[PendingPost] = None


async def build_and_send_draft(app: Application) -> None:
    """Yangi post generatsiya qilib, adminga tasdiqlash uchun yuboradi."""
    global pending

    # eski timeout task bo'lsa, bekor qilamiz
    if pending and pending.timeout_task and not pending.timeout_task.done():
        pending.timeout_task.cancel()

    logger.info("Generatsiya boshlandi...")
    topic, caption, image_bytes = await generate_post()

    photo_msg = await app.bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=image_bytes,
    )
    text_msg = await app.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=caption,
        reply_to_message_id=photo_msg.message_id,
        reply_markup=APPROVAL_KEYBOARD,
        parse_mode=ParseMode.HTML,
    )

    pending = PendingPost(
        topic=topic,
        caption=caption,
        image_bytes=image_bytes,
        photo_message_id=photo_msg.message_id,
        text_message_id=text_msg.message_id,
    )
    pending.timeout_task = asyncio.create_task(auto_publish_after_timeout(app))
    logger.info("Draft admin'ga yuborildi. Mavzu: %s", topic)


async def auto_publish_after_timeout(app: Application) -> None:
    """2 daqiqa ichida javob bo'lmasa, postni avtomatik kanalga yuboradi."""
    try:
        await asyncio.sleep(APPROVAL_WINDOW_SECONDS)
    except asyncio.CancelledError:
        return

    if pending and not pending.decided:
        logger.info("2 daqiqa javobsiz o'tdi — avtomatik yuborilmoqda.")
        await publish_to_channel(app)


async def publish_to_channel(app: Application) -> None:
    """Joriy pending postni kanalga yuboradi."""
    global pending
    if not pending or pending.decided:
        return
    pending.decided = True

    await app.bot.send_photo(
        chat_id=CHANNEL_USERNAME,
        photo=pending.image_bytes,
        caption=pending.caption[:1024],
        parse_mode=ParseMode.HTML,
    )
    # Agar caption 1024 belgidan uzun bo'lsa, qolgan qismini alohida xabar sifatida yuboramiz
    if len(pending.caption) > 1024:
        await app.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=pending.caption[1024:],
            parse_mode=ParseMode.HTML,
        )

    await app.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text="✅ Post kanalga yuborildi.",
        reply_to_message_id=pending.text_message_id,
    )
    pending = None


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global pending
    query = update.callback_query
    await query.answer()

    if not pending or pending.decided:
        await query.edit_message_reply_markup(reply_markup=None)
        return

    if query.data == ACCEPT_CB:
        pending.decided = True
        if pending.timeout_task:
            pending.timeout_task.cancel()
        await query.edit_message_reply_markup(reply_markup=None)
        # decided=True qilib qo'yildi, publish_to_channel ichida yana True qilinadi — muammo yo'q
        pending.decided = False
        await publish_to_channel(context.application)

    elif query.data == REGEN_CB:
        if pending.timeout_task:
            pending.timeout_task.cancel()
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text="🔄 Yangi post generatsiya qilinmoqda...",
        )
        await build_and_send_draft(context.application)


async def cmd_generate_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/generate — qo'lda darhol yangi draft yaratish (test uchun)."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    await update.message.reply_text("Generatsiya boshlanmoqda...")
    await build_and_send_draft(context.application)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Kamalim kanal boti ishlayapti.\n"
        f"Har kuni {POST_HOUR:02d}:{POST_MINUTE:02d} da yangi post tayyorlanadi.\n"
        "Qo'lda test qilish uchun: /generate"
    )


def schedule_daily_job(app: Application) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        lambda: asyncio.create_task(build_and_send_draft(app)),
        "cron",
        hour=POST_HOUR,
        minute=POST_MINUTE,
    )
    scheduler.start()
    return scheduler


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("generate", cmd_generate_now))
    app.add_handler(CallbackQueryHandler(on_callback))

    schedule_daily_job(app)

    logger.info("Bot ishga tushdi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
