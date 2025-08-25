import os

# 🚨 Clean environment from wrong packages on Render
os.system("pip uninstall -y telegram")
os.system("pip uninstall -y telegram-bot")
os.system("pip uninstall -y python-telegram-bot")
os.system("pip install python-telegram-bot==20.7 --no-cache-dir")

# Now safe to import PTB
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import telegram
print("🚀 Running with python-telegram-bot version:", telegram.__version__)
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

app = Flask(__name__)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am alive on Render 🚀")

# Message handler (echo)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

# Setup bot
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# Webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    from flask import request
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

# Root route (for Render health check)
@app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
