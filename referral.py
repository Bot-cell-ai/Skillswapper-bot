
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

DB_FILE = "referrals.db"

def db_connect():
    """Connect to SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        referrer_id INTEGER,
        referred_count INTEGER DEFAULT 0,
        first_use_done INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create referrals table
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (referrer_id) REFERENCES users (user_id),
        FOREIGN KEY (referred_id) REFERENCES users (user_id)
    )''')
    
    conn.commit()
    return conn

def get_or_create_user(user_id, username=None, first_name=None, referrer_id=None):
    """Get user from database or create if doesn't exist."""
    conn = db_connect()
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    
    if not user:
        c.execute("""INSERT INTO users (user_id, username, first_name, referrer_id) 
                     VALUES (?, ?, ?, ?)""", (user_id, username, first_name, referrer_id))
        conn.commit()
        
        # If they were referred, update referrer's count
        if referrer_id:
            c.execute("UPDATE users SET referred_count = referred_count + 1 WHERE user_id=?", (referrer_id,))
            c.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user_id))
            conn.commit()
    
    conn.close()

def can_user_use_bot(user_id):
    """Check if user can use the bot (either first time or has referrals)."""
    conn = db_connect()
    c = conn.cursor()
    
    c.execute("SELECT first_use_done, referred_count FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return True  # First time user
    
    first_use_done, referred_count = result
    
    if first_use_done == 0:
        return True  # Haven't used their free trial yet
    
    return referred_count > 0  # Can use if they have referrals

async def start_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle referral logic when user starts the bot."""
    user = update.effective_user
    user_id = user.id
    
    # Check if this is a referral link
    referrer_id = None
    if context.args and len(context.args) > 0:
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            pass
    
    # Create or get user
    get_or_create_user(user_id, user.username, user.first_name, referrer_id)
    
    # If they were referred, notify both users
    if referrer_id:
        try:
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"🎉 Great! {user.first_name or 'Someone'} joined using your referral link!\n"
                     f"You can now use the bot again. Use /points to see your progress."
            )
        except Exception:
            pass  # Referrer might have blocked the bot

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send referral link."""
    user_id = update.effective_user.id
    bot_username = context.bot.username
    
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    await update.message.reply_text(
        f"🔗 Your referral link:\n{referral_link}\n\n"
        f"Share this with friends to unlock more uses of the bot!\n"
        f"Each friend that joins gives you another use."
    )

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's referral stats."""
    user_id = update.effective_user.id
    
    conn = db_connect()
    c = conn.cursor()
    
    c.execute("SELECT referred_count, first_use_done FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        await update.message.reply_text("You haven't started using the bot yet. Use /start to begin!")
        return
    
    referred_count, first_use_done = result
    
    status = "Used" if first_use_done else "Available"
    
    await update.message.reply_text(
        f"📊 Your Stats:\n\n"
        f"👥 Friends referred: {referred_count}\n"
        f"🎫 Free trial: {status}\n"
        f"✅ Bot uses available: {'Yes' if can_user_use_bot(user_id) else 'No'}\n\n"
        f"💡 Each referral = 1 more use!"
    )

async def rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show rewards/achievements."""
    user_id = update.effective_user.id
    
    conn = db_connect()
    c = conn.cursor()
    
    c.execute("SELECT referred_count FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    referred_count = result[0] if result else 0
    
    rewards_text = "🏆 Rewards & Achievements:\n\n"
    
    # Basic rewards
    if referred_count >= 1:
        rewards_text += "✅ First Referral - Bot access unlocked!\n"
    else:
        rewards_text += "❌ First Referral - Invite 1 friend\n"
    
    if referred_count >= 5:
        rewards_text += "✅ Social Butterfly - 5 referrals!\n"
    else:
        rewards_text += f"❌ Social Butterfly - {referred_count}/5 referrals\n"
    
    if referred_count >= 10:
        rewards_text += "✅ Community Builder - 10 referrals!\n"
    else:
        rewards_text += f"❌ Community Builder - {referred_count}/10 referrals\n"
    
    rewards_text += f"\n💡 You have {referred_count} bot uses from referrals"
    
    await update.message.reply_text(rewards_text)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show referral menu with buttons."""
    keyboard = [
        [InlineKeyboardButton("🔗 Get Invite Link", callback_data="menu_invite")],
        [InlineKeyboardButton("📊 Check Points", callback_data="menu_points")],
        [InlineKeyboardButton("🏆 View Rewards", callback_data="menu_rewards")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 Referral Menu:\n\n"
        "Choose an option below to manage your referrals and check your progress.",
        reply_markup=reply_markup
    )

async def menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "menu_invite":
        await invite_callback(update, context)
    elif query.data == "menu_points":
        await points_callback(update, context)
    elif query.data == "menu_rewards":
        await rewards_callback(update, context)

async def invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send referral link from callback."""
    user_id = update.effective_user.id
    bot_username = context.bot.username
    
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    await update.callback_query.edit_message_text(
        f"🔗 Your referral link:\n{referral_link}\n\n"
        f"Share this with friends to unlock more uses of the bot!\n"
        f"Each friend that joins gives you another use."
    )

async def points_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's referral stats from callback."""
    user_id = update.effective_user.id
    
    conn = db_connect()
    c = conn.cursor()
    
    c.execute("SELECT referred_count, first_use_done FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        await update.callback_query.edit_message_text("You haven't started using the bot yet. Use /start to begin!")
        return
    
    referred_count, first_use_done = result
    
    status = "Used" if first_use_done else "Available"
    
    await update.callback_query.edit_message_text(
        f"📊 Your Stats:\n\n"
        f"👥 Friends referred: {referred_count}\n"
        f"🎫 Free trial: {status}\n"
        f"✅ Bot uses available: {'Yes' if can_user_use_bot(user_id) else 'No'}\n\n"
        f"💡 Each referral = 1 more use!"
    )

async def rewards_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show rewards/achievements from callback."""
    user_id = update.effective_user.id
    
    conn = db_connect()
    c = conn.cursor()
    
    c.execute("SELECT referred_count FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    referred_count = result[0] if result else 0
    
    rewards_text = "🏆 Rewards & Achievements:\n\n"
    
    # Basic rewards
    if referred_count >= 1:
        rewards_text += "✅ First Referral - Bot access unlocked!\n"
    else:
        rewards_text += "❌ First Referral - Invite 1 friend\n"
    
    if referred_count >= 5:
        rewards_text += "✅ Social Butterfly - 5 referrals!\n"
    else:
        rewards_text += f"❌ Social Butterfly - {referred_count}/5 referrals\n"
    
    if referred_count >= 10:
        rewards_text += "✅ Community Builder - 10 referrals!\n"
    else:
        rewards_text += f"❌ Community Builder - {referred_count}/10 referrals\n"
    
    rewards_text += f"\n💡 You have {referred_count} bot uses from referrals"
    
    await update.callback_query.edit_message_text(rewards_text)

async def complete_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark user's first use as complete (admin/debug command)."""
    user_id = update.effective_user.id
    
    conn = db_connect()
    c = conn.cursor()
    
    c.execute("UPDATE users SET first_use_done=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("✅ First use marked as complete!")
