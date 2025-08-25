import os
import threading
from flask import Flask
from telegram.ext import Application, CommandHandler

# --- Flask Setup ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

# --- Telegram Bot Setup ---
TOKEN = os.getenv("BOT_TOKEN")   # must be set in Render Environment Variables

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing. Set it in Render → Environment Variables.")
TOKEN = TOKEN.strip()

print(f"✅ BOT_TOKEN loaded (starts with: {TOKEN[:8]}...)")  # log check

application = Application.builder().token(TOKEN).build()

# Example handler
async def start(update, context):
    await update.message.reply_text("Hello! I am alive 🚀")
application.add_handler(CommandHandler("start", start))

# --- Run Telegram Bot in Background ---
def run_bot():
    application.run_polling()

# --- Entry Point ---
if __name__ == "__main__":
    # Start Telegram bot in background thread
    threading.Thread(target=run_bot, daemon=True).start()

    # Run Flask (important: must use PORT from Render)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
