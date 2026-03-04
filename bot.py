import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, ChatMemberUpdatedFilter, LEFT, KICKED
from aiogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatMemberStatus
from config import BOT_TOKEN, CHANNEL_ID, ADMIN_IDS
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
db = Database()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""

    # Check if banned
    if await db.is_banned(user_id):
        await message.answer(
            "⛔️ Вам закрыт доступ в этот канал.\n\n"
            "Если считаете, что это ошибка — обратитесь к администратору."
        )
        return

    # Check if already in channel
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            await message.answer("✅ Вы уже являетесь участником канала!")
            return
    except Exception:
        pass

    # Generate invite link
    try:
        invite = await bot.create_chat_invite_link(
            CHANNEL_ID,
            member_limit=1,
            name=f"user_{user_id}"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Войти в канал", url=invite.invite_link)]
        ])

        await message.answer(
            f"👋 Привет, {full_name}!\n\n"
            "Нажми кнопку ниже, чтобы войти в канал.\n\n"
            "⚠️ <b>Важно:</b> если ты покинешь канал, вход будет закрыт навсегда.",
            reply_markup=kb,
            parse_mode="HTML"
        )

        # Save user to DB
        await db.add_user(user_id, username, full_name)
        logger.info(f"Invite sent to user {user_id} ({full_name})")

    except Exception as e:
        logger.error(f"Error creating invite for {user_id}: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору.")


@router.chat_member(ChatMemberUpdatedFilter(LEFT | KICKED))
async def user_left_channel(event: ChatMemberUpdated):
    if str(event.chat.id) != str(CHANNEL_ID):
        return

    user = event.new_chat_member.user
    user_id = user.id

    if user_id == (await bot.get_me()).id:
        return

    # Skip if already banned
    if await db.is_banned(user_id):
        return

    # Add to blacklist
    await db.ban_user(user_id, reason="Покинул канал")

    # Ban in channel (so they can't rejoin via other links)
    try:
        await bot.ban_chat_member(CHANNEL_ID, user_id)
        logger.info(f"User {user_id} ({user.full_name}) left and was banned")
    except Exception as e:
        logger.error(f"Failed to ban {user_id}: {e}")

    # Notify user
    try:
        await bot.send_message(
            user_id,
            "⛔️ Вы покинули канал. Повторный вход невозможен.\n\n"
            "Если считаете, что это ошибка — обратитесь к администратору."
        )
    except Exception:
        pass


@router.chat_member()
async def user_joined_channel(event: ChatMemberUpdated):
    """Track when user actually joins the channel"""
    if str(event.chat.id) != str(CHANNEL_ID):
        return

    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status

    if new_status == ChatMemberStatus.MEMBER and old_status not in [
        ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR
    ]:
        user = event.new_chat_member.user
        await db.mark_joined(user.id)
        logger.info(f"User {user.id} ({user.full_name}) joined the channel")


# Admin commands
@router.message(F.text.startswith("/unban "))
async def unban_user(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        user_id = int(message.text.split()[1])
        await db.unban_user(user_id)
        await bot.unban_chat_member(CHANNEL_ID, user_id, only_if_banned=True)
        await message.answer(f"✅ Пользователь {user_id} разбанен. Он может снова получить ссылку через /start.")
    except (IndexError, ValueError):
        await message.answer("Использование: /unban <user_id>")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@router.message(F.text == "/stats")
async def stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    total = await db.count_users()
    banned = await db.count_banned()
    await message.answer(
        f"📊 <b>Статистика канала</b>\n\n"
        f"👥 Всего пользователей: {total}\n"
        f"⛔️ Забанено: {banned}\n"
        f"✅ Активных: {total - banned}",
        parse_mode="HTML"
    )


async def main():
    await db.init()
    dp.include_router(router)

    logger.info("Bot started!")
    await dp.start_polling(bot, allowed_updates=["message", "chat_member"])


if __name__ == "__main__":
    asyncio.run(main())
