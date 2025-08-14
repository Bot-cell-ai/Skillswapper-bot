# main.py
import threading
import logging
from web import start_web
from chat_manager import start_cleanup_thread
from main_bot import main as run_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # 1) start Flask web server in a background thread
    t_web = threading.Thread(target=start_web, kwargs={"host": "0.0.0.0", "port": 5000}, daemon=True)
    t_web.start()
    logger.info("Web server started on http://0.0.0.0:5000")

    # 2) start Firebase cleanup thread (removes expired chats)
    start_cleanup_thread()

    # 3) run Telegram bot (blocking)
    run_bot()