# web.py
import os
import json
from flask import Flask, request, Response

app = Flask(__name__)

# Load client config once from secret
CLIENT_CONFIG = json.loads(os.environ["FIREBASE_CLIENT_CONFIG_JSON"])

CHAT_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>SkillSwapper Chat</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    body { font-family: Arial, sans-serif; margin: 12px; }
    #chat-box { border:1px solid #ddd; height:60vh; overflow:auto; padding:8px; }
    #message-row { margin-top:8px; display:flex; gap:8px; }
    #msg { flex:1; padding:8px; }
    #ad-top, #ad-bottom { border:1px dashed #aaa; padding:8px; margin:8px 0; text-align:center; }
  </style>
</head>
<body>
  <div id="ad-top">
    <!-- Put your ad code later (e.g., AdSense) -->
    <em>Ad slot</em>
  </div>

  <h3>Chat Room</h3>
  <div id="room-info"></div>
  <div id="chat-box"></div>

  <div id="message-row">
    <input id="msg" type="text" placeholder="Type a message" />
    <button id="sendBtn">Send</button>
  </div>

  <div id="ad-bottom">
    <em>Ad slot</em>
  </div>

  <script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-app-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-database-compat.js"></script>
  <script>
    const FIREBASE_CONFIG = %CLIENT_CONFIG%;
    firebase.initializeApp(FIREBASE_CONFIG);
    const db = firebase.database();

    function qp(name) { return new URLSearchParams(window.location.search).get(name); }

    const roomId = qp('room');
    const me = qp('me') || 'User';
    const box = document.getElementById('chat-box');
    const info = document.getElementById('room-info');
    const input = document.getElementById('msg');
    const sendBtn = document.getElementById('sendBtn');

    if (!roomId) {
      info.innerHTML = "<strong>No room specified.</strong>";
      input.disabled = true; sendBtn.disabled = true;
    } else {
      info.textContent = "Room: " + roomId;

      // check room and expiration
      db.ref('chats/' + roomId).once('value', snap => {
        if (!snap.exists()) {
          box.innerHTML = "<p><strong>This chat has expired or does not exist.</strong></p>";
          input.disabled = true; sendBtn.disabled = true;
          return;
        }
        const data = snap.val();
        if (data.expires_at && Date.now() > new Date(data.expires_at).getTime()) {
          box.innerHTML = "<p><strong>This chat has expired.</strong></p>";
          input.disabled = true; sendBtn.disabled = true;
          return;
        }
      });

      // listen for messages
      db.ref('chats/' + roomId + '/messages').on('child_added', snap => {
        const m = snap.val();
        if (!m) return;
        const div = document.createElement('div');
        const ts = new Date(m.time).toLocaleString();
        div.textContent = `[${ts}] ${m.sender || 'User'}: ${m.text}`;
        box.appendChild(div);
        box.scrollTop = box.scrollHeight;
      });

      // send
      sendBtn.onclick = () => {
        const text = input.value.trim();
        if (!text) return;
        const msgRef = db.ref('chats/' + roomId + '/messages').push();
        msgRef.set({ text, time: Date.now(), sender: me });
        input.value = "";
      };

      input.onkeyup = (e) => { if (e.key === 'Enter') sendBtn.click(); };
    }
  </script>
</body>
</html>
"""

@app.route("/chat")
def chat_page():
    html = CHAT_HTML.replace("%CLIENT_CONFIG%", json.dumps(CLIENT_CONFIG))
    return Response(html, mimetype="text/html")

def start_web(host="0.0.0.0", port=5000):
    app.run(host=host, port=port)