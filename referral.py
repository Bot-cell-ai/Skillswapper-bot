from telegram import Bot
import re

# Escape text for MarkdownV2 safely
def escape_markdown(text: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

# Function to send referral reminder
async def send_referral_reminder(bot: Bot, chat_id: int, bot_username: str):
    try:
        referral_link = f"https://t.me/{bot_username}?start={chat_id}"

        # Escape everything for MarkdownV2
        message = (
            "✨ Your conversations matter ✨\n\n"
            "💬 If you enjoy using SkillSwapper, why keep it to yourself?\n\n"
            "👉 Share this link with friends who would love to learn or teach skills:\n"
            f"{referral_link}\n\n"
            "🚀 The more friends join, the bigger our community becomes"
        )

        safe_message = escape_markdown(message)

        await bot.send_message(
            chat_id=chat_id,
            text=safe_message,
            parse_mode="MarkdownV2"  # Safe formatting
        )
    except Exception as e:
        print(f"Error sending referral reminder: {e}")