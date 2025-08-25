import os
import threading
from flask import Flask
from telegram.ext import Application

# --- Flask Setup ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

# --- Telegram Bot Setup ---
TOKEN = os.getenv("BOT_TOKEN")   # set this in Render environment variables
application = Application.builder().token(TOKEN).build()

# Example handler
from telegram.ext import CommandHandler
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
