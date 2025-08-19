
from telegram import Update
from telegram.ext import ContextTypes

# Simple in-memory storage (replace with DB in production)
users = {}
referrals = {}

async def start_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args  # /start ref12345 → args = ["ref12345"]

    if user_id not in users:
        users[user_id] = {"points": 0, "referrer": None}

        # Check if user came via referral
        if args and args[0].startswith("ref"):
            referrer_id = int(args[0].replace("ref", ""))

            if referrer_id != user_id and referrer_id in users:
                users[user_id]["referrer"] = referrer_id
                referrals.setdefault(referrer_id, []).append(user_id)
                users[referrer_id]["points"] += 10  # reward

                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 Congrats! You referred {update.effective_user.first_name} and earned 10 SkillPoints!"
                )

    await update.message.reply_text(
        "👋 Welcome! You can now use the bot.\n\n"
        "Your first match is free. After that, invite friends to unlock more features!"
    )


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = f"https://t.me/{context.bot.username}?start=ref{user_id}"
    await update.message.reply_text(
        f"🚀 Invite friends and earn rewards!\n"
        f"Here's your link: {link}\n\n"
        f"✅ 1 friend = +10 SkillPoints\n"
        f"✅ 3 friends = Unlock Unlimited Matches\n"
        f"✅ 5 friends = Mentor Badge 🏅"
    )


async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    points = users.get(user_id, {}).get("points", 0)
    await update.message.reply_text(f"💰 You have {points} SkillPoints.")


async def rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏆 Rewards:\n\n"
        "✅ 1 friend = +10 SkillPoints\n"
        "✅ 3 friends = Unlock Unlimited Matches\n"
        "✅ 5 friends = Mentor Badge 🏅"
    )
