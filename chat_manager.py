# chat_manager.py
import os
import json
import uuid
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import firebase_admin
from firebase_admin import credentials, db

# ---- init firebase admin ----
if not firebase_admin._apps:
    svc_json = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"])
    cred = credentials.Certificate(svc_json)
    firebase_admin.initialize_app(cred, {
        "databaseURL": os.environ["FIREBASE_DB_URL"]
    })

def _now_utc():
    return datetime.now(timezone.utc)

def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()

def create_chat_room(user_a_id: int, user_b_id: int, user_a_name: str = "", user_b_name: str = ""):
    """
    Creates a chat room in RTDB that expires in 24 hours.
    Returns two full URLs to /chat?room=ROOM_ID with &me=<id>&myName=&peerName= pre-filled,
    and the room_id.
    """
    room_id = uuid.uuid4().hex[:16]
    ref = db.reference(f"chats/{room_id}")
    created = _now_utc()
    expires = created + timedelta(hours=24)

    # Fallback names
    user_a_name = (user_a_name or f"User{user_a_id}").strip()
    user_b_name = (user_b_name or f"User{user_b_id}").strip()

    ref.set({
        "users": {
            str(user_a_id): {"name": user_a_name},
            str(user_b_id): {"name": user_b_name},
        },
        "created_at": _iso(created),
        "expires_at": _iso(expires),
        "messages": {}
    })

    base = os.getenv("WEB_CHAT_BASE", "https://workspace.username.repl.co")
    # each user gets their own link with encoded names
    link_a = (
        f"{base}/chat?room={room_id}"
        f"&me={user_a_id}"
        f"&myName={quote(user_a_name)}"
        f"&peerName={quote(user_b_name)}"
    )
    link_b = (
        f"{base}/chat?room={room_id}"
        f"&me={user_b_id}"
        f"&myName={quote(user_b_name)}"
        f"&peerName={quote(user_a_name)}"
    )
    return link_a, link_b, room_id

def delete_chat_room(room_id: str):
    db.reference(f"chats/{room_id}").delete()

def cleanup_expired_once():
    root = db.reference("chats").get() or {}
    now = _now_utc()
    to_delete = []
    for room_id, data in root.items():
        try:
            exp = datetime.fromisoformat(data.get("expires_at"))
        except Exception:
            continue
        if exp < now:
            to_delete.append(room_id)
    for rid in to_delete:
        db.reference(f"chats/{rid}").delete()

def _cleanup_loop():
    while True:
        try:
            cleanup_expired_once()
        except Exception:
            pass
        time.sleep(600)  # every 10 min

def start_cleanup_thread():
    t = threading.Thread(target=_cleanup_loop, daemon=True)
    t.start()