# main_bot.py
import os  # NEW
import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

import sheet_manager
import matcher
from chat_manager import create_chat_room  # NEW
from referral import start_referral, invite, points, rewards, menu, menu_buttons, complete_use, can_user_use_bot

# --------------- CONFIG ----------------
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]  # CHANGED: read from secret
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# conversation states
STATE_NAME, STATE_CHOICE, STATE_MAIN_ANSWER, STATE_OPTIONAL = range(4)


# ---------------- helpers ----------------
def _inline_choice_markup():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📘 I want to Learn", callback_data="learn")],
         [InlineKeyboardButton("📗 I want to Teach", callback_data="teach")]])


def _inline_none_back_markup():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("None", callback_data="none")],
         [InlineKeyboardButton("Back", callback_data="back")]])


# --------------- handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Handle referral logic first
    await start_referral(update, context)
    
    # Check if user can use the bot
    if not can_user_use_bot(user_id):
        from referral import get_user_daily_limit, reset_daily_usage
        reset_daily_usage(user_id)
        daily_limit = get_user_daily_limit(user_id)
        
        await update.message.reply_text(
            f"⚠️ You've reached your daily usage limit of {daily_limit} matches!\n"
            f"Invite friends using your referral link to unlock more matches.\n"
            f"Use /menu to see referral options or come back tomorrow."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "👋 Welcome to SkillSwapper!\n\nWhat's your name?")
    return STATE_NAME


async def name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    user = update.message.from_user
    context.user_data.clear()
    context.user_data['user_id'] = user.id
    context.user_data['name'] = name

    await update.message.reply_text("Great — choose an option:",
                                    reply_markup=_inline_choice_markup())
    return STATE_CHOICE


async def choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data  # 'learn' or 'teach'
    context.user_data['choice'] = choice

    if choice == "learn":
        await query.edit_message_text(
            "What skill do you want to *learn*? (type below)")
    else:
        await query.edit_message_text(
            "What skill do you want to *teach*? (type below)")

    return STATE_MAIN_ANSWER


async def main_answer_received(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    choice = context.user_data.get('choice')

    if choice == "learn":
        context.user_data['want'] = text  # they want to learn this
        await update.message.reply_text(
            "Do you want to *teach* any skill in return? (optional)",
            reply_markup=_inline_none_back_markup())
    else:
        context.user_data['skill'] = text  # they offer this
        await update.message.reply_text(
            "Do you want to *learn* any skill in return? (optional)",
            reply_markup=_inline_none_back_markup())

    return STATE_OPTIONAL


async def optional_text_received(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    choice = context.user_data.get('choice')

    if choice == "learn":
        context.user_data['skill'] = text
    else:
        context.user_data['want'] = text

    await update.message.reply_text(
        "✅ Your information is saved.\nSearching for a match — please wait...")
    await _save_and_match(context, reply_target=update.message.chat_id)
    return ConversationHandler.END


async def optional_button_none(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = context.user_data.get('choice')

    if choice == "learn":
        context.user_data['skill'] = ""  # save blank
    else:
        context.user_data['want'] = ""  # save blank

    try:
        await query.edit_message_text(
            "✅ Your information is saved.\nSearching for a match — please wait..."
        )
    except Exception:
        await query.message.reply_text(
            "✅ Your information is saved.\nSearching for a match — please wait..."
        )

    await _save_and_match(context, reply_target=query.message.chat_id)
    return ConversationHandler.END


async def back_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text("Choose an option:",
                                      reply_markup=_inline_choice_markup())
    except Exception:
        await query.message.reply_text("Choose an option:",
                                       reply_markup=_inline_choice_markup())
    return STATE_CHOICE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


# ---------------- save & match ----------------
async def _save_and_match(context: ContextTypes.DEFAULT_TYPE,
                          reply_target: int = None):
    ud = context.user_data
    user_id = ud.get('user_id')
    name = ud.get('name', "")
    skill = ud.get('skill', "") or ""
    want = ud.get('want', "") or ""

    # 1) Save to sheet
    try:
        sheet_manager.save_user_row(user_id, name, skill, want)
    except Exception as e:
        logger.exception("Failed saving to sheet: %s", e)

    # 2) Build new_row dict and look for a match
    new_row = {
        "User ID": str(user_id),
        "Name": name,
        "Skill": skill,
        "Want": want,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    all_rows = sheet_manager.get_all_records()
    matched = matcher.find_one_match(new_row, all_rows)

    chat_id = reply_target or user_id

    if matched:
        matched_user_id = int(matched.get("User ID"))
        matched_name = matched.get("Name", "")
        matched_skill = matched.get("Skill") or "—"
        matched_want = matched.get("Want") or "—"

        # --- NEW: create chat room + links for both users
        try:
            link_a, link_b, room_id = create_chat_room(user_id, matched_user_id)
        except Exception:
            logger.exception("Failed to create chat room")
            link_a = link_b = "Chat temporarily unavailable."

        # notify new user
        try:
            msg_for_new = (f"🎉 Match found!\n\n"
                           f"👤 {matched_name}\n"
                           f"📗 Offers: {matched_skill}\n"
                           f"📘 Wants: {matched_want}\n\n"
                           f"💬 Private chat (24h): {link_a}")
            await context.bot.send_message(chat_id=chat_id, text=msg_for_new)
        except Exception:
            logger.exception("Could not message new user.")

        # notify matched existing user
        try:
            msg_for_matched = (f"🎉 Someone matched with you!\n\n"
                               f"👤 {name}\n"
                               f"📗 Offers: {skill or '—'}\n"
                               f"📘 Wants: {want or '—'}\n\n"
                               f"💬 Private chat (24h): {link_b}")
            await context.bot.send_message(chat_id=matched_user_id,
                                           text=msg_for_matched)
        except Exception:
            logger.exception("Could not message matched user.")

         # --- NEW: delete both users from sheet by skill/want match
        try:
            sheet_manager.delete_matched_pair(new_row)
        except Exception as e:
            logger.exception("Failed to delete users after matching: %s", e)
        
        # Mark user's first use as complete if this was their first match
        try:
            await complete_use_for_user(context, user_id)
        except Exception as e:
            logger.exception("Failed to complete use for user: %s", e)

    else:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="No match found yet. We'll notify you when a match is available."
            )
        except Exception:
            logger.exception("Failed to send 'no match' message.")

    context.user_data.clear()


async def complete_use_for_user(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Helper to mark user's first use as complete and increment daily usage"""
    from referral import db_connect, increment_usage, get_user_daily_limit, has_reached_limit
    
    # Increment daily usage
    increment_usage(user_id)
    
    conn = db_connect()
    c = conn.cursor()
    
    c.execute("SELECT first_use_done FROM users WHERE user_id=?", (user_id,))
    first_use = c.fetchone()
    if first_use and first_use[0] == 0:
        c.execute("UPDATE users SET first_use_done=1 WHERE user_id=?", (user_id,))
        conn.commit()
    
    # Check if they've reached their daily limit
    if has_reached_limit(user_id):
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Your details are saved!\n\n"
                     "⚠️ You've now reached today's usage limit. "
                     "Invite friends to unlock more matches or come back tomorrow.\n"
                     "Use /menu to see referral options."
            )
        except Exception:
            pass
    else:
        daily_limit = get_user_daily_limit(user_id)
        c.execute("SELECT daily_usage FROM users WHERE user_id=?", (user_id,))
        usage_result = c.fetchone()
        daily_usage = usage_result[0] if usage_result else 0
        remaining = daily_limit - daily_usage
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Your details are saved! You'll be matched soon.\n"
                     f"👉 Remaining uses today: {remaining}"
            )
        except Exception:
            pass
    
    conn.close()

# -------------- setup & run -------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STATE_NAME:
            [MessageHandler(filters.TEXT & ~filters.COMMAND, name_received)],
            STATE_CHOICE:
            [CallbackQueryHandler(choice_callback, pattern="^(learn|teach)$")],
            STATE_MAIN_ANSWER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               main_answer_received)
            ],
            STATE_OPTIONAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               optional_text_received),
                CallbackQueryHandler(optional_button_none, pattern="^none$"),
                CallbackQueryHandler(back_button, pattern="^back$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    
    # Add referral system commands
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("rewards", rewards))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("complete_use", complete_use))
    app.add_handler(CallbackQueryHandler(menu_buttons))
    
    logging.getLogger(__name__).info("Bot starting...")
    app.run_polling()
